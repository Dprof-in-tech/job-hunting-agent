"""
Job Researcher Agent - Expert job market researcher with autonomous role detection
"""

import asyncio
import re
import time
import html
from langchain_core.messages import AIMessage, SystemMessage
from .base import MultiAgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api.tools import search_google_jobs, llm
from api.ai_safety import safe_ai_wrapper, AISafetyCoordinator


#########################################
# Agent 3: Job Researcher              #
#########################################

@safe_ai_wrapper(agent_name="job_researcher", safety_level="high")
def job_researcher_agent(state: MultiAgentState):
    """Expert job market researcher with autonomous role detection and career advice"""
    
    analysis = state.get('resume_analysis', {})
    user_request = state.get('user_request', '').lower()
    # Sanitize user input to prevent prompt injection
    user_request_safe = html.escape(user_request).strip()
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
            "completed_tasks": state.get('completed_tasks', []),
            "messages": [AIMessage(content="🔍 **Job Researcher**: Resume analysis required first for optimal job market research. Requesting analysis...")] + state.get('messages', [])
        }
    
    # Detect career transition scenarios first
    transition_patterns = [
        'transition from', 'switch from', 'change from', 'move from', 'pivot from',
        'go from', 'shift from', 'leave', 'career change', 'career switch',
        'transition to', 'switch to', 'change to', 'move to', 'pivot to',
        'go to', 'shift to', 'enter', 'break into', 'get into'
    ]
    
    is_career_transition = any(pattern in user_request_safe for pattern in transition_patterns)
    
    # Extract target industry/field from career transition requests
    primary_role = None
    if is_career_transition:
        transition_prompt = f"""
            This user wants to make a career transition. Extract the TARGET field/industry they want to transition TO.
            
            USER REQUEST: {user_request_safe}
            
            Look for phrases like:
            - "from X to Y" -> focus on Y
            - "transition to Y" -> focus on Y  
            - "move into Y" -> focus on Y
            - "switch to Y" -> focus on Y
            
            Common target fields: finance, marketing, sales, healthcare, education, consulting, etc.
            
            If they want to transition to a specific field but don't mention a specific role, ask for clarification about what kind of role in that field.
            
            Return the target field/industry or "NEEDS_CLARIFICATION" if unclear.
            Examples: "finance", "marketing", "healthcare", "NEEDS_CLARIFICATION"
        """
        
        try:
            response = llm.invoke([SystemMessage(content=transition_prompt)])
            target_field = response.content.strip().lower()
            
            if target_field == "needs_clarification" or not target_field:
                job_id = state.get('job_id')
                if job_id and _should_request_role_clarification(state):
                    return {
                        "next_agent": "HITL_APPROVAL", 
                        "hitl_checkpoint": "job_role_clarification",
                        "hitl_data": {
                            "user_request": user_request_safe,
                            "extracted_role": target_field,
                            "clarification_message": f"I understand you want to make a career transition, but I need clarification about your target.\n\nYour request: \"{user_request_safe}\"\n\nPlease specify:\n1. What field/industry do you want to transition TO? (e.g., finance, marketing, healthcare)\n2. What type of role in that field interests you? (e.g., 'investment banker', 'marketing manager', 'financial analyst')\n\nFor example: 'I want to transition from tech to investment banking' or 'I want to move into financial analysis roles'"
                        },
                        "completed_tasks": state.get('completed_tasks', []),
                        "messages": [AIMessage(content=f"🔍 **Career Transition Clarification Needed**\n\nI understand you want to make a career transition, but I need more details.\n\nYour request: \"{user_request_safe}\"\n\n⏸️ Please specify what field and role you want to transition TO.")] + state.get('messages', [])
                    }
            
            # For career transitions, we need to clarify the specific role within the target field
            primary_role = target_field
        except Exception:
            primary_role = 'general'
    
    # Use resume analysis if available and not a career transition
    elif analysis and analysis.get('possible_jobs') and not is_career_transition:
        target_roles = analysis.get('possible_jobs', [])
        primary_role = target_roles[0] if target_roles else 'general'
    elif not resume_path and not is_career_transition:
        # LLM-based role extraction from user request
        role_extraction_prompt = f"""
            Extract the specific job role from this user request. If there is no specific role, you can analyze the user request to understand what they are asking 
            about and infer a specific role from their request. Be specific and return a real job title.

            If the user is seeking trends or information in a specific industry, infer they work in that industry unless otherwise stated.

            USER REQUEST: {user_request_safe}

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
                            "user_request": user_request_safe,
                            "extracted_role": extracted_role,
                            "clarification_message": f"I need help understanding what specific job role you're interested in.\n\nYour request: \"{user_request_safe}\"\n\nPlease clarify the specific job title or role you'd like me to focus on (e.g., 'software engineer', 'marketing manager', 'data scientist')."
                        },
                        "completed_tasks": state.get('completed_tasks', []),
                        "messages": [AIMessage(content=f"🔍 **Job Role Clarification Needed**\n\nI need help understanding what specific job role you're interested in.\n\nYour request: \"{user_request_safe}\"\n\n⏸️ Please clarify the specific job title or role you'd like me to focus on.")] + state.get('messages', [])
                    }
        except Exception:
            primary_role = 'general'
    
    # Determine if this is a career advice/transition request vs job search request
    career_advice_keywords = [
        'advice', 'guidance', 'transition', 'switch', 'change career', 'move into', 
        'how to', 'should i', 'what skills', 'learn', 'prepare', 'break into',
        'skills needed', 'requirements', 'qualifications', 'experience needed',
        'roadmap', 'path', 'steps to', 'become'
    ]
    
    is_career_advice_request = any(keyword in user_request_safe for keyword in career_advice_keywords)
    
    # Check if user explicitly wants job listings
    job_search_keywords = ['find jobs', 'job listings', 'opportunities', 'openings', 'positions', 'vacancies', 'hiring']
    explicit_job_search = any(keyword in user_request_safe for keyword in job_search_keywords)
    
    if is_career_advice_request and not explicit_job_search:
        # Provide career advice and market insights without job listings
        return _provide_career_advice(state, primary_role, user_request_safe)
    
    try:
        # Traditional job search flow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            jobs = loop.run_until_complete(search_google_jobs("remote", primary_role, 15))
        finally:
            loop.close()
        
        if not jobs:
            # If no jobs found, still provide career advice about the role
            return _provide_career_advice(state, primary_role, user_request_safe, fallback_mode=True)
        
        # If user wants both job listings AND advice, provide enhanced response
        if is_career_advice_request:
            return _provide_jobs_with_advice(state, jobs, primary_role, user_request_safe)
        
        # Traditional job listings response
        return _provide_job_listings(state, jobs, primary_role)
    
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"❌ **Job Researcher**: Research failed - {str(e)}")] + state.get('messages', []),
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher']
        }


def _provide_career_advice(state: MultiAgentState, role: str, user_request: str, fallback_mode: bool = False):
    """Provide career advice and market insights without job listings"""
    
    # Detect if this is a career transition request
    transition_patterns = [
        'transition from', 'switch from', 'change from', 'move from', 'pivot from',
        'go from', 'shift from', 'leave', 'career change', 'career switch',
        'transition to', 'switch to', 'change to', 'move to', 'pivot to',
        'go to', 'shift to', 'enter', 'break into', 'get into'
    ]
    is_career_transition = any(pattern in user_request for pattern in transition_patterns)
    
    # Get current background from resume analysis if available
    current_background = "technology" if state.get('resume_analysis') else "your current field"
    if state.get('resume_analysis', {}).get('industry_focus'):
        current_background = state['resume_analysis']['industry_focus'].split(';')[0].strip()
    
    if is_career_transition:
        career_advice_prompt = f"""
        You are a senior career advisor with 20+ years of experience specializing in career transitions. 
        
        USER REQUEST: {user_request}
        TARGET FIELD/INDUSTRY: {role}
        CURRENT BACKGROUND: {current_background}

        {"Note: No job listings were found for this field, so focus on career guidance." if fallback_mode else ""}

        This person wants to TRANSITION INTO {role} from {current_background}. Provide comprehensive transition guidance covering:
        
        1. Overview of the {role} industry and typical entry-level roles for career changers
        2. Skills and qualifications needed to break into {role} (emphasize what's most important for career switchers)
        3. How to leverage transferable skills from {current_background} when transitioning to {role}
        4. Educational requirements and recommended courses/certifications for career changers
        5. Realistic career path and timeline for someone transitioning into {role}
        6. Market trends and demand in {role} (especially opportunities for career switchers)
        7. Salary expectations for entry-level positions in {role} for career changers
        8. Key companies and industries in {role} that are open to hiring career changers
        9. Networking strategies specific to breaking into {role} from another field
        10. Common interview questions for career changers entering {role}
        11. Day-to-day responsibilities in typical {role} roles
        12. Potential challenges and how to overcome them when switching to {role}

        Important: Focus on PURE {role} roles, not hybrid roles that combine {current_background} with {role}. 
        For example, if someone wants to transition from tech to finance, focus on roles like investment banking, 
        financial analysis, wealth management - NOT fintech or financial software development.

        Be specific, actionable, realistic about the challenges, and encouraging. Provide a clear roadmap for making this transition successfully. Your response should be brief and concise. Don't say too much that would be a bore to read.
        """
    else:
        career_advice_prompt = f"""
        You are a senior career advisor with 20+ years of experience. Provide comprehensive career guidance for someone interested in {role}.

        USER REQUEST: {user_request}
        TARGET ROLE: {role}

        {"Note: No job listings were found for this role, so focus on career guidance." if fallback_mode else ""}

        Provide detailed career advice covering:
        1. Skills and qualifications needed for {role}
        2. Career path and progression options
        3. Educational requirements and recommended courses/certifications  
        4. Market trends and demand for this role
        5. Salary expectations and growth potential
        6. How to break into this field or transition from another field
        7. Key companies and industries that hire for this role
        8. Networking and job search strategies
        9. Common interview questions and preparation tips
        10. Day-to-day responsibilities and work environment

        Be specific, actionable, and encouraging. Provide real-world advice that helps someone succeed in this career path. Your response should be brief and concise. Don't say too much that would be a bore to read.
        """
    
    try:
        response = llm.invoke([SystemMessage(content=career_advice_prompt)])
        advice_content = response.content
        
        if is_career_transition:
            mode_indicator = "🔄 (Career Transition Guide)"
            guidance_type = f"Transition from {current_background} to {role.title()}"
            next_steps_focus = role
        else:
            mode_indicator = "📚 (Career Guidance Mode)"
            guidance_type = 'Market Analysis + Career Path' if not fallback_mode else 'Comprehensive Career Guide'
            next_steps_focus = role
        
        summary = f"""
        💼 **Career Advice & Market Insights** {mode_indicator}

        **Focus:** {guidance_type}
        
        {advice_content}
        
        **🎯 Next Steps:**
        Based on this guidance, consider whether you'd like me to:
        • Find specific job opportunities in the {next_steps_focus} field
        • Analyze your resume for transitioning to {next_steps_focus} roles
        • Create a tailored CV for {next_steps_focus} positions
        """

        return {
            "job_market_data": {
                "role_researched": role,
                "analysis_mode": "career_transition" if is_career_transition else "career_advice",
                "advice_provided": True,
                "market_insights": {
                    "advice_type": "career_transition" if is_career_transition else "career_guidance",
                    "target_field": role,
                    "source_field": current_background if is_career_transition else None,
                    "transition_guidance": is_career_transition
                }
            },
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher'],
            "messages": [AIMessage(content=summary)] + state.get('messages', [])
        }
        
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"❌ **Job Researcher**: Career advice generation failed - {str(e)}")] + state.get('messages', []),
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher']
        }


def _provide_jobs_with_advice(state: MultiAgentState, jobs, role: str, user_request: str):
    """Provide job listings combined with career advice"""
    
    # Sanitize user input to prevent prompt injection
    user_request_safe = html.escape(user_request).strip()
    
    # Get traditional job market data
    job_result = _provide_job_listings(state, jobs, role)
    
    # Generate additional career advice
    advice_prompt = f"""
    Based on {len(jobs)} current job openings for {role}, provide strategic career advice:

    USER REQUEST: {user_request_safe}
    
    Focus on:
    1. How to stand out in this competitive market
    2. Key skills that appear most frequently in current job postings
    3. Career transition strategies if applicable
    4. Application and interview tips specific to this role
    5. Salary negotiation insights
    
    Keep it concise but actionable.
    """
    
    try:
        response = llm.invoke([SystemMessage(content=advice_prompt)])
        advice_content = response.content
        
        # Combine job listings with career advice
        enhanced_message = job_result['messages'][0].content + f"""
        
        **💡 Strategic Career Advice:**
        {advice_content}
        """
        
        # Update the message
        job_result['messages'][0].content = enhanced_message
        
        return job_result
        
    except Exception:
        # Fallback to just job listings if advice generation fails
        return job_result


def _provide_job_listings(state: MultiAgentState, jobs, role: str):
    """Provide traditional job listings with market analysis"""
    
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
    
    # Create job dictionaries for safety verification
    job_dicts = []
    for job in jobs[:10]:
        job_dicts.append({
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description[:300] + "..." if len(job.description) > 300 else job.description,
            "apply_url": job.apply_url
        })
    
    # Apply AI safety checks to job market data
    safety_coordinator = AISafetyCoordinator()
    
    # Prepare job data for verification
    job_data_for_verification = {
        'job_listings': job_dicts,
        'role': role,
        'demand_level': 'High' if len(jobs) > 10 else 'Medium' if len(jobs) > 5 else 'Low',
        'job_count': len(jobs)
    }
    hallucination_check = safety_coordinator.hallucination_detector.check_salary_claims(job_data_for_verification)
    
    # Check for any bias in job recommendations
    job_descriptions_text = ' '.join([job.description for job in jobs[:5]])
    bias_check = safety_coordinator.fairness_monitor.detect_job_listing_bias(
        job_listings=job_descriptions_text,
        role=role
    )
    
    market_data = {
        "role_researched": role,
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
        "analysis_mode": "resume_based" if state.get('resume_analysis') else "autonomous",
        "ai_safety": {
            'hallucination_check': hallucination_check.__dict__,
            'bias_check': bias_check.__dict__,
            'data_quality_score': safety_coordinator._calculate_data_quality_score(jobs),
            'safety_warnings': []
        }
    }
    
    # Add safety warnings if needed
    if not hallucination_check.verified:
        market_data['ai_safety']['safety_warnings'].append("Market demand claims need verification")
    
    if bias_check.bias_detected:
        market_data['ai_safety']['safety_warnings'].append(f"Potential bias in job listings: {bias_check.bias_type}")
    
    
    top_companies_str = ", ".join([f"{comp} ({count})" for comp, count in market_data['top_companies'][:5]])
    top_keywords_str = ", ".join(market_data['in_demand_keywords'][:8])
    
    mode_indicator = "📊 (Based on your resume)" if state.get('resume_analysis') else "🔍 (Market research mode)"
    
    safety_status = '🛡️ Verified' if hallucination_check.verified and not bias_check.bias_detected else '⚠️ Review Needed'
    data_quality = market_data['ai_safety']['data_quality_score']
    
    summary = f"""
        🔍 **Job Market Research Complete** {mode_indicator}

        **Role Analyzed:** {role}
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
        • Competition level: {market_data['market_insights']['competition_level']}
        • Top hiring company: {market_data['market_insights']['top_hiring_company']}
        
        **🛡️ AI Safety:** {safety_status} | Data Quality: {data_quality}%
    """
    
    return {
        "job_market_data": market_data,
        "job_listings": job_dicts,
        "completed_tasks": state.get('completed_tasks', []) + ['job_researcher'],
        "messages": [AIMessage(content=summary)] + state.get('messages', [])
    }


def _should_request_role_clarification(state):
    """Determine if human clarification should be requested for job role extraction"""
    # For now, always request clarification when role is unclear
    # Future: Could check state conditions like previous clarifications, user preferences, etc.
    _ = state  # Parameter reserved for future use
    return True