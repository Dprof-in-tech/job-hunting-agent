from flask import Flask, request, jsonify, send_file
import os
import traceback
import tempfile
from datetime import datetime
import logging
from werkzeug.utils import secure_filename
import mimetypes
from main import JobHuntingMultiAgent
import threading
import uuid
from langchain_core.messages import BaseMessage

job_results = {} 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'doc'}

try:
    multi_agent = JobHuntingMultiAgent()
    logger.info("✅ Multi-agent system initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize multi-agent system: {e}")
    multi_agent = None

#########################################
# Utility Functions                    #
#########################################

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_error_response(message, status_code=400, details=None):
    """Create standardized error response"""
    response = {
        "success": False,
        "error": message,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        response["details"] = details
    
    return jsonify(response), status_code

def create_success_response(data, message="Operation successful"):
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(response), 200

def save_uploaded_file(file):
    """Save uploaded file securely and return filepath"""
    if not file or file.filename == '':
        return None, "No file selected"
    
    if not allowed_file(file.filename):
        return None, f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
    

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        logger.info(f"File uploaded successfully: {filename}")
        return filepath, None
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return None, f"File upload failed: {str(e)}"
    
def serialize_result(result: dict) -> dict:
    """Sanitize and keep meaningful structure from the agent's result"""
    serialized = {
        "agent_workflow": result.get("agent_workflow", ""),
        "completed_tasks": result.get("completed_tasks", []),
        "execution_time": result.get("execution_time", ""),
        "resume_analysis": result.get("resume_analysis", {}),
        "job_market_data": result.get("job_market_data", {}),
        "job_listings": result.get("job_listings", []),
        "cv_path": result.get("cv_path", ""),
        "cv_download_url": "",
        "cv_filename": "",
        "comparison_results": result.get("comparison_results", {}),
        "agent_messages": []
    }

    # Sanitize agent messages
    messages = result.get("messages", [])
    serialized["agent_messages"] = [
        {
            "content": m.content,
            "timestamp": getattr(m, "additional_kwargs", {}).get("timestamp", ""),
        }
        for m in messages if isinstance(m, BaseMessage)
    ]

    # Add download URL if cv_path exists
    if serialized["cv_path"]:
        filename = os.path.basename(serialized["cv_path"])
        serialized["cv_filename"] = filename
        serialized["cv_download_url"] = f"/api/download/{filename}"

    return serialized
    
def background_process(job_id, user_prompt, resume_path):
    start_time = datetime.now()
    try:
        result = multi_agent.process_request(user_prompt, resume_path)
        execution_time = (datetime.now() - start_time).total_seconds()

        if result.get("success"):
            safe_result = serialize_result({**result, "execution_time": execution_time})
            job_results[job_id] = {
                "status": "completed",
                "result": safe_result,
                "summary": "✅ Job completed successfully",
            }
        else:
            job_results[job_id] = {
                "status": "failed",
                "error": result.get("error", "Unknown error"),
                "execution_time": execution_time
            }

    except Exception as e:
        job_results[job_id] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "execution_time": (datetime.now() - start_time).total_seconds()
        }



#########################################
# Health Check Endpoints               #
#########################################

@app.route("/", methods=['GET'])
def health_check():
    """Health check endpoint"""
    status = {
        "service": "Multi-Agent Job Hunting API",
        "status": "healthy" if multi_agent else "degraded",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoint": "/api/process - Unified intelligent endpoint",
        "agents_available": multi_agent is not None
    }
    
    return jsonify(status), 200 if multi_agent else 503

@app.route("/api/status", methods=['GET'])
def system_status():
    """Detailed system status"""
    if not multi_agent:
        return create_error_response("Multi-agent system not available", 503)
    
    status = {
        "system": "Multi-Agent Job Hunting System",
        "status": "operational",
        "intelligent_routing": "enabled",
        "autonomous_agents": {
            "coordinator": "active - orchestrates workflow",
            "resume_analyst": "active - resume analysis expert", 
            "job_researcher": "active - job market intelligence",
            "cv_creator": "active - professional CV generation",
            "job_matcher": "active - job compatibility analysis"
        },
        "capabilities": [
            "🔍 Resume Analysis & Optimization",
            "📊 Job Market Research & Trends",
            "📝 Professional CV Generation", 
            "🎯 Job Matching & Compatibility",
            "🤖 Autonomous Workflow Orchestration"
        ],
        "supported_requests": [
            "Analyze my resume",
            "Find me jobs",
            "Create an optimized CV", 
            "Complete job hunting help",
            "Compare my resume to this job",
            "Research the job market for [role]",
            "Help me improve my resume"
        ]
    }
    
    return create_success_response(status, "System operational")

#########################################
# ENDPOINT                #
#########################################

@app.route('/api/status/<job_id>', methods=['GET'])
def check_job_status(job_id):
    """
    🔍 Returns the current status of a background job.
    """
    job_info = job_results.get(job_id)
    
    if not job_info:
        return create_error_response(f"No job found with ID: {job_id}", 404)

    if job_info["status"] == "processing":
        return jsonify({"status": "processing", "job_id": job_id}), 200

    if job_info["status"] == "failed":
        return jsonify({
            "status": "failed",
            "job_id": job_id,
            "error": job_info.get("error", "Unknown error")
        }), 200

    if job_info["status"] == "completed":
        return jsonify({
            "status": "completed",
            "job_id": job_id,
            "result": job_info.get("result", {}),
            "summary": job_info.get("summary", "")
        }), 200

    return create_error_response("Unexpected job status", 500)


