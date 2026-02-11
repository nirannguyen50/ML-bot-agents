"""
Voting System — Feature 8
Allows agents to propose and vote on decisions.
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

VOTES_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'votes.json')


class VotingSystem:
    """Agent voting system for collaborative decisions"""
    
    def __init__(self):
        self.votes_path = os.path.abspath(VOTES_PATH)
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.votes_path):
            self._save({"proposals": [], "next_id": 1})
    
    def _load(self) -> Dict:
        with open(self.votes_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save(self, data: Dict):
        with open(self.votes_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def propose(self, title: str, description: str, proposer: str, 
                voters: List[str] = None) -> Dict:
        """Create a new proposal for voting"""
        data = self._load()
        
        if voters is None:
            voters = ["data_scientist", "quant_analyst", "engineer", "devops"]
        
        proposal = {
            "id": data["next_id"],
            "title": title,
            "description": description,
            "proposer": proposer,
            "voters": voters,
            "votes": {},  # {agent_name: "approve" | "reject" | "abstain"}
            "status": "open",  # open, passed, rejected
            "created_at": datetime.now().isoformat(),
            "closed_at": None,
            "result": None
        }
        
        data["proposals"].append(proposal)
        data["next_id"] += 1
        self._save(data)
        
        logger.info(f"📋 New proposal #{proposal['id']}: {title} by {proposer}")
        return proposal
    
    def vote(self, proposal_id: int, agent_name: str, decision: str, 
             reason: str = "") -> str:
        """Cast a vote on a proposal"""
        if decision not in ("approve", "reject", "abstain"):
            return f"Invalid decision: {decision}. Use 'approve', 'reject', or 'abstain'."
        
        data = self._load()
        
        for proposal in data["proposals"]:
            if proposal["id"] == proposal_id and proposal["status"] == "open":
                if agent_name not in proposal["voters"]:
                    return f"{agent_name} is not a voter for this proposal"
                
                proposal["votes"][agent_name] = {
                    "decision": decision,
                    "reason": reason,
                    "voted_at": datetime.now().isoformat()
                }
                
                self._save(data)
                logger.info(f"🗳️ {agent_name} voted '{decision}' on proposal #{proposal_id}")
                
                # Auto-tally if all votes are in
                if len(proposal["votes"]) >= len(proposal["voters"]):
                    return self.tally(proposal_id)
                
                return f"Vote recorded: {agent_name} → {decision}"
        
        return f"Proposal #{proposal_id} not found or already closed"
    
    def tally(self, proposal_id: int) -> str:
        """Count votes and determine result"""
        data = self._load()
        
        for proposal in data["proposals"]:
            if proposal["id"] == proposal_id:
                approvals = sum(1 for v in proposal["votes"].values() 
                              if v["decision"] == "approve")
                rejections = sum(1 for v in proposal["votes"].values() 
                               if v["decision"] == "reject")
                total_voters = len(proposal["voters"])
                
                # Majority wins (> 50%)
                threshold = total_voters / 2
                
                if approvals > threshold:
                    proposal["status"] = "passed"
                    proposal["result"] = "APPROVED"
                elif rejections > threshold:
                    proposal["status"] = "rejected"
                    proposal["result"] = "REJECTED"
                elif len(proposal["votes"]) >= total_voters:
                    # All voted but no majority — proposer breaks tie
                    proposal["status"] = "passed" if approvals >= rejections else "rejected"
                    proposal["result"] = "APPROVED (tie-break)" if approvals >= rejections else "REJECTED (tie-break)"
                else:
                    proposal["result"] = f"Pending ({approvals} approve, {rejections} reject, {total_voters - len(proposal['votes'])} remaining)"
                    self._save(data)
                    return proposal["result"]
                
                proposal["closed_at"] = datetime.now().isoformat()
                self._save(data)
                
                result = f"📊 Proposal #{proposal_id} '{proposal['title']}': {proposal['result']} ({approvals}/{total_voters} approved)"
                logger.info(result)
                return result
        
        return f"Proposal #{proposal_id} not found"
    
    def get_proposal(self, proposal_id: int) -> Optional[Dict]:
        """Get a specific proposal"""
        data = self._load()
        for p in data["proposals"]:
            if p["id"] == proposal_id:
                return p
        return None
    
    def get_open_proposals(self) -> List[Dict]:
        """Get all open proposals"""
        data = self._load()
        return [p for p in data["proposals"] if p["status"] == "open"]
    
    def get_summary(self) -> str:
        """Get voting summary"""
        data = self._load()
        proposals = data["proposals"]
        total = len(proposals)
        passed = sum(1 for p in proposals if p["status"] == "passed")
        rejected = sum(1 for p in proposals if p["status"] == "rejected")
        open_count = sum(1 for p in proposals if p["status"] == "open")
        return f"Votes: {total} total | {passed} passed | {rejected} rejected | {open_count} open"
