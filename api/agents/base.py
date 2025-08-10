"""
Base classes and shared utilities for agents
"""

from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import add_messages
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

#########################################
# Shared State and Data Structures     #
#########################################

class MultiAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_request: str
    resume_path: str
    resume_content: str
    resume_analysis: Dict[str, Any]
    job_market_data: Dict[str, Any]
    job_listings: List[Dict[str, Any]]
    cv_path: str
    comparison_results: Dict[str, Any]
    coordinator_plan: Dict[str, Any]
    completed_tasks: List[str]
    next_agent: str
    job_id: str
    hitl_checkpoint: str
    hitl_data: Dict[str, Any]
    user_feedback: str
    plan_rejected: bool

@dataclass
class JobListing:
    title: str
    company: str
    location: str
    description: str
    salary: str
    apply_url: str
    source: str
    date_found: datetime
