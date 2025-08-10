from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from api.tools import llm, extract_location, extract_salary, build_job_description
from api.agents.base import MultiAgentState
from api.agents.coordinator_agent import coordinator_agent
from api.agents.cv_creator_agent import cv_creator_agent
from api.agents.job_matcher_agent import job_matcher_agent
from api.agents.job_researcher_agent import job_researcher_agent
from api.agents.resume_analyst_agent import resume_analyst_agent
# performance_evaluator consolidated inline
#########################################
# Performance Evaluation System        #
#########################################

# removed unused import: statistics
from dataclasses import dataclass, asdict

@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for individual agents"""
    agent_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    success_rate: float = 0.0
    errors: list = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.last_updated is None:
            self.last_updated = datetime.now()

@dataclass
class UserOutcome:
    """Simple tracking of user outcomes"""
    user_id: str
    session_id: str
    timestamp: datetime
    user_satisfaction: float = None  # 1-10 scale
    resume_improved: bool = None
    jobs_found_helpful: bool = None
    would_use_again: bool = None

@dataclass
class SystemPerformanceMetrics:
    """Overall system performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_request_time: float = 0.0
    user_satisfaction_score: float = 0.0
    human_interventions: int = 0
    most_used_agent: str = ""
    least_reliable_agent: str = ""
    uptime_percentage: float = 100.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

