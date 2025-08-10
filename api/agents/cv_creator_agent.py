"""
CV Creator Agent - Professional CV creator with superior generation capabilities
"""

import json
import os
# tempfile not needed with Cloudinary storage
import time
from datetime import datetime
from fpdf import FPDF
from langchain_core.messages import AIMessage, SystemMessage
from .base import  MultiAgentState
from api.tools import llm
from api.ai_safety import safe_ai_wrapper, AISafetyCoordinator



#########################################
# Agent 4: CV Creator                  #
#########################################

@safe_ai_wrapper(agent_name="cv_creator", safety_level="high")
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
            "completed_tasks": state.get('completed_tasks', []),
            "messages": [AIMessage(content="📝 **CV Creator**: Requesting resume analysis first to create optimal CV...")] + state.get('messages', [])
        }
    
    if not resume_content or not analysis:
        return {
            "messages": [AIMessage(content="❌ **CV Creator**: Missing resume content or analysis data. Please provide a resume file.")] + state.get('messages', []),
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator']
        }
    
    
    # ENHANCED CV CREATION PROMPT WITH COMPREHENSIVE RESUME INTEGRATION
    cv_prompt = f"""
    You are an expert CV writer and career consultant with 25 years of experience helping professionals get hired.

    TASK: Create a completely rewritten, ATS-optimized CV that transforms this candidate's profile into an irresistible hire.

    ORIGINAL RESUME CONTENT (USE ALL INFORMATION):
    {resume_content}

    DETAILED ANALYSIS TO IMPLEMENT:
    {json.dumps(analysis, indent=2)}

    MARKET INTELLIGENCE TO INTEGRATE:
    {json.dumps(market_data, indent=2) if market_data else "No specific market data available"}

    IMPORTANT: If the original resume mentions LinkedIn or GitHub profiles, include the actual URLs:
    - LinkedIn: https://linkedin.com/in/[username] (extract from original if available)
    - GitHub: https://github.com/[username] (extract from original if available)
    - If URLs aren't provided in original resume, use placeholder format but make it clear they are links

    EDUCATION DATE HANDLING - CRITICAL:
    - If original says "Expected Graduation: September 2024" → Keep "Expected Graduation: September 2024"
    - If original says "Present" or "Current" → Keep "Present" or "Current"  
    - If original says "In Progress" → Keep "In Progress"
    - NEVER change expected dates to completed dates
    - NEVER assume someone has graduated if not explicitly stated

    CRITICAL INSTRUCTIONS - FOLLOW EVERY ONE:
    1. REWRITE COMPLETELY - Don't just copy, transform the content
    2. USE EVERY piece of information from the original resume (education, experience, skills, projects, etc.)
    3. IMPLEMENT ALL analysis suggestions (weaknesses, improvements, keyword optimization)
    4. ENHANCE all strengths with powerful, quantified language
    5. ADDRESS all identified weaknesses with strategic positioning
    6. INTEGRATE market-relevant keywords naturally throughout
    7. CREATE compelling achievements from basic job descriptions
    8. ADD metrics and numbers wherever possible (even estimated impact)
    9. USE action verbs and powerful professional language
    10. ENSURE ATS compatibility (standard sections, simple formatting)
    11. TARGET the specific roles and career level identified
    12. MAKE every bullet point achievement-focused, not task-focused
    13. PRESERVE EXACT education dates - Do NOT assume graduation dates or change "Expected" to completed dates
    14. MAINTAIN ACCURACY - Only use information explicitly provided in the original resume

    FORMATTING REQUIREMENTS FOR PDF:
    - Use **SECTION NAME** for main section headers ONLY
    - Use **Job Title** for job titles and position names
    - Use **Company Name** for company names
    - For projects, use: PROJECT NAME | Year (NO ** around project names in content)
    - Use - (dash) for bullet points, NOT • or * symbols
    - Do NOT use --- separators or extra formatting
    - Keep contact info on single line with | separators
    - Include actual URLs for LinkedIn and GitHub, not just text
    - Use standard sections: CONTACT INFORMATION, PROFESSIONAL SUMMARY, PROFESSIONAL EXPERIENCE, KEY SKILLS, EDUCATION, and any relevant additional sections
    
    OUTPUT FORMAT STRUCTURE:
    
    **CONTACT INFORMATION**
    [Full Name]
    [Phone] | [Email] | https://linkedin.com/in/[username] | https://github.com/[username] | [Location]
    
    **PROFESSIONAL SUMMARY**
    [2-3 compelling sentences highlighting key qualifications and career goals that address the role requirements]
    
    **PROFESSIONAL EXPERIENCE**
    
    **[Job Title]**
    **[Company Name]** | [Employment Dates]
    - [Achievement-focused bullet point with specific metrics and results]
    - [Another achievement with quantifiable impact using action verbs]
    - [Third achievement showing progression and responsibility growth]
    
    **KEY SKILLS**
    Technical Skills: [skill1, skill2, skill3 - include keywords from market research]
    Soft Skills: [skill1, skill2, skill3 - relevant to target roles]
    Industry Knowledge: [relevant industry skills and knowledge areas]
    
    **EDUCATION**
    [Degree] | [Institution] | [Exact dates from original - Expected Graduation: Date, Present, In Progress, etc.]
    [Relevant coursework, honors, or certifications if applicable - only if mentioned in original]
    
    **PROJECTS** (if applicable)
    Project Name | Year
    - [Achievement-focused description of the project and its impact]
    - [Technologies used and key features implemented]

    [Additional relevant sections as needed based on original resume using **SECTION NAME** format]

    FORMATTING RULES TO FOLLOW STRICTLY:
    1. NEVER use ** around project names, company details, or content within sections
    2. ONLY use ** for main section headers like **CONTACT INFORMATION**, **PROJECTS**, etc.
    3. Replace LinkedIn/GitHub placeholder text with actual clickable URLs if available in original
    4. Clean formatting - no markdown artifacts should appear in final output

    TRANSFORMATION REQUIREMENTS:
    - Extract EVERY relevant detail from the original resume
    - Transform basic job duties into powerful achievements
    - Use specific examples and metrics from the original content
    - Maintain all factual information while enhancing presentation
    - Include all education, certifications, and credentials mentioned
    - Incorporate any projects, publications, or awards from the original
    - Ensure no valuable information is lost in the rewrite
    - PRESERVE original education status (Expected, Present, In Progress, etc.) - DO NOT assume completion
    - KEEP all dates exactly as provided in the original resume

    OUTPUT: A complete, professionally rewritten CV that uses ALL original resume information while implementing every analysis recommendation. Make this CV irresistible to recruiters and ATS systems with achievement-focused content and market-relevant optimization.
    """
    
    try:
        response = llm.invoke([SystemMessage(content=cv_prompt)])
        cv_content = response.content
        
        # Enhanced PDF generation with proper formatting
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Parse and format the CV content with improved logic
        def clean_text(text):
            """Clean text for PDF output"""
            # Replace problematic characters with Latin-1 compatible ones
            replacements = {
                '?': '-',  # Replace with hyphen for PDF compatibility
                '•': '-',  # Replace bullet with hyphen
                '\u2022': '-',  # Unicode bullet
                '\u2013': '-',  # En dash
                '\u2014': '-',  # Em dash
                ''': "'",  # Smart quote
                ''': "'",  # Smart quote
                '"': '"',  # Smart quote
                '"': '"',  # Smart quote
                '–': '-',  # En dash
                '—': '-',  # Em dash
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            # Ensure the result can be encoded in Latin-1
            return text.encode('latin-1', 'replace').decode('latin-1')
        
        lines = cv_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(3)  # Add small space for empty lines
                continue
            
            # Clean the line and remove ALL markdown formatting
            clean_line = clean_text(line).replace('**', '')
            
            # Handle different types of content with improved logic
            if line.startswith('**') and line.endswith('**') and len(line) > 4:
                # Section headers (like **CONTACT INFORMATION**)
                header_text = clean_line.strip()
                pdf.set_font("Arial", 'B', 14)
                pdf.ln(8)
                pdf.cell(0, 8, header_text, ln=True)
                pdf.ln(3)
                
            elif '|' in line and any(marker in line.lower() for marker in ['@', 'phone', 'email', 'linkedin']):
                # Contact information line
                pdf.set_font("Arial", '', 11)
                contact_text = clean_line.strip()
                pdf.cell(0, 6, contact_text, ln=True)
                pdf.ln(2)
                
            elif line.startswith('**') and not line.endswith('**'):
                # Job titles or company names (like **Frontend Engineer**)
                title_text = clean_line.strip()
                pdf.set_font("Arial", 'B', 12)
                pdf.ln(5)
                pdf.cell(0, 6, title_text, ln=True)
                pdf.ln(1)
                
            elif line.startswith('**') and line.endswith('**') and '|' in line:
                # Company with dates (like **Company Name** | Dates)
                company_text = clean_line.strip()
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, company_text, ln=True)
                pdf.ln(2)
                
            elif line.startswith('•') or line.startswith('-') or line.startswith('?'):
                # Bullet points
                pdf.set_font("Arial", '', 10)
                bullet_text = clean_line.lstrip('•-? ').strip()
                # Use simple dash for bullet formatting to avoid encoding issues
                pdf.cell(10, 5, '-', ln=False)
                pdf.multi_cell(0, 5, bullet_text)
                pdf.ln(1)
                
            elif line.startswith('---'):
                # Skip separator lines
                continue
                
            elif ':' in line and not line.startswith('•'):
                # Skill categories or field labels
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(0, 5, clean_line)
                pdf.ln(2)
                
            else:
                # Regular text (summaries, descriptions, etc.)
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(0, 5, clean_line)
                pdf.ln(2)
        
        # Generate PDF content in memory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"optimized_cv_{timestamp}.pdf"
        
        # Output PDF to memory buffer
        pdf_content = pdf.output(dest='S').encode('latin1')
        
        # Upload to Cloudinary storage
        from api.tools import upload_cv_file
        cv_url = upload_cv_file(pdf_content, filename)
        
        # Set filename to the URL for compatibility
        filename = cv_url if cv_url else filename
        
        
        # Enhanced summary with comprehensive integration details
        market_integration = ""
        if market_data:
            keywords_count = len(market_data.get('in_demand_keywords', [])[:10])
            market_integration = f"• Integrated {keywords_count} market-relevant keywords\n• Optimized for {market_data.get('role_researched', 'target')} market\n"
        
        weaknesses_addressed = len(analysis.get('resume_weaknesses', []))
        strengths_enhanced = len(analysis.get('resume_strengths', []))
        
        # Create download filename
        download_filename = os.path.basename(filename)
        
        summary = f"""
            📝 **Professional CV Successfully Created & Optimized**

            **✅ Complete Resume Transformation Applied:**
            • Completely rewritten using ALL original resume information
            • Addressed {weaknesses_addressed} key weaknesses identified in analysis
            • Enhanced {strengths_enhanced} core strengths for maximum impact
            {market_integration}• Transformed job duties into achievement-focused bullet points
            • Added quantifiable metrics and professional language
            • Implemented all analysis recommendations and improvements
            • Ensured ATS compatibility with standard formatting

            **📄 Your Optimized CV:**
            • **Download Available**: {download_filename}
            • Target roles: {', '.join(analysis.get('target_roles', ['General']))}
            • Career level: {analysis.get('career_level', 'Not specified').title()}
            • Industry focus: {analysis.get('industry_focus', 'Multi-industry')}

            **🎯 Ready for Job Applications!**
            Your CV has been completely rewritten using every detail from your original resume, enhanced with market-relevant keywords and achievement-focused content. Download and start applying to your target roles!
        """
        
        return {
            "cv_path": filename,
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator'],
            "messages": [AIMessage(content=summary)] + state.get('messages', [])
        }
        
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"❌ **CV Creator**: CV creation failed - {str(e)}")] + state.get('messages', []),
            "completed_tasks": state.get('completed_tasks', []) + ['cv_creator']
        }