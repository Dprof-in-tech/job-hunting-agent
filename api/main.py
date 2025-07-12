from typing import Annotated, Union, Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import PyPDF2
from docx import Document
import asyncio
import aiohttp
import os
import re
from datetime import datetime
from dataclasses import dataclass
import json
import requests
import tempfile
from fpdf import FPDF
from langchain_core.runnables.config import RunnableConfig

config = RunnableConfig(recursion_limit=50)

from dotenv import load_dotenv
load_dotenv()

# Environment variables
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
SCRAPER_API_URL = "https://api.scraperapi.com/structured/google/jobs"
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
RAPID_API_URL="https://daily-international-job-postings.p.rapidapi.com/api/v2/jobs/search"

# Shared LLM instance
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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

#########################################
# Tools                   #
#########################################
@tool
def parse_resume(resume_path: str) -> str:
    """Parse PDF, DOCX, or TXT resume"""
    try:
        if resume_path.endswith('.pdf'):
            with open(resume_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        elif resume_path.endswith('.docx'):
            doc = Document(resume_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        elif resume_path.endswith('.txt'):
            with open(resume_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError("Resume must be PDF, DOCX, or TXT format")
    except Exception as e:
        return f"Resume parsing failed: {str(e)}"

@tool
def extract_location(job_data: str) -> str:
    """
    Extract location information from job data.
    
    Args:
        job_data: JSON string containing job information from API response
        
    Returns:
        Formatted location string (e.g., "San Francisco, California" or "Remote")
    """
    try:
        job = json.loads(job_data) if isinstance(job_data, str) else job_data
        
        # Try to get location from jobLocation in jsonLD
        json_ld = job.get("jsonLD", {})
        job_location = json_ld.get("jobLocation", {})
        
        if job_location:
            address = job_location.get("address", {})
            city = address.get("addressLocality", "")
            state = address.get("addressRegion", "")
            country = address.get("addressCountry", "")
            
            # Build location string
            location_parts = []
            if city:
                location_parts.append(city)
            if state:
                location_parts.append(state)
            if country and country != "United States":
                location_parts.append(country)
                
            if location_parts:
                return ", ".join(location_parts)
        
        # Fallback to direct fields
        city = job.get("city", "")
        state = job.get("state", "")
        
        if city and state:
            return f"{city}, {state}"
        elif city:
            return city
        elif state:
            return state
        
        # Check workplace type
        workplace = job.get("workPlace", [])
        if workplace and workplace[0] != "N/A":
            return f"Remote ({workplace[0]})"
        
        return "Remote"
        
    except Exception as e:
        return f"Location extraction error: {str(e)}"


@tool
def extract_salary(job_data: str) -> str:
    """
    Extract and format salary information from job data.
    
    Args:
        job_data: JSON string containing job information from API response
        
    Returns:
        Formatted salary string (e.g., "$75,000 - $105,000/year" or "$50.00/hr")
    """
    try:
        job = json.loads(job_data) if isinstance(job_data, str) else job_data
        
        # Try to get salary from jsonLD first (most detailed)
        json_ld = job.get("jsonLD", {})
        base_salary = json_ld.get("baseSalary", {})
        
        if base_salary:
            value = base_salary.get("value", {})
            min_value = value.get("minValue")
            max_value = value.get("maxValue")
            unit_text = value.get("unitText", "").upper()
            currency = base_salary.get("currency", "USD")
            
            if min_value and max_value:
                # Convert to proper format
                if unit_text == "HOUR":
                    if float(min_value) == float(max_value):
                        return f"${float(min_value):.2f}/hr"
                    else:
                        return f"${float(min_value):.2f} - ${float(max_value):.2f}/hr"
                elif unit_text == "YEAR":
                    if int(min_value) == int(max_value):
                        return f"${int(min_value):,}/year"
                    else:
                        return f"${int(min_value):,} - ${int(max_value):,}/year"
        
        # Fallback to direct minSalary field
        min_salary = job.get("minSalary")
        if min_salary:
            # Determine if it's hourly or yearly based on value
            if float(min_salary) < 200:  # Likely hourly
                return f"${float(min_salary):.2f}/hr"
            else:  # Likely yearly
                return f"${int(min_salary):,}/year"
        
        return "Salary not specified"
        
    except Exception as e:
        return f"Salary extraction error: {str(e)}"


@tool
def build_job_description(job_data: str) -> str:
    """
    Build a comprehensive job description from available job data.
    
    Args:
        job_data: JSON string containing job information from API response
        
    Returns:
        Formatted job description with key details
    """
    try:
        job = json.loads(job_data) if isinstance(job_data, str) else job_data
        
        description_parts = []
        
        # Add occupation/role
        occupation = job.get("occupation")
        if occupation and occupation != "N/A":
            description_parts.append(f"Role: {occupation}")
        
        # Add industry
        industry = job.get("industry")
        if industry and industry != "N/A":
            description_parts.append(f"Industry: {industry}")
        
        # Add contract type
        contract_type = job.get("contractType", [])
        if contract_type and contract_type[0] != "N/A":
            description_parts.append(f"Contract Type: {', '.join(contract_type)}")
        
        # Add work type
        work_type = job.get("workType", [])
        if work_type:
            description_parts.append(f"Work Type: {', '.join(work_type)}")
        
        # Add workplace
        workplace = job.get("workPlace", [])
        if workplace and workplace[0] != "N/A":
            description_parts.append(f"Workplace: {', '.join(workplace)}")
        
        # Add timezone if available
        timezone = job.get("timezone")
        if timezone:
            description_parts.append(f"Timezone: {timezone}")
        
        # Add skills
        skills = job.get("skills", [])
        if skills:
            skills_limited = skills[:5]  # Limit to first 5 skills
            description_parts.append(f"Key Skills: {', '.join(skills_limited)}")
            if len(skills) > 5:
                description_parts.append(f"(+{len(skills) - 5} more skills)")
        
        # Add benefits if available
        json_ld = job.get("jsonLD", {})
        benefits = json_ld.get("jobBenefits")
        if benefits:
            description_parts.append(f"Benefits: {benefits}")
        
        # Add employment type
        employment_type = json_ld.get("employmentType")
        if employment_type:
            description_parts.append(f"Employment: {employment_type}")
        
        # Add a portion of the actual job description if available
        full_description = json_ld.get("description", "")
        if full_description:
            # Extract first 300 characters of actual description
            clean_description = full_description.replace("\\n", " ").replace("\\n", "").strip()
            if len(clean_description) > 200:
                clean_description = clean_description[:300] + "..."
            description_parts.append(f"Description: {clean_description}")
        
        return " | ".join(description_parts) if description_parts else "No description available"
        
    except Exception as e:
        return f"Description building error: {str(e)}" 


async def search_google_jobs(location: str, job_role: str, max_jobs: int = 10) -> List[JobListing]:
    # """Search Google Jobs via ScraperAPI"""
    """Search Google Jobs via RapidAPI"""
    jobs = []
    # query = job_role
    querystring = {"format":"json","countryCode":"us","hasSalary":"true","title": job_role, "page":"1"}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "daily-international-job-postings.p.rapidapi.com"
    }
    # payload = {'api_key': SCRAPER_API_KEY, 'query': query}

    try:
        # response = requests.get(SCRAPER_API_URL, params=payload)
        response = requests.get(RAPID_API_URL, headers=headers, params=querystring)
        response.raise_for_status() 
        data = response.json()
        job_results = data.get("result", [])
        
        for job in job_results[:max_jobs]:
            try:
                job_json = json.dumps(job)
                # Extract location information with fallback
                location_info = extract_location.invoke({"job_data": job_json}) 
                
                # Extract salary information with proper handling
                salary_info = extract_salary.invoke({"job_data": job_json})

                
                # Extract skills from the job data
                skills = job.get("skills", [])
                skills_str = ", ".join(skills) if skills else "Not specified"
                
                # Build comprehensive description
                description = build_job_description.invoke({"job_data": job_json})
                jobs.append(JobListing(
                    title=job.get("title", "Unknown Position"),
                    company=job.get("company", "Unknown Company"),
                    location=location_info,
                    description=description,
                    salary=salary_info,
                    apply_url=job.get("jsonLD", {}).get("url", ""),
                    source="Jobs via RapidAPI",
                    date_found=datetime.now()
                ))
                 # for scraper api
                # jobs.append(JobListing(
                #     title=job.get("title", "Unknown"),
                #     company=job.get("company_name", "Unknown"),
                #     location=job.get("location", "Remote"),
                #     description=job.get("description", ""),
                #     salary="Not specified",
                #     apply_url=job.get("link", ""),
                #     source="Google Jobs via ScraperAPI",
                #     date_found=datetime.now()
                # ))
            except Exception as e:
                print(f"⚠️ Error parsing job result: {e}")
                continue
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")

    return jobs

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
                print(f"🎯 Coordinator Plan: {plan.get('primary_goal', 'Unknown goal')}")
                print(f"📋 Execution Order: {' → '.join(plan.get('execution_order', []))}")
                
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
            print(f"❌ Coordinator error: {e}")
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
        
        print(f"🔄 Coordinator routing to: {next_agent}")
        
        return {
            "next_agent": next_agent,
            "completed_tasks": completed,
            "messages": state.get('messages', [])
        }

#########################################
# Agent 2: Resume Analyst              #
#########################################

def resume_analyst_agent(state: MultiAgentState):
    """Expert resume analyst with superior analysis capabilities"""
    
    resume_path = state.get('resume_path', '')
    if not resume_path or not os.path.exists(resume_path):
        return {
            "messages": [AIMessage(content="❌ **Resume Analyst**: No valid resume file provided")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
        }
    
    resume_content = parse_resume(resume_path)
    
    # RESTORED SUPERIOR PROMPT FROM SINGLE-AGENT SYSTEM
    analysis_prompt = f"""You are an expert HR Manager / Recruiter with 25 years of experience recruiting top talents for top firms across the world.
    Analyze this resume against actual world recognized standard and your very standard hiring experience.
    
    RESUME CONTENT:
    {resume_content}
    
    Provide detailed analysis as JSON:
    {{
        "overall_score": 85,
        "resume_strengths": ["What parts of the resume are working well?"],
        "resume_weaknesses": ["What's missing or weak in the resume?"],
        "keyword_optimization": ["What keywords should be added based on actual job market demands?"],
        "experience_gaps": ["What experience gaps are evident from industry standards?"],
        "formatting_issues": ["How can the resume format/structure be improved?"],
        "market_alignment": "How well does this resume match current market demands?",
        "specific_improvements": ["Detailed, actionable changes to make"],
        "possible_jobs": ["List 1-3 job roles this resume is best suited for"],
        "target_roles": ["primary job roles based on experience"],
        "career_level": "entry/mid/senior/executive",
        "industry_focus": "primary industry based on experience",
        "ats_compatibility": {{
            "score": 90,
            "issues": ["ATS compatibility issues"],
            "recommendations": ["ATS optimization recommendations"]
        }},
        "next_steps": ["actionable step 1", "actionable step 2"]
    }}
    
    Be thorough, specific, and actionable in your analysis. Focus on real-world hiring standards.
    The end goal is to optimize this Resume to help this user get a job.
    """
    
    try:
        print("🔍 **Resume Analyst**: Starting comprehensive analysis...")
        
        response = llm.invoke([SystemMessage(content=analysis_prompt)])
        content = response.content
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            analysis = json.loads(content.strip())
            
            print(f"✅ **Resume Analyst**: Analysis complete. Score: {analysis.get('overall_score', 'N/A')}/100")
            
            summary = f"""
                📊 **Resume Analysis Complete**

                **Overall Score:** {analysis.get('overall_score', 'N/A')}/100
                **Career Level:** {analysis.get('career_level', 'Unknown').title()}
                **Industry Focus:** {analysis.get('industry_focus', 'Not specified')}

                **🟢 Key Strengths:**
                {chr(10).join(f"• {strength}" for strength in analysis.get('resume_strengths', [])[:3])}

                **🟡 Areas for Improvement:**
                {chr(10).join(f"• {weakness}" for weakness in analysis.get('resume_weaknesses', [])[:3])}

                **🎯 Target Roles Identified:**
                {', '.join(analysis.get('target_roles', ['Not specified']))}

                **ATS Compatibility:** {analysis.get('ats_compatibility', {}).get('score', 'N/A')}/100
            """
            
            return {
                "resume_content": resume_content,
                "resume_analysis": analysis,
                "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst'],
                "next_agent": "coordinator",
                "messages": [AIMessage(content=summary)] + state.get('messages', [])
            }
            
        except json.JSONDecodeError:
            return {
                "messages": [AIMessage(content="❌ **Resume Analyst**: Failed to parse analysis results")] + state.get('messages', []),
                "next_agent": "coordinator",
                "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
            }
            
    except Exception as e:
        print(f"❌ Resume Analyst error: {e}")
        return {
            "messages": [AIMessage(content=f"❌ **Resume Analyst**: Analysis failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
        }

#########################################
# Agent 3: Job Researcher              #
#########################################

def job_researcher_agent(state: MultiAgentState):
    """Expert job market researcher with autonomous role detection"""
    
    analysis = state.get('resume_analysis', {})
    user_request = state.get('user_request', '').lower()
    resume_path = state.get('resume_path', '')

    if resume_path and not analysis:
        print("🔍 **Job Researcher**: Resume provided but not analyzed yet. Requesting resume analysis first...")
        
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
        print(f"🔍 **Job Researcher**: Using resume analysis for role: {primary_role}")
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
            primary_role = response.content.strip().lower()
            print(f"🔍 **Job Researcher**: Extracted role from request: {primary_role}")
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
        
        print(f"✅ **Job Researcher**: Found {len(jobs)} opportunities, analyzed market trends")
        
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
        print(f"❌ Job Researcher error: {e}")
        return {
            "messages": [AIMessage(content=f"❌ **Job Researcher**: Research failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['job_researcher']
        }

#########################################
# Agent 4: CV Creator                  #
#########################################

def cv_creator_agent(state: MultiAgentState):
    """Professional CV creator with superior generation capabilities"""
    
    resume_content = state.get('resume_content', '')
    analysis = state.get('resume_analysis', {})
    market_data = state.get('job_market_data', {})
    resume_path = state.get('resume_path', '')
    
    if not resume_content and resume_path:
        print("📝 **CV Creator**: Resume analysis needed first, triggering dependency...")
        plan = state.get('coordinator_plan', {})
        execution_order = plan.get('execution_order', [])
        
        if 'resume_analyst' not in execution_order:
            if 'cv_creator' in execution_order:
                idx = execution_order.index('cv_creator')
                execution_order.insert(idx, 'resume_analyst')
            else:
                execution_order.append('resume_analyst')
            plan['execution_order'] = execution_order
            
        return {
            "coordinator_plan": plan,
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []),
            "messages": [AIMessage(content="📝 **CV Creator**: Requesting resume analysis first to create optimal CV...")] + state.get('messages', [])
        }
    
    if not resume_content or not analysis:
        return {
            "messages": [AIMessage(content="❌ **CV Creator**: Missing resume content or analysis data. Please provide a resume file.")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator']
        }
    
    print("📝 **CV Creator**: Creating optimized CV...")
    
    # RESTORED AND ENHANCED SUPERIOR PROMPT FROM SINGLE-AGENT SYSTEM
    cv_prompt = f"""
    You are a professional recruiter with 25 years of experience.

    TASK: Create an ATS-optimized CV that will get this candidate hired.

    ORIGINAL RESUME:
    {resume_content}

    ANALYSIS INSIGHTS:
    {json.dumps(analysis, indent=2)}

    MARKET DATA:
    {json.dumps(market_data, indent=2) if market_data else "No market data available"}

    REQUIREMENTS:
    1. Implement ALL suggestions from the analysis
    2. Include keywords from keyword_optimization and market research
    3. Address ALL weaknesses identified in the analysis
    4. Enhance and amplify ALL strengths mentioned
    5. Format for ATS compatibility (simple formatting, standard sections)
    6. Use professional language
    7. Avoid complicated buzzwords and use normal day to day words as much as possible
    8. Include specific achievements and metrics wherever possible
    9. Target the identified career level and roles
    10. Integrate in-demand keywords from job market research

    OUTPUT FORMAT - these are example section headers:
    
    CONTACT INFORMATION
    [Full Name]
    [Phone] | [Email] | [LinkedIn] | [Location]
    
    PROFESSIONAL SUMMARY
    [2-3 compelling sentences highlighting key qualifications and career goals that address the role requirements]
    
    PROFESSIONAL EXPERIENCE
    [Job Title]
    [Company Name] | [Employment Dates]
    • [Achievement-focused bullet point with specific metrics and results]
    • [Another achievement with quantifiable impact using action verbs]
    • [Third achievement showing progression and responsibility growth]
    
    KEY SKILLS
    Technical Skills: [skill1, skill2, skill3 - include keywords from market research]
    Soft Skills: [skill1, skill2, skill3 - relevant to target roles]
    Industry Knowledge: [relevant industry skills and knowledge areas]
    
    EDUCATION
    [Degree] | [Institution] | [Graduation Year]
    [Relevant coursework, honors, or certifications if applicable]
    
    [Additional relevant sections as needed - Certifications, Projects, etc.]

    Make this CV irresistible to recruiters and ATS systems.
    Focus on specific achievements, quantifiable results, and market-relevant keywords.
    Every bullet point should demonstrate value and impact.
    """
    
    try:
        response = llm.invoke([SystemMessage(content=cv_prompt)])
        cv_content = response.content
        
        # Enhanced PDF generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=10)
        
        try:
            clean_content = cv_content.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, clean_content)
        except UnicodeEncodeError:
            pdf.multi_cell(0, 5, cv_content.encode('ascii', 'ignore').decode('ascii'))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(tempfile.gettempdir(), f"optimized_cv_{timestamp}.pdf")
        pdf.output(filename)
        
        print(f"✅ **CV Creator**: Professional CV generated at {filename}")
        
        # Enhanced summary with comprehensive integration details
        market_integration = ""
        if market_data:
            keywords_count = len(market_data.get('in_demand_keywords', [])[:10])
            market_integration = f"• Integrated {keywords_count} market-relevant keywords\n• Optimized for {market_data.get('role_researched', 'target')} market\n"
        
        weaknesses_addressed = len(analysis.get('resume_weaknesses', []))
        strengths_enhanced = len(analysis.get('resume_strengths', []))
        
        summary = f"""
            📝 **Professional CV Created & Optimized**

            **✅ Comprehensive Optimizations Applied:**
            • Addressed {weaknesses_addressed} key weaknesses identified in analysis
            • Enhanced {strengths_enhanced} core strengths for maximum impact
            {market_integration}• Achieved ATS compatibility score improvement
            • Applied professional language with day-to-day terminology
            • Added achievement-focused content with quantifiable metrics
            • Implemented all specific improvements from analysis

            **📄 CV Details:**
            • File location: {filename}
            • Target roles: {', '.join(analysis.get('target_roles', ['General']))}
            • Career level: {analysis.get('career_level', 'Not specified').title()}
            • Industry focus: {analysis.get('industry_focus', 'Multi-industry')}

            **🎯 Ready for Applications!**
            Your CV is now optimized for both human recruiters and ATS systems, with market-relevant keywords and compelling achievement-focused content.
        """
        
        return {
            "cv_path": filename,
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator'],
            "next_agent": "coordinator",
            "messages": [AIMessage(content=summary)] + state.get('messages', [])
        }
        
    except Exception as e:
        print(f"❌ CV Creator error: {e}")
        return {
            "messages": [AIMessage(content=f"❌ **CV Creator**: CV creation failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator']
        }

#########################################
# Agent 5: Job Matcher                 #
#########################################

def job_matcher_agent(state: MultiAgentState):
    """Expert job compatibility analyzer with superior matching algorithms"""
    
    resume_content = state.get('resume_content', '')
    job_listings = state.get('job_listings', [])
    resume_path = state.get('resume_path', '')
    
    # Smart dependency management
    missing_deps = []
    
    if not resume_content and resume_path:
        missing_deps.append('resume_analyst')
    
    if not job_listings:
        missing_deps.append('job_researcher')
    
    if missing_deps:
        print(f"🎯 **Job Matcher**: Missing dependencies: {missing_deps}, triggering them...")
        
        plan = state.get('coordinator_plan', {})
        execution_order = plan.get('execution_order', [])
        
        if 'job_matcher' in execution_order:
            idx = execution_order.index('job_matcher')
            for dep in reversed(missing_deps):
                if dep not in execution_order:
                    execution_order.insert(idx, dep)
        else:
            execution_order.extend(missing_deps)
        
        plan['execution_order'] = execution_order
        
        return {
            "coordinator_plan": plan,
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []),
            "messages": [AIMessage(content=f"🎯 **Job Matcher**: Requesting {' and '.join(missing_deps)} first to enable comprehensive job compatibility analysis...")] + state.get('messages', [])
        }
    
    if not resume_content or not job_listings:
        return {
            "messages": [AIMessage(content="❌ **Job Matcher**: Missing required data for job matching analysis.")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['job_matcher']
        }
    
    print("🎯 **Job Matcher**: Analyzing job compatibility with enhanced matching...")
    
    # Enhanced analysis of top jobs
    top_jobs = job_listings[:3]
    match_results = []
    
    for i, job in enumerate(top_jobs):
        # ENHANCED SUPERIOR PROMPT FOR JOB MATCHING
        match_prompt = f"""
        You are an expert job matching specialist with 20+ years of experience in recruitment and career counseling.
        
        TASK: Perform comprehensive resume-to-job fit analysis against actual industry standards
        
        RESUME:
        {resume_content}
        
        JOB POSTING:
        Title: {job['title']}
        Company: {job['company']}
        Location: {job['location']}
        Description: {job['description']}
        
        Analyze the fit based on real-world hiring criteria and provide JSON response:
        {{
            "match_percentage": 85,
            "fit_level": "excellent/good/fair/poor",
            "matching_skills": ["specific skills that directly match job requirements"],
            "missing_skills": ["critical skills needed but not present in resume"],
            "matching_experience": ["relevant experience that aligns with job needs"],
            "experience_gaps": ["experience areas that need development"],
            "strengths_for_role": ["candidate's strongest points for this specific role"],
            "weaknesses_for_role": ["areas where candidate may struggle in this role"],
            "application_strategy": ["specific strategies for applying to this job"],
            "interview_prep_points": ["key points to prepare for interview"],
            "resume_customization_tips": ["how to tailor resume for this specific job"],
            "salary_expectation": "realistic salary range based on experience and market",
            "likelihood_of_success": "high/medium/low with reasoning",
            "next_steps": ["immediate actionable steps to improve chances"]
        }}
        
        Be brutally honest and specific. Focus on what recruiters actually look for.
        """
        
        try:
            response = llm.invoke([SystemMessage(content=match_prompt)])
            content = response.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            match_analysis = json.loads(content.strip())
            match_analysis['job_title'] = job['title']
            match_analysis['company'] = job['company']
            match_results.append(match_analysis)
            
        except Exception as e:
            print(f"❌ Error analyzing job {i+1}: {e}")
            continue
    
    if not match_results:
        return {
            "messages": [AIMessage(content="❌ **Job Matcher**: Failed to analyze job compatibility")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['job_matcher']
        }
    
    # Enhanced comprehensive analysis
    best_match = max(match_results, key=lambda x: x.get('match_percentage', 0))
    avg_match = sum(r.get('match_percentage', 0) for r in match_results) / len(match_results)
    
    # Calculate additional insights
    high_matches = [r for r in match_results if r.get('match_percentage', 0) >= 70]
    excellent_fits = [r for r in match_results if r.get('fit_level', '').lower() == 'excellent']
    
    summary = f"""
        🎯 **Comprehensive Job Compatibility Analysis Complete**

        **Analysis Overview:**
        • Analyzed {len(match_results)} top opportunities
        • Average Match Score: {avg_match:.1f}%
        • High-fit positions (70%+): {len(high_matches)}
        • Excellent fits: {len(excellent_fits)}

        **🥇 Best Match: {best_match['job_title']} at {best_match['company']}**
        • **Match Score:** {best_match.get('match_percentage', 0)}%
        • **Fit Level:** {best_match.get('fit_level', 'Unknown').title()}
        • **Success Likelihood:** {best_match.get('likelihood_of_success', 'Not assessed').title()}

        **🟢 Your Strongest Assets for This Role:**
        {chr(10).join(f"• {strength}" for strength in best_match.get('strengths_for_role', [])[:3])}

        **🟡 Skills to Develop:**
        {chr(10).join(f"• {skill}" for skill in best_match.get('missing_skills', [])[:3])}

        **📋 Strategic Application Approach:**
        {chr(10).join(f"• {strategy}" for strategy in best_match.get('application_strategy', [])[:3])}

        **🎤 Interview Preparation Focus:**
        {chr(10).join(f"• {point}" for point in best_match.get('interview_prep_points', [])[:3])}

        **📝 Resume Customization Tips:**
        {chr(10).join(f"• {tip}" for tip in best_match.get('resume_customization_tips', [])[:2])}

        **💰 Expected Salary Range:** {best_match.get('salary_expectation', 'Market rate based on experience')}

        **🎯 Immediate Next Steps:**
        {chr(10).join(f"• {step}" for step in best_match.get('next_steps', [])[:3])}
    """
    
    print(f"✅ **Job Matcher**: Analysis complete. Best match: {best_match.get('match_percentage', 0)}%")
    
    return {
        "comparison_results": {
            "matches": match_results,
            "best_match": best_match,
            "average_score": avg_match,
            "high_fit_count": len(high_matches),
            "excellent_fit_count": len(excellent_fits),
            "analysis_summary": {
                "total_analyzed": len(match_results),
                "recommendation": "excellent" if best_match.get('match_percentage', 0) >= 80 else "good" if best_match.get('match_percentage', 0) >= 60 else "consider_improvement"
            }
        },
        "completed_tasks": state.get('completed_tasks', []) + ['job_matcher'],
        "next_agent": "coordinator",
        "messages": [AIMessage(content=summary)] + state.get('messages', [])
    }

#########################################
# Multi-Agent Orchestration System     #
#########################################

def should_continue(state: MultiAgentState):
    """Enhanced routing with smart decision making"""
    next_agent = state.get('next_agent', 'END')
    
    print(f"🔄 Routing decision: {next_agent}")
    
    if next_agent == 'END':
        return END
    
    agent_map = {
        'coordinator': 'coordinator',
        'resume_analyst': 'resume_analyst', 
        'job_researcher': 'job_researcher',
        'cv_creator': 'cv_creator',
        'job_matcher': 'job_matcher'
    }
    
    return agent_map.get(next_agent, END)

def create_multi_agent_system():
    """Create the enhanced multi-agent orchestration system"""
    
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
    
    # All agents route back to coordinator for intelligent next decision
    graph.add_edge("resume_analyst", "coordinator")
    graph.add_edge("job_researcher", "coordinator")
    graph.add_edge("cv_creator", "coordinator")
    graph.add_edge("job_matcher", "coordinator")
    
    return graph.compile()

#########################################
# Enhanced Main Interface              #
#########################################

class JobHuntingMultiAgent:
    """
    Enhanced multi-agent job hunting system with superior performance
    """
    
    def __init__(self):
        self.system = create_multi_agent_system()
        print("🚀 Enhanced Multi-Agent Job Hunting System Initialized")
        print("📋 Specialists: Coordinator, Resume Analyst, Job Researcher, CV Creator, Job Matcher")
        print("✨ Performance: Superior prompts, intelligent routing, comprehensive analysis")
    
    def process_request(self, user_message: str, resume_path: str = None) -> Dict[str, Any]:
        """
        Process user request with enhanced multi-agent coordination
        """
        
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
            "next_agent": "coordinator"
        }
        
        try:
            print(f"\n🎯 Processing Request: {user_message[:100]}...")
            print("="*60)
            
            result = self.system.invoke(initial_state, config)
            
            print("\n" + "="*60)
            print("✅ Enhanced Multi-Agent Processing Complete!")
            print(f"🎭 Completed Tasks: {', '.join(result.get('completed_tasks', []))}")
            
            return {
                "success": True,
                "messages": result.get("messages", []),
                "completed_tasks": result.get("completed_tasks", []),
                "resume_analysis": result.get("resume_analysis", {}),
                "job_listings": result.get("job_listings", []),
                "cv_path": result.get("cv_path", ""),
                "job_market_data": result.get("job_market_data", {}),
                "comparison_results": result.get("comparison_results", {})
            }
            
        except Exception as e:
            print(f"❌ Multi-agent processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "messages": [HumanMessage(content=f"System error: {str(e)}")]
            }
    
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
        
        return f"✅ Enhanced Performance Summary:\n" + "\n".join(capabilities_used)