class PerformanceEvaluator:
    """Comprehensive performance evaluation system - in-memory storage for serverless deployment"""
    
    def __init__(self):
        self.agent_metrics = {}
        self.system_metrics = SystemPerformanceMetrics()
        self.session_start_time = datetime.now()

    def reset_session(self):
        """Reset all metrics for a new session - useful for serverless environments"""
        self.agent_metrics.clear()
        self.system_metrics = SystemPerformanceMetrics()
        self.session_start_time = datetime.now()
    
    def get_current_session_data(self):
        """Get all current session data as dict - for API responses"""
        return {
            'agents': {
                agent_name: asdict(metrics) 
                for agent_name, metrics in self.agent_metrics.items()
            },
            'system': asdict(self.system_metrics),
            'session_start': self.session_start_time.isoformat(),
            'current_time': datetime.now().isoformat()
        }
    
    def log_agent_call(self, agent_name: str, success: bool, processing_time: float, error: str = None):
        """Log an agent call for performance tracking"""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentPerformanceMetrics(agent_name=agent_name)
        
        metrics = self.agent_metrics[agent_name]
        metrics.total_calls += 1
        metrics.total_processing_time += processing_time
        
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if error:
                metrics.errors.append(f"{datetime.now().isoformat()}: {error}")
                # Keep only last 10 errors
                metrics.errors = metrics.errors[-10:]
        
        # Update calculated fields
        metrics.success_rate = (metrics.successful_calls / metrics.total_calls) * 100
        metrics.avg_processing_time = metrics.total_processing_time / metrics.total_calls
        metrics.last_updated = datetime.now()
    
    def log_system_request(self, success: bool, request_time: float, human_intervention: bool = False):
        """Log a system-level request"""
        self.system_metrics.total_requests += 1
        
        if success:
            self.system_metrics.successful_requests += 1
        else:
            self.system_metrics.failed_requests += 1
        
        if human_intervention:
            self.system_metrics.human_interventions += 1
        
        # Update average request time
        total_time = self.system_metrics.avg_request_time * (self.system_metrics.total_requests - 1) + request_time
        self.system_metrics.avg_request_time = total_time / self.system_metrics.total_requests
        
        self.system_metrics.last_updated = datetime.now()
    
    def record_request_metrics(self, agent_name: str, request_type: str, processing_time: float, success: bool, error: str = None):
        """Record request metrics for performance tracking"""
        self.log_agent_call(agent_name, success, processing_time, error)
        self.log_system_request(success, processing_time)
    
    def log_user_satisfaction(self, score: float):
        """Log user satisfaction score (1-10 scale)"""
        if not (1 <= score <= 10):
            raise ValueError("Satisfaction score must be between 1 and 10")
        
        # Simple running average for now - could be improved with weighted averages
        current_score = self.system_metrics.user_satisfaction_score
        total_requests = self.system_metrics.total_requests
        
        if total_requests == 0:
            self.system_metrics.user_satisfaction_score = score
        else:
            self.system_metrics.user_satisfaction_score = ((current_score * (total_requests - 1)) + score) / total_requests
    
    def get_agent_performance_summary(self, agent_name: str):
        """Get performance summary for a specific agent"""
        if agent_name not in self.agent_metrics:
            return {"error": f"No metrics found for agent: {agent_name}"}
        
        metrics = self.agent_metrics[agent_name]
        return {
            "agent_name": agent_name,
            "total_calls": metrics.total_calls,
            "success_rate": round(metrics.success_rate, 2),
            "avg_processing_time": round(metrics.avg_processing_time, 3),
            "recent_errors": metrics.errors[-3:] if metrics.errors else [],
            "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None,
            "performance_grade": self._calculate_performance_grade(metrics)
        }
    
    def get_system_performance_summary(self):
        """Get overall system performance summary"""
        # Calculate additional metrics
        success_rate = (self.system_metrics.successful_requests / max(self.system_metrics.total_requests, 1)) * 100
        
        # Find most and least reliable agents
        most_used = self._get_most_used_agent()
        least_reliable = self._get_least_reliable_agent()
        
        # Calculate uptime (simplified - based on successful vs failed requests)
        uptime = success_rate if self.system_metrics.total_requests > 0 else 100.0
        
        return {
            "total_requests": self.system_metrics.total_requests,
            "success_rate": round(success_rate, 2),
            "avg_request_time": round(self.system_metrics.avg_request_time, 3),
            "user_satisfaction": round(self.system_metrics.user_satisfaction_score, 2),
            "human_interventions": self.system_metrics.human_interventions,
            "human_intervention_rate": round((self.system_metrics.human_interventions / max(self.system_metrics.total_requests, 1)) * 100, 2),
            "most_used_agent": most_used,
            "least_reliable_agent": least_reliable,
            "uptime_percentage": round(uptime, 2),
            "session_duration": str(datetime.now() - self.session_start_time),
            "last_updated": self.system_metrics.last_updated.isoformat() if self.system_metrics.last_updated else None,
            "overall_grade": self._calculate_system_grade(success_rate, self.system_metrics.user_satisfaction_score)
        }
    
    def get_comprehensive_report(self):
        """Get comprehensive performance report"""
        return {
            "system_overview": self.get_system_performance_summary(),
            "agent_details": {
                agent_name: self.get_agent_performance_summary(agent_name)
                for agent_name in self.agent_metrics.keys()
            },
            "recommendations": self._generate_recommendations(),
            "report_generated": datetime.now().isoformat()
        }
    
    def _calculate_performance_grade(self, metrics):
        """Calculate performance grade for an agent"""
        if metrics.total_calls == 0:
            return "N/A"
        
        score = 0
        # Success rate (40% weight)
        score += (metrics.success_rate / 100) * 40
        
        # Response time (30% weight) - lower is better
        if metrics.avg_processing_time <= 1.0:
            score += 30
        elif metrics.avg_processing_time <= 3.0:
            score += 20
        elif metrics.avg_processing_time <= 5.0:
            score += 10
        
        # Error frequency (30% weight)
        error_rate = len(metrics.errors) / metrics.total_calls
        if error_rate <= 0.05:  # 5% or less
            score += 30
        elif error_rate <= 0.1:  # 10% or less
            score += 20
        elif error_rate <= 0.2:  # 20% or less
            score += 10
        
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
    
    def _calculate_system_grade(self, success_rate: float, user_satisfaction: float):
        """Calculate overall system grade"""
        # Weight: 60% success rate, 40% user satisfaction
        score = (success_rate * 0.6) + (user_satisfaction * 10 * 0.4)
        
        if score >= 85:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 55:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"
    
    def _get_most_used_agent(self):
        """Find the most frequently used agent"""
        if not self.agent_metrics:
            return "None"
        
        return max(self.agent_metrics.items(), key=lambda x: x[1].total_calls)[0]
    
    def _get_least_reliable_agent(self):
        """Find the least reliable agent (lowest success rate)"""
        if not self.agent_metrics:
            return "None"
        
        # Filter out agents with too few calls to be meaningful
        reliable_agents = {name: metrics for name, metrics in self.agent_metrics.items() if metrics.total_calls >= 3}
        
        if not reliable_agents:
            return "Insufficient data"
        
        return min(reliable_agents.items(), key=lambda x: x[1].success_rate)[0]
    
    def _generate_recommendations(self):
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # System-level recommendations
        system_success_rate = (self.system_metrics.successful_requests / max(self.system_metrics.total_requests, 1)) * 100
        
        if system_success_rate < 80:
            recommendations.append("System success rate is below 80%. Consider investigating failure patterns and improving error handling.")
        
        if self.system_metrics.user_satisfaction_score < 7.0:
            recommendations.append("User satisfaction is below 7.0. Consider implementing more human-in-the-loop interactions and user feedback mechanisms.")
        
        if self.system_metrics.avg_request_time > 30:
            recommendations.append("Average request time is high. Consider optimizing agent processing or implementing parallel execution.")
        
        # Agent-level recommendations
        for agent_name, metrics in self.agent_metrics.items():
            if metrics.success_rate < 70:
                recommendations.append(f"{agent_name} has low success rate ({metrics.success_rate:.1f}%). Review error patterns and improve robustness.")
            
            if metrics.avg_processing_time > 10:
                recommendations.append(f"{agent_name} has high processing time ({metrics.avg_processing_time:.1f}s). Consider optimizing or breaking into smaller tasks.")
        
        if not recommendations:
            recommendations.append("System is performing well! Continue monitoring and consider implementing advanced optimization features.")
        
        return recommendations

