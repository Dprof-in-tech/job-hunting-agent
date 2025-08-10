from flask import Flask, request, jsonify, send_file, Response, redirect, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import traceback
import tempfile
from datetime import datetime
import logging
from werkzeug.utils import secure_filename
import mimetypes
from api.main import JobHuntingMultiAgent
# performance_evaluator consolidated inline
#########################################
# Performance Evaluation System        #
#########################################

import statistics
from dataclasses import dataclass, asdict

@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for individual agents"""
    agent_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    success_rate: float = 0.0
    errors: list = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.last_updated is None:
            self.last_updated = datetime.now()

@dataclass
class UserOutcome:
    """Simple tracking of user outcomes"""
    user_id: str
    session_id: str
    timestamp: datetime
    user_satisfaction: float = None  # 1-10 scale
    resume_improved: bool = None
    jobs_found_helpful: bool = None
    would_use_again: bool = None

@dataclass
class SystemPerformanceMetrics:
    """Overall system performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_request_time: float = 0.0
    user_satisfaction_score: float = 0.0
    human_interventions: int = 0
    most_used_agent: str = ""
    least_reliable_agent: str = ""
    uptime_percentage: float = 100.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

class PerformanceEvaluator:
    """Comprehensive performance evaluation system - in-memory storage for serverless deployment"""
    
    def __init__(self):
        self.agent_metrics = {}
        self.system_metrics = SystemPerformanceMetrics()
        self.session_start_time = datetime.now()

    def reset_session(self):
        """Reset all metrics for a new session - useful for serverless environments"""
        self.agent_metrics.clear()
        self.system_metrics = SystemPerformanceMetrics()
        self.session_start_time = datetime.now()
    
    def get_current_session_data(self):
        """Get all current session data as dict - for API responses"""
        return {
            'agents': {
                agent_name: asdict(metrics) 
                for agent_name, metrics in self.agent_metrics.items()
            },
            'system': asdict(self.system_metrics),
            'session_start': self.session_start_time.isoformat(),
            'current_time': datetime.now().isoformat()
        }
    
    def log_agent_call(self, agent_name: str, success: bool, processing_time: float, error: str = None):
        """Log an agent call for performance tracking"""
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = AgentPerformanceMetrics(agent_name=agent_name)
        
        metrics = self.agent_metrics[agent_name]
        metrics.total_calls += 1
        metrics.total_processing_time += processing_time
        
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if error:
                metrics.errors.append(f"{datetime.now().isoformat()}: {error}")
                # Keep only last 10 errors
                metrics.errors = metrics.errors[-10:]
        
        # Update calculated fields
        metrics.success_rate = (metrics.successful_calls / metrics.total_calls) * 100
        metrics.avg_processing_time = metrics.total_processing_time / metrics.total_calls
        metrics.last_updated = datetime.now()
    
    def log_system_request(self, success: bool, request_time: float, human_intervention: bool = False):
        """Log a system-level request"""
        self.system_metrics.total_requests += 1
        
        if success:
            self.system_metrics.successful_requests += 1
        else:
            self.system_metrics.failed_requests += 1
        
        if human_intervention:
            self.system_metrics.human_interventions += 1
        
        # Update average request time
        total_time = self.system_metrics.avg_request_time * (self.system_metrics.total_requests - 1) + request_time
        self.system_metrics.avg_request_time = total_time / self.system_metrics.total_requests
        
        self.system_metrics.last_updated = datetime.now()
    
    def record_request_metrics(self, agent_name: str, request_type: str, processing_time: float, success: bool, error: str = None):
        """Record request metrics for performance tracking"""
        self.log_agent_call(agent_name, success, processing_time, error)
        self.log_system_request(success, processing_time)
    
    def log_user_satisfaction(self, score: float):
        """Log user satisfaction score (1-10 scale)"""
        if not (1 <= score <= 10):
            raise ValueError("Satisfaction score must be between 1 and 10")
        
        # Simple running average for now - could be improved with weighted averages
        current_score = self.system_metrics.user_satisfaction_score
        total_requests = self.system_metrics.total_requests
        
        if total_requests == 0:
            self.system_metrics.user_satisfaction_score = score
        else:
            self.system_metrics.user_satisfaction_score = ((current_score * (total_requests - 1)) + score) / total_requests
    
    def get_agent_performance_summary(self, agent_name: str):
        """Get performance summary for a specific agent"""
        if agent_name not in self.agent_metrics:
            return {"error": f"No metrics found for agent: {agent_name}"}
        
        metrics = self.agent_metrics[agent_name]
        return {
            "agent_name": agent_name,
            "total_calls": metrics.total_calls,
            "success_rate": round(metrics.success_rate, 2),
            "avg_processing_time": round(metrics.avg_processing_time, 3),
            "recent_errors": metrics.errors[-3:] if metrics.errors else [],
            "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None,
            "performance_grade": self._calculate_performance_grade(metrics)
        }
    
    def get_system_performance_summary(self):
        """Get overall system performance summary"""
        # Calculate additional metrics
        success_rate = (self.system_metrics.successful_requests / max(self.system_metrics.total_requests, 1)) * 100
        
        # Find most and least reliable agents
        most_used = self._get_most_used_agent()
        least_reliable = self._get_least_reliable_agent()
        
        # Calculate uptime (simplified - based on successful vs failed requests)
        uptime = success_rate if self.system_metrics.total_requests > 0 else 100.0
        
        return {
            "total_requests": self.system_metrics.total_requests,
            "success_rate": round(success_rate, 2),
            "avg_request_time": round(self.system_metrics.avg_request_time, 3),
            "user_satisfaction": round(self.system_metrics.user_satisfaction_score, 2),
            "human_interventions": self.system_metrics.human_interventions,
            "human_intervention_rate": round((self.system_metrics.human_interventions / max(self.system_metrics.total_requests, 1)) * 100, 2),
            "most_used_agent": most_used,
            "least_reliable_agent": least_reliable,
            "uptime_percentage": round(uptime, 2),
            "session_duration": str(datetime.now() - self.session_start_time),
            "last_updated": self.system_metrics.last_updated.isoformat() if self.system_metrics.last_updated else None,
            "overall_grade": self._calculate_system_grade(success_rate, self.system_metrics.user_satisfaction_score)
        }
    
    def get_comprehensive_report(self):
        """Get comprehensive performance report"""
        return {
            "system_overview": self.get_system_performance_summary(),
            "agent_details": {
                agent_name: self.get_agent_performance_summary(agent_name)
                for agent_name in self.agent_metrics.keys()
            },
            "recommendations": self._generate_recommendations(),
            "report_generated": datetime.now().isoformat()
        }
    
    def _calculate_performance_grade(self, metrics):
        """Calculate performance grade for an agent"""
        if metrics.total_calls == 0:
            return "N/A"
        
        score = 0
        # Success rate (40% weight)
        score += (metrics.success_rate / 100) * 40
        
        # Response time (30% weight) - lower is better
        if metrics.avg_processing_time <= 1.0:
            score += 30
        elif metrics.avg_processing_time <= 3.0:
            score += 20
        elif metrics.avg_processing_time <= 5.0:
            score += 10
        
        # Error frequency (30% weight)
        error_rate = len(metrics.errors) / metrics.total_calls
        if error_rate <= 0.05:  # 5% or less
            score += 30
        elif error_rate <= 0.1:  # 10% or less
            score += 20
        elif error_rate <= 0.2:  # 20% or less
            score += 10
        
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
    
    def _calculate_system_grade(self, success_rate: float, user_satisfaction: float):
        """Calculate overall system grade"""
        # Weight: 60% success rate, 40% user satisfaction
        score = (success_rate * 0.6) + (user_satisfaction * 10 * 0.4)
        
        if score >= 85:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 55:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"
    
    def _get_most_used_agent(self):
        """Find the most frequently used agent"""
        if not self.agent_metrics:
            return "None"
        
        return max(self.agent_metrics.items(), key=lambda x: x[1].total_calls)[0]
    
    def _get_least_reliable_agent(self):
        """Find the least reliable agent (lowest success rate)"""
        if not self.agent_metrics:
            return "None"
        
        # Filter out agents with too few calls to be meaningful
        reliable_agents = {name: metrics for name, metrics in self.agent_metrics.items() if metrics.total_calls >= 3}
        
        if not reliable_agents:
            return "Insufficient data"
        
        return min(reliable_agents.items(), key=lambda x: x[1].success_rate)[0]
    
    def _generate_recommendations(self):
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # System-level recommendations
        system_success_rate = (self.system_metrics.successful_requests / max(self.system_metrics.total_requests, 1)) * 100
        
        if system_success_rate < 80:
            recommendations.append("System success rate is below 80%. Consider investigating failure patterns and improving error handling.")
        
        if self.system_metrics.user_satisfaction_score < 7.0:
            recommendations.append("User satisfaction is below 7.0. Consider implementing more human-in-the-loop interactions and user feedback mechanisms.")
        
        if self.system_metrics.avg_request_time > 30:
            recommendations.append("Average request time is high. Consider optimizing agent processing or implementing parallel execution.")
        
        # Agent-level recommendations
        for agent_name, metrics in self.agent_metrics.items():
            if metrics.success_rate < 70:
                recommendations.append(f"{agent_name} has low success rate ({metrics.success_rate:.1f}%). Review error patterns and improve robustness.")
            
            if metrics.avg_processing_time > 10:
                recommendations.append(f"{agent_name} has high processing time ({metrics.avg_processing_time:.1f}s). Consider optimizing or breaking into smaller tasks.")
        
        if not recommendations:
            recommendations.append("System is performing well! Continue monitoring and consider implementing advanced optimization features.")
        
        return recommendations

