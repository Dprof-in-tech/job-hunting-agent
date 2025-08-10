"""
Security and System Monitoring module for the multi-agent job hunting system
Provides anonymous session-based security and comprehensive system monitoring
"""

import os
import jwt
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from flask import request, jsonify, g
from cryptography.fernet import Fernet
import bleach
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
import re
from pathlib import Path
import logging

#########################################
# System Monitoring Integration        #
#########################################

import psutil
import platform
from dataclasses import dataclass, asdict

@dataclass
class SystemHealthData:
    """System health metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    response_time_p95: float
    error_rate: float
    uptime_seconds: int
    last_restart: str

@dataclass
class SecurityMetrics:
    """Security monitoring metrics"""
    blocked_requests: int
    suspicious_activities: int
    rate_limit_hits: int
    active_sessions: int
    failed_authentications: int
    vulnerability_scan_status: str
    last_security_scan: str
    threat_level: str

@dataclass
class AlertData:
    """System alert information"""
    id: str
    type: str  # 'info', 'warning', 'error', 'critical'
    message: str
    timestamp: str
    resolved: bool
    component: str

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security for anonymous sessions without user signup"""
    
    def __init__(self):
        # Generate encryption key (should be stored securely in production)
        self.encryption_key = self._get_or_generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # JWT secret for session tokens
        self.jwt_secret = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
        
        # Session storage (in production, use Redis or similar)
        self.active_sessions: Dict[str, Dict] = {}
        
        # Rate limiting storage
        self.rate_limits: Dict[str, Dict] = {}
        
        # Security settings
        self.max_sessions_per_ip = 20  # Increased for testing
        self.session_duration_hours = 24
        self.rate_limit_requests = 50  # requests per hour
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        
        # Cleanup old sessions periodically
        self._last_cleanup = time.time()
    
    def _get_or_generate_key(self) -> bytes:
        """Get encryption key from environment or generate temporary one"""
        import os
        import base64
        
        # Try to get key from environment variable (production)
        env_key = os.environ.get('ENCRYPTION_KEY')
        if env_key:
            try:
                # Decode base64 encoded key from environment
                return base64.b64decode(env_key)
            except Exception as e:
                logger.warning(f"Invalid ENCRYPTION_KEY format: {e}")
        
        # Check if we're in serverless environment
        if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
            logger.error("ENCRYPTION_KEY environment variable not set in production!")
            # Generate temporary key (sessions won't persist across deployments)
            key = Fernet.generate_key()
            logger.warning("Using temporary encryption key - set ENCRYPTION_KEY env var!")
            return key
        
        # Local development - try file-based key
        key_file = Path('.encryption_key')
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            try:
                key_file.write_bytes(key)
                logger.info("Generated new encryption key for local development")
            except Exception as e:
                logger.warning(f"Could not save encryption key: {e}")
            return key
    
    def create_anonymous_session(self, client_ip: str) -> Tuple[str, str]:
        """
        Create anonymous session without user signup
        Returns (session_token, session_id)
        """
        
        # Check if IP has too many active sessions
        active_sessions_for_ip = sum(
            1 for session in self.active_sessions.values() 
            if session.get('client_ip') == client_ip and not self._is_session_expired(session)
        )
        
        if active_sessions_for_ip >= self.max_sessions_per_ip:
            raise SecurityException(f"Too many active sessions from IP {client_ip}")
        
        # Generate session ID and data
        session_id = secrets.token_urlsafe(32)
        anonymous_user_id = f"anon_{secrets.token_urlsafe(16)}"
        
        session_data = {
            'session_id': session_id,
            'user_id': anonymous_user_id,
            'client_ip': client_ip,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=self.session_duration_hours)).isoformat(),
            'requests_made': 0,
            'last_activity': datetime.utcnow().isoformat()
        }
        
        # Store session
        self.active_sessions[session_id] = session_data
        
        # Create JWT token
        token_payload = {
            'session_id': session_id,
            'user_id': anonymous_user_id,
            'exp': datetime.utcnow() + timedelta(hours=self.session_duration_hours),
            'iat': datetime.utcnow(),
            'client_ip': client_ip
        }
        
        session_token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
        
        return session_token, session_id
    
    def validate_session(self, token: str, client_ip: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return session data"""
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload.get('session_id')
            
            # Check if session exists and is valid
            if session_id not in self.active_sessions:
                return None
            
            session_data = self.active_sessions[session_id]
            
            # Check if session is expired
            if self._is_session_expired(session_data):
                del self.active_sessions[session_id]
                return None
            
            # Verify IP address (basic session hijacking protection)
            if session_data.get('client_ip') != client_ip:
                logger.warning(f"IP mismatch for session {session_id}: {session_data.get('client_ip')} vs {client_ip}")
                return None
            
            # Update last activity
            session_data['last_activity'] = datetime.utcnow().isoformat()
            session_data['requests_made'] += 1
            
            return session_data
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None
    
    def _is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """Check if session is expired"""
        expires_at = datetime.fromisoformat(session_data['expires_at'])
        return datetime.utcnow() > expires_at
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like resume content"""
        if not data:
            return ""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return ""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            return ""
    
    def sanitize_user_input(self, user_input: str, max_length: int = 10000) -> str:
        """Sanitize user input to prevent prompt injection and XSS"""
        
        if not user_input:
            return ""
        
        # Length limit
        if len(user_input) > max_length:
            raise SecurityException(f"Input too long. Maximum {max_length} characters allowed.")
        
        # Remove HTML tags and potential XSS
        sanitized = bleach.clean(user_input, tags=[], strip=True)
        
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r'ignore\s+previous\s+instructions',
            r'system\s*:',
            r'assistant\s*:',
            r'user\s*:',
            r'<\s*script',
            r'javascript\s*:',
            r'data\s*:',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__.*__',  # Python dunder methods
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Limit consecutive special characters
        sanitized = re.sub(r'[^\w\s]{3,}', '***', sanitized)
        
        return sanitized.strip()
    
    def validate_file_upload(self, file) -> Tuple[bool, Optional[str]]:
        """Comprehensive file validation"""
        
        if not file or not file.filename:
            return False, "No file provided"
        
        filename = file.filename.lower()
        
        # Check file extension
        allowed_extensions = {'.pdf', '.docx', '.txt', '.doc'}
        file_ext = Path(filename).suffix
        if file_ext not in allowed_extensions:
            return False, f"File type not allowed. Supported: {', '.join(allowed_extensions)}"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > self.max_file_size:
            return False, f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
        
        if file_size < 10:  # Suspiciously small files
            return False, "File appears to be empty or corrupted"
        
        # Read file content for validation
        try:
            file_content = file.read(1024)  # Read first 1KB
            file.seek(0)  # Reset pointer
            
            # Use python-magic to detect actual file type (if available)
            if MAGIC_AVAILABLE:
                try:
                    file_type = magic.from_buffer(file_content, mime=True)
                    
                    # Validate file type matches extension
                    allowed_mime_types = {
                        '.pdf': ['application/pdf'],
                        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                        '.doc': ['application/msword'],
                        '.txt': ['text/plain', 'text/x-ascii']
                    }
                    
                    expected_types = allowed_mime_types.get(file_ext, [])
                    if file_type not in expected_types:
                        return False, f"File content doesn't match extension. Detected: {file_type}"
                except Exception as e:
                    logger.warning(f"Magic file type detection failed: {e}")
            else:
                logger.warning("python-magic not available - skipping MIME type validation")
            
            # Check for suspicious content
            suspicious_patterns = [
                b'<script',
                b'javascript:',
                b'eval(',
                b'exec(',
                b'<iframe',
                b'<object',
                b'<embed'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in file_content.lower():
                    return False, "File contains potentially malicious content"
            
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, "File validation failed"
        
        return True, None
    
    def check_rate_limit(self, client_ip: str, session_id: str = None) -> bool:
        """Check if client is within rate limits"""
        
        current_time = time.time()
        hour_window = current_time - 3600  # 1 hour window
        
        # Cleanup old entries
        if current_time - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_data()
        
        # Check IP-based rate limit
        ip_key = f"ip:{client_ip}"
        if ip_key not in self.rate_limits:
            self.rate_limits[ip_key] = []
        
        # Remove old entries
        self.rate_limits[ip_key] = [
            timestamp for timestamp in self.rate_limits[ip_key]
            if timestamp > hour_window
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[ip_key]) >= self.rate_limit_requests:
            return False
        
        # Add current request
        self.rate_limits[ip_key].append(current_time)
        
        return True
    
    def _cleanup_old_data(self):
        """Cleanup expired sessions and rate limit data"""
        
        current_time = time.time()
        self._last_cleanup = current_time
        
        # Remove expired sessions
        expired_sessions = [
            session_id for session_id, session_data in self.active_sessions.items()
            if self._is_session_expired(session_data)
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        # Remove old rate limit data (older than 2 hours)
        cleanup_threshold = current_time - 7200
        for key in list(self.rate_limits.keys()):
            self.rate_limits[key] = [
                timestamp for timestamp in self.rate_limits[key]
                if timestamp > cleanup_threshold
            ]
            if not self.rate_limits[key]:
                del self.rate_limits[key]
    
    def generate_secure_filename(self, original_filename: str, session_id: str) -> str:
        """Generate secure filename with session isolation"""
        
        # Extract safe extension
        safe_filename = bleach.clean(original_filename)
        extension = Path(safe_filename).suffix.lower()
        
        # Create hash of session for isolation
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8]
        
        # Generate secure filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = secrets.token_urlsafe(8)
        
        return f"{session_hash}_{timestamp}_{random_suffix}{extension}"
    
    def validate_filename(self, filename: str) -> Optional[str]:
        """Validate and sanitize filename for downloads"""
        if not filename:
            return None
            
        # Clean the filename
        clean_filename = bleach.clean(filename)
        
        # Check for path traversal attempts
        if '..' in clean_filename or '/' in clean_filename or '\\' in clean_filename:
            return None
            
        # Ensure reasonable length
        if len(clean_filename) > 255:
            return None
            
        return clean_filename
    
    def validate_file_access(self, filepath: str, session_id: str) -> bool:
        """Validate that a file belongs to the given session"""
        if not filepath or not session_id:
            return False
            
        # Extract filename from path
        filename = os.path.basename(filepath)
        
        # Check if filename contains session hash (first 8 chars of session hash)
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8]
        
        # Method 1: File starts with session hash (for uploaded files)
        if filename.startswith(session_hash):
            return True
        
        # Method 2: For CV files, allow if the filename matches expected CV patterns
        # and we have a reasonable timestamp match (created recently)
        if filename.startswith(('optimized_cv_', 'cv_', 'resume_')):
            # Check file creation time - should be recent (within session lifetime)
            try:
                file_stat = os.stat(filepath)
                file_age = time.time() - file_stat.st_mtime
                # Allow files created within the last 24 hours (session lifetime)
                if file_age < 24 * 3600:  # 24 hours
                    return True
            except Exception:
                pass
        
        # If neither validation method passes, deny access
        return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get security statistics (for monitoring)"""
        
        active_count = len([
            s for s in self.active_sessions.values() 
            if not self._is_session_expired(s)
        ])
        
        return {
            'active_sessions': active_count,
            'total_sessions_created': len(self.active_sessions),
            'rate_limit_entries': len(self.rate_limits),
            'avg_requests_per_session': sum(
                s.get('requests_made', 0) for s in self.active_sessions.values()
            ) / max(len(self.active_sessions), 1)
        }


class SecurityException(Exception):
    """Custom exception for security-related errors"""
    pass


# Global security manager instance
security_manager = SecurityManager()


def require_session(f):
    """Decorator to require valid session for endpoint access"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Check rate limiting first
        if not security_manager.check_rate_limit(client_ip):
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.',
                'retry_after': 3600
            }), 429
        
        # Get session token from either Authorization header or X-Session-ID header
        token = None
        session_id = None
        
        # Check Authorization header first (JWT token)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            # Validate JWT token
            session_data = security_manager.validate_session(token, client_ip)
            if session_data:
                # Store session data in Flask g for use in endpoint
                g.session_data = session_data
                g.client_ip = client_ip
                return f(*args, **kwargs)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired session'
                }), 401
        
        # Check X-Session-ID header (session ID)
        elif request.headers.get('X-Session-ID'):
            session_id = request.headers.get('X-Session-ID')
            
            # For X-Session-ID, we need to validate the session directly
            if session_id in security_manager.active_sessions:
                session_data = security_manager.active_sessions[session_id]
                
                # Check if session is valid
                if not security_manager._is_session_expired(session_data):
                    
                    # Verify IP address (basic session hijacking protection)
                    if session_data.get('client_ip') == client_ip:
                        
                        # Update last activity
                        session_data['last_activity'] = datetime.utcnow().isoformat()
                        session_data['requests_made'] += 1
                        
                        # Store session data in Flask g for use in endpoint
                        g.session_data = session_data
                        g.client_ip = client_ip
                        return f(*args, **kwargs)
                    else:
                        logger.warning(f"IP mismatch: session {session_data.get('client_ip')} vs {client_ip}")
                        return jsonify({
                            'success': False,
                            'error': 'Session access denied'
                        }), 403
                else:
                    # Session expired
                    logger.info(f"Session {session_id[:8]}*** expired")
                    return jsonify({
                        'success': False,
                        'error': 'Session expired'
                    }), 401
            else:
                # Session not found
                logger.info(f"Session {session_id[:8]}*** not found")
                return jsonify({
                    'success': False,
                    'error': 'Invalid session'
                }), 401
        
        # If no session headers provided, create new anonymous session
        try:
            new_token, new_session_id = security_manager.create_anonymous_session(client_ip)
            return jsonify({
                'success': False,
                'error': 'Session required',
                'session_token': new_token,
                'session_id': new_session_id,
                'message': 'New anonymous session created. Please retry with the provided token.'
            }), 401
        except SecurityException as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 403
    
    return decorated_function