# Global performance evaluator instance
performance_evaluator = PerformanceEvaluator()

import time
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

config = RunnableConfig(recursion_limit=50)

#########################################
# Utility Functions                    #
#########################################

def serialize_message(message: Any) -> str:
    """Convert any message type to a serializable string"""
    if isinstance(message, HumanMessage):
        return str(message.content)
    elif isinstance(message, str):
        return message
    else:
        return str(message)

def serialize_messages(messages: List[Any]) -> List[str]:
    """Convert a list of messages to serializable strings"""
    return [serialize_message(msg) for msg in messages]

def make_serializable(data: Dict[str, Any]) -> Dict[str, Any]:
    """Make a dictionary fully serializable by converting AIMessage objects"""
    if not isinstance(data, dict):
        return data
    
    serialized = {}
    for key, value in data.items():
        if key == 'messages' and isinstance(value, list):
            # Convert messages to strings
            serialized[key] = serialize_messages(value)
        elif hasattr(value, 'content'):
            # Convert single message
            serialized[key] = serialize_message(value)
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            serialized[key] = make_serializable(value)
        elif isinstance(value, list):
            # Process lists
            serialized[key] = [make_serializable(item) if isinstance(item, dict) else serialize_message(item) if hasattr(item, 'content') else item for item in value]
        else:
            serialized[key] = value
    
    return serialized

#########################################
# Multi-Agent Orchestration System     #
#########################################

def should_continue(state: MultiAgentState):
    """Enhanced routing with smart decision making based on execution plan"""
    next_agent = state.get('next_agent', 'END')
    
    # Handle HITL approval checkpoint
    if next_agent == 'HITL_APPROVAL':
        return END
    
    if next_agent == 'END':
        return END
    
    # For agent transitions, use the coordinator plan to determine next agent
    plan = state.get('coordinator_plan', {})
    completed = state.get('completed_tasks', [])
    execution_order = plan.get('execution_order', [])
    
    # Find the next agent in execution order that hasn't been completed
    for agent in execution_order:
        if agent not in completed:
            return agent
    
    # If all agents in execution order are complete, end the workflow
    return END

