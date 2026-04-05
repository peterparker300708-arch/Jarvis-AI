"""Tests for database manager"""
import pytest
import tempfile
import os
from database.db_manager import DatabaseManager


@pytest.fixture
def db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    manager = DatabaseManager(db_path)
    yield manager
    os.unlink(db_path)


def test_log_command(db):
    db.log_command("test command", "test response", True)
    history = db.get_recent_commands(limit=1)
    assert len(history) == 1
    assert history[0]['command_text'] == "test command"


def test_preferences(db):
    db.save_preference("test_key", "test_value")
    value = db.get_preference("test_key")
    assert value == "test_value"


def test_default_preference(db):
    value = db.get_preference("nonexistent", "default")
    assert value == "default"


def test_add_note(db):
    db.add_note("Test Note", "Note content", "tag1,tag2")
    notes = db.get_notes()
    assert len(notes) >= 1
    assert any(n['title'] == "Test Note" for n in notes)


def test_log_activity(db):
    db.log_activity("test_action", "test details")
    # Should not raise
