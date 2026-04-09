from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class VoteType(Enum):
    ADD = "add"
    REMOVE = "remove"

class VoteStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    VETOED = "vetoed"

@dataclass
class Vote:
    id: int
    mod_id: int
    vote_type: VoteType
    initiated_by: str
    created_at: datetime
    expires_at: datetime
    status: VoteStatus
    votes: Dict[str, bool]  # user_id -> vote (True/False)
    vetoed_by: Optional[str] = None
    force_approved_by: Optional[str] = None

class VoteManager:
    def __init__(self, quorum: int = 1, majority_required: int = 1):
        self.quorum = quorum
        self.majority_required = majority_required
        self.votes: Dict[int, Vote] = {}
    
    def create_vote(self, mod_id: int, vote_type: VoteType, initiated_by: str, 
                   duration_hours: int = 24) -> Vote:
        """Create a new vote"""
        vote_id = len(self.votes) + 1
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        vote = Vote(
            id=vote_id,
            mod_id=mod_id,
            vote_type=vote_type,
            initiated_by=initiated_by,
            created_at=datetime.now(),
            expires_at=expires_at,
            status=VoteStatus.PENDING,
            votes={}
        )
        
        self.votes[vote_id] = vote
        return vote
    
    def vote(self, vote_id: int, user_id: str, vote: bool) -> bool:
        """Cast a vote"""
        if vote_id not in self.votes:
            return False
            
        vote_obj = self.votes[vote_id]
        
        # Check if vote has expired
        if datetime.now() > vote_obj.expires_at:
            return False
            
        # Check if user already voted
        if user_id in vote_obj.votes:
            return False
            
        vote_obj.votes[user_id] = vote
        self._evaluate_vote(vote_id)
        return True
    
    def veto(self, vote_id: int, user_id: str) -> bool:
        """Veto a vote (Role 2 only)"""
        if vote_id not in self.votes:
            return False
            
        vote_obj = self.votes[vote_id]
        if vote_obj.status != VoteStatus.PENDING:
            return False
            
        vote_obj.status = VoteStatus.VETOED
        vote_obj.vetoed_by = user_id
        return True
    
    def force_approve(self, vote_id: int, user_id: str) -> bool:
        """Force approve a vote (Role 2 only)"""
        if vote_id not in self.votes:
            return False
            
        vote_obj = self.votes[vote_id]
        if vote_obj.status != VoteStatus.PENDING:
            return False
            
        vote_obj.status = VoteStatus.APPROVED
        vote_obj.force_approved_by = user_id
        return True
    
    def _evaluate_vote(self, vote_id: int) -> None:
        """Evaluate if vote should be approved/rejected"""
        vote_obj = self.votes[vote_id]
        
        if vote_obj.status != VoteStatus.PENDING:
            return
            
        # Check if quorum is met
        total_votes = len(vote_obj.votes)
        if total_votes < self.quorum:
            return  # Not enough votes yet
            
        # Count yes/no votes
        yes_votes = sum(1 for v in vote_obj.votes.values() if v)
        no_votes = total_votes - yes_votes
        
        # Check if majority is reached
        if yes_votes >= self.majority_required:
            vote_obj.status = VoteStatus.APPROVED
        elif no_votes >= self.majority_required:
            vote_obj.status = VoteStatus.REJECTED
