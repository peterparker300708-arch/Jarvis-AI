# Jarvis AI - Advanced Edition v2.0.0

> 🤖 The Ultimate AI Assistant with Complete System Control, Machine Learning, and Smart Automation

[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.3+-green)](https://flask.palletsprojects.com)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-orange)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-95%20passing-brightgreen)](#testing)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

## 🚀 Features

### 🧠 Advanced AI & Machine Learning
- **Free AI Backend**: Ollama + Mistral/Llama 2 (no API costs)
- **Predictive Actions**: Anticipate user needs before asking
- **Behavior Analysis**: Learn your patterns and habits
- **NLU v2**: Intent recognition with entity extraction
- **Emotion Detection**: Adapt responses to your mood
- **Conversation Memory**: Context persistence across sessions

### ⚙️ Complete System Control
- Process management (start/stop/monitor any process)
- File system operations (create/read/write/move/copy/delete)
- Shell command execution with output capture
- Hardware monitoring (CPU, RAM, Disk, Network, Temperature)
- Application launcher and window management
- Network status and management

### 🎯 Smart Automation
- **Workflow Engine**: Chain multiple tasks with conditionals and error handling
- **IFTTT Triggers**: Event-based automation (CPU alert → run cleanup)
- **Smart Scheduler**: Conflict-free task scheduling with timezone support
- **Routine Manager**: Morning/evening/work routines with customizable steps
- **Recommendation Engine**: AI-driven task suggestions

### 📊 Analytics & Reporting
- Real-time system performance monitoring
- Usage statistics and behavioral profiling
- Trend analysis and anomaly detection
- Automated daily/weekly HTML reports
- Interactive charts with matplotlib/plotly

### 🌐 Web & Browser Features
- Web content extraction and search (DuckDuckGo)
- Website change monitoring
- PDF management (create, merge, split, extract text)
- Smart download manager with auto-categorization
- Screenshot capture with OCR support

### 📚 Knowledge & Learning
- Personal wiki with full-text search
- Python code analysis with AST
- Auto documentation generator
- Interactive tutorial system
- Research assistant with citation management
- Multi-language translation (50+ languages)

### 🎨 User Interface
- **Web Dashboard**: Dark-themed real-time monitoring UI
- **CLI Interface**: Rich interactive terminal with history
- **REST API**: Full FastAPI endpoints with Swagger docs
- **Theme System**: Dark, Light, Iron Man, Matrix themes
- **Personality Manager**: Jarvis, Friday, EDITH modes

### 🔔 Smart Notifications
- Multi-channel: Desktop, Console, Telegram, Email
- Priority system with AI-determined importance
- Do Not Disturb scheduling
- System health alerts
- Daily/weekly digest generation

### ⚡ Performance & Optimization
- Smart in-memory cache with TTL
- Parallel batch processing
- Resource optimizer and cleanup system
- GPU detection and acceleration (when PyTorch available)
- Auto log rotation and storage cleanup

## 📁 Project Structure

```
Jarvis-AI/
├── core/               # AI engine, system control, ML models, voice, behavior
├── intelligence/       # NLU, emotion, memory, recommendations, predictor, context
├── automation/         # Workflow, triggers, scheduler, routines
├── modules/            # Web browser, PDF, downloads, screenshots
├── analytics/          # Analytics engine, visualizer, trends, reports
├── knowledge/          # Wiki, code analyzer, docs, tutorials, translator
├── optimization/       # Cache, GPU, resources, batch, cleanup
├── notifications/      # Notifications, priority, DND, alerts, digests
├── ui/                 # Web dashboard, themes, personalities
├── api/                # REST API (FastAPI)
├── cli/                # Command-line interface
├── database/           # SQLAlchemy models + manager
├── web/                # Flask templates and static assets
│   ├── templates/      # HTML pages (dashboard, terminal, analytics, settings)
│   └── static/         # CSS + JavaScript
├── utils/              # Config, logger, helpers
├── tests/              # 95+ passing tests
├── config.yaml         # Configuration
├── requirements.txt    # Dependencies
├── setup.py            # Package setup
└── jarvis.py           # Entry point
```

## ⚡ Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/peterparker300708-arch/Jarvis-AI.git
cd Jarvis-AI
pip install -r requirements.txt
```

### 2. Install Ollama (Free AI Backend)

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral   # Pull the AI model (~4GB)
ollama serve          # Start the Ollama server
```

### 3. Run Jarvis

```bash
# Interactive CLI (default)
python jarvis.py

# Web dashboard at http://localhost:5000
python jarvis.py --mode web

# REST API at http://localhost:8000/docs
python jarvis.py --mode api

# All services running (daemon mode)
python jarvis.py --mode daemon
```

## 🎙️ Example Commands

```
You: What's my system status?
You: Search for Python tutorials
You: Create a folder called Projects on my Desktop
You: Summarize recent AI research
You: Schedule a meeting for tomorrow at 3 PM
You: Analyze my spending patterns
You: What was I working on last Tuesday?
You: Monitor Amazon for price drops
You: Translate "Hello World" to Spanish
```

## 🔌 REST API

FastAPI Swagger UI available at `http://localhost:8000/docs`

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Chat with Jarvis AI |
| `/system/status` | GET | System metrics |
| `/system/processes` | GET | Top processes |
| `/notes` | GET/POST | Manage notes |
| `/tasks` | GET | Pending tasks |
| `/memory` | GET/DELETE | Conversation memory |
| `/history` | GET | Command history |

## ⚙️ Configuration

Edit `config.yaml`:

```yaml
ai:
  model: mistral         # or llama2, codellama, phi
  base_url: http://localhost:11434
  temperature: 0.7

voice:
  personality: jarvis    # jarvis | friday | edith
  enabled: true

notifications:
  telegram_bot_token: ""   # Add your bot token
  telegram_chat_id: ""     # Add your chat ID

web:
  port: 5000
api:
  port: 8000
```

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

> 95 tests passing across all modules

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| AI Backend | Ollama, Mistral, Llama 2 |
| Web Framework | Flask + FastAPI |
| Database | SQLite + SQLAlchemy |
| Task Scheduling | APScheduler |
| NLP | NLTK, spaCy, langdetect |
| ML | scikit-learn, NumPy, pandas |
| Visualization | matplotlib, plotly |
| Voice | SpeechRecognition, pyttsx3 |
| System | psutil |
| Web Scraping | BeautifulSoup4, requests |

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
