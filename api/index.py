from flask import Flask, request, jsonify, send_file
import os
import traceback
import tempfile
from datetime import datetime
import logging
from werkzeug.utils import secure_filename
import mimetypes
from api.main import JobHuntingMultiAgent
from api.performance_evaluator import performance_evaluator
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
        "execution_time": result.get("processing_time", ""),
        "session_id": result.get("session_id", ""),
        "user_id": result.get("user_id", ""),
        "resume_analysis": result.get("resume_analysis", {}),
        "job_market_data": result.get("job_market_data", {}),
        "job_listings": result.get("job_listings", []),
        "cv_path": result.get("cv_path", ""),
        "cv_download_url": "",
        "cv_filename": "",
        "comparison_results": result.get("comparison_results", {}),
        "performance_summary": result.get("performance_summary", {}),
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
    
def background_process(job_id, user_prompt, resume_path, user_id):
    start_time = datetime.now()
    try:
        # Add job_id to the request for HITL support
        result = multi_agent.process_request_with_hitl(user_prompt, resume_path, user_id, job_id)
        execution_time = (datetime.now() - start_time).total_seconds()

        if result.get("success"):
            safe_result = serialize_result({**result, "execution_time": execution_time})
            job_results[job_id] = {
                "status": "completed",
                "result": safe_result,
                "summary": "✅ Job completed successfully",
            }
        elif result.get("hitl_checkpoint"):
            # Job needs human approval
            job_results[job_id].update({
                "status": "awaiting_approval",
                "hitl_checkpoint": result["hitl_checkpoint"],
                "hitl_data": result["hitl_data"],
                "partial_result": result
            })
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
        "agents_available": multi_agent is not None,
        "performance_tracking": "enabled"
    }
    
    return jsonify(status), 200 if multi_agent else 503

