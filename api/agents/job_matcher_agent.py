"""
Job Matcher Agent - Expert job compatibility analyzer with superior matching algorithms
"""

import json
import time
from langchain_core.messages import AIMessage, SystemMessage
from .base import  MultiAgentState
from api.tools import llm


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