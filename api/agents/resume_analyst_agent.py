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
from api.ai_safety import safe_ai_wrapper, AISafetyCoordinator



#########################################
# Agent 2: Resume Analyst              #
#########################################

@safe_ai_wrapper(agent_name="resume_analyst", safety_level="high")
def resume_analyst_agent(state: MultiAgentState):
    """Expert resume analyst with superior analysis capabilities"""
    
    resume_path = state.get('resume_path', '')
    if not resume_path or not os.path.exists(resume_path):
        return {
            "messages": [AIMessage(content="❌ **Resume Analyst**: No valid resume file provided")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
        }
    
    resume_content = parse_resume.invoke(resume_path)
    
    # Check if this is a career transition scenario (job_researcher has already run)
    job_market_data = state.get('job_market_data', {})
    is_career_transition = bool(job_market_data) and 'job_researcher' in state.get('completed_tasks', [])
    target_role = job_market_data.get('role_researched', '') if is_career_transition else ''
    
    # RESTORED SUPERIOR PROMPT FROM SINGLE-AGENT SYSTEM with career transition awareness
    if is_career_transition:
        analysis_prompt = f"""You are an expert Career Transition Coach and HR Manager with 25 years of experience helping professionals switch careers successfully.
        
        CAREER TRANSITION CONTEXT:
        The user wants to transition INTO: {target_role}
        Target field research shows: {job_market_data.get('market_insights', {}).get('demand_level', 'Unknown')} demand
        Required skills for target field: {', '.join(job_market_data.get('in_demand_keywords', [])[:10])}
        
        CURRENT RESUME CONTENT:
        {resume_content}
        
        Analyze this resume specifically for CAREER TRANSITION to {target_role}. Focus on:
        1. Which current skills/experiences transfer well to {target_role}
        2. What gaps need to be addressed for {target_role}
        3. How to reposition current experience for {target_role}
        4. What additional skills/certifications are needed
        
        Provide detailed analysis as JSON:
        {{
            "overall_score": 85,
            "resume_strengths": ["Transferable skills and experiences for {target_role}"],
            "resume_weaknesses": ["What's missing for {target_role} transition?"],
            "keyword_optimization": ["Keywords needed for {target_role} field"],
            "experience_gaps": ["Experience gaps for {target_role} based on market research"],
            "formatting_issues": ["How to reformat resume for {target_role}"],
            "market_alignment": "How well does this resume align with {target_role} market demands based on research?",
            "specific_improvements": ["Detailed changes to make for {target_role} transition"],
            "possible_jobs": ["{target_role} related roles this resume could target"],
            "target_roles": ["roles in {target_role} field based on transferable skills"],
            "career_level": "entry/mid/senior/executive for {target_role}",
            "industry_focus": "{target_role} industry transition path",
            "transition_strategy": "How to successfully transition to {target_role}",
            "skill_gaps": ["Skills to develop for {target_role}"],
            "ats_compatibility": {{
                "score": 90,
                "issues": ["ATS compatibility issues for {target_role} applications"],
                "recommendations": ["ATS optimization for {target_role} field"]
            }},
            "next_steps": ["actionable steps for {target_role} transition"]
        }}
        """
    else:
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
            
            # Apply AI safety checks to the analysis
            safety_coordinator = AISafetyCoordinator()
            
            # Check for bias in scoring and recommendations
            bias_check = safety_coordinator.fairness_monitor.detect_resume_scoring_bias(
                resume_text=resume_content,
                score=analysis.get('overall_score', 0),
                recommendations=analysis.get('specific_improvements', [])
            )
            
            # Verify claims about job market and requirements
            market_data = {
                'market_alignment': analysis.get('market_alignment', ''),
                'keyword_optimization': analysis.get('keyword_optimization', []),
                'context': "resume_analysis"
            }
            hallucination_check = safety_coordinator.hallucination_detector.check_market_claims(market_data)
            
            # Add safety metadata to analysis
            analysis['ai_safety'] = {
                'bias_check': bias_check.__dict__,
                'hallucination_check': hallucination_check.__dict__,
                'confidence_score': safety_coordinator._calculate_confidence_score(analysis),
                'safety_warnings': []
            }
            
            # Add warnings if needed
            if bias_check.bias_detected:
                analysis['ai_safety']['safety_warnings'].append(f"Potential bias detected: {bias_check.bias_type}")
            
            if not hallucination_check.verified:
                analysis['ai_safety']['safety_warnings'].append("Some job market claims could not be verified")
            
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
                
                **🛡️ AI Safety:** Confidence {analysis['ai_safety']['confidence_score']:.1f}% | Bias Check: {'⚠️ ' + bias_check.bias_type if bias_check.bias_detected else '✅ Clear'}
            """
            
            return {
                "resume_content": resume_content,
                "resume_analysis": analysis,
                "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst'],
                "messages": [AIMessage(content=summary)] + state.get('messages', [])
            }
            
        except json.JSONDecodeError:
            return {
                "messages": [AIMessage(content="❌ **Resume Analyst**: Failed to parse analysis results")] + state.get('messages', []),
                "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
            }
            
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"❌ **Resume Analyst**: Analysis failed - {str(e)}")] + state.get('messages', []),
            "completed_tasks": state.get('completed_tasks', []) + ['resume_analyst']
        }