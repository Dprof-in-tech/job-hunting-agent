from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from tools import llm, extract_location, extract_salary, build_job_description
from agents.base import MultiAgentState
from agents.coordinator_agent import coordinator_agent
from agents.cv_creator_agent import cv_creator_agent
from agents.job_matcher_agent import job_matcher_agent
from agents.job_researcher_agent import job_researcher_agent
from agents.resume_analyst_agent import resume_analyst_agent
from performance_evaluator import performance_evaluator, UserOutcome
import time
import uuid
from datetime import datetime

config = RunnableConfig(recursion_limit=50)

#########################################
# Multi-Agent Orchestration System     #
#########################################

def should_continue(state: MultiAgentState):
    """Enhanced routing with smart decision making"""
    next_agent = state.get('next_agent', 'END')
    
    
    if next_agent == 'END':
        return END
    
    agent_map = {
        'coordinator': 'coordinator',
        'resume_analyst': 'resume_analyst', 
        'job_researcher': 'job_researcher',
        'cv_creator': 'cv_creator',
        'job_matcher': 'job_matcher'
    }
    
    return agent_map.get(next_agent, END)

def create_multi_agent_system():
    """Create the enhanced multi-agent orchestration system"""
    
    graph = StateGraph(MultiAgentState)

    JOB_PROCESSING_TOOLS = [
        extract_location,
        extract_salary, 
        build_job_description,
    ]

    # Create LLM instances with tools bound
    lm_with_tools = llm.bind_tools(JOB_PROCESSING_TOOLS)
    
    # Add all specialist agents
    graph.add_node("coordinator", coordinator_agent)
    graph.add_node("resume_analyst", resume_analyst_agent)
    graph.add_node("job_researcher", job_researcher_agent)
    graph.add_node("cv_creator", cv_creator_agent)
    graph.add_node("job_matcher", job_matcher_agent)
    
    # Set coordinator as entry point
    graph.set_entry_point("coordinator")
    
    # Enhanced routing system
    graph.add_conditional_edges("coordinator", should_continue, {
        "resume_analyst": "resume_analyst",
        "job_researcher": "job_researcher", 
        "cv_creator": "cv_creator",
        "job_matcher": "job_matcher",
        END: END
    })
    
    # All agents route back to coordinator for intelligent next decision
    graph.add_edge("resume_analyst", "coordinator")
    graph.add_edge("job_researcher", "coordinator")
    graph.add_edge("cv_creator", "coordinator")
    graph.add_edge("job_matcher", "coordinator")
    
    return graph.compile()

#########################################
# Enhanced Main Interface              #
#########################################

