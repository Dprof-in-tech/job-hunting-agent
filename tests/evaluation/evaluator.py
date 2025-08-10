"""
Main evaluation framework for the multi-agent job hunting system
"""

import asyncio
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

from .custom_metrics import (
    ResumeAnalysisAccuracyMetric,
    JobSearchRelevanceMetric,
    CVGenerationQualityMetric,
    JobMatchingAccuracyMetric,
    SystemCoherenceMetric,
    PerformanceEfficiencyMetric
)

@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    agent_name: str
    test_case_id: str
    metrics_results: Dict[str, Any]
    overall_score: float
    success: bool
    execution_time: float
    error_message: Optional[str] = None

@dataclass
class SystemEvaluationReport:
    """Comprehensive system evaluation report"""
    timestamp: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_score: float
    agent_scores: Dict[str, float]
    performance_metrics: Dict[str, float]
    detailed_results: List[EvaluationResult]
    recommendations: List[str]

class MultiAgentEvaluator:
    """
    Comprehensive evaluator for the multi-agent job hunting system
    """
    
    def __init__(self):
        self.metrics_registry = {
            "resume_analyst": [
                ResumeAnalysisAccuracyMetric(threshold=0.8),
                SystemCoherenceMetric(threshold=0.8)
            ],
            "job_researcher": [
                JobSearchRelevanceMetric(threshold=0.75, min_jobs=3),
                PerformanceEfficiencyMetric(threshold=0.7, max_time=10.0)
            ],
            "cv_creator": [
                CVGenerationQualityMetric(threshold=0.8),
                PerformanceEfficiencyMetric(threshold=0.7, max_time=15.0)
            ],
            "job_matcher": [
                JobMatchingAccuracyMetric(threshold=0.75),
                SystemCoherenceMetric(threshold=0.75)
            ],
            "system_integration": [
                SystemCoherenceMetric(threshold=0.8),
                PerformanceEfficiencyMetric(threshold=0.7, max_time=20.0)
            ]
        }
        
        self.evaluation_results: List[EvaluationResult] = []
    
    def create_test_cases(self, test_data: List[Dict[str, Any]]) -> List[LLMTestCase]:
        """Create LLMTestCase objects from test data"""
        test_cases = []
        
        for i, data in enumerate(test_data):
            test_case = LLMTestCase(
                input=data.get("input", ""),
                actual_output=data.get("actual_output", ""),
                expected_output=data.get("expected_output", ""),
                context=data.get("context", []),
                retrieval_context=data.get("retrieval_context", [])
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def evaluate_agent(self, 
                      agent_name: str, 
                      test_cases: List[LLMTestCase]) -> List[EvaluationResult]:
        """Evaluate a specific agent with appropriate metrics"""
        
        if agent_name not in self.metrics_registry:
            raise ValueError(f"No metrics defined for agent: {agent_name}")
        
        metrics = self.metrics_registry[agent_name]
        results = []
        
        for i, test_case in enumerate(test_cases):
            start_time = time.time()
            
            try:
                # Run evaluation with DeepEval
                evaluation_result = evaluate(
                    test_cases=[test_case],
                    metrics=metrics,
                    print_results=False
                )
                
                execution_time = time.time() - start_time
                
                # Calculate overall score
                metric_scores = []
                metrics_results = {}
                
                for metric in metrics:
                    metric_name = metric.__name__
                    metrics_results[metric_name] = {
                        "score": metric.score,
                        "success": metric.success,
                        "reason": metric.reason
                    }
                    metric_scores.append(metric.score)
                
                overall_score = sum(metric_scores) / len(metric_scores) if metric_scores else 0.0
                success = all(metric.success for metric in metrics)
                
                result = EvaluationResult(
                    agent_name=agent_name,
                    test_case_id=f"{agent_name}_test_{i}",
                    metrics_results=metrics_results,
                    overall_score=overall_score,
                    success=success,
                    execution_time=execution_time
                )
                
                results.append(result)
                self.evaluation_results.append(result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                result = EvaluationResult(
                    agent_name=agent_name,
                    test_case_id=f"{agent_name}_test_{i}",
                    metrics_results={},
                    overall_score=0.0,
                    success=False,
                    execution_time=execution_time,
                    error_message=str(e)
                )
                
                results.append(result)
                self.evaluation_results.append(result)
        
        return results
    
    def evaluate_system_integration(self, 
                                   integration_test_cases: List[LLMTestCase]) -> List[EvaluationResult]:
        """Evaluate complete system integration"""
        return self.evaluate_agent("system_integration", integration_test_cases)
    
    def generate_performance_benchmark(self, 
                                     agent_name: str, 
                                     test_iterations: int = 10) -> Dict[str, float]:
        """Generate performance benchmarks for an agent"""
        
        # This would be called during actual system testing
        # For now, we'll return mock benchmark data
        
        benchmarks = {
            "avg_response_time": 5.2,
            "p95_response_time": 8.7,
            "success_rate": 0.92,
            "memory_usage_mb": 150.5,
            "cpu_utilization": 0.45,
            "throughput_per_minute": 12.0
        }
        
        return benchmarks
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns across evaluations"""
        
        error_results = [r for r in self.evaluation_results if not r.success]
        
        if not error_results:
            return {"total_errors": 0, "error_patterns": {}}
        
        # Categorize errors
        error_categories = {}
        agent_error_counts = {}
        
        for result in error_results:
            agent = result.agent_name
            error_msg = result.error_message or "Unknown error"
            
            agent_error_counts[agent] = agent_error_counts.get(agent, 0) + 1
            
            # Simple error categorization
            if "timeout" in error_msg.lower():
                error_categories["timeout"] = error_categories.get("timeout", 0) + 1
            elif "api" in error_msg.lower():
                error_categories["api_error"] = error_categories.get("api_error", 0) + 1
            elif "format" in error_msg.lower() or "parse" in error_msg.lower():
                error_categories["format_error"] = error_categories.get("format_error", 0) + 1
            else:
                error_categories["other"] = error_categories.get("other", 0) + 1
        
        return {
            "total_errors": len(error_results),
            "error_rate": len(error_results) / len(self.evaluation_results),
            "error_categories": error_categories,
            "agent_error_counts": agent_error_counts,
            "most_problematic_agent": max(agent_error_counts.items(), 
                                        key=lambda x: x[1])[0] if agent_error_counts else None
        }
    
    def generate_recommendations(self, 
                               evaluation_report: 'SystemEvaluationReport') -> List[str]:
        """Generate actionable recommendations based on evaluation results"""
        
        recommendations = []
        
        # Performance recommendations
        if evaluation_report.overall_score < 0.7:
            recommendations.append("🚨 Overall system performance is below acceptable threshold (70%). Immediate optimization required.")
        
        # Agent-specific recommendations
        for agent, score in evaluation_report.agent_scores.items():
            if score < 0.6:
                recommendations.append(f"⚠️ {agent.replace('_', ' ').title()} performance is critically low ({score:.2f}). Review and optimize.")
            elif score < 0.8:
                recommendations.append(f"📈 {agent.replace('_', ' ').title()} has room for improvement ({score:.2f}). Consider tuning parameters.")
        
        # Error pattern recommendations
        error_analysis = self.analyze_error_patterns()
        if error_analysis["error_rate"] > 0.1:  # More than 10% error rate
            recommendations.append(f"🔧 High error rate ({error_analysis['error_rate']:.2%}). Focus on error handling and resilience.")
        
        # Performance metric recommendations
        performance = evaluation_report.performance_metrics
        if performance.get("avg_response_time", 0) > 15:
            recommendations.append("⚡ Response time is too high. Consider parallel processing and caching strategies.")
        
        if performance.get("success_rate", 1.0) < 0.9:
            recommendations.append("🎯 Success rate is below 90%. Improve error handling and fallback mechanisms.")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def generate_comprehensive_report(self) -> SystemEvaluationReport:
        """Generate a comprehensive evaluation report"""
        
        if not self.evaluation_results:
            return SystemEvaluationReport(
                timestamp=datetime.now(),
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                overall_score=0.0,
                agent_scores={},
                performance_metrics={},
                detailed_results=[],
                recommendations=["No evaluation data available. Run tests first."]
            )
        
        total_tests = len(self.evaluation_results)
        passed_tests = sum(1 for r in self.evaluation_results if r.success)
        failed_tests = total_tests - passed_tests
        
        # Calculate agent scores
        agent_scores = {}
        agent_results = {}
        
        for result in self.evaluation_results:
            agent = result.agent_name
            if agent not in agent_results:
                agent_results[agent] = []
            agent_results[agent].append(result.overall_score)
        
        for agent, scores in agent_results.items():
            agent_scores[agent] = sum(scores) / len(scores) if scores else 0.0
        
        # Calculate overall score
        all_scores = [r.overall_score for r in self.evaluation_results]
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        # Calculate performance metrics
        execution_times = [r.execution_time for r in self.evaluation_results]
        performance_metrics = {
            "avg_response_time": sum(execution_times) / len(execution_times) if execution_times else 0.0,
            "max_response_time": max(execution_times) if execution_times else 0.0,
            "min_response_time": min(execution_times) if execution_times else 0.0,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "failure_rate": failed_tests / total_tests if total_tests > 0 else 0.0
        }
        
        # Generate report
        report = SystemEvaluationReport(
            timestamp=datetime.now(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            overall_score=overall_score,
            agent_scores=agent_scores,
            performance_metrics=performance_metrics,
            detailed_results=self.evaluation_results.copy(),
            recommendations=[]
        )
        
        # Generate recommendations
        report.recommendations = self.generate_recommendations(report)
        
        return report
    
    def export_report(self, report: SystemEvaluationReport, filepath: str):
        """Export evaluation report to JSON file"""
        
        # Convert report to serializable dictionary
        report_dict = {
            "timestamp": report.timestamp.isoformat(),
            "summary": {
                "total_tests": report.total_tests,
                "passed_tests": report.passed_tests,
                "failed_tests": report.failed_tests,
                "overall_score": report.overall_score,
                "success_rate": report.passed_tests / report.total_tests if report.total_tests > 0 else 0.0
            },
            "agent_scores": report.agent_scores,
            "performance_metrics": report.performance_metrics,
            "recommendations": report.recommendations,
            "detailed_results": [
                {
                    "agent_name": r.agent_name,
                    "test_case_id": r.test_case_id,
                    "overall_score": r.overall_score,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "metrics_results": r.metrics_results,
                    "error_message": r.error_message
                }
                for r in report.detailed_results
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
    
    def clear_results(self):
        """Clear all evaluation results"""
        self.evaluation_results.clear()