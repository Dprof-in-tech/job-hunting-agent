"""
Resume Analyst Agent - Expert resume analysis with superior capabilities
"""

import json
import os
import time
from langchain_core.messages import AIMessage, SystemMessage
from .base import MultiAgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api.tools import parse_resume, llm



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
        
        response = llm.invoke([SystemMessage(content=analysis_prompt)])
        content = response.content
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        try:
            analysis = json.loads(content.strip())
            
            
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
        return {
            "messages": [AIMessage(content=f"❌ **Resume Analyst**: Analysis failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
        }