class JobHuntingMultiAgent:
    """
    Enhanced multi-agent job hunting system with performance tracking
    """
    
    def __init__(self):
        self.system = create_multi_agent_system()
        self.user_outcomes = []  # Store user outcomes for this session
    
    def process_request_with_hitl(self, user_message: str, resume_path: str = None, user_id: str = None, job_id: str = None) -> Dict[str, Any]:
        """
        Process user request with HITL support
        """
        # Add job_id to initial state for HITL checkpoints
        result = self._process_request_internal(user_message, resume_path, user_id, job_id)
        
        # Check if we hit an HITL checkpoint
        if result.get("next_agent") == "HITL_APPROVAL":
            return {
                "success": False,
                "hitl_checkpoint": result.get("hitl_checkpoint"),
                "hitl_data": result.get("hitl_data"),
                "messages": result.get("messages", []),
                "partial_state": result
            }
        
        return result
    
    def continue_from_approval(self, partial_state: Dict[str, Any], approval_response: Any) -> Dict[str, Any]:
        """Continue processing after human approval"""
        try:
            # Update state with approval response
            updated_state = partial_state.copy()
            updated_state['hitl_response'] = approval_response
            updated_state['next_agent'] = self._determine_next_agent_after_approval(partial_state, approval_response)
            
            # Continue processing from where we left off
            result = self.system.invoke(updated_state, {"recursion_limit": 50})
            
            return {
                "success": True,
                "messages": result.get("messages", []),
                "job_listings": result.get("job_listings", []),
                "cv_path": result.get("cv_path", ""),
                "agent_workflow": result.get("agent_workflow", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to continue after approval: {str(e)}"
            }
    
    def _determine_next_agent_after_approval(self, partial_state: Dict[str, Any], approval_response: Any) -> str:
        """Determine which agent to run next after approval"""
        checkpoint = partial_state.get("hitl_checkpoint")
        
        if checkpoint == "coordinator_plan":
            # After coordinator plan approval, follow the execution order
            plan = partial_state.get("coordinator_plan", {})
            return plan.get("next_agent", "END")
        elif checkpoint == "job_role_clarification":
            # After role clarification, continue with job research
            return "job_researcher"
        else:
            return "END"

    def process_request(self, user_message: str, resume_path: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Process user request with enhanced multi-agent coordination and performance tracking (backwards compatibility)
        """
        return self._process_request_internal(user_message, resume_path, user_id, None)
    
    def _process_request_internal(self, user_message: str, resume_path: str = None, user_id: str = None, job_id: str = None) -> Dict[str, Any]:
        """
        Internal processing with HITL support
        """
        
        # Generate session ID and user ID for tracking
        session_id = str(uuid.uuid4())
        user_id = user_id or f"user_{int(time.time())}"
        start_time = time.time()
        
        # Track individual agent timing
        agent_timings = {}
        
        initial_state = {
            "messages": [],
            "user_request": user_message,
            "resume_path": resume_path or "",
            "resume_content": "",
            "resume_analysis": {},
            "job_market_data": {},
            "job_listings": [],
            "cv_path": "",
            "comparison_results": {},
            "coordinator_plan": {},
            "completed_tasks": [],
            "next_agent": "coordinator",
            "session_id": session_id,
            "user_id": user_id,
            "job_id": job_id,  # Add job_id for HITL support
            "agent_start_times": {}  # Track individual agent start times
        }
        
        try:            
            # Process the request
            result = self.system.invoke(initial_state, config)
            
            # Calculate total processing time
            total_time = time.time() - start_time
            
            # Log system-level performance
            performance_evaluator.log_system_request(
                success=True, 
                request_time=total_time,
                human_intervention=False
            )
            
            # Log individual agent performance
            completed_tasks = result.get('completed_tasks', [])
            for agent_name in completed_tasks:
                if agent_name != 'coordinator':  # Skip coordinator as it's orchestration
                    # Estimate individual agent time (simplified)
                    estimated_agent_time = total_time / max(len([a for a in completed_tasks if a != 'coordinator']), 1)
                    
                    performance_evaluator.log_agent_call(
                        agent_name=agent_name,
                        success=True,
                        processing_time=estimated_agent_time,
                        error=None
                    )
            
            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "messages": result.get("messages", []),
                "completed_tasks": completed_tasks,
                "resume_analysis": result.get("resume_analysis", {}),
                "job_listings": result.get("job_listings", []),
                "cv_path": result.get("cv_path", ""),
                "job_market_data": result.get("job_market_data", {}),
                "comparison_results": result.get("comparison_results", {}),
                "processing_time": total_time,
                "performance_summary": self._generate_session_performance_summary(completed_tasks, total_time)
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            error_message = str(e)
            
            # Log system failure
            performance_evaluator.log_system_request(
                success=False, 
                request_time=total_time,
                human_intervention=False
            )
            
            # Log agent failures if we know which agent failed
            completed_tasks = initial_state.get('completed_tasks', [])
            if completed_tasks:
                last_agent = completed_tasks[-1] if completed_tasks else "unknown"
                if last_agent != 'coordinator':
                    performance_evaluator.log_agent_call(
                        agent_name=last_agent,
                        success=False,
                        processing_time=total_time,
                        error=error_message
                    )
            
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "session_id": session_id,
                "user_id": user_id,
                "error": error_message,
                "messages": [HumanMessage(content=f"System error: {error_message}")],
                "processing_time": total_time,
                "completed_tasks": completed_tasks
            }
    
    def collect_user_feedback(self, session_id: str, user_id: str, 
                            satisfaction: float, resume_helpful: bool = None, 
                            jobs_helpful: bool = None, would_use_again: bool = None) -> Dict[str, Any]:
        """
        Collect user feedback and update performance metrics
        """
        try:
            # Validate satisfaction score
            if not (1 <= satisfaction <= 10):
                return {
                    "success": False,
                    "error": "Satisfaction must be between 1 and 10"
                }
            
            # Create user outcome record
            outcome = UserOutcome(
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now(),
                user_satisfaction=satisfaction,
                resume_improved=resume_helpful,
                jobs_found_helpful=jobs_helpful,
                would_use_again=would_use_again
            )
            
            # Store outcome
            self.user_outcomes.append(outcome)
            
            # Log satisfaction in the performance evaluator
            performance_evaluator.log_user_satisfaction(satisfaction)
            
            return {
                "success": True,
                "message": "Feedback recorded successfully",
                "satisfaction_recorded": satisfaction,
                "feedback_summary": {
                    "session_id": session_id,
                    "satisfaction": satisfaction,
                    "resume_helpful": resume_helpful,
                    "jobs_helpful": jobs_helpful,
                    "would_use_again": would_use_again
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_user_outcomes_summary(self) -> Dict[str, Any]:
        """
        Get summary of user outcomes for this session
        """
        if not self.user_outcomes:
            return {
                "message": "No user feedback collected yet",
                "total_feedback": 0
            }
        
        total_outcomes = len(self.user_outcomes)
        
        # Calculate satisfaction metrics
        satisfaction_scores = [o.user_satisfaction for o in self.user_outcomes if o.user_satisfaction]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        # Calculate improvement rates
        resume_improved_count = sum(1 for o in self.user_outcomes if o.resume_improved)
        jobs_helpful_count = sum(1 for o in self.user_outcomes if o.jobs_found_helpful)
        would_use_again_count = sum(1 for o in self.user_outcomes if o.would_use_again)
        
        return {
            "total_feedback": total_outcomes,
            "avg_satisfaction": round(avg_satisfaction, 2),
            "satisfaction_distribution": {
                "excellent (9-10)": sum(1 for s in satisfaction_scores if s >= 9),
                "good (7-8)": sum(1 for s in satisfaction_scores if 7 <= s < 9),
                "fair (5-6)": sum(1 for s in satisfaction_scores if 5 <= s < 7),
                "poor (1-4)": sum(1 for s in satisfaction_scores if s < 5)
            },
            "helpfulness_rates": {
                "resume_improvement": round((resume_improved_count / total_outcomes) * 100, 1),
                "job_search_help": round((jobs_helpful_count / total_outcomes) * 100, 1),
                "user_retention": round((would_use_again_count / total_outcomes) * 100, 1)
            },
            "satisfaction_grade": self._grade_satisfaction(avg_satisfaction)
        }
    
    def get_system_effectiveness_report(self) -> Dict[str, Any]:
        """
        Get comprehensive system effectiveness report
        """
        try:
            # Get system performance from evaluator
            system_performance = performance_evaluator.get_system_performance_summary()
            
            # Get user outcomes
            user_outcomes = self.get_user_outcomes_summary()
            
            # Calculate effectiveness score
            effectiveness_score = self._calculate_effectiveness_score(system_performance, user_outcomes)
            
            # Get benchmark comparison
            benchmark_comparison = self._get_benchmark_comparison(system_performance)
            
            return {
                "effectiveness_score": effectiveness_score,
                "effectiveness_grade": self._grade_effectiveness(effectiveness_score),
                "system_performance": system_performance,
                "user_outcomes": user_outcomes,
                "benchmark_comparison": benchmark_comparison,
                "agent_performance": self._get_agent_performance_breakdown(),
                "recommendations": self._generate_recommendations(effectiveness_score, system_performance, user_outcomes),
                "report_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "fallback_report": performance_evaluator.get_comprehensive_report()
            }
    
    def _generate_session_performance_summary(self, completed_tasks: list, processing_time: float) -> Dict[str, Any]:
        """Generate performance summary for a single session"""
        return {
            "agents_used": len([task for task in completed_tasks if task != 'coordinator']),
            "total_processing_time": round(processing_time, 2),
            "avg_time_per_agent": round(processing_time / max(len([task for task in completed_tasks if task != 'coordinator']), 1), 2),
            "efficiency_rating": "excellent" if processing_time < 10 else "good" if processing_time < 20 else "fair"
        }
    
    def _calculate_effectiveness_score(self, system_performance: Dict[str, Any], user_outcomes: Dict[str, Any]) -> float:
        """Calculate overall system effectiveness score"""
        score = 0
        
        # System reliability (40% weight)
        success_rate = system_performance.get("success_rate", 0)
        if success_rate >= 90:
            score += 40
        elif success_rate >= 75:
            score += 30
        elif success_rate >= 60:
            score += 20
        elif success_rate >= 40:
            score += 10
        
        # User satisfaction (35% weight)
        user_satisfaction = user_outcomes.get("avg_satisfaction", 0)
        if user_satisfaction >= 8:
            score += 35
        elif user_satisfaction >= 6:
            score += 25
        elif user_satisfaction >= 4:
            score += 15
        elif user_satisfaction >= 2:
            score += 5
        
        # User helpfulness rates (25% weight)
        helpfulness = user_outcomes.get("helpfulness_rates", {})
        avg_helpfulness = sum(helpfulness.values()) / max(len(helpfulness), 1) if helpfulness else 0
        if avg_helpfulness >= 80:
            score += 25
        elif avg_helpfulness >= 60:
            score += 20
        elif avg_helpfulness >= 40:
            score += 15
        elif avg_helpfulness >= 20:
            score += 10
        
        return round(score, 1)
    
    def _get_benchmark_comparison(self, system_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Compare system performance against benchmarks"""
        benchmarks = {
            "target_satisfaction": 8.0,
            "target_success_rate": 90.0,
            "target_response_time": 15.0,
            "manual_resume_time": 60.0,  # minutes
            "manual_job_search_time": 120.0,  # minutes
            "system_resume_time": 2.0,  # minutes
            "system_job_search_time": 5.0  # minutes
        }
        
        actual_satisfaction = system_performance.get("user_satisfaction", 0)
        actual_success_rate = system_performance.get("success_rate", 0)
        actual_response_time = system_performance.get("avg_request_time", 0)
        
        return {
            "performance_vs_targets": {
                "satisfaction": {
                    "actual": actual_satisfaction,
                    "target": benchmarks["target_satisfaction"],
                    "status": "✅ Meeting target" if actual_satisfaction >= benchmarks["target_satisfaction"] else "⚠️ Below target"
                },
                "success_rate": {
                    "actual": actual_success_rate,
                    "target": benchmarks["target_success_rate"],
                    "status": "✅ Meeting target" if actual_success_rate >= benchmarks["target_success_rate"] else "⚠️ Below target"
                },
                "response_time": {
                    "actual": actual_response_time,
                    "target": benchmarks["target_response_time"],
                    "status": "✅ Meeting target" if actual_response_time <= benchmarks["target_response_time"] else "⚠️ Too slow"
                }
            },
            "efficiency_vs_manual": {
                "resume_analysis": {
                    "manual_time": benchmarks["manual_resume_time"],
                    "system_time": benchmarks["system_resume_time"],
                    "time_saved": benchmarks["manual_resume_time"] - benchmarks["system_resume_time"],
                    "efficiency_gain": f"{((benchmarks['manual_resume_time'] / benchmarks['system_resume_time']) - 1) * 100:.0f}% faster"
                },
                "job_search": {
                    "manual_time": benchmarks["manual_job_search_time"],
                    "system_time": benchmarks["system_job_search_time"],
                    "time_saved": benchmarks["manual_job_search_time"] - benchmarks["system_job_search_time"],
                    "efficiency_gain": f"{((benchmarks['manual_job_search_time'] / benchmarks['system_job_search_time']) - 1) * 100:.0f}% faster"
                }
            }
        }
    
    def _get_agent_performance_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown for all agents"""
        agent_names = ["resume_analyst", "job_researcher", "cv_creator", "job_matcher"]
        breakdown = {}
        
        for agent_name in agent_names:
            if agent_name in performance_evaluator.agent_metrics:
                breakdown[agent_name] = performance_evaluator.get_agent_performance_summary(agent_name)
            else:
                breakdown[agent_name] = {"message": "No data available"}
        
        return breakdown
    
    def _generate_recommendations(self, effectiveness_score: float, 
                                system_performance: Dict[str, Any], 
                                user_outcomes: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Overall system recommendations
        if effectiveness_score >= 85:
            recommendations.append("🎉 Excellent performance! System is highly effective. Continue current approach.")
        elif effectiveness_score >= 65:
            recommendations.append("✅ Good performance. System is effective with room for optimization.")
        else:
            recommendations.append("⚠️ System needs improvement. Focus on reliability and user satisfaction.")
        
        # Specific recommendations based on metrics
        if system_performance.get("success_rate", 0) < 80:
            recommendations.append("🔧 Improve system reliability - success rate below 80%. Review error patterns.")
        
        if user_outcomes.get("avg_satisfaction", 0) < 6:
            recommendations.append("😊 Enhance user experience - satisfaction below 6/10. Consider human-in-the-loop features.")
        
        if system_performance.get("avg_request_time", 0) > 20:
            recommendations.append("⚡ Optimize response time - currently above 20 seconds. Consider parallel processing.")
        
        helpfulness_rates = user_outcomes.get("helpfulness_rates", {})
        if helpfulness_rates.get("resume_improvement", 0) < 60:
            recommendations.append("📄 Improve resume analysis quality - users finding it less helpful.")
        
        if helpfulness_rates.get("job_search_help", 0) < 60:
            recommendations.append("🔍 Enhance job search relevance - users not finding job matches helpful.")
        
        if not recommendations or len(recommendations) == 1:
            recommendations.append("📊 Continue monitoring metrics and collecting user feedback for insights.")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _grade_satisfaction(self, score: float) -> str:
        """Grade user satisfaction score"""
        if score >= 8:
            return "Excellent"
        elif score >= 6:
            return "Good"
        elif score >= 4:
            return "Fair"
        else:
            return "Poor"
    
    def _grade_effectiveness(self, score: float) -> str:
        """Grade overall system effectiveness"""
        if score >= 85:
            return "Highly Effective"
        elif score >= 65:
            return "Effective"
        elif score >= 45:
            return "Moderately Effective"
        else:
            return "Needs Improvement"
    
    def get_performance_summary(self, result: Dict[str, Any]) -> str:
        """
        Get detailed performance and capability summary
        """
        completed = result.get("completed_tasks", [])
        if not completed:
            return "❌ No agents completed their tasks"
        
        capabilities_used = []
        
        if "resume_analyst" in completed:
            analysis = result.get("resume_analysis", {})
            score = analysis.get("overall_score", "N/A")
            capabilities_used.append(f"📊 Resume Analysis (Score: {score}/100)")
        
        if "job_researcher" in completed:
            market_data = result.get("job_market_data", {})
            jobs_found = market_data.get("total_jobs_found", 0)
            capabilities_used.append(f"🔍 Job Research ({jobs_found} opportunities)")
        
        if "cv_creator" in completed:
            cv_path = result.get("cv_path", "")
            status = "✅ Created" if cv_path else "❌ Failed"
            capabilities_used.append(f"📝 CV Creation ({status})")
        
        if "job_matcher" in completed:
            comparison = result.get("comparison_results", {})
            avg_score = comparison.get("average_score", 0)
            capabilities_used.append(f"🎯 Job Matching (Avg: {avg_score:.1f}%)")
        
        processing_time = result.get("processing_time", 0)
        performance_summary = result.get("performance_summary", {})
        
        summary = f"✅ Enhanced Performance Summary:\n" + "\n".join(capabilities_used)
        summary += f"\n⏱️ Processing Time: {processing_time:.2f}s"
        summary += f"\n🎭 Agents Used: {performance_summary.get('agents_used', 0)}"
        summary += f"\n⚡ Efficiency: {performance_summary.get('efficiency_rating', 'N/A').title()}"
        
        return summary