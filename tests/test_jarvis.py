"""
Tests for Jarvis AI - Core and utility modules.
"""

import os
import sys
import tempfile
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import Config
from utils.logger import setup_logger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_config_file(tmp_path):
    cfg = {
        "app": {"name": "TestJarvis", "log_level": "DEBUG"},
        "ai": {"provider": "ollama", "model": "mistral", "base_url": "http://localhost:11434"},
        "memory": {"max_turns": 10, "persistence": False},
        "database": {"path": str(tmp_path / "test.db")},
        "optimization": {"cache_enabled": True, "cache_ttl": 60},
        "analytics": {"reports_dir": str(tmp_path / "reports")},
        "paths": {"screenshots": str(tmp_path / "screenshots"), "pdfs": str(tmp_path / "pdfs")},
    }
    import yaml
    cfg_path = str(tmp_path / "test_config.yaml")
    with open(cfg_path, "w") as f:
        yaml.dump(cfg, f)
    return cfg_path


@pytest.fixture
def config(temp_config_file):
    return Config(temp_config_file)


@pytest.fixture
def db(config):
    from database.db_manager import DatabaseManager
    db_mgr = DatabaseManager(config)
    db_mgr.initialize()
    return db_mgr


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_load_config(self, config):
        assert config.get("app.name") == "TestJarvis"

    def test_default_value(self, config):
        assert config.get("nonexistent.key", "default") == "default"

    def test_nested_key(self, config):
        assert config.get("ai.provider") == "ollama"

    def test_set_value(self, config):
        config.set("test.key", "value")
        assert config.get("test.key") == "value"

    def test_missing_file(self, tmp_path):
        cfg = Config(str(tmp_path / "nonexistent.yaml"))
        assert cfg.get("anything", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------

class TestDatabaseManager:
    def test_initialize(self, db):
        assert db._initialized is True

    def test_log_command(self, db):
        cmd_id = db.log_command("test command", "test", success=True)
        assert cmd_id is not None
        assert cmd_id > 0

    def test_get_command_history(self, db):
        db.log_command("first command", "cli")
        db.log_command("second command", "web")
        history = db.get_command_history(limit=10)
        assert len(history) >= 2
        assert all("command" in h for h in history)

    def test_save_and_get_note(self, db):
        nid = db.save_note("Test Note", "Content here", tags="test", category="general")
        assert nid > 0
        notes = db.get_notes(limit=5)
        assert any(n["id"] == nid for n in notes)

    def test_preferences(self, db):
        db.set_preference("theme", "dark")
        val = db.get_preference("theme")
        assert val == "dark"

    def test_preferences_all(self, db):
        db.set_preference("theme", "dark")
        db.set_preference("personality", "jarvis")
        prefs = db.get_all_preferences()
        assert prefs["theme"] == "dark"
        assert prefs["personality"] == "jarvis"

    def test_memory_save_and_search(self, db):
        entry = {
            "session_id": "sess_001",
            "role": "user",
            "content": "Remember the blue elephant",
            "metadata": {},
        }
        db.save_memory_entry(entry)
        results = db.search_memory("blue elephant")
        assert len(results) >= 1
        assert "blue elephant" in results[0]["content"]

    def test_scheduled_task(self, db):
        dt = datetime(2030, 1, 1, 9, 0, 0)
        task_id = db.create_task("Meeting", dt, priority="high")
        assert task_id > 0
        tasks = db.get_pending_tasks()
        assert any(t["id"] == task_id for t in tasks)

    def test_complete_task(self, db):
        dt = datetime(2030, 6, 15, 14, 0, 0)
        task_id = db.create_task("Finish report", dt)
        success = db.complete_task(task_id)
        assert success is True

    def test_log_event(self, db):
        db.log_event("test_event", '{"value": 42}')  # Should not raise


# ---------------------------------------------------------------------------
# Memory System tests
# ---------------------------------------------------------------------------

class TestMemorySystem:
    @pytest.fixture
    def memory(self, config):
        from intelligence.memory_system import MemorySystem
        return MemorySystem(config, db=None)

    def test_add_and_get_recent(self, memory):
        memory.add("user", "Hello Jarvis")
        memory.add("assistant", "Hello! How can I help?")
        recent = memory.get_recent(10)
        assert len(recent) == 2

    def test_clear(self, memory):
        memory.add("user", "Something")
        memory.clear_short_term()
        assert len(memory.get_recent()) == 0

    def test_max_turns_limit(self, memory):
        for i in range(20):
            memory.add("user", f"Message {i}")
        assert len(memory._short_term) <= memory.max_turns

    def test_search_history(self, memory):
        memory.add("user", "I love Python programming")
        results = memory.search_history("Python")
        assert len(results) >= 1

    def test_stats(self, memory):
        stats = memory.get_stats()
        assert "short_term_count" in stats
        assert "session_id" in stats


# ---------------------------------------------------------------------------
# NLP Engine tests
# ---------------------------------------------------------------------------

class TestNLPEngine:
    @pytest.fixture
    def nlp(self, config):
        from intelligence.nlp_engine import NLPEngine
        return NLPEngine(config)

    def test_recognize_intent_greeting(self, nlp):
        result = nlp.recognize_intent("Hello Jarvis")
        assert result["intent"] == "greeting"
        assert result["confidence"] > 0

    def test_recognize_intent_file_ops(self, nlp):
        result = nlp.recognize_intent("create a new folder on my desktop")
        assert result["intent"] in ("file_operation", "open_app", "general_chat")

    def test_recognize_intent_search(self, nlp):
        result = nlp.recognize_intent("search Google for Python tutorials")
        assert result["intent"] == "search_web"

    def test_extract_entities_email(self, nlp):
        entities = nlp.extract_entities("Send email to john@example.com")
        emails = [e for e in entities if e["label"] == "EMAIL"]
        assert len(emails) >= 1

    def test_extract_entities_url(self, nlp):
        entities = nlp.extract_entities("Visit https://github.com for more info")
        urls = [e for e in entities if e["label"] == "URL"]
        assert len(urls) >= 1

    def test_get_keywords(self, nlp):
        keywords = nlp.get_keywords("Python programming language is great for data science")
        assert len(keywords) > 0
        assert all(len(k) >= 3 for k in keywords)

    def test_preprocess(self, nlp):
        text = "  Hello   World  "
        result = nlp.preprocess(text)
        assert result == "Hello World"

    def test_analyze(self, nlp):
        result = nlp.analyze("Search for news about AI")
        assert "intent" in result
        assert "entities" in result
        assert "keywords" in result

    def test_detect_language_english(self, nlp):
        lang = nlp.detect_language("Hello world")
        # langdetect may not be available, should return "en" as default
        assert isinstance(lang, str)


# ---------------------------------------------------------------------------
# Emotion Detector tests
# ---------------------------------------------------------------------------

class TestEmotionDetector:
    @pytest.fixture
    def detector(self, config):
        from intelligence.emotion_detector import EmotionDetector
        return EmotionDetector(config)

    def test_detect_happy(self, detector):
        result = detector.detect("I'm so happy and excited today!")
        assert result["dominant"] in ("happy", "curious", "neutral")

    def test_detect_frustrated(self, detector):
        result = detector.detect("This is terrible and I hate it, it's not working!")
        assert result["dominant"] in ("frustrated", "sad")

    def test_detect_neutral(self, detector):
        result = detector.detect("Okay, sure, fine")
        assert "emotions" in result
        assert "dominant" in result

    def test_adapt_response_frustrated(self, detector):
        emotion = detector.detect("I'm so frustrated right now!")
        response = detector.adapt_response("Here is your answer.", emotion)
        # If emotion adaptation is on, should be prepended
        assert isinstance(response, str)
        assert len(response) >= len("Here is your answer.")

    def test_stress_level(self, detector):
        result = detector.detect("I'm super stressed and overwhelmed with this deadline!")
        assert result["stress_level"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# System Control tests
# ---------------------------------------------------------------------------

class TestSystemControl:
    @pytest.fixture
    def sysctl(self, config):
        from core.system_control import SystemControl
        return SystemControl(config)

    def test_get_system_status(self, sysctl):
        status = sysctl.get_system_status()
        assert "cpu_percent" in status
        assert "ram_percent" in status
        assert "disk_percent" in status
        assert 0 <= status["cpu_percent"] <= 100

    def test_get_processes(self, sysctl):
        processes = sysctl.get_processes(top_n=5)
        assert isinstance(processes, list)
        assert len(processes) <= 5

    def test_list_directory(self, sysctl, tmp_path):
        (tmp_path / "test.txt").write_text("hello")
        files = sysctl.list_directory(str(tmp_path))
        names = [f["name"] for f in files]
        assert "test.txt" in names

    def test_create_directory(self, sysctl, tmp_path):
        new_dir = str(tmp_path / "new_folder")
        result = sysctl.create_directory(new_dir)
        assert result is True
        assert os.path.isdir(new_dir)

    def test_write_and_read_file(self, sysctl, tmp_path):
        path = str(tmp_path / "test.txt")
        assert sysctl.write_file(path, "Hello Jarvis!")
        content = sysctl.read_file(path)
        assert content == "Hello Jarvis!"

    def test_run_command(self, sysctl):
        result = sysctl.run_command("echo hello")
        assert result["success"] is True
        assert "hello" in result["stdout"].lower()

    def test_get_os_info(self, sysctl):
        info = sysctl.get_os_info()
        assert "system" in info
        assert "python_version" in info

    def test_copy_path(self, sysctl, tmp_path):
        src = tmp_path / "source.txt"
        dst = tmp_path / "copy.txt"
        src.write_text("data")
        result = sysctl.copy_path(str(src), str(dst))
        assert result is True
        assert dst.exists()


# ---------------------------------------------------------------------------
# ML Models tests
# ---------------------------------------------------------------------------

class TestMLModels:
    @pytest.fixture
    def ml(self, config):
        from core.ml_models import MLModels
        return MLModels(config)

    def test_classify_task(self, ml):
        result = ml.classify_task("open Chrome browser")
        assert "category" in result
        assert "confidence" in result

    def test_detect_anomaly_no_anomaly(self, ml):
        values = [10, 11, 10, 12, 10, 11]
        anomalies = ml.detect_anomaly(values)
        assert all(not a for a in anomalies)

    def test_detect_anomaly_with_anomaly(self, ml):
        # With threshold=1.5, a single large outlier should be detected
        values = [10.0, 10.0, 10.0, 10.0, 10.0, 200.0]
        anomalies = ml.detect_anomaly(values, threshold=1.5)
        assert any(anomalies), "Expected at least one anomaly to be detected"

    def test_forecast(self, ml):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        forecast = ml.forecast(values, steps=3)
        assert len(forecast) == 3
        assert all(isinstance(v, float) for v in forecast)

    def test_record_and_get_peak_hours(self, ml):
        ml.record_usage("open browser", "web_search", hour=9)
        ml.record_usage("write code", "file_ops", hour=9)
        peaks = ml.get_peak_hours()
        assert 9 in peaks

    def test_save_and_load_state(self, ml, tmp_path):
        ml._models_dir = str(tmp_path)
        ml.record_usage("test cmd", "test_cat")
        ml.models_dir = str(tmp_path)
        ml.save_state()
        ml2 = ml.__class__(ml.config)
        ml2.models_dir = str(tmp_path)
        ml2.load_state()
        # Just verify no exceptions were raised


# ---------------------------------------------------------------------------
# Behavior Analyzer tests
# ---------------------------------------------------------------------------

class TestBehaviorAnalyzer:
    @pytest.fixture
    def analyzer(self, config):
        from core.behavior_analyzer import BehaviorAnalyzer
        return BehaviorAnalyzer(config)

    def test_record_command(self, analyzer):
        analyzer.record_command("open browser", "web_search")
        assert len(analyzer._command_history) == 1

    def test_get_top_categories(self, analyzer):
        for _ in range(5):
            analyzer.record_command("search", "web_search")
        for _ in range(2):
            analyzer.record_command("list files", "file_ops")
        top = analyzer.get_top_categories(2)
        assert top[0]["category"] == "web_search"
        assert top[0]["count"] == 5

    def test_get_behavioral_profile(self, analyzer):
        analyzer.record_command("test", "general")
        profile = analyzer.get_behavioral_profile()
        assert "total_commands" in profile
        assert "success_rate" in profile
        assert profile["total_commands"] >= 1

    def test_detect_anomaly(self, analyzer):
        for _ in range(50):
            analyzer.record_command("common task", "file_ops")
        # A rare category should be detected as anomaly
        is_anomaly = analyzer.detect_anomaly("rare task", "rarely_used_category")
        assert isinstance(is_anomaly, bool)


# ---------------------------------------------------------------------------
# Cache Manager tests
# ---------------------------------------------------------------------------

class TestCacheManager:
    @pytest.fixture
    def cache(self, config):
        from optimization.cache_manager import CacheManager
        return CacheManager(config)

    def test_set_and_get(self, cache):
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_miss(self, cache):
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self, cache):
        import time
        cache.set("temp_key", "temp_value", ttl=1)
        time.sleep(1.1)
        assert cache.get("temp_key") is None

    def test_delete(self, cache):
        cache.set("del_key", "del_value")
        assert cache.delete("del_key") is True
        assert cache.get("del_key") is None

    def test_clear(self, cache):
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None

    def test_stats(self, cache):
        cache.set("x", 1)
        cache.get("x")
        cache.get("nonexistent")
        stats = cache.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_make_key(self):
        from optimization.cache_manager import CacheManager
        k1 = CacheManager.make_key("fn", (1, 2), {})
        k2 = CacheManager.make_key("fn", (1, 2), {})
        k3 = CacheManager.make_key("fn", (1, 3), {})
        assert k1 == k2
        assert k1 != k3


# ---------------------------------------------------------------------------
# Trend Analyzer tests
# ---------------------------------------------------------------------------

class TestTrendAnalyzer:
    @pytest.fixture
    def analyzer(self, config):
        from analytics.trend_analyzer import TrendAnalyzer
        return TrendAnalyzer(config)

    def test_analyze_increasing(self, analyzer):
        result = analyzer.analyze_trend([1, 2, 3, 4, 5])
        assert result["direction"] == "increasing"

    def test_analyze_decreasing(self, analyzer):
        result = analyzer.analyze_trend([5, 4, 3, 2, 1])
        assert result["direction"] == "decreasing"

    def test_analyze_stable(self, analyzer):
        result = analyzer.analyze_trend([5, 5, 5, 5, 5])
        assert result["direction"] == "stable"

    def test_detect_anomalies(self, analyzer):
        values = [10, 10, 10, 100, 10, 10]
        anomalies = analyzer.detect_anomalies(values, z_threshold=2.0)
        assert (3, 100) in anomalies

    def test_moving_average(self, analyzer):
        values = [1, 2, 3, 4, 5]
        ma = analyzer.moving_average(values, window=3)
        assert len(ma) == len(values)
        assert ma[-1] == pytest.approx(4.0, abs=0.1)

    def test_forecast(self, analyzer):
        values = [1, 2, 3, 4, 5]
        forecast = analyzer.forecast_simple(values, steps=2)
        assert len(forecast) == 2
        # Should be increasing
        assert forecast[0] > values[-1] or abs(forecast[0] - values[-1]) < 2

    def test_compare_periods(self, analyzer):
        result = analyzer.compare_periods([10, 10, 10], [20, 20, 20])
        assert result["direction"] == "increase"
        assert result["change_percent"] == pytest.approx(100.0, abs=0.1)


# ---------------------------------------------------------------------------
# Wiki Engine tests
# ---------------------------------------------------------------------------

class TestWikiEngine:
    @pytest.fixture
    def wiki(self, config):
        from knowledge.wiki_engine import WikiEngine
        return WikiEngine(config)

    def test_create_article(self, wiki):
        article = wiki.create_article("Python Basics", "Python is a programming language.", tags=["python", "programming"])
        assert article["id"] is not None
        assert article["title"] == "Python Basics"

    def test_get_article(self, wiki):
        article = wiki.create_article("Test Article", "Content here.")
        fetched = wiki.get_article(article["id"])
        assert fetched is not None
        assert fetched["title"] == "Test Article"

    def test_search(self, wiki):
        wiki.create_article("Machine Learning", "ML is the future of AI.")
        results = wiki.search("Machine Learning")
        assert len(results) >= 1

    def test_search_by_tag(self, wiki):
        wiki.create_article("Python Guide", "Guide to Python.", tags=["python"])
        results = wiki.search_by_tag("python")
        assert len(results) >= 1

    def test_delete_article(self, wiki):
        article = wiki.create_article("Temp Article", "Delete me.")
        assert wiki.delete_article(article["id"]) is True
        assert wiki.get_article(article["id"]) is None

    def test_list_articles(self, wiki):
        wiki.create_article("Article 1", "Content 1.")
        wiki.create_article("Article 2", "Content 2.")
        articles = wiki.list_articles()
        assert len(articles) >= 2

    def test_stats(self, wiki):
        wiki.create_article("Stats Test", "Some content for statistics.")
        stats = wiki.get_stats()
        assert stats["total_articles"] >= 1


# ---------------------------------------------------------------------------
# Notification Engine tests
# ---------------------------------------------------------------------------

class TestNotificationEngine:
    @pytest.fixture
    def notif(self, config):
        from notifications.notification_engine import NotificationEngine
        return NotificationEngine(config)

    def test_console_notification(self, notif, capsys):
        notif.notify("Test Title", "Test message", channel="console")
        captured = capsys.readouterr()
        assert "Test Title" in captured.out

    def test_notification_history(self, notif):
        notif.notify("Title", "Message", channel="console")
        history = notif.get_history()
        assert len(history) >= 1
        assert history[0]["title"] == "Title"


# ---------------------------------------------------------------------------
# Translator tests
# ---------------------------------------------------------------------------

class TestTranslator:
    @pytest.fixture
    def translator(self, config):
        from knowledge.translator import Translator
        return Translator(config)

    def test_translate_same_language(self, translator):
        result = translator.translate("Hello", target="en")
        assert result["original"] == "Hello"
        # Should return same text when translating to same language or if unavailable
        assert isinstance(result["translated"], str)

    def test_supported_languages(self, translator):
        langs = translator.get_supported_languages()
        assert "en" in langs
        assert "es" in langs
        assert langs["en"] == "English"

    def test_get_language_name(self, translator):
        assert translator.get_language_name("en") == "English"
        assert translator.get_language_name("fr") == "French"


# ---------------------------------------------------------------------------
# Recommendation Engine tests
# ---------------------------------------------------------------------------

class TestRecommendationEngine:
    @pytest.fixture
    def engine(self, config):
        from intelligence.recommendation_engine import RecommendationEngine
        return RecommendationEngine(config)

    def test_get_recommendations(self, engine):
        recs = engine.get_recommendations(n=3)
        assert isinstance(recs, list)
        assert len(recs) <= 3

    def test_accept_recommendation(self, engine):
        recs = engine.get_recommendations(n=1)
        if recs:
            engine.accept_recommendation(recs[0]["text"])
            assert engine.get_acceptance_rate() > 0

    def test_reject_recommendation(self, engine):
        recs = engine.get_recommendations(n=1)
        if recs:
            engine.reject_recommendation(recs[0]["text"])
            # Rejected recommendations should not appear again
            new_recs = engine.get_recommendations(n=10)
            texts = [r["text"] for r in new_recs]
            assert recs[0]["text"] not in texts


# ---------------------------------------------------------------------------
# DND Manager tests
# ---------------------------------------------------------------------------

class TestDNDManager:
    @pytest.fixture
    def dnd(self, config):
        from notifications.dnd_manager import DNDManager
        return DNDManager(config)

    def test_enable_disable(self, dnd):
        dnd.enable()
        assert dnd.is_active() is True
        dnd.disable()
        assert dnd.is_active() is False

    def test_should_suppress(self, dnd):
        dnd.enable()
        assert dnd.should_suppress("normal") is True
        assert dnd.should_suppress("critical") is False  # Exception

    def test_add_schedule(self, dnd):
        dnd.add_schedule(22, 0, 7, 0, name="night")
        assert len(dnd.get_schedules()) == 1

    def test_remove_schedule(self, dnd):
        dnd.add_schedule(22, 0, 7, 0, name="night")
        dnd.remove_schedule("night")
        assert len(dnd.get_schedules()) == 0


# ---------------------------------------------------------------------------
# Priority Manager tests
# ---------------------------------------------------------------------------

class TestPriorityManager:
    @pytest.fixture
    def pm(self, config):
        from notifications.priority_manager import PriorityManager
        return PriorityManager(config)

    def test_assess_critical(self, pm):
        result = pm.assess_priority("System Failure", "Critical error in database")
        assert result["priority"] == "critical"

    def test_assess_normal(self, pm):
        result = pm.assess_priority("Reminder", "Buy groceries")
        assert result["priority"] in ("medium", "normal", "low")

    def test_filter_by_min_priority(self, pm):
        notifications = [
            {"priority": "critical"},
            {"priority": "high"},
            {"priority": "low"},
        ]
        filtered = pm.filter_notifications(notifications, min_priority="high")
        assert all(pm.get_priority_score(n["priority"]) >= pm.get_priority_score("high") for n in filtered)


# ---------------------------------------------------------------------------
# Code Analyzer tests
# ---------------------------------------------------------------------------

class TestCodeAnalyzer:
    @pytest.fixture
    def analyzer(self, config):
        from knowledge.code_analyzer import CodeAnalyzer
        return CodeAnalyzer(config)

    def test_analyze_valid_python(self, analyzer):
        code = '''
def greet(name: str) -> str:
    """Greet a person."""
    return f"Hello, {name}!"
'''
        result = analyzer.analyze_python(code)
        assert result["syntax_valid"] is True
        assert result["metrics"]["functions"] == 1

    def test_analyze_invalid_python(self, analyzer):
        code = "def broken_func(\n  missing close paren"
        result = analyzer.analyze_python(code)
        assert result["syntax_valid"] is False
        assert len(result["errors"]) >= 1

    def test_cyclomatic_complexity(self, analyzer):
        code = '''
def complex_function(x):
    if x > 0:
        if x > 10:
            return "big"
        return "small"
    elif x < 0:
        return "negative"
    return "zero"
'''
        complexity = analyzer.cyclomatic_complexity(code)
        assert "complex_function" in complexity
        assert complexity["complex_function"] >= 3


# ---------------------------------------------------------------------------
# Performance Tracker tests
# ---------------------------------------------------------------------------

class TestPerformanceTracker:
    @pytest.fixture
    def tracker(self, config):
        from analytics.performance_tracker import PerformanceTracker
        return PerformanceTracker(config)

    def test_sample(self, tracker):
        snapshot = tracker.sample()
        assert "cpu_percent" in snapshot
        assert "ram_percent" in snapshot
        assert "timestamp" in snapshot

    def test_history(self, tracker):
        tracker.sample()
        tracker.sample()
        history = tracker.get_history(n=10)
        assert len(history) >= 2

    def test_health_score(self, tracker):
        tracker.sample()
        score = tracker.get_health_score()
        assert 0 <= score <= 100

    def test_averages(self, tracker):
        for _ in range(5):
            tracker.sample()
        avgs = tracker.get_averages(n=5)
        assert "cpu_percent" in avgs
        assert 0 <= avgs["cpu_percent"] <= 100
