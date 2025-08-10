"""
Shared tools and utilities for the multi-agent job hunting system
"""

import PyPDF2
from docx import Document
import asyncio
import aiohttp
import os
import re
from datetime import datetime
import json
import requests
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing import List
from api.agents.base import JobListing

# Environment variables
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
SCRAPER_API_URL = "https://api.scraperapi.com/structured/google/jobs"
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
RAPID_API_URL="https://daily-international-job-postings.p.rapidapi.com/api/v2/jobs/search"

# Shared LLM instance
llm = ChatOpenAI(model="gpt-5-nano", temperature=1)

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
                # Skip malformed job entries silently
                continue
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            raise Exception("Rate limit exceeded - Job search API quota reached. Please try again later.")
        else:
            raise Exception(f"Job search API error ({e.response.status_code}): {str(e)}")
    except Exception as e:
        raise Exception(f"Job search failed: {str(e)}")

    return jobs


#########################################
# Cloudinary Storage for Serverless    #
#########################################

import io
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
from typing import Optional

class CloudinaryStorage:
    """Cloudinary storage provider for serverless deployment"""
    
    def __init__(self):
        # Configure Cloudinary from environment variables
        self.configured = self._configure_cloudinary()
    
    def _configure_cloudinary(self) -> bool:
        """Configure Cloudinary from environment variables"""
        try:
            cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
            api_key = os.environ.get('CLOUDINARY_API_KEY')
            api_secret = os.environ.get('CLOUDINARY_API_SECRET')
            
            if not all([cloud_name, api_key, api_secret]):
                return False
            
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            
            return True
            
        except Exception:
            return False
    
    def upload_cv(self, cv_content: bytes, filename: str) -> Optional[str]:
        """Upload CV file and return secure URL"""
        if not self.configured:
            return self._fallback_storage(cv_content, filename)
        
        try:
            # Create file-like object from bytes
            file_obj = io.BytesIO(cv_content)
            
            # Generate unique public_id
            import time
            timestamp = int(time.time())
            public_id = f"cv_{timestamp}_{filename.replace('.', '_')}"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_obj,
                public_id=public_id,
                resource_type="auto",
                folder="job-hunting-agent/cvs"
            )
            
            return result['secure_url']
            
        except Exception:
            return self._fallback_storage(cv_content, filename)
    
    def _fallback_storage(self, file_content: bytes, filename: str) -> Optional[str]:
        """Fallback to base64 data URL if Cloudinary fails"""
        try:
            import base64
            
            # Determine MIME type
            ext = os.path.splitext(filename)[1].lower()
            mime_type = 'application/pdf' if ext == '.pdf' else 'application/octet-stream'
            
            encoded = base64.b64encode(file_content).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
            
        except Exception:
            return None

# Global storage instance
_storage = CloudinaryStorage()

def upload_cv_file(cv_content: bytes, filename: str) -> Optional[str]:
    """Upload CV file and return URL"""
    return _storage.upload_cv(cv_content, filename)