# system_monitor now consolidated in security module
from api.security import (
    security_manager, 
    require_session, 
    create_anonymous_session_endpoint,
    create_secure_error_response,
    SecurityException,
    system_monitor
)
from api.ai_safety import AISafetyCoordinator
import threading
import uuid
from langchain_core.messages import BaseMessage

# Global performance evaluator instance
performance_evaluator = PerformanceEvaluator()

# Secure job results storage with session isolation
secure_job_results = {} 

# Configure logging securely (no sensitive data) - Vercel compatible
def setup_logging():
    """Setup logging compatible with serverless deployment"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    
    # Use only console logging for serverless environments
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        # Vercel captures console output automatically
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[logging.StreamHandler()]
        )
    else:
        # Local development can still use file logging
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('app_security.log', mode='a')
            ]
        )

setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app with security settings
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
# Serverless-compatible upload configuration
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    # Use memory for temporary file handling in serverless
    app.config['UPLOAD_FOLDER'] = '/tmp'  # Vercel provides /tmp directory
else:
    # Local development
    app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'doc'}

# CORS configuration
CORS(app, 
     origins=os.environ.get('ALLOWED_ORIGINS', '*').split(','),
     methods=['GET', 'POST'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=False  # No cookies for anonymous sessions
)

# Rate limiter with secure configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

try:
    multi_agent = JobHuntingMultiAgent()
except Exception as e:
    logger.error(f"❌ Failed to initialize multi-agent system: {e}")
    multi_agent = None

# Initialize AI Safety Coordinator
try:
    safety_coordinator = AISafetyCoordinator()
except Exception as e:
    logger.warning(f"⚠️ AI Safety Coordinator initialization failed: {e}")
    safety_coordinator = None

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

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

def save_uploaded_file_secure(file, session_id):
    """Save uploaded file securely with session isolation"""
    if not file or file.filename == '':
        return None, "No file selected"
    
    # Validate file using security manager
    is_valid, error_msg = security_manager.validate_file_upload(file)
    if not is_valid:
        return None, error_msg
    
    # Generate secure filename with session isolation
    secure_filename_generated = security_manager.generate_secure_filename(
        file.filename, session_id
    )
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename_generated)
    
    try:
        file.save(filepath)
        return filepath, None
    except Exception as e:
        logger.error(f"Secure file upload failed for session {session_id[:8]}***: {e}")
        return None, "File upload failed"

def background_process_secure(job_id, user_prompt, resume_path, session_data):
    """Secure background processing with AI safety checks"""
    session_id = session_data['session_id']
    start_time = datetime.now()
    
    try:
        # Sanitize input
        sanitized_prompt = security_manager.sanitize_user_input(user_prompt)
        
        # Process with AI safety checks
        if safety_coordinator:
            # Pre-process safety check
            safety_check = safety_coordinator.comprehensive_safety_check(
                {"prompt": sanitized_prompt, "has_file": resume_path is not None},
                output_type="job_request"
            )
            
            if safety_check.bias_check.bias_detected:
                logger.warning(f"Bias detected in request from session {session_id[:8]}***")
        
        # Process request with multi-agent system
        result = multi_agent.process_request_with_hitl(
            user_message=sanitized_prompt, 
            resume_path=resume_path, 
            user_id=session_id,
            job_id=job_id
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Serialize and encrypt sensitive data
        if result.get("success"):
            # Encrypt sensitive information
            if result.get("resume_analysis"):
                result["resume_analysis"] = security_manager.encrypt_sensitive_data(
                    str(result["resume_analysis"])
                )
            
            safe_result = serialize_result({**result, "execution_time": execution_time})
            
            # Update download URLs for secure access
            if safe_result.get("cv_filename"):
                safe_result["cv_download_url"] = f"/api/download/{session_id}/{safe_result['cv_filename']}"
            
            if session_id not in secure_job_results:
                secure_job_results[session_id] = {}
                
            secure_job_results[session_id][job_id] = {
                "status": "completed",
                "result": safe_result,
                "summary": "✅ Job completed successfully with security checks",
            }
        elif result.get("hitl_checkpoint"):
            # Handle HITL with security
            if session_id not in secure_job_results:
                secure_job_results[session_id] = {}
                
            secure_job_results[session_id][job_id].update({
                "status": "awaiting_approval",
                "hitl_checkpoint": result.get("hitl_checkpoint"),
                "hitl_data": result.get("hitl_data", {}),
                "thread_id": result.get("thread_id"),  # Store thread_id for resume
                "partial_result": serialize_result(result)
            })
        else:
            if session_id not in secure_job_results:
                secure_job_results[session_id] = {}
                
            secure_job_results[session_id][job_id] = {
                "status": "failed",
                "error": result.get("error", "Unknown error"),
                "execution_time": execution_time
            }
            
    except Exception as e:
        logger.error(f"Secure processing error for job {job_id}: {str(e)}")
        if session_id not in secure_job_results:
            secure_job_results[session_id] = {}
            
        secure_job_results[session_id][job_id] = {
            "status": "failed",
            "error": "Processing failed with security checks",
            "execution_time": (datetime.now() - start_time).total_seconds()
        }

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

    # Sanitize agent messages - handle both BaseMessage objects and strings
    messages = result.get("messages", [])
    serialized["agent_messages"] = []
    
    for m in messages:
        if isinstance(m, BaseMessage):
            # Handle LangChain message objects
            serialized["agent_messages"].append({
                "content": str(m.content),
                "timestamp": getattr(m, "additional_kwargs", {}).get("timestamp", ""),
                "type": m.__class__.__name__
            })
        elif isinstance(m, str):
            # Handle plain string messages
            serialized["agent_messages"].append({
                "content": m,
                "timestamp": "",
                "type": "string"
            })
        else:
            # Handle any other type by converting to string
            serialized["agent_messages"].append({
                "content": str(m),
                "timestamp": "",
                "type": "unknown"
            })

    # Add download URL if cv_path exists
    if serialized["cv_path"]:
        filename = os.path.basename(serialized["cv_path"])
        serialized["cv_filename"] = filename
        # For secure downloads, we'll set this during processing with session_id
        serialized["cv_download_url"] = ""

    return serialized
    

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

@app.route("/api/session", methods=['POST'])
@limiter.limit("5 per minute")
def create_session():
    """Create anonymous session without signup"""
    return create_anonymous_session_endpoint()

@app.route("/api/status", methods=['GET'])
@limiter.limit("20 per minute")
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
@require_session
@limiter.limit("60 per hour")
def secure_check_job_status(job_id):
    """
    Secure job status checking with session validation
    """
    session_data = g.session_data
    session_id = session_data['session_id']
    
    # Check if session has any jobs
    if session_id not in secure_job_results:
        return create_secure_error_response("No jobs found for session", 404)
    
    # Check if specific job exists in session
    session_jobs = secure_job_results[session_id]
    if job_id not in session_jobs:
        return create_secure_error_response("Job not found", 404)
    
    job_info = session_jobs[job_id]
    
    if job_info["status"] == "processing":
        return jsonify({
            "status": "processing", 
            "job_id": job_id,
            "session_id": session_id
        }), 200

    elif job_info["status"] == "failed":
        return jsonify({
            "status": "failed",
            "job_id": job_id,
            "session_id": session_id,
            "error": job_info.get("error", "Unknown error")
        }), 200

    elif job_info["status"] == "completed":
        return jsonify({
            "status": "completed",
            "job_id": job_id,
            "session_id": session_id,
            "result": job_info.get("result", {}),
            "summary": job_info.get("summary", "")
        }), 200

    elif job_info["status"] == "awaiting_approval":
        return jsonify({
            "status": "awaiting_approval",
            "job_id": job_id,
            "session_id": session_id,
            "hitl_checkpoint": job_info.get("hitl_checkpoint"),
            "hitl_data": job_info.get("hitl_data", {}),
            "partial_result": job_info.get("partial_result", {}),
            "revision": job_info.get("revision", False)  # Indicate if this is a revised plan
        }), 200

    return create_secure_error_response("Unexpected job status", 500)

@app.route('/api/process', methods=['POST'])
@require_session
@limiter.limit("20 per hour")
def secure_process_job_hunting_request():
    """
    Secure job hunting processing endpoint with full security measures
    """
    
    if not multi_agent:
        return create_secure_error_response("Service temporarily unavailable", 503)
    
    session_data = g.session_data
    session_id = session_data['session_id']
    
    try:
        # Handle secure file upload
        resume_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                resume_path, error = save_uploaded_file_secure(file, session_id)
                if error:
                    return create_secure_error_response(error, 400)
        
        # Get and sanitize user prompt
        user_prompt = None
        if request.form.get('prompt'):
            user_prompt = request.form.get('prompt')
        elif request.is_json:
            data = request.get_json()
            user_prompt = data.get('prompt') or data.get('request') or data.get('message')
        
        if not user_prompt:
            return create_secure_error_response("Prompt is required", 400)
        
        # Additional input validation
        if len(user_prompt.strip()) < 5:
            return create_secure_error_response("Prompt too short", 400)
        
        # Generate secure job ID
        job_id = f"{session_id[:8]}_{uuid.uuid4().hex[:16]}"
        
        # Initialize secure job storage for session
        if session_id not in secure_job_results:
            secure_job_results[session_id] = {}
        
        secure_job_results[session_id][job_id] = {
            "status": "processing",
            "start_time": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        
        # Start secure background processing
        thread = threading.Thread(
            target=background_process_secure,
            args=(job_id, user_prompt, resume_path, session_data),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Request is being processed securely",
            "job_id": job_id,
            "session_id": session_id,
            "status_check_url": f"/api/status/{job_id}",
            "estimated_time": "5-15 seconds"
        }), 202
        
    except SecurityException as e:
        logger.warning(f"Security violation from session {session_id[:8]}***: {str(e)}")
        return create_secure_error_response(str(e), 403)
    except Exception as e:
        logger.error(f"Processing error for session {session_id[:8]}***")
        return create_secure_error_response("Request processing failed", 500)

#########################################
# HITL Approval Endpoints             #
#########################################

@app.route('/api/approve/<job_id>', methods=['POST'])
@require_session
@limiter.limit("10 per hour")
def secure_approve_job(job_id):
    """
    Handle HITL (Human-In-The-Loop) approval for jobs
    """
    try:
        session_data = g.session_data
        session_id = session_data['session_id']
        
        if not request.is_json:
            return create_secure_error_response("Request must be JSON", 400)
        
        data = request.get_json()
        approval_response = data.get('response')
        
        if not approval_response:
            return create_secure_error_response("Approval response is required", 400)
        
        # Check if job exists in session
        if session_id not in secure_job_results or job_id not in secure_job_results[session_id]:
            return create_secure_error_response("Job not found", 404)
        
        job_info = secure_job_results[session_id][job_id]
        
        # Check if job is waiting for approval
        if job_info.get("status") != "awaiting_approval":
            return create_secure_error_response("Job is not awaiting approval", 400)
        
        # Get partial state and continue processing
        partial_state = job_info.get("partial_result")
        if not partial_state:
            return create_secure_error_response("No partial state found", 500)
        
        
        # Continue processing with approval using thread_id
        thread_id = job_info.get("thread_id")
        if not thread_id:
            return create_secure_error_response("No thread ID found for job", 500)
        
        # IMMEDIATELY update job status to processing to fix race condition with polling
        # This applies to both approvals AND change requests - both require processing time
        secure_job_results[session_id][job_id]["status"] = "processing"
        if approval_response.get("approved") == False:
            logger.info(f"Job {job_id} status updated to 'processing' for plan revision request")
        else:
            logger.info(f"Job {job_id} status updated to 'processing' immediately after approval")
            
        # Process approval in background to avoid HTTP timeouts
        def process_approval_async():
            try:
                result = multi_agent.continue_from_approval(thread_id, approval_response)
                
                # Update job status based on result
                
                if result.get("success") or result.get("revision_applied"):
                    execution_time = result.get("execution_time", 0)
                    safe_result = serialize_result({**result, "execution_time": execution_time})
                    
                    # Update download URLs for secure access
                    if safe_result.get("cv_filename"):
                        safe_result["cv_download_url"] = f"/api/download/{session_id}/{safe_result['cv_filename']}"
                    
                    # Determine completion message based on whether this was a revision
                    summary = "✅ Job completed successfully after approval"
                    if result.get("revision_applied"):
                        summary = "✅ Job completed successfully after plan revision"
                    
                    secure_job_results[session_id][job_id] = {
                        "status": "completed",
                        "result": safe_result,
                        "summary": summary,
                    }
                    
                elif result.get("hitl_checkpoint"):
                    # Check if this is a revision (user rejected plan) or just execution progress
                    if approval_response.get("approved") == False:
                        # Handle plan revision - user requested changes, new plan created
                        secure_job_results[session_id][job_id].update({
                            "status": "awaiting_approval",
                            "hitl_checkpoint": result.get("hitl_checkpoint"),
                            "hitl_data": result.get("hitl_data", {}),
                            "thread_id": result.get("thread_id"),  # Keep the same thread_id
                            "revision": result.get("revision", True),  # Mark as revision
                            "partial_result": serialize_result(result)
                        })
                    else:
                        # User approved plan, but execution hit another checkpoint
                        # This should continue processing, not wait for approval again
                        logger.info(f"Job {job_id} approved and continuing execution, hit intermediate checkpoint")
                        
                        # Continue processing from the intermediate checkpoint automatically
                        try:
                            # Auto-approve intermediate checkpoints to continue execution
                            continued_result = multi_agent.continue_from_approval(thread_id, {"approved": True})
                            
                            # Handle the continued result
                            if continued_result.get("success") or continued_result.get("revision_applied"):
                                execution_time = continued_result.get("execution_time", 0)
                                safe_continued_result = serialize_result({**continued_result, "execution_time": execution_time})
                                
                                # Update download URLs for secure access
                                if safe_continued_result.get("cv_filename"):
                                    safe_continued_result["cv_download_url"] = f"/api/download/{session_id}/{safe_continued_result['cv_filename']}"
                                
                                secure_job_results[session_id][job_id] = {
                                    "status": "completed",
                                    "result": safe_continued_result,
                                    "summary": "✅ Job completed successfully",
                                }
                            else:
                                # Mark as processing if still ongoing
                                secure_job_results[session_id][job_id].update({
                                    "status": "processing",
                                    "message": "Executing approved plan..."
                                })
                        except Exception as continue_error:
                            logger.error(f"Failed to auto-continue job {job_id}: {continue_error}")
                            # Fallback to processing status
                            secure_job_results[session_id][job_id].update({
                                "status": "processing",
                                "message": "Executing approved plan..."
                            })
                else:
                    # Actual failure case
                    logger.error(f"Job {job_id} failed after approval: {result.get('error', 'Unknown error')}")
                    secure_job_results[session_id][job_id] = {
                        "status": "failed",
                        "error": result.get("error", "Processing failed after approval"),
                    }
            except Exception as process_error:
                logger.error(f"Async approval processing error: {process_error}")
                secure_job_results[session_id][job_id] = {
                    "status": "failed",
                    "error": f"Processing failed: {str(process_error)}",
                }
        
        # Start background processing
        thread = threading.Thread(target=process_approval_async, daemon=True)
        thread.start()
        
        # Respond immediately to prevent timeout
        return jsonify({
            "success": True,
            "message": "Approval processed successfully - execution in progress",
            "job_id": job_id
        }), 200
        
    except Exception as e:
        logger.error(f"Approval processing error for job {job_id}: {str(e)}")
        return create_secure_error_response("Failed to process approval", 500)


#########################################
# User Feedback Endpoints             #
#########################################

@app.route('/api/feedback', methods=['POST'])
@require_session
@limiter.limit("10 per hour")
def secure_collect_user_feedback():
    """
    Collect user feedback for performance evaluation
    
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
# File Download Endpoint               #
#########################################