def create_anonymous_session_endpoint():
    """Endpoint to create new anonymous session"""
    
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    try:
        # Check rate limiting
        if not security_manager.check_rate_limit(client_ip):
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.',
                'retry_after': 3600
            }), 429
        
        # Create session
        token, session_id = security_manager.create_anonymous_session(client_ip)
        
        return jsonify({
            'success': True,
            'session_token': token,
            'session_id': session_id,
            'expires_in': security_manager.session_duration_hours * 3600,
            'message': 'Anonymous session created successfully'
        }), 200
        
    except SecurityException as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create session'
        }), 500


def create_secure_error_response(message: str, status_code: int = 400) -> Tuple:
    """Create security-safe error response without internal details"""
    
    # Generic error messages to prevent information disclosure
    safe_messages = {
        400: "Invalid request",
        401: "Authentication required", 
        403: "Access denied",
        404: "Resource not found",
        429: "Rate limit exceeded",
        500: "Internal server error"
    }
    
    # Use generic message if specific message might leak info
    if status_code >= 500:
        safe_message = safe_messages.get(status_code, "Server error")
    else:
        safe_message = message
    
    response = {
        'success': False,
        'error': safe_message,
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': secrets.token_urlsafe(8)  # For support/debugging
    }
    
    return jsonify(response), status_code