@app.route("/api/status", methods=['GET'])
def system_status():
    """Detailed system status with performance metrics"""
    if not multi_agent:
        return create_error_response("Multi-agent system not available", 503)
    
    # Get current performance metrics
    try:
        system_performance = performance_evaluator.get_system_performance_summary()
        
        status = {
            "system": "Multi-Agent Job Hunting System",
            "status": "operational",
            "intelligent_routing": "enabled",
            "performance_tracking": "enabled",
            "current_metrics": {
                "total_requests": system_performance.get("total_requests", 0),
                "success_rate": f"{system_performance.get('success_rate', 0):.1f}%",
                "avg_response_time": f"{system_performance.get('avg_request_time', 0):.1f}s",
                "user_satisfaction": f"{system_performance.get('user_satisfaction', 0):.1f}/10",
                "system_grade": system_performance.get("overall_grade", "Not Available")
            },
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
                "🤖 Autonomous Workflow Orchestration",
                "📈 Performance Tracking & Analytics"
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
        
        return create_success_response(status, "System operational with performance tracking")
        
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return create_error_response("Failed to get system status", 500)

#########################################
# Core Processing Endpoint            #
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
    🚀 UNIFIED INTELLIGENT ENDPOINT WITH PERFORMANCE TRACKING
    
    Handles any job hunting request with optional file upload and user tracking.
    The multi-agent system autonomously decides which agents to involve.
    All requests are tracked for performance analysis.
    """
    
    start_time = datetime.now()
    
    try:
        if not multi_agent:
            return create_error_response("Multi-agent system not available", 503)
        
        # Extract user_id for tracking
        user_id = None
        
        # Handle file upload (optional)
        resume_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                resume_path, error = save_uploaded_file(file)
                if error:
                    return create_error_response(error)
                logger.info(f"Resume uploaded: {resume_path}")
        
        # Get user request/prompt and user_id
        user_prompt = None
        
        if request.form.get('prompt'):
            user_prompt = request.form.get('prompt')
            user_id = request.form.get('user_id', f"user_{int(start_time.timestamp())}")
            logger.info("Received prompt from form data")
        
        elif request.is_json:
            data = request.get_json()
            user_prompt = data.get('prompt') or data.get('request') or data.get('message')
            user_id = data.get('user_id', f"user_{int(start_time.timestamp())}")
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
        logger.info(f"User ID: {user_id}")
        if resume_path:
            logger.info(f"Resume file: {os.path.basename(resume_path)}")
        
        job_id = str(uuid.uuid4())

        # Initialize job status with HITL support
        job_results[job_id] = {
            "status": "processing",
            "start_time": datetime.now().isoformat(),
            "user_id": user_id,
            "hitl_checkpoint": None,  # 'coordinator_plan' or 'job_role_clarification'
            "hitl_data": None,  # Data requiring approval
            "hitl_response": None  # User's approval response
        }

        # Start background thread with user_id
        thread = threading.Thread(
            target=background_process,
            args=(job_id, user_prompt, resume_path, user_id),
            daemon=True
        )
        thread.start()

        # Return job ID immediately to frontend
        return jsonify({
            "message": "🧠 Request is being processed in the background with performance tracking.",
            "job_id": job_id,
            "user_id": user_id,
            "status_check_url": f"/api/status/{job_id}",
            "feedback_url": f"/api/feedback"
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

def continue_after_approval(job_id, approval_response):
    """Continue processing after human approval"""
    start_time = datetime.now()
    try:
        job = job_results[job_id]
        partial_result = job.get('partial_result', {})
        
        logger.info(f"🔄 Continuing job {job_id} after approval: {approval_response}")
        
        # Continue from where we left off - this is a simplified approach
        # In a full implementation, you'd resume the exact agent workflow state
        result = multi_agent.continue_from_approval(partial_result, approval_response)
        execution_time = (datetime.now() - start_time).total_seconds()

        if result.get("success"):
            safe_result = serialize_result({**result, "execution_time": execution_time})
            job_results[job_id].update({
                "status": "completed",
                "result": safe_result,
                "summary": "✅ Job completed successfully after approval",
            })
        else:
            job_results[job_id].update({
                "status": "failed",
                "error": result.get("error", "Unknown error after approval"),
                "execution_time": execution_time
            })

    except Exception as e:
        job_results[job_id].update({
            "status": "error",
            "error": f"Error continuing after approval: {str(e)}",
            "traceback": traceback.format_exc(),
            "execution_time": (datetime.now() - start_time).total_seconds()
        })

#########################################
# Human-in-the-Loop Endpoints         #
#########################################

@app.route('/api/approve/<job_id>', methods=['POST'])
def approve_checkpoint(job_id):
    """Submit approval for a HITL checkpoint"""
    try:
        if job_id not in job_results:
            return create_error_response("Job not found", 404)
            
        data = request.get_json()
        approval_response = data.get('response')
        
        if not approval_response:
            return create_error_response("Approval response required")
        
        job = job_results[job_id]
        
        if job['status'] != 'awaiting_approval':
            return create_error_response("Job is not awaiting approval")
        
        # Store the approval response
        job['hitl_response'] = approval_response
        job['status'] = 'processing'
        
        logger.info(f"✅ HITL approval received for job {job_id}: {approval_response}")
        
        # Continue processing in background thread
        thread = threading.Thread(
            target=continue_after_approval,
            args=(job_id, approval_response),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Approval received - continuing processing",
            "job_id": job_id
        })
        
    except Exception as e:
        logger.error(f"Approval error: {e}")
        return create_error_response(f"Failed to process approval: {str(e)}")

#########################################
# User Feedback Endpoints             #
#########################################

@app.route('/api/feedback', methods=['POST'])
def collect_user_feedback():
    """
    🎯 Collect user feedback for performance evaluation
    
    Expected JSON:
    {
        "session_id": "session123",
        "user_id": "user123", 
        "satisfaction": 8.5,
        "resume_helpful": true,
        "jobs_helpful": true,
        "would_use_again": true,
        "feedback_text": "Optional feedback text"
    }
    """
    try:
        if not multi_agent:
            return create_error_response("Multi-agent system not available", 503)
        
        if not request.is_json:
            return create_error_response("Request must be JSON")
        
        data = request.get_json()
        
        # Validate required fields
        session_id = data.get('session_id')
        user_id = data.get('user_id', 'anonymous')
        satisfaction = data.get('satisfaction')
        
        if not session_id:
            return create_error_response("session_id is required")
        
        if satisfaction is None or not (1 <= satisfaction <= 10):
            return create_error_response("satisfaction must be between 1 and 10")
        
        # Collect feedback through multi-agent system
        feedback_result = multi_agent.collect_user_feedback(
            session_id=session_id,
            user_id=user_id,
            satisfaction=satisfaction,
            resume_helpful=data.get('resume_helpful'),
            jobs_helpful=data.get('jobs_helpful'),
            would_use_again=data.get('would_use_again')
        )
        
        if feedback_result.get('success'):
            logger.info(f"User feedback collected: {satisfaction}/10 satisfaction for user {user_id}")
            
            return create_success_response({
                "feedback_recorded": True,
                "satisfaction": satisfaction,
                "session_id": session_id,
                "user_id": user_id,
                "feedback_summary": feedback_result.get('feedback_summary', {})
            }, "Thank you for your feedback! Your input helps us improve the system.")
        else:
            return create_error_response("Failed to record feedback", 500, feedback_result.get('error'))
            
    except Exception as e:
        logger.error(f"Feedback collection error: {e}")
        return create_error_response("Failed to collect feedback", 500, str(e))

#########################################
# Performance & Analytics Endpoint    #
#########################################

@app.route('/api/performance', methods=['GET'])
def get_comprehensive_performance():
    """
    📊 UNIFIED PERFORMANCE ENDPOINT
    
    Get all performance data in one comprehensive response:
    - System health and metrics
    - User satisfaction and outcomes  
    - Agent performance breakdown
    - Effectiveness scores and grades
    - Benchmark comparisons
    - Recommendations
    """
    try:
        if not multi_agent:
            return create_error_response("Multi-agent system not available", 503)
        
        # Get all performance data
        system_performance = performance_evaluator.get_system_performance_summary()
        user_outcomes = multi_agent.get_user_outcomes_summary()
        effectiveness_report = multi_agent.get_system_effectiveness_report()
        
        # Create comprehensive performance data
        performance_data = {
            # System Overview
            "system_overview": {
                "status": "healthy" if system_performance.get("success_rate", 0) > 80 else "warning",
                "total_requests": system_performance.get("total_requests", 0),
                "success_rate": system_performance.get("success_rate", 0),
                "avg_response_time": system_performance.get("avg_request_time", 0),
                "uptime_percentage": system_performance.get("uptime_percentage", 100),
                "system_grade": system_performance.get("overall_grade", "Not Available"),
                "human_interventions": system_performance.get("human_interventions", 0),
                "session_duration": system_performance.get("session_duration", "Unknown")
            },
            
            # User Satisfaction & Outcomes
            "user_satisfaction": {
                "current_score": system_performance.get("user_satisfaction", 0),
                "total_feedback": user_outcomes.get("total_feedback", 0),
                "avg_satisfaction": user_outcomes.get("avg_satisfaction", 0),
                "satisfaction_grade": user_outcomes.get("satisfaction_grade", "No data"),
                "satisfaction_distribution": user_outcomes.get("satisfaction_distribution", {}),
                "helpfulness_rates": user_outcomes.get("helpfulness_rates", {})
            },
            
            # Agent Performance Breakdown
            "agent_performance": {
                agent: performance_evaluator.get_agent_performance_summary(agent)
                for agent in ["resume_analyst", "job_researcher", "cv_creator", "job_matcher"]
                if agent in performance_evaluator.agent_metrics
            },
            
            # System Effectiveness
            "effectiveness": {
                "overall_score": effectiveness_report.get("effectiveness_score", 0),
                "effectiveness_grade": effectiveness_report.get("effectiveness_grade", "Not Available"),
                "benchmark_comparison": effectiveness_report.get("benchmark_comparison", {}),
                "key_insights": effectiveness_report.get("recommendations", [])[:5]
            },
            
            # Performance Trends
            "trends": {
                "most_used_agent": system_performance.get("most_used_agent", "None"),
                "least_reliable_agent": system_performance.get("least_reliable_agent", "None"),
                "human_intervention_rate": system_performance.get("human_intervention_rate", 0),
                "performance_trajectory": "improving" if system_performance.get("success_rate", 0) > 85 else "stable"
            },
            
            # Quick Stats for Dashboard Cards
            "quick_stats": {
                "requests_today": system_performance.get("total_requests", 0),
                "success_rate_display": f"{system_performance.get('success_rate', 0):.1f}%",
                "avg_response_time_display": f"{system_performance.get('avg_request_time', 0):.1f}s",
                "user_satisfaction_display": f"{system_performance.get('user_satisfaction', 0):.1f}/10",
                "effectiveness_display": f"{effectiveness_report.get('effectiveness_score', 0):.0f}/100"
            },
            
            # Recommendations & Actions
            "recommendations": {
                "top_priorities": effectiveness_report.get("recommendations", [])[:3],
                "all_recommendations": effectiveness_report.get("recommendations", []),
                "system_health_actions": performance_evaluator._generate_recommendations()[:3]
            },
            
            # Meta Information
            "meta": {
                "last_updated": datetime.now().isoformat(),
                "data_freshness": "real-time",
                "report_version": "2.0",
                "tracking_since": system_performance.get("last_updated", "Unknown")
            }
        }
        
        return create_success_response(performance_data, "Comprehensive performance data retrieved")
        
    except Exception as e:
        logger.error(f"Comprehensive performance endpoint error: {e}")
        logger.error(traceback.format_exc())
        return create_error_response("Failed to get performance data", 500, str(e))

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
    """Get example requests and expected performance"""
    
    examples = {
        "resume_analysis": {
            "prompt": "Please analyze my resume and tell me how I can improve it",
            "description": "Analyzes resume for strengths, weaknesses, and provides improvement suggestions",
            "expected_agents": ["Resume Analyst"],
            "expected_time": "2-5 seconds",
            "performance_tracked": True
        },
        "job_search": {
            "prompt": "Find me software engineering jobs that match my background",
            "description": "Searches for relevant job opportunities based on your profile",
            "expected_agents": ["Resume Analyst", "Job Researcher"],
            "expected_time": "5-10 seconds",
            "performance_tracked": True
        },
        "cv_creation": {
            "prompt": "Create a professional CV optimized for tech companies",
            "description": "Generates an ATS-optimized CV tailored for specific industries",
            "expected_agents": ["Resume Analyst", "Job Researcher", "CV Creator"],
            "expected_time": "8-15 seconds",
            "performance_tracked": True
        },
        "complete_workflow": {
            "prompt": "I need complete job hunting help - analyze my resume, find jobs, and create an optimized CV",
            "description": "Full job hunting assistance with all agents working together",
            "expected_agents": ["Resume Analyst", "Job Researcher", "CV Creator"],
            "expected_time": "10-20 seconds",
            "performance_tracked": True
        },
        "job_matching": {
            "prompt": "Compare my resume against the jobs you find and tell me which ones are the best fit",
            "description": "Analyzes job compatibility and provides application strategy",
            "expected_agents": ["Resume Analyst", "Job Researcher", "Job Matcher"],
            "expected_time": "8-15 seconds",
            "performance_tracked": True
        },
        "feedback_example": {
            "endpoint": "/api/feedback",
            "method": "POST",
            "description": "Submit feedback after using the system",
            "example_payload": {
                "session_id": "from_job_result",
                "user_id": "your_user_id",
                "satisfaction": 8.5,
                "resume_helpful": True,
                "jobs_helpful": True,
                "would_use_again": True
            }
        }
    }
    
    return create_success_response(examples, "Example requests and performance expectations")

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