def create_multi_agent_system():
    """Create the enhanced multi-agent orchestration system with HITL support"""
    
    graph = StateGraph(MultiAgentState)

    JOB_PROCESSING_TOOLS = [
        extract_location,
        extract_salary, 
        build_job_description,
    ]

    # Create LLM instances with tools bound
    lm_with_tools = llm.bind_tools(JOB_PROCESSING_TOOLS)
    
    # Add all specialist agents
    graph.add_node("coordinator", coordinator_agent)
    graph.add_node("resume_analyst", resume_analyst_agent)
    graph.add_node("job_researcher", job_researcher_agent)
    graph.add_node("cv_creator", cv_creator_agent)
    graph.add_node("job_matcher", job_matcher_agent)
    
    # Set coordinator as entry point
    graph.set_entry_point("coordinator")
    
    # Enhanced routing system
    graph.add_conditional_edges("coordinator", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    
    # Agents route directly to next agent based on coordinator plan (no need to return to coordinator)
    # Coordinator will set next_agent in state, and the conditional routing will handle the flow
    graph.add_conditional_edges("resume_analyst", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    graph.add_conditional_edges("job_researcher", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    graph.add_conditional_edges("cv_creator", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    graph.add_conditional_edges("job_matcher", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    
    # Create checkpointer for HITL support
    checkpointer = MemorySaver()
    
    return graph.compile(checkpointer=checkpointer)

#########################################
# Enhanced Main Interface              #
#########################################

class JobHuntingMultiAgent:
    """
    Enhanced multi-agent job hunting system with performance tracking
    """
    
    def __init__(self):
        self.system = create_multi_agent_system()
        self.user_outcomes = []  # Store user outcomes for this session
    
    def process_request_with_hitl(self, user_message: str, resume_path: str = None, user_id: str = None, job_id: str = None) -> Dict[str, Any]:
        """
        Process user request with HITL support
        """
        # Add job_id to initial state for HITL checkpoints
        result = self._process_request_internal(user_message, resume_path, user_id, job_id)
        
        # HITL is now handled directly in _process_request_internal using LangGraph's interrupt system
        
        return result
    
    def continue_from_approval(self, thread_id: str, approval_response: Any) -> Dict[str, Any]:
        """Continue processing after human approval using LangGraph's resume"""
        try:
            config_with_thread = {"configurable": {"thread_id": thread_id}}
            
            # Check if user rejected the plan
            if not approval_response.get("approved", True):
                
                # Update the state with rejection feedback and ask coordinator to create a new plan
                try:
                    current_state = self.system.get_state(config_with_thread)
                    
                    # Create updated values with feedback
                    updated_values = {
                        **current_state.values,
                        'user_feedback': approval_response.get("feedback", "User requested modifications"),
                        'plan_rejected': True,
                        'next_agent': 'coordinator',
                        'completed_tasks': []  # Reset to allow coordinator to run again
                    }
                    
                    
                    # Update the state with feedback
                    self.system.update_state(config_with_thread, updated_values)
                    
                    
                except Exception as update_error:
                    logger.error(f"Failed to update state: {update_error}")
                    return {
                        "success": False,
                        "error": f"Failed to process revision: {str(update_error)}"
                    }
                
                # Resume execution to let coordinator create a new plan with feedback
                try:
                    from langgraph.types import Command
                    for event in self.system.stream(Command(resume=approval_response), config_with_thread):
                        
                        # Check if we hit another interrupt (new plan for approval)
                        if '__interrupt__' in event:
                            interrupt_data = event['__interrupt__']
                            if interrupt_data and len(interrupt_data) > 0:
                                interrupt_obj = interrupt_data[0]
                                if hasattr(interrupt_obj, 'value'):
                                    interrupt_value = interrupt_obj.value
                                    
                                    return {
                                        "success": False,
                                        "hitl_checkpoint": interrupt_value.get("checkpoint"),
                                        "hitl_data": interrupt_value.get("data"),
                                        "job_id": interrupt_value.get("job_id"),
                                        "partial_state": self.system.get_state(config_with_thread).values,
                                        "thread_id": thread_id,
                                        "revision": True  # Indicate this is a revised plan
                                    }
                    
                    # If no new interrupt, return the final result
                    final_state = self.system.get_state(config_with_thread)
                    return {
                        "success": True,
                        "messages": final_state.values.get("messages", []),
                        "completed_tasks": final_state.values.get("completed_tasks", []),
                        "revision_applied": True
                    }
                    
                except Exception as stream_error:
                    logger.error(f"Error during revision stream: {stream_error}")
                    import traceback
                    traceback.print_exc()
                    return {
                        "success": False,
                        "error": f"Failed to create revised plan: {str(stream_error)}"
                    }
            
            # Reset plan_rejected flag for approved plans before resuming
            try:
                current_state = self.system.get_state(config_with_thread)
                if current_state.values.get('plan_rejected', False):
                    
                    # Get the plan and determine correct next_agent
                    plan = current_state.values.get('coordinator_plan', {})
                    execution_order = plan.get('execution_order', [])
                    completed_tasks = current_state.values.get('completed_tasks', [])
                    
                    # Find the first uncompleted agent in execution order
                    next_agent = 'END'
                    for agent in execution_order:
                        if agent not in completed_tasks:
                            next_agent = agent
                            break
                    
                    
                    updated_values = {
                        **current_state.values,
                        'plan_rejected': False,
                        'user_feedback': "",  # Clear the feedback too
                        'next_agent': next_agent  # Set correct next agent to avoid coordinator loop
                    }
                    self.system.update_state(config_with_thread, updated_values)
            except Exception as reset_error:
                logger.warning(f"Failed to reset plan_rejected flag: {reset_error}")
            
            # Resume execution using Command with approval response
            from langgraph.types import Command
            
            for event in self.system.stream(Command(resume=approval_response), config_with_thread):
                
                # Check if we hit another interrupt during resume
                if '__interrupt__' in event:
                    interrupt_data = event['__interrupt__']
                    if interrupt_data and len(interrupt_data) > 0:
                        interrupt_obj = interrupt_data[0]
                        if hasattr(interrupt_obj, 'value'):
                            interrupt_value = interrupt_obj.value
                            
                            return {
                                "success": False,
                                "hitl_checkpoint": interrupt_value.get("checkpoint"),
                                "hitl_data": interrupt_value.get("data"),
                                "job_id": interrupt_value.get("job_id"),
                                "partial_state": self.system.get_state(config_with_thread).values,
                                "thread_id": thread_id
                            }
            
            # Get final result
            final_state = self.system.get_state(config_with_thread)
            result = final_state.values
            
            return {
                "success": True,
                "messages": result.get("messages", []),
                "job_listings": result.get("job_listings", []),
                "cv_path": result.get("cv_path", ""),
                "completed_tasks": result.get("completed_tasks", []),
                "resume_analysis": result.get("resume_analysis", {}),
                "job_market_data": result.get("job_market_data", {}),
                "comparison_results": result.get("comparison_results", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to continue after approval: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to continue after approval: {str(e)}"
            }
    
    def _determine_next_agent_after_approval(self, partial_state: Dict[str, Any], approval_response: Any) -> str:
        """Determine which agent to run next after approval"""
        checkpoint = partial_state.get("hitl_checkpoint")
        
        if checkpoint == "coordinator_plan":
            # After coordinator plan approval, follow the execution order
            plan = partial_state.get("coordinator_plan", {})
            return plan.get("next_agent", "END")
        elif checkpoint == "job_role_clarification":
            # After role clarification, continue with job research
            return "job_researcher"
        else:
            return "END"

    def process_request(self, user_message: str, resume_path: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Process user request with enhanced multi-agent coordination and performance tracking (backwards compatibility)
        """
        return self._process_request_internal(user_message, resume_path, user_id, None)
    
    def _process_request_internal(self, user_message: str, resume_path: str = None, user_id: str = None, job_id: str = None) -> Dict[str, Any]:
        """
        Internal processing with HITL support
        """
        
        # Generate session ID and user ID for tracking
        session_id = str(uuid.uuid4())
        user_id = user_id or f"user_{int(time.time())}"
        start_time = time.time()
        
        # Set reasonable timeout for processing (5 minutes)
        processing_timeout = 300  # seconds
        
        # Track individual agent timing
        agent_timings = {}
        
        initial_state = {
            "messages": [],
            "user_request": user_message,
            "resume_path": resume_path or "",
            "resume_content": "",
            "resume_analysis": {},
            "job_market_data": {},
            "job_listings": [],
            "cv_path": "",
            "comparison_results": {},
            "coordinator_plan": {},
            "completed_tasks": [],
            "next_agent": "coordinator",
            "session_id": session_id,
            "user_id": user_id,
            "job_id": job_id or "",  # Add job_id for HITL support
            "hitl_checkpoint": "",  # Add HITL fields to state
            "hitl_data": {},
            "user_feedback": "",  # User feedback for plan revisions
            "plan_rejected": False,  # Whether the plan was rejected
            "agent_start_times": {}  # Track individual agent start times
        }
        
        
        try:            
            # Process the request with LangGraph's built-in HITL support
            thread_id = f"thread_{job_id}"
            config_with_thread = {"configurable": {"thread_id": thread_id}}
            
            # Stream the execution to detect interrupts with proper exception handling
            try:
                stream_events = []
                for event in self.system.stream(initial_state, config_with_thread):
                    # Check for timeout to prevent GeneratorExit from long-running processes
                    current_time = time.time()
                    if current_time - start_time > processing_timeout:
                        logger.warning(f"Processing timeout after {processing_timeout}s")
                        return {
                            "success": False,
                            "error": "Processing timeout. Please try with a shorter request.",
                            "job_id": job_id,
                            "processing_time": current_time - start_time
                        }
                    
                    stream_events.append(event)
                    
                    # Check if this event contains an interrupt
                    if '__interrupt__' in event:
                        interrupt_data = event['__interrupt__']
                        if interrupt_data and len(interrupt_data) > 0:
                            interrupt_obj = interrupt_data[0]  # First interrupt
                            if hasattr(interrupt_obj, 'value'):
                                interrupt_value = interrupt_obj.value
                                
                                return {
                                    "success": False,
                                    "hitl_checkpoint": interrupt_value.get("checkpoint"),
                                    "hitl_data": interrupt_value.get("data"),
                                    "job_id": interrupt_value.get("job_id"),
                                    "partial_state": self.system.get_state(config_with_thread).values,
                                    "thread_id": thread_id
                                }
                
                # If stream completed without interrupts, continue with normal processing
                logger.info(f"Stream completed successfully with {len(stream_events)} events")
                    
            except GeneratorExit:
                # Handle generator being closed prematurely
                logger.warning("LangGraph stream was closed prematurely (GeneratorExit)")
                return {
                    "success": False,
                    "error": "Processing was interrupted. Please try again.",
                    "job_id": job_id,
                    "thread_id": thread_id
                }
            except Exception as e:
                # Check if this is an interrupt exception
                if "interrupt" in str(e).lower():
                    
                    # Get current state to access interrupt data
                    current_state = self.system.get_state(config_with_thread)
                    
                    # The interrupt data should be in the most recent message or state
                    # Let's check if we have any interrupt information stored
                    if current_state.values.get('messages'):
                        last_message = current_state.values['messages'][-1]
                        if hasattr(last_message, 'content') and "Awaiting Your Approval" in str(last_message.content):
                            # Extract HITL data from the coordinator plan
                            return {
                                "success": False,
                                "hitl_checkpoint": "coordinator_plan",
                                "hitl_data": {
                                    "plan_summary": str(last_message.content)
                                },
                                "job_id": job_id,
                                "partial_state": current_state.values,
                                "thread_id": thread_id
                            }
                    
                    # Fallback: return basic HITL response
                    return {
                        "success": False,
                        "hitl_checkpoint": "coordinator_plan",
                        "hitl_data": {"plan_summary": "Plan created, awaiting approval"},
                        "job_id": job_id,
                        "partial_state": current_state.values,
                        "thread_id": thread_id
                    }
                else:
                    raise e
            
            # Get final result if no interrupt occurred
            final_state = self.system.get_state(config_with_thread)
            result = final_state.values
            
            # Calculate total processing time
            total_time = time.time() - start_time
            
            # Log system-level performance
            performance_evaluator.log_system_request(
                success=True, 
                request_time=total_time,
                human_intervention=False
            )
            
            # Log individual agent performance
            completed_tasks = result.get('completed_tasks', [])
            for agent_name in completed_tasks:
                if agent_name != 'coordinator':  # Skip coordinator as it's orchestration
                    # Estimate individual agent time (simplified)
                    estimated_agent_time = total_time / max(len([a for a in completed_tasks if a != 'coordinator']), 1)
                    
                    performance_evaluator.log_agent_call(
                        agent_name=agent_name,
                        success=True,
                        processing_time=estimated_agent_time,
                        error=None
                    )
            
            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "messages": result.get("messages", []),
                "completed_tasks": completed_tasks,
                "resume_analysis": result.get("resume_analysis", {}),
                "job_listings": result.get("job_listings", []),
                "cv_path": result.get("cv_path", ""),
                "job_market_data": result.get("job_market_data", {}),
                "comparison_results": result.get("comparison_results", {}),
                "processing_time": total_time,
                "performance_summary": self._generate_session_performance_summary(completed_tasks, total_time)
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            error_message = str(e)
            
            # Log system failure
            performance_evaluator.log_system_request(
                success=False, 
                request_time=total_time,
                human_intervention=False
            )
            
            # Log agent failures if we know which agent failed
            completed_tasks = initial_state.get('completed_tasks', [])
            if completed_tasks:
                last_agent = completed_tasks[-1] if completed_tasks else "unknown"
                if last_agent != 'coordinator':
                    performance_evaluator.log_agent_call(
                        agent_name=last_agent,
                        success=False,
                        processing_time=total_time,
                        error=error_message
                    )
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "session_id": session_id,
                "user_id": user_id,
                "error": error_message,
                "messages": [HumanMessage(content=f"System error: {error_message}")],
                "processing_time": total_time,
                "completed_tasks": completed_tasks
            }
    
    def collect_user_feedback(self, session_id: str, user_id: str, 
                            satisfaction: float, resume_helpful: bool = None, 
                            jobs_helpful: bool = None, would_use_again: bool = None) -> Dict[str, Any]:
        """
        Collect user feedback and update performance metrics
        """
        try:
            # Validate satisfaction score
            if not (1 <= satisfaction <= 10):
                return {
                    "success": False,
                    "error": "Satisfaction must be between 1 and 10"
                }
            
            # Create user outcome record
            outcome = UserOutcome(
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now(),
                user_satisfaction=satisfaction,
                resume_improved=resume_helpful,
                jobs_found_helpful=jobs_helpful,
                would_use_again=would_use_again
            )
            
            # Store outcome
            self.user_outcomes.append(outcome)
            
            # Log satisfaction in the performance evaluator
            performance_evaluator.log_user_satisfaction(satisfaction)
            
            return {
                "success": True,
                "message": "Feedback recorded successfully",
                "satisfaction_recorded": satisfaction,
                "feedback_summary": {
                    "session_id": session_id,
                    "satisfaction": satisfaction,
                    "resume_helpful": resume_helpful,
                    "jobs_helpful": jobs_helpful,
                    "would_use_again": would_use_again
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_outcomes_summary(self) -> Dict[str, Any]:
        """
        Get summary of user outcomes for this session
        """
        if not self.user_outcomes:
            return {
                "message": "No user feedback collected yet",
                "total_feedback": 0
            }
        
        total_outcomes = len(self.user_outcomes)
        
        # Calculate satisfaction metrics
        satisfaction_scores = [o.user_satisfaction for o in self.user_outcomes if o.user_satisfaction]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        # Calculate improvement rates
        resume_improved_count = sum(1 for o in self.user_outcomes if o.resume_improved)
        jobs_helpful_count = sum(1 for o in self.user_outcomes if o.jobs_found_helpful)
        would_use_again_count = sum(1 for o in self.user_outcomes if o.would_use_again)
        
        return {
            "total_feedback": total_outcomes,
            "avg_satisfaction": round(avg_satisfaction, 2),
            "satisfaction_distribution": {
                "excellent (9-10)": sum(1 for s in satisfaction_scores if s >= 9),
                "good (7-8)": sum(1 for s in satisfaction_scores if 7 <= s < 9),
                "fair (5-6)": sum(1 for s in satisfaction_scores if 5 <= s < 7),
                "poor (1-4)": sum(1 for s in satisfaction_scores if s < 5)
            },
            "helpfulness_rates": {
                "resume_improvement": round((resume_improved_count / total_outcomes) * 100, 1),
                "job_search_help": round((jobs_helpful_count / total_outcomes) * 100, 1),
                "user_retention": round((would_use_again_count / total_outcomes) * 100, 1)
            },
            "satisfaction_grade": self._grade_satisfaction(avg_satisfaction)
        }
    
    def get_system_effectiveness_report(self) -> Dict[str, Any]:
        """
        Get comprehensive system effectiveness report
        """
        try:
            # Get system performance from evaluator
            system_performance = performance_evaluator.get_system_performance_summary()
            
            # Get user outcomes
            user_outcomes = self.get_user_outcomes_summary()
            
            # Calculate effectiveness score
            effectiveness_score = self._calculate_effectiveness_score(system_performance, user_outcomes)
            
            # Get benchmark comparison
            benchmark_comparison = self._get_benchmark_comparison(system_performance)
            
            return {
                "effectiveness_score": effectiveness_score,
                "effectiveness_grade": self._grade_effectiveness(effectiveness_score),
                "system_performance": system_performance,
                "user_outcomes": user_outcomes,
                "benchmark_comparison": benchmark_comparison,
                "agent_performance": self._get_agent_performance_breakdown(),
                "recommendations": self._generate_recommendations(effectiveness_score, system_performance, user_outcomes),
                "report_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "fallback_report": performance_evaluator.get_comprehensive_report()
            }
    
    def _generate_session_performance_summary(self, completed_tasks: list, processing_time: float) -> Dict[str, Any]:
        """Generate performance summary for a single session"""
        return {
            "agents_used": len([task for task in completed_tasks if task != 'coordinator']),
            "total_processing_time": round(processing_time, 2),
            "avg_time_per_agent": round(processing_time / max(len([task for task in completed_tasks if task != 'coordinator']), 1), 2),
            "efficiency_rating": "excellent" if processing_time < 10 else "good" if processing_time < 20 else "fair"
        }
    
    def _calculate_effectiveness_score(self, system_performance: Dict[str, Any], user_outcomes: Dict[str, Any]) -> float:
        """Calculate overall system effectiveness score"""
        score = 0
        
        # System reliability (40% weight)
        success_rate = system_performance.get("success_rate", 0)
        if success_rate >= 90:
            score += 40
        elif success_rate >= 75:
            score += 30
        elif success_rate >= 60:
            score += 20
        elif success_rate >= 40:
            score += 10
        
        # User satisfaction (35% weight)
        user_satisfaction = user_outcomes.get("avg_satisfaction", 0)
        if user_satisfaction >= 8:
            score += 35
        elif user_satisfaction >= 6:
            score += 25
        elif user_satisfaction >= 4:
            score += 15
        elif user_satisfaction >= 2:
            score += 5
        
        # User helpfulness rates (25% weight)
        helpfulness = user_outcomes.get("helpfulness_rates", {})
        avg_helpfulness = sum(helpfulness.values()) / max(len(helpfulness), 1) if helpfulness else 0
        if avg_helpfulness >= 80:
            score += 25
        elif avg_helpfulness >= 60:
            score += 20
        elif avg_helpfulness >= 40:
            score += 15
        elif avg_helpfulness >= 20:
            score += 10
        
        return round(score, 1)
    
    def _get_benchmark_comparison(self, system_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Compare system performance against benchmarks"""
        benchmarks = {
            "target_satisfaction": 8.0,
            "target_success_rate": 90.0,
            "target_response_time": 15.0,
            "manual_resume_time": 60.0,  # minutes
            "manual_job_search_time": 120.0,  # minutes
            "system_resume_time": 2.0,  # minutes
            "system_job_search_time": 5.0  # minutes
        }
        
        actual_satisfaction = system_performance.get("user_satisfaction", 0)
        actual_success_rate = system_performance.get("success_rate", 0)
        actual_response_time = system_performance.get("avg_request_time", 0)
        
        return {
            "performance_vs_targets": {
                "satisfaction": {
                    "actual": actual_satisfaction,
                    "target": benchmarks["target_satisfaction"],
                    "status": "✅ Meeting target" if actual_satisfaction >= benchmarks["target_satisfaction"] else "⚠️ Below target"
                },
                "success_rate": {
                    "actual": actual_success_rate,
                    "target": benchmarks["target_success_rate"],
                    "status": "✅ Meeting target" if actual_success_rate >= benchmarks["target_success_rate"] else "⚠️ Below target"
                },
                "response_time": {
                    "actual": actual_response_time,
                    "target": benchmarks["target_response_time"],
                    "status": "✅ Meeting target" if actual_response_time <= benchmarks["target_response_time"] else "⚠️ Too slow"
                }
            },
            "efficiency_vs_manual": {
                "resume_analysis": {
                    "manual_time": benchmarks["manual_resume_time"],
                    "system_time": benchmarks["system_resume_time"],
                    "time_saved": benchmarks["manual_resume_time"] - benchmarks["system_resume_time"],
                    "efficiency_gain": f"{((benchmarks['manual_resume_time'] / benchmarks['system_resume_time']) - 1) * 100:.0f}% faster"
                },
                "job_search": {
                    "manual_time": benchmarks["manual_job_search_time"],
                    "system_time": benchmarks["system_job_search_time"],
                    "time_saved": benchmarks["manual_job_search_time"] - benchmarks["system_job_search_time"],
                    "efficiency_gain": f"{((benchmarks['manual_job_search_time'] / benchmarks['system_job_search_time']) - 1) * 100:.0f}% faster"
                }
            }
        }
    
    def _get_agent_performance_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown for all agents"""
        agent_names = ["resume_analyst", "job_researcher", "cv_creator", "job_matcher"]
        breakdown = {}
        
        for agent_name in agent_names:
            if agent_name in performance_evaluator.agent_metrics:
                breakdown[agent_name] = performance_evaluator.get_agent_performance_summary(agent_name)
            else:
                breakdown[agent_name] = {"message": "No data available"}
        
        return breakdown
    
    def _generate_recommendations(self, effectiveness_score: float, 
                                system_performance: Dict[str, Any], 
                                user_outcomes: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Overall system recommendations
        if effectiveness_score >= 85:
            recommendations.append("🎉 Excellent performance! System is highly effective. Continue current approach.")
        elif effectiveness_score >= 65:
            recommendations.append("✅ Good performance. System is effective with room for optimization.")
        else:
            recommendations.append("⚠️ System needs improvement. Focus on reliability and user satisfaction.")
        
        # Specific recommendations based on metrics
        if system_performance.get("success_rate", 0) < 80:
            recommendations.append("🔧 Improve system reliability - success rate below 80%. Review error patterns.")
        
        if user_outcomes.get("avg_satisfaction", 0) < 6:
            recommendations.append("😊 Enhance user experience - satisfaction below 6/10. Consider human-in-the-loop features.")
        
        if system_performance.get("avg_request_time", 0) > 20:
            recommendations.append("⚡ Optimize response time - currently above 20 seconds. Consider parallel processing.")
        
        helpfulness_rates = user_outcomes.get("helpfulness_rates", {})
        if helpfulness_rates.get("resume_improvement", 0) < 60:
            recommendations.append("📄 Improve resume analysis quality - users finding it less helpful.")
        
        if helpfulness_rates.get("job_search_help", 0) < 60:
            recommendations.append("🔍 Enhance job search relevance - users not finding job matches helpful.")
        
        if not recommendations or len(recommendations) == 1:
            recommendations.append("📊 Continue monitoring metrics and collecting user feedback for insights.")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _grade_satisfaction(self, score: float) -> str:
        """Grade user satisfaction score"""
        if score >= 8:
            return "Excellent"
        elif score >= 6:
            return "Good"
        elif score >= 4:
            return "Fair"
        else:
            return "Poor"
    
    def _grade_effectiveness(self, score: float) -> str:
        """Grade overall system effectiveness"""
        if score >= 85:
            return "Highly Effective"
        elif score >= 65:
            return "Effective"
        elif score >= 45:
            return "Moderately Effective"
        else:
            return "Needs Improvement"
    
    def get_performance_summary(self, result: Dict[str, Any]) -> str:
        """
        Get detailed performance and capability summary
        """
        completed = result.get("completed_tasks", [])
        if not completed:
            return "❌ No agents completed their tasks"
        
        capabilities_used = []
        
        if "resume_analyst" in completed:
            analysis = result.get("resume_analysis", {})
            score = analysis.get("overall_score", "N/A")
            capabilities_used.append(f"📊 Resume Analysis (Score: {score}/100)")
        
        if "job_researcher" in completed:
            market_data = result.get("job_market_data", {})
            jobs_found = market_data.get("total_jobs_found", 0)
            capabilities_used.append(f"🔍 Job Research ({jobs_found} opportunities)")
        
        if "cv_creator" in completed:
            cv_path = result.get("cv_path", "")
            status = "✅ Created" if cv_path else "❌ Failed"
            capabilities_used.append(f"📝 CV Creation ({status})")
        
        if "job_matcher" in completed:
            comparison = result.get("comparison_results", {})
            avg_score = comparison.get("average_score", 0)
            capabilities_used.append(f"🎯 Job Matching (Avg: {avg_score:.1f}%)")
        
        processing_time = result.get("processing_time", 0)
        performance_summary = result.get("performance_summary", {})
        
        summary = f"✅ Enhanced Performance Summary:\n" + "\n".join(capabilities_used)
        summary += f"\n⏱️ Processing Time: {processing_time:.2f}s"
        summary += f"\n🎭 Agents Used: {performance_summary.get('agents_used', 0)}"
        summary += f"\n⚡ Efficiency: {performance_summary.get('efficiency_rating', 'N/A').title()}"
        
        return summary
