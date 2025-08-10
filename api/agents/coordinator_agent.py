"""
Coordinator Agent - Orchestrates the entire multi-agent workflow
"""

import json
import time
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.types import interrupt
from .base import MultiAgentState
from api.tools import llm
from api.ai_safety import safe_ai_wrapper, AISafetyCoordinator
import logging

logger = logging.getLogger(__name__)


#########################################
# Agent 1: Coordinator Agent           #
#########################################

@safe_ai_wrapper(agent_name="coordinator", safety_level="medium")
def coordinator_agent(state: MultiAgentState):
    """Orchestrates the entire multi-agent workflow with smart dependency management"""
    
    # Check if we should create a new plan or use existing one
    coordinator_plan = state.get("coordinator_plan")
    has_plan = bool(coordinator_plan)
    is_rejected = state.get("plan_rejected", False)
    should_create_new_plan = not has_plan or is_rejected
    
    
    if should_create_new_plan:
        coordinator_prompt = f"""
        You are the Coordinator Agent in a multi-agent job hunting system. Your role is to:
        1. Analyze user requests and determine what they need
        2. Create an execution plan using available specialist agents
        3. Route tasks to appropriate agents in logical order
        4. Handle dependencies automatically
        
        you have access to and control of the below available specialist agents.

        AVAILABLE SPECIALIST AGENTS:
        - resume_analyst: Analyzes resumes for strengths, weaknesses, and improvements (REQUIRED for most other agents)
        - job_researcher: Searches and analyzes job markets and opportunities  
        - cv_creator: Generates professional, tailored CVs (requires resume_analyst)
        - job_matcher: Compares resumes against specific job descriptions (requires resume_analyst and job_researcher)
        
        USER REQUEST: {state.get('user_request', 'No specific request')}
        RESUME PROVIDED: {state.get('resume_path', 'None')}
        
        {f"PREVIOUS PLAN WAS REJECTED. USER FEEDBACK: {state.get('user_feedback', '')}" if state.get('plan_rejected') else ""}
        {f"Please create a REVISED plan that addresses the user's feedback above." if state.get('plan_rejected') else ""}
        
        Here are some depemdency rules you can work with but you are not restricted to them. you can choose which agent to call when you think its neccessary.

        DEPENDENCY RULES:
        - If user wants job research but no resume is provided, only run job_researcher
        - If user wants job research for their CURRENT field AND resume is provided, run resume_analyst first, then job_researcher
        - If user wants CV creation, run resume_analyst first, then cv_creator
        - If user wants job matching, run resume_analyst, then job_researcher, then job_matcher
        - If user asks for market research only, run job_researcher (no dependencies)
        
        CAREER TRANSITION RULES:
        - If user mentions "transition", "change career", "switch to", "move into", or similar language, this is a CAREER TRANSITION
        - For career transitions: run job_researcher FIRST to understand the target field, then resume_analyst to see how current skills transfer
        - Career transition flow: job_researcher (target field) → resume_analyst (skill transfer analysis) → cv_creator (transition-focused CV)
        
        Based on the user request, determine:
        1. Which agents should be involved
        2. What order they should execute in (respecting dependencies)
        3. What the primary goal is
        4. What the next immediate step should be
        
        Respond with a JSON plan:
        {{
            "primary_goal": "description of main objective",
            "agents_needed": ["agent1", "agent2", "agent3"],
            "execution_order": ["agent1", "agent2", "agent3"],
            "next_agent": "immediate_next_agent",
            "task_for_next_agent": "specific task description",
            "reasoning": "why this plan makes sense"
        }}
        """
        
        try:
            response = llm.invoke([SystemMessage(content=coordinator_prompt)])
            content = response.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            try:
                plan = json.loads(content.strip())
                
                # Check if HITL is enabled for this job
                job_id = state.get('job_id')
                should_request = _should_request_approval(state) if job_id else False
                
                if job_id and _should_request_approval(state):
                    
                    # CRITICAL: Store plan in state BEFORE interrupt (since interrupt stops execution)
                    # We need to return the state with the plan stored, then trigger interrupt
                    updated_state = {
                        "coordinator_plan": plan,
                        "next_agent": plan.get('next_agent', 'END'),
                        "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                        "messages": [AIMessage(content=f"📋 **Coordination Plan Created**\n\n**Goal:** {plan.get('primary_goal')}\n\n**Strategy:** {plan.get('reasoning')}\n\n**Agents Needed:** {' → '.join(plan.get('execution_order', []))}")] + state.get('messages', [])
                    }
                    
                    # Store the plan data for the approval
                    plan_data = {
                        "plan": plan,
                        "plan_summary": f"I'll {plan.get('primary_goal', 'help with your request')}.\n\nStrategy: {plan.get('reasoning', 'Execute the planned approach')}\n\nAgents needed: {' → '.join(plan.get('execution_order', []))}"
                    }
                    
                    # Use LangGraph's interrupt system with proper approval handling
                    approval_response = interrupt({
                        "checkpoint": "coordinator_plan",
                        "data": plan_data,
                        "job_id": job_id,
                        "message": f"📋 **Coordination Plan Created - Awaiting Your Approval**\n\n**Goal:** {plan.get('primary_goal')}\n\n**Strategy:** {plan.get('reasoning')}\n\n**Agents Needed:** {' → '.join(plan.get('execution_order', []))}\n\n⏸️ Please review and approve this plan to continue."
                    })
                    
                    # If we reach here, the interrupt was resumed - process the approval
                    
                    # Handle rejection - modify plan based on feedback
                    if not approval_response.get("approved", True):
                        # Mark as rejected and add feedback to state
                        updated_state.update({
                            "plan_rejected": True,
                            "user_feedback": approval_response.get("feedback", "User requested modifications"),
                            "completed_tasks": []  # Reset to allow re-planning
                        })
                        return updated_state
                    
                    # Plan was approved - ensure plan is saved and mark as approved
                    updated_state.update({
                        "plan_rejected": False,
                        "user_feedback": "",  # Clear any previous feedback
                        "next_agent": plan.get('next_agent', 'END'),  # Ensure next_agent is set correctly
                    })
                    return updated_state
                
                # This will only execute if no interrupt occurred or after approval
                return {
                    "coordinator_plan": plan,
                    "next_agent": plan.get('next_agent', 'END'),
                    "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                    "messages": [AIMessage(content=f"📋 **Coordination Plan Created**\n\n**Goal:** {plan.get('primary_goal')}\n\n**Strategy:** {plan.get('reasoning')}\n\n**Agents Needed:** {' → '.join(plan.get('execution_order', []))}")] + state.get('messages', [])
                }
                
            except json.JSONDecodeError:
                user_request = state.get('user_request', '').lower()
                resume_provided = bool(state.get('resume_path'))
                
                if 'market' in user_request or 'research' in user_request:
                    next_agent = 'job_researcher'
                elif resume_provided and ('analyze' in user_request or 'resume' in user_request):
                    next_agent = 'resume_analyst'
                elif resume_provided and ('cv' in user_request or 'create' in user_request):
                    next_agent = 'resume_analyst'
                else:
                    next_agent = 'job_researcher'
                
                return {
                    "next_agent": next_agent,
                    "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                    "messages": [AIMessage(content="📋 **Coordinator Active** - Creating execution plan and routing to specialist agents...")] + state.get('messages', [])
                }
                
        except Exception as e:
            # Check if this is an interrupt - let it bubble up
            if "Interrupt" in str(e) or "interrupt" in str(type(e).__name__.lower()):
                raise e
            
            return {
                "next_agent": "END",
                "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                "messages": [AIMessage(content=f"❌ Coordination failed: {str(e)}")] + state.get('messages', [])
            }
    
    else:
        # Check if we're in the middle of HITL approval process
        if state.get("next_agent") == "HITL_APPROVAL":
            return {
                "next_agent": "HITL_APPROVAL",
                "completed_tasks": state.get('completed_tasks', []),
                "messages": state.get('messages', []),
                "hitl_checkpoint": state.get("hitl_checkpoint"),
                "hitl_data": state.get("hitl_data"),
                "coordinator_plan": state.get("coordinator_plan", {})
            }
        
        plan = state.get("coordinator_plan", {})
        completed = state.get("completed_tasks", [])
        execution_order = plan.get("execution_order", [])
        
        next_agent = "END"
        for agent in execution_order:
            if agent not in completed:
                next_agent = agent
                break
        
        return {
            "next_agent": next_agent,
            "completed_tasks": completed,
            "messages": state.get('messages', [])
        }
    
def _should_request_approval(state: dict[str, any]) -> bool:
    """Determine if human approval should be requested for this job"""
    # Only request approval for the initial plan creation, not on subsequent coordinator runs
    # This prevents endless approval loops after user approves
    
    # Check if we're in a revision flow (user requested changes)
    if state.get('plan_rejected', False):
        # For revisions, always request approval for the new plan
        return True
    
    # Check if coordinator plan already exists and was approved
    # (coordinator_plan exists means we've already created a plan before)
    if state.get('coordinator_plan'):
        return False
    
    # Check if we already have completed tasks (meaning execution has started)
    # If so, don't request approval again - we're in execution phase
    completed_tasks = state.get('completed_tasks', [])
    if completed_tasks and 'coordinator' in completed_tasks:
        return False
        
    # For new plans, always request approval
    return True