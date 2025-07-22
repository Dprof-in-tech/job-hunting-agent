"""
Job Researcher Agent - Expert job market researcher with autonomous role detection
"""

import asyncio
import re
import time
from langchain_core.messages import AIMessage, SystemMessage
from .base import MultiAgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api.tools import search_google_jobs, llm


#########################################
# Agent 3: Job Researcher              #
#########################################

def job_researcher_agent(state: MultiAgentState):
    """Expert job market researcher with autonomous role detection"""
    
    analysis = state.get('resume_analysis', {})
    user_request = state.get('user_request', '').lower()
    resume_path = state.get('resume_path', '')

    if resume_path and not analysis:
        
        # Update coordinator plan to include resume_analyst before job_researcher
        plan = state.get('coordinator_plan', {})
        execution_order = plan.get('execution_order', [])
        
        # Insert resume_analyst before job_researcher if not already there
        if 'job_researcher' in execution_order:
            idx = execution_order.index('job_researcher')
            if 'resume_analyst' not in execution_order:
                execution_order.insert(idx, 'resume_analyst')
            elif execution_order.index('resume_analyst') > idx:
                # Move resume_analyst before job_researcher
                execution_order.remove('resume_analyst')
                execution_order.insert(idx, 'resume_analyst')
        else:
            if 'resume_analyst' not in execution_order:
                execution_order.append('resume_analyst')
            execution_order.append('job_researcher')
        
        plan['execution_order'] = execution_order
        
        return {
            **state,
            "coordinator_plan": plan,
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []),
            "messages": [AIMessage(content="🔍 **Job Researcher**: Resume analysis required first for optimal job market research. Requesting analysis...")] + state.get('messages', [])
        }
    
    # Use resume analysis if available, otherwise extract from user request
    if analysis and analysis.get('possible_jobs'):
        target_roles = analysis.get('possible_jobs', [])
        primary_role = target_roles[0] if target_roles else 'general'
    elif not resume_path:
        # LLM-based role extraction from user request
        role_extraction_prompt = f"""
            Extract the specific job role from this user request. If there is no specific role, you can analyze the user request to understand what they are aksing 
            about and infer a specific role from their request. Be specific and return a real job title.

            If the user is seeking trends or information in a specific industry, infer they work in that industry unless otherwise stated.

            USER REQUEST: {user_request}

            Examples of good responses: "software engineer", "data scientist", "marketing manager", "frontend developer"
            If you cant infer a specific role, return "UNCLEAR" to indicate the user needs to be more specific.
            Return only the job role name or "UNCLEAR".
        """
        
        try:
            response = llm.invoke([SystemMessage(content=role_extraction_prompt)])
            extracted_role = response.content.strip()
            primary_role = extracted_role.lower()
            
            # Check if role is unclear and request human clarification
            if primary_role == 'unclear' or not primary_role or len(primary_role.strip()) < 3:
                job_id = state.get('job_id')
                if job_id and _should_request_role_clarification(state):
                    return {
                        "next_agent": "HITL_APPROVAL", 
                        "hitl_checkpoint": "job_role_clarification",
                        "hitl_data": {
                            "user_request": user_request,
                            "extracted_role": extracted_role,
                            "clarification_message": f"I need help understanding what specific job role you're interested in.\n\nYour request: \"{user_request}\"\n\nPlease clarify the specific job title or role you'd like me to focus on (e.g., 'software engineer', 'marketing manager', 'data scientist')."
                        },
                        "completed_tasks": state.get('completed_tasks', []),
                        "messages": [AIMessage(content=f"🔍 **Job Role Clarification Needed**\n\nI need help understanding what specific job role you're interested in.\n\nYour request: \"{user_request}\"\n\n⏸️ Please clarify the specific job title or role you'd like me to focus on.")] + state.get('messages', [])
                    }
        except:
            primary_role = 'general'
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            jobs = loop.run_until_complete(search_google_jobs("remote", primary_role, 15))
        finally:
            loop.close()
        
        if not jobs:
            return {
                "messages": [AIMessage(content=f"❌ **Job Researcher**: No jobs found for {primary_role}. Try a different role or check your search terms.")] + state.get('messages', []),
                "next_agent": "coordinator",
                "completed_tasks": state.get('completed_tasks', []) + ['job_researcher']
            }
        
        # Enhanced market analysis
        companies = {}
        locations = {}
        all_descriptions = []
        
        for job in jobs:
            companies[job.company] = companies.get(job.company, 0) + 1
            locations[job.location] = locations.get(job.location, 0) + 1
            all_descriptions.append(job.description.lower())
        
        # Advanced keyword analysis
        all_text = " ".join(all_descriptions)
        words = re.findall(r'\b\w+\b', all_text)
        common_words = {'the', 'and', 'for', 'are', 'with', 'you', 'will', 'have', 'this', 'that', 'from', 'they', 'been', 'their', 'said', 'each', 'which', 'she', 'has', 'had'}
        word_freq = {}
        
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
        
        market_data = {
            "role_researched": primary_role,
            "total_jobs_found": len(jobs),
            "top_companies": sorted(companies.items(), key=lambda x: x[1], reverse=True)[:8],
            "popular_locations": sorted(locations.items(), key=lambda x: x[1], reverse=True)[:8],
            "in_demand_keywords": [kw[0] for kw in top_keywords],
            "market_insights": {
                "demand_level": "High" if len(jobs) > 10 else "Medium" if len(jobs) > 5 else "Low",
                "remote_percentage": round((sum(1 for job in jobs if "remote" in job.location.lower()) / len(jobs)) * 100, 1),
                "top_hiring_company": companies and max(companies.items(), key=lambda x: x[1])[0],
                "competition_level": "High" if len(set(companies.keys())) < len(jobs) * 0.7 else "Medium",
                "salary_transparency": round((sum(1 for job in jobs if job.salary != "Not specified") / len(jobs)) * 100, 1)
            },
            "analysis_mode": "resume_based" if analysis else "autonomous"
        }
        
        job_dicts = []
        for job in jobs[:10]:
            job_dicts.append({
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": job.description[:300] + "..." if len(job.description) > 300 else job.description,
                "apply_url": job.apply_url
            })
        
        
        top_companies_str = ", ".join([f"{comp} ({count})" for comp, count in market_data['top_companies'][:5]])
        top_keywords_str = ", ".join(market_data['in_demand_keywords'][:8])
        
        mode_indicator = "📊 (Based on your resume)" if analysis else "🔍 (Market research mode)"
        
        summary = f"""
            🔍 **Job Market Research Complete** {mode_indicator}

            **Role Analyzed:** {primary_role}
            **Opportunities Found:** {len(jobs)} positions
            **Market Demand:** {market_data['market_insights']['demand_level']}
            **Remote Work:** {market_data['market_insights']['remote_percentage']}% of positions

            **🏢 Top Hiring Companies:**
            {top_companies_str}

            **🔑 In-Demand Keywords:**
            {top_keywords_str}

            **📊 Market Insights:**
            • Demand level is {market_data['market_insights']['demand_level'].lower()}
            • {market_data['market_insights']['remote_percentage']}% offer remote work options
            • Competition level: {market_data['market_insights'].get('competition_level', 'Medium')}
            • Top hiring company: {market_data['market_insights'].get('top_hiring_company', 'Various')}
        """
        
        return {
            "job_market_data": market_data,
            "job_listings": job_dicts,
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher'],
            "next_agent": "coordinator",
            "messages": [AIMessage(content=summary)] + state.get('messages', [])
        }
        
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"❌ **Job Researcher**: Research failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher']
        }

def _should_request_role_clarification(state):
    """Determine if human clarification should be requested for job role extraction"""
    # For now, always request clarification when role is unclear
    return True