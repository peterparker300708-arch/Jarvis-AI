# Jarvis AI - Complete System Control Assistant 🤖

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

Jarvis is a production-ready, AI-powered personal assistant that provides full system control through a natural language interface. It integrates with local LLMs via Ollama and exposes CLI, Web, REST API, Voice, and Daemon modes — all from a single Python application.

## Features

- 🧠 **AI-Powered** — Conversational intelligence via Ollama (LLaMA 3, Mistral, etc.)
- 🖥️ **System Control** — CPU, memory, disk monitoring; process management; shell execution
- 📁 **File Management** — Browse, create, delete, search, move, and copy files
- 🌐 **Web Dashboard** — Real-time system stats and chat interface in the browser
- 🔌 **REST API** — Full HTTP API for integration with external tools and scripts
- 🎙️ **Voice Interface** — Wake-word detection, speech-to-text, and text-to-speech
- 🗓️ **Reminders & Notes** — Persistent notes and scheduled reminders with SQLite storage
- 🌦️ **Weather & Web Search** — Real-time weather and DuckDuckGo search
- 🔒 **Secure** — API key authentication, configurable CORS, input sanitisation
- 🐳 **Docker Ready** — Single-command deployment with Docker Compose

## Architecture

```
Jarvis-AI/
├── jarvis.py              # Entry point — mode dispatcher
├── config.yaml            # Central configuration
├── requirements.txt       # Python dependencies
├── setup.py               # Package setup
├── api/                   # REST API layer (Flask)
│   ├── __init__.py
│   └── routes.py
├── cli/                   # Interactive CLI interface
│   ├── __init__.py
│   └── interface.py
├── core/                  # Core AI and system logic
│   ├── __init__.py
│   ├── ai_engine.py       # Ollama / LLM integration
│   ├── command_processor.py
│   ├── system_control.py  # psutil-based system ops
│   └── voice_engine.py    # STT / TTS / wake-word
├── database/              # Persistence layer
│   ├── __init__.py
│   └── db_manager.py      # SQLite manager
├── modules/               # Feature modules
│   ├── __init__.py
│   ├── file_manager.py
│   ├── reminder_manager.py
│   ├── weather.py
│   └── web_search.py
├── utils/                 # Shared utilities
│   ├── __init__.py
│   └── helpers.py
├── web/                   # Web dashboard (HTML/JS)
│   └── templates/
├── docker/                # Container configuration
│   ├── Dockerfile
│   └── docker-compose.yml
└── tests/                 # Pytest test suite
    ├── test_utils.py
    ├── test_database.py
    ├── test_system_control.py
    └── test_file_manager.py
```

## Prerequisites

- **Python 3.9+**
- **[Ollama](https://ollama.ai)** — local LLM runtime
  ```bash
  curl -fsSL https://ollama.ai/install.sh | sh
  ollama pull llama3
  ```
- **PortAudio** (voice mode only)
  ```bash
  # Ubuntu/Debian
  sudo apt install portaudio19-dev espeak ffmpeg
  # macOS
  brew install portaudio espeak ffmpeg
  ```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/Jarvis-AI.git
   cd Jarvis-AI
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Jarvis** — edit `config.yaml` as needed (see Configuration below)

5. **Start Ollama** and pull a model
   ```bash
   ollama serve &
   ollama pull llama3
   ```

6. **Launch Jarvis**
   ```bash
   python jarvis.py --mode cli
   ```

## Configuration

All settings live in `config.yaml`:

```yaml
jarvis:
  name: "Jarvis"
  version: "1.0.0"

ai:
  provider: "ollama"        # ollama | openai
  model: "llama3"           # Any model pulled in Ollama
  base_url: "http://localhost:11434"
  temperature: 0.7
  max_tokens: 2048

database:
  path: "jarvis.db"

api:
  host: "0.0.0.0"
  port: 5000
  api_key: ""               # Set to enable authentication

voice:
  enabled: false
  wake_word: "jarvis"
  stt_engine: "whisper"     # whisper | google
  tts_engine: "espeak"      # espeak | pyttsx3
```

Key sections:
| Section | Purpose |
|---------|---------|
| `ai` | LLM provider, model name, sampling params |
| `database` | SQLite file path |
| `api` | Host, port, optional API key auth |
| `voice` | Wake-word, STT/TTS engine selection |

## Usage

### CLI mode
Interactive terminal session:
```bash
python jarvis.py --mode cli
```

### Web dashboard
Opens a browser-based chat and system-monitor UI on port 8080:
```bash
python jarvis.py --mode web
```

### REST API
Headless API server on port 5000:
```bash
python jarvis.py --mode api --host 0.0.0.0
```

### Voice mode
Always-on microphone with wake-word detection:
```bash
python jarvis.py --mode voice
```

### Daemon mode
Background service (logs to file, no interactive output):
```bash
python jarvis.py --mode daemon
```

## Docker Deployment

```bash
# Build and start all services (Jarvis + Ollama)
cd docker
docker compose up -d

# View logs
docker compose logs -f jarvis

# Stop
docker compose down
```

The compose stack exposes:
- `5000` — REST API
- `8080` — Web dashboard
- `11434` — Ollama API

Data is persisted in a named Docker volume (`jarvis-data`).

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/chat` | Send a message, receive AI response |
| `GET` | `/api/system` | Current system stats |
| `GET` | `/api/history` | Command history |
| `GET` | `/api/notes` | List all notes |
| `POST` | `/api/notes` | Create a note |
| `DELETE` | `/api/notes/<id>` | Delete a note |
| `GET` | `/api/reminders` | List reminders |
| `POST` | `/api/reminders` | Create a reminder |
| `POST` | `/api/execute` | Run a shell command |

**Example:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the CPU usage?"}'
```

## Voice Commands Examples

| Command | Action |
|---------|--------|
| `"Jarvis, open Firefox"` | Launch Firefox |
| `"What's the weather in London?"` | Fetch weather |
| `"Set a reminder in 30 minutes to check email"` | Create reminder |
| `"Show disk usage"` | Report disk stats |
| `"Search the web for Python tutorials"` | DuckDuckGo search |
| `"Create a note: buy groceries"` | Save a note |
| `"List files in Downloads"` | List directory |

## Systemd Service

Auto-start Jarvis on Linux boot:

```ini
# /etc/systemd/system/jarvis.service
[Unit]
Description=Jarvis AI Assistant
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/opt/Jarvis-AI
ExecStart=/opt/Jarvis-AI/.venv/bin/python jarvis.py --mode daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis
sudo systemctl status jarvis
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

Please ensure all tests pass (`pytest tests/`) and follow the existing code style before submitting.

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