@app.route('/api/download/<session_id>/<filename>', methods=['GET'])
@limiter.limit("20 per hour")
def secure_download_file(session_id, filename):
    """Secure download with session validation from URL"""
    try:
        # Get client IP for session validation
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        
        # Validate session directly (no headers needed for downloads)
        if session_id not in security_manager.active_sessions:
            logger.info(f"Session {session_id[:8]}*** not found in active sessions")
            return create_secure_error_response("Invalid session", 401)
            
        session_data = security_manager.active_sessions[session_id]
        
        # Check if session is expired
        if security_manager._is_session_expired(session_data):
            return create_secure_error_response("Session expired", 401)
        
        # Verify IP address (basic session hijacking protection)
        if session_data.get('client_ip') != client_ip:
            logger.warning(f"IP mismatch for download session {session_id[:8]}***: {session_data.get('client_ip')} vs {client_ip}")
            return create_secure_error_response("Access denied", 403)
        
        
        # Secure filename validation
        secure_filename_clean = security_manager.validate_filename(filename)
        if not secure_filename_clean:
            return create_secure_error_response("Invalid filename", 400)
        
        
        # Check if filename is a URL (Cloudinary storage)
        if secure_filename_clean.startswith(('http://', 'https://')) or secure_filename_clean.startswith('data:'):
            # Redirect to external URL or handle data URL
            if secure_filename_clean.startswith('data:'):
                # Handle base64 data URLs
                try:
                    import base64
                    header, encoded = secure_filename_clean.split(';base64,', 1)
                    mime_type = header.replace('data:', '')
                    file_data = base64.b64decode(encoded)
                    
                    # Extract original filename from secure_filename_clean or use generic
                    download_name = filename if filename != secure_filename_clean else "download.pdf"
                    
                    return Response(
                        file_data,
                        mimetype=mime_type,
                        headers={
                            'Content-Disposition': f'attachment; filename="{download_name}"'
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to handle data URL: {e}")
                    return create_secure_error_response("Invalid file format", 400)
            else:
                # External URL - redirect
                return redirect(secure_filename_clean)
        
        # Traditional file path handling (local development)
        if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
            # In serverless, files should be URLs
            return create_secure_error_response("File not available in serverless environment", 404)
        
        # Build secure file path for local development
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename_clean)
        
        if not os.path.exists(filepath):
            return create_secure_error_response("File not found", 404)
        
        # Validate file belongs to session (additional security check)
        if not security_manager.validate_file_access(filepath, session_id):
            return create_secure_error_response("Access denied", 403)
        
        # Determine MIME type
        mime_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=secure_filename_clean,
            mimetype=mime_type
        )
        
    except Exception as e:
        logger.error(f"Secure download error: {e}")
        return create_secure_error_response("Download failed", 500)

