# ML Bot Agents — Project Context
# This file is loaded by ALL agents at startup to understand the project.

## PROJECT GOAL
Xây dựng hệ thống AI Trading Bot tự động, sử dụng đội ngũ multi-agent cộng tác.
Mục tiêu cuối: Agents tự download data → phân tích → tạo chiến lược → backtest → deploy.

## TEAM STRUCTURE
- **Project Manager** (PM): Điều phối task, chạy standup, giám sát tiến độ
- **Data Scientist** (DS): Data pipeline, feature engineering, ML models
- **Quant Analyst** (QA): Trading strategy, backtesting, risk metrics
- **Engineer** (ENG): System architecture, code quality, backtest engine
- **DevOps** (OPS): Monitoring, deployment, health checks

## PROJECT STRUCTURE
```
ML-bot-agents/
├── scripts/start_agents.py      — Main entry: khởi động và điều phối agents
├── src/agents/
│   ├── base_agent.py            — Base class với LLM, tools, memory
│   ├── data_scientist.py        — Download data, feature engineering
│   ├── quant_analyst.py         — Strategy design, risk analysis
│   ├── engineer.py              — Code quality, system architecture
│   └── devops.py                — Monitoring, deployment
├── src/utils/
│   ├── llm_client.py            — DeepSeek API client
│   ├── agent_tools.py           — File I/O, commands, git tools
│   ├── memory.py                — Persistent JSON memory
│   └── backlog_manager.py       — Task queue with priorities & dependencies
├── backlog.json                 — Task backlog (PM reads/writes)
├── memory/                      — Agent memory files (per agent)
├── workspace/                   — Agent-generated code files
├── data/raw/                    — Downloaded market data CSVs
├── logs/                        — Communication & startup logs
└── monitor_agent_communications.py — Dashboard at http://localhost:8080
```

## CURRENT BACKLOG STATUS
Tasks are in backlog.json. Use READ_FILE to check current status.
Pipeline: DS downloads data → DS calculates features → QA designs strategy → ENG builds backtest → OPS monitors.

## WORKFLOW RULES
1. Khi nhận task, đọc kỹ description rồi dùng tools để thực hiện
2. Viết code thực tế vào workspace/ bằng WRITE_FILE
3. Test code bằng EXECUTE trước khi báo cáo
4. Lưu kết quả quan trọng bằng LEARN
5. Sau khi hoàn thành, dùng GIT_COMMIT để lưu thay đổi
6. Tham khảo memory của mình bằng RECALL nếu cần context cũ

## GIT REPO
Repository: https://github.com/nirannguyen50/ML-bot-agents
Branch: main
All agents share the same repo. Commit after completing significant work.
