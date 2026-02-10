# 🤖 ML Bot Agents — AI-Powered Trading Team

An autonomous multi-agent system where AI agents collaborate to build, test, and deploy ML-based trading strategies.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              Project Manager                │
│         (Orchestration & Tasking)            │
├──────┬──────┬──────────┬────────────────────┤
│  DS  │  QA  │   ENG    │      DEVOPS        │
│ Data │Quant │ Software │   Infrastructure   │
│ Sci. │Anal. │ Engineer │    & Monitoring     │
├──────┴──────┴──────────┴────────────────────┤
│          Shared Infrastructure              │
│  🧠 DeepSeek LLM  │  💾 Memory  │  🔧 Tools │
└─────────────────────────────────────────────┘
```

## 👥 Agent Roles

| Agent | Responsibility |
|-------|---------------|
| **Project Manager** | Task assignment, standup meetings, monitoring |
| **Data Scientist** | Data pipeline, feature engineering, ML models |
| **Quant Analyst** | Strategy design, backtesting, risk metrics |
| **Engineer** | Architecture, code quality, API integration |
| **DevOps** | Monitoring, deployment, disaster recovery |

## 🛠️ Agent Capabilities

- **Tools**: `WRITE_FILE`, `READ_FILE`, `EXECUTE`, `GIT_COMMIT`, `GIT_PUSH`
- **Memory**: `LEARN` (store facts), `RECALL` (retrieve knowledge)
- **Communication**: Real-time inter-agent messaging with logging

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/nirannguyen50/ML-bot-agents.git
cd ML-bot-agents
pip install openai yfinance pandas pyyaml
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

### 3. Run
```bash
# Start monitoring dashboard
python monitor_agent_communications.py

# Start agents (in another terminal)
python scripts/start_agents.py
```

### 4. Monitor
Open **http://localhost:8080** to watch agents communicate in real-time.

## 📁 Project Structure

```
ML-bot-agents/
├── scripts/
│   └── start_agents.py          # Main entry point
├── src/
│   ├── agents/
│   │   ├── base_agent.py        # Base agent with tools & memory
│   │   ├── data_scientist.py    # Data pipeline & ML
│   │   ├── quant_analyst.py     # Strategy & risk
│   │   ├── engineer.py          # Architecture & code
│   │   └── devops.py            # Infrastructure
│   └── utils/
│       ├── llm_client.py        # DeepSeek API client
│       ├── agent_tools.py       # File, command & git tools
│       ├── memory.py            # Persistent JSON memory
│       └── backlog_manager.py   # Task queue system
├── backlog.json                 # Project task backlog
├── memory/                      # Agent memory files
├── workspace/                   # Agent-generated files
└── logs/                        # Communication logs
```

## 📊 Backlog System

Tasks are managed via `backlog.json`. The PM assigns tasks with priorities and dependencies:
```json
{"id": 1, "title": "Download EURUSD data", "assigned_to": "data_scientist", "priority": "high"}
```

## 🔐 Security
- API keys stored in `.env` (never committed)
- File operations sandboxed to `workspace/`
- Command whitelist: `python`, `pip`, `git`, `dir`, `ls`

## 📜 License
MIT