#########################################
# Example Usage Endpoint               #
#########################################

@app.route('/api/examples', methods=['GET'])
@limiter.limit("10 per minute")
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
# Performance & Analytics Endpoint    #
#########################################

@app.route('/api/performance', methods=['GET'])
@limiter.limit("10 per minute")
def get_comprehensive_performance():
    """
    UNIFIED PERFORMANCE ENDPOINT WITH SECURITY
    
    Get all performance data in one comprehensive response:
    - System health and metrics
    - User satisfaction and outcomes  
    - Agent performance breakdown
    - Effectiveness scores and grades
    - System monitoring data
    - Security metrics
    """
    try:
        if not multi_agent:
            return create_secure_error_response("Multi-agent system not available", 503)
        
        # Get all performance data
        system_performance = performance_evaluator.get_system_performance_summary()
        user_outcomes = multi_agent.get_user_outcomes_summary()
        effectiveness_report = multi_agent.get_system_effectiveness_report()
        
        # Get system monitoring data
        monitoring_data = system_monitor.to_dict()
        
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
                "system_health_actions": performance_evaluator._generate_recommendations()[:3] if hasattr(performance_evaluator, '_generate_recommendations') else []
            },
            
            # Meta Information
            "meta": {
                "last_updated": datetime.utcnow().isoformat(),
                "data_freshness": "real-time",
                "report_version": "3.0-secure",
                "tracking_since": system_performance.get("last_updated", "Unknown"),
                "security_enabled": True,
                "anonymous_sessions": True
            },
            
            # System Monitoring Data
            "system_health": monitoring_data.get("system_health", {}),
            "security_metrics": monitoring_data.get("security_metrics", {}),
            "recent_alerts": monitoring_data.get("recent_alerts", [])
        }
        
        return jsonify({
            "success": True,
            "message": "Comprehensive performance data retrieved",
            "data": performance_data,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Performance endpoint error: {str(e)}")
        return create_secure_error_response("Failed to get performance data", 500)

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

if __name__ == '__main__':
    
    # Run with security settings
    app.run(
        host='127.0.0.1',  # Localhost only for security
        port=5000, 
        debug=False,       # Disable debug in secure mode
        threaded=True
    )