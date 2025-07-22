"""
Coordinator Agent - Orchestrates the entire multi-agent workflow
"""

import json
import time
from langchain_core.messages import AIMessage, SystemMessage
from .base import MultiAgentState
from api.tools import llm


#########################################
# Agent 1: Coordinator Agent           #
#########################################

def coordinator_agent(state: MultiAgentState):
    """Orchestrates the entire multi-agent workflow with smart dependency management"""
    
    if not state.get("coordinator_plan"):
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
        
        Here are some depemdency rules you can work with but you are not restricted to them. you can choose which agent to call when you think its neccessary.

        DEPENDENCY RULES:
        - If user wants job research but no resume is provided, only run job_researcher
        - If user wants job research AND resume is provided, run resume_analyst first, then job_researcher
        - If user wants CV creation, run resume_analyst first, then cv_creator
        - If user wants job matching, run resume_analyst, then job_researcher, then job_matcher
        - If user asks for market research only, run job_researcher (no dependencies)
        
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
                if job_id and _should_request_approval(state):
                    return {
                        "coordinator_plan": plan,
                        "next_agent": "HITL_APPROVAL",
                        "hitl_checkpoint": "coordinator_plan",
                        "hitl_data": {
                            "plan": plan,
                            "plan_summary": f"I'll {plan.get('primary_goal', 'help with your request')}.\n\nStrategy: {plan.get('reasoning', 'Execute the planned approach')}\n\nAgents needed: {' → '.join(plan.get('execution_order', []))}"
                        },
                        "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                        "messages": [AIMessage(content=f"📋 **Coordination Plan Created - Awaiting Your Approval**\n\n**Goal:** {plan.get('primary_goal')}\n\n**Strategy:** {plan.get('reasoning')}\n\n**Agents Needed:** {' → '.join(plan.get('execution_order', []))}\n\n⏸️ Please review and approve this plan to continue.")] + state.get('messages', [])
                    }
                else:
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
            return {
                "next_agent": "END",
                "completed_tasks": state.get('completed_tasks', []) + ['coordinator'],
                "messages": [AIMessage(content=f"❌ Coordination failed: {str(e)}")] + state.get('messages', [])
            }
    
    else:
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
    
def _should_request_approval(self, state: dict[str, any]) -> bool:
    """Determine if human approval should be requested for this job"""
    # For now, always request approval for coordinator plans
    # In the future, this could be configurable per user or based on complexity
    return True