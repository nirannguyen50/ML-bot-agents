import json
import os
from datetime import datetime
from pathlib import Path

class AgentCommunicationLogger:
    def __init__(self):
        self.log_dir = Path("logs/agent_communications")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"communications_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        self.agent_names = {
            "agent:main:subagent:12b2e050-8ff9-4f2a-af19-5f362ae546fb": "Project Manager",
            "agent:main:subagent:6a1a837e-d912-4889-abd8-3127c8f4d42a": "Data Scientist",
            "agent:main:subagent:003e337a-e6fe-4035-b8e5-0d754a447f6c": "Quant Analyst",
            "agent:main:subagent:875988ba-7250-4c5b-883b-7b226735e4e0": "Engineer",
            "agent:main:subagent:9bd475bd-9f19-4bff-83b7-b1ee2ab962be": "DevOps",
            "agent:main:main": "Main System"
        }

    def log_message(self, from_agent, to_agent, message, message_type="direct"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from": self.agent_names.get(from_agent, from_agent),
            "from_id": from_agent,
            "to": self.agent_names.get(to_agent, to_agent),
            "to_id": to_agent,
            "type": message_type,
            "message": message,
            "vn_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        self._update_summary(log_entry)
        return log_entry

    def _update_summary(self, last_entry):
        summary_file = self.log_dir / "summary.json"
        summary = {"total_messages": 0, "messages_by_agent": {}, "last_updated": ""}
        
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            except: pass
            
        summary["total_messages"] += 1
        agent = last_entry["from"]
        summary["messages_by_agent"][agent] = summary["messages_by_agent"].get(agent, 0) + 1
        summary["last_updated"] = datetime.now().isoformat()
        
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

_logger = AgentCommunicationLogger()

def log_agent_message(from_agent, to_agent, message, message_type="direct"):
    return _logger.log_message(from_agent, to_agent, message, message_type)