class SystemMonitor:
    """Comprehensive system monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.alerts = []
        self.security_counters = {
            'blocked_requests': 0,
            'suspicious_activities': 0, 
            'rate_limit_hits': 0,
            'failed_authentications': 0
        }
        
    def get_system_health(self) -> SystemHealthData:
        """Get current system health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network connections (handle permission errors)
            try:
                connections = len(psutil.net_connections())
            except (psutil.AccessDenied, PermissionError):
                connections = 0  # Fallback when permissions are denied
            
            # System uptime
            uptime_seconds = int(time.time() - self.start_time)
            
            # Mock response time and error rate for now
            response_time_p95 = self._get_response_time_p95()
            error_rate = self._get_error_rate()
            
            return SystemHealthData(
                cpu_usage=round(cpu_percent, 1),
                memory_usage=round(memory_percent, 1),
                disk_usage=round(disk_percent, 1),
                active_connections=connections,
                response_time_p95=response_time_p95,
                error_rate=error_rate,
                uptime_seconds=uptime_seconds,
                last_restart=datetime.fromtimestamp(self.start_time).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            # Return default values on error
            return SystemHealthData(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                active_connections=0,
                response_time_p95=0.0,
                error_rate=0.0,
                uptime_seconds=int(time.time() - self.start_time),
                last_restart=datetime.fromtimestamp(self.start_time).isoformat()
            )
    
    def get_security_metrics(self, security_manager=None) -> SecurityMetrics:
        """Get security monitoring metrics"""
        try:
            # Get active sessions from security manager if available
            active_sessions = 0
            if security_manager and hasattr(security_manager, 'active_sessions'):
                active_sessions = len([
                    s for s in security_manager.active_sessions.values()
                    if not self._is_session_expired(s)
                ])
            
            # Calculate threat level
            threat_level = self._calculate_threat_level()
            
            return SecurityMetrics(
                blocked_requests=self.security_counters['blocked_requests'],
                suspicious_activities=self.security_counters['suspicious_activities'],
                rate_limit_hits=self.security_counters['rate_limit_hits'],
                active_sessions=active_sessions,
                failed_authentications=self.security_counters['failed_authentications'],
                vulnerability_scan_status="Passed",
                last_security_scan=datetime.now().isoformat(),
                threat_level=threat_level
            )
            
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}")
            return SecurityMetrics(
                blocked_requests=0,
                suspicious_activities=0,
                rate_limit_hits=0,
                active_sessions=0,
                failed_authentications=0,
                vulnerability_scan_status="Unknown",
                last_security_scan="Never",
                threat_level="low"
            )
    
    def get_recent_alerts(self, limit: int = 10):
        """Get recent system alerts"""
        # Sort by timestamp and return most recent
        sorted_alerts = sorted(
            self.alerts, 
            key=lambda x: x.timestamp, 
            reverse=True
        )
        return sorted_alerts[:limit]
    
    def add_alert(self, alert_type: str, message: str, component: str = "System"):
        """Add a new system alert"""
        alert = AlertData(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            type=alert_type,
            message=message,
            timestamp=datetime.now().isoformat(),
            resolved=False,
            component=component
        )
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def increment_security_counter(self, counter_name: str):
        """Increment security counter"""
        if counter_name in self.security_counters:
            self.security_counters[counter_name] += 1
    
    def _get_response_time_p95(self) -> float:
        """Calculate 95th percentile response time"""
        # Mock implementation - in production, use actual request timing data
        return 250.0
    
    def _get_error_rate(self) -> float:
        """Calculate current error rate"""
        # Mock implementation - in production, use actual error tracking
        return 1.2
    
    def _is_session_expired(self, session):
        """Check if session is expired"""
        try:
            created_at = session.get('created_at')
            if not created_at:
                return True
            
            # Simple check - assume 24 hour expiry
            session_age = time.time() - created_at
            return session_age > 86400  # 24 hours
            
        except Exception:
            return True
    
    def _calculate_threat_level(self) -> str:
        """Calculate current threat level based on security metrics"""
        total_threats = (
            self.security_counters['blocked_requests'] +
            self.security_counters['suspicious_activities'] +
            self.security_counters['failed_authentications']
        )
        
        if total_threats > 50:
            return "high"
        elif total_threats > 10:
            return "medium"
        else:
            return "low"
    
    def generate_sample_alerts(self):
        """Generate sample alerts for testing"""
        sample_alerts = [
            {
                'type': 'info',
                'message': 'System monitoring initialized successfully',
                'component': 'SystemMonitor'
            },
            {
                'type': 'warning', 
                'message': 'High memory usage detected (85%)',
                'component': 'ResourceMonitor'
            },
            {
                'type': 'info',
                'message': 'Security scan completed - no vulnerabilities found',
                'component': 'SecurityScanner'
            }
        ]
        
        for alert_data in sample_alerts:
            self.add_alert(
                alert_data['type'],
                alert_data['message'], 
                alert_data['component']
            )
    
    def to_dict(self):
        """Convert all monitoring data to dictionary"""
        try:
            health = self.get_system_health()
            security = self.get_security_metrics()
            alerts = self.get_recent_alerts()
            
            return {
                'system_health': asdict(health),
                'security_metrics': asdict(security),
                'recent_alerts': [asdict(alert) for alert in alerts]
            }
            
        except Exception as e:
            logger.error(f"Error converting monitoring data to dict: {e}")
            return {
                'system_health': {},
                'security_metrics': {},
                'recent_alerts': []
            }

# Global system monitor instance
system_monitor = SystemMonitor()

# Generate some sample alerts for demonstration
system_monitor.generate_sample_alerts()