"""
Performance Evaluation System for Multi-Agent Job Hunting System
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import statistics

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
    errors: List[str] = None
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
    user_satisfaction: Optional[float] = None  # 1-10 scale
    resume_improved: Optional[bool] = None
    jobs_found_helpful: Optional[bool] = None
    would_use_again: Optional[bool] = None

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
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
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
    
    def get_agent_performance_summary(self, agent_name: str) -> Dict[str, Any]:
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
    
    def get_system_performance_summary(self) -> Dict[str, Any]:
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
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
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
    
    def _calculate_performance_grade(self, metrics: AgentPerformanceMetrics) -> str:
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
    
    def _calculate_system_grade(self, success_rate: float, user_satisfaction: float) -> str:
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
    
    def _get_most_used_agent(self) -> str:
        """Find the most frequently used agent"""
        if not self.agent_metrics:
            return "None"
        
        return max(self.agent_metrics.items(), key=lambda x: x[1].total_calls)[0]
    
    def _get_least_reliable_agent(self) -> str:
        """Find the least reliable agent (lowest success rate)"""
        if not self.agent_metrics:
            return "None"
        
        # Filter out agents with too few calls to be meaningful
        reliable_agents = {name: metrics for name, metrics in self.agent_metrics.items() if metrics.total_calls >= 3}
        
        if not reliable_agents:
            return "Insufficient data"
        
        return min(reliable_agents.items(), key=lambda x: x[1].success_rate)[0]
    
    def _generate_recommendations(self) -> List[str]:
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

# Global performance evaluator instance
performance_evaluator = PerformanceEvaluator()