@app.route('/api/process', methods=['POST'])
def process_job_hunting_request():
    """
    🚀 UNIFIED INTELLIGENT ENDPOINT
    
    Handles any job hunting request with optional file upload.
    The multi-agent system autonomously decides which agents to involve.
    
    Supports:
    - Resume analysis requests
    - Job search requests  
    - CV generation requests
    - Complete workflow requests
    - Job matching requests
    - Market research requests
    - Any combination of the above
    """
    
    start_time = datetime.now()
    
    try:
        if not multi_agent:
            return create_error_response("Multi-agent system not available", 503)
        
        # Handle file upload (optional)
        resume_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                resume_path, error = save_uploaded_file(file)
                if error:
                    return create_error_response(error)
                logger.info(f"Resume uploaded: {resume_path}")
        
        # Get user request/prompt
        user_prompt = None
        
        if request.form.get('prompt'):
            user_prompt = request.form.get('prompt')
            logger.info("Received prompt from form data")
        
        elif request.is_json:
            data = request.get_json()
            user_prompt = data.get('prompt') or data.get('request') or data.get('message')
            # Also check if resume_path was provided in JSON
            if not resume_path and data.get('resume_path'):
                resume_path = data.get('resume_path')
                if not os.path.exists(resume_path):
                    return create_error_response(f"Resume file not found: {resume_path}")
            logger.info("Received prompt from JSON data")
        
        # Validate that we have a prompt
        if not user_prompt:
            return create_error_response(
                "No prompt provided. Please include 'prompt', 'request', or 'message' in your request."
            )
        
        logger.info(f"Processing intelligent request: {user_prompt[:100]}...")
        if resume_path:
            logger.info(f"Resume file: {os.path.basename(resume_path)}")
        job_id = str(uuid.uuid4())

        # Initialize job status
        job_results[job_id] = {
            "status": "processing",
            "start_time": datetime.now().isoformat(),
        }

        # Start background thread
        thread = threading.Thread(
            target=background_process,
            args=(job_id, user_prompt, resume_path),
            daemon=True
        )
        thread.start()

        # Return job ID immediately to frontend
        return jsonify({
            "message": "🧠 Request is being processed in the background.",
            "job_id": job_id,
            "status_check_url": f"/api/status/{job_id}"
        }), 202
            
    except Exception as e:
        logger.error(f"❌ Endpoint error: {e}")
        logger.error(traceback.format_exc())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return create_error_response(
            "Internal server error", 
            500, 
            {
                "error_details": str(e),
                "execution_time": f"{execution_time:.2f}s"
            }
        )

#########################################
# File Download Endpoint               #
#########################################

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Download generated files (CVs, reports, etc.)"""
    try:
        # Secure the filename to prevent directory traversal
        filename = secure_filename(filename)
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        if not os.path.exists(filepath):
            return create_error_response("File not found", 404)
        
        logger.info(f"Serving file download: {filename}")
        
        # Determine MIME type
        mime_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
        
    except Exception as e:
        logger.error(f"File download error: {e}")
        return create_error_response("File download failed", 500, str(e))

#########################################
# Example Usage Endpoint               #
#########################################

@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example requests that can be processed"""
    
    examples = {
        "resume_analysis": {
            "prompt": "Please analyze my resume and tell me how I can improve it",
            "description": "Analyzes resume for strengths, weaknesses, and provides improvement suggestions",
            "expected_agents": ["Resume Analyst"]
        },
        "job_search": {
            "prompt": "Find me software engineering jobs that match my background",
            "description": "Searches for relevant job opportunities based on your profile",
            "expected_agents": ["Resume Analyst", "Job Researcher"]
        },
        "cv_creation": {
            "prompt": "Create a professional CV optimized for tech companies",
            "description": "Generates an ATS-optimized CV tailored for specific industries",
            "expected_agents": ["Resume Analyst", "Job Researcher", "CV Creator"]
        },
        "complete_workflow": {
            "prompt": "I need complete job hunting help - analyze my resume, find jobs, and create an optimized CV",
            "description": "Full job hunting assistance with all agents working together",
            "expected_agents": ["Resume Analyst", "Job Researcher", "CV Creator"]
        },
        "job_matching": {
            "prompt": "Compare my resume against the jobs you find and tell me which ones are the best fit",
            "description": "Analyzes job compatibility and provides application strategy",
            "expected_agents": ["Resume Analyst", "Job Researcher", "Job Matcher"]
        },
        "market_research": {
            "prompt": "What's the current job market like for data scientists? What skills are in demand?",
            "description": "Research job market trends and in-demand skills for specific roles",
            "expected_agents": ["Job Researcher"]
        },
        "specific_job_comparison": {
            "prompt": "I found this job posting: [paste job description]. How well does my resume match and what should I focus on?",
            "description": "Compares your resume against a specific job description",
            "expected_agents": ["Resume Analyst", "Job Matcher"]
        }
    }
    
    return create_success_response(examples, "Example requests and expected workflows")

#########################################
# Error Handlers                       #
#########################################

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return create_error_response("File too large. Maximum size is 16MB.", 413)

@app.errorhandler(404)
def not_found(e):
    """Handle not found error"""
    return create_error_response("Endpoint not found", 404)

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server error"""
    logger.error(f"Internal server error: {e}")
    return create_error_response("Internal server error", 500)

#########################################
# Development Testing                  #
#########################################

@app.route('/api/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for development"""
    try:
        # Test with a simple request
        test_prompt = "Test the multi-agent system"
        
        if multi_agent:
            result = multi_agent.process_request(test_prompt)
            return create_success_response({
                "test_status": "passed",
                "multi_agent_available": True,
                "agents_involved": result.get("completed_tasks", []),
                "test_result": "Multi-agent system responding correctly"
            }, "Test successful")
        else:
            return create_error_response("Multi-agent system not available")
            
    except Exception as e:
        return create_error_response("Test failed", 500, str(e))