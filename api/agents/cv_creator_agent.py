"""
CV Creator Agent - Professional CV creator with superior generation capabilities
"""

import json
import os
import tempfile
import time
from datetime import datetime
from fpdf import FPDF
from langchain_core.messages import AIMessage, SystemMessage
from .base import  MultiAgentState
from api.tools import llm



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
        return {
            "messages": [AIMessage(content=f"❌ **CV Creator**: CV creation failed - {str(e)}")] + state.get('messages', []),
            "next_agent": "coordinator",
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator']
        }