"""
Comprehensive evaluation tests using DeepEval for the multi-agent system
"""

import pytest
import json
import os
from datetime import datetime
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

from tests.evaluation.evaluator import MultiAgentEvaluator, SystemEvaluationReport
from tests.evaluation.custom_metrics import (
    ResumeAnalysisAccuracyMetric,
    JobSearchRelevanceMetric, 
    CVGenerationQualityMetric,
    JobMatchingAccuracyMetric,
    SystemCoherenceMetric,
    PerformanceEfficiencyMetric
)
from tests.test_data.sample_resumes import SAMPLE_RESUMES
from tests.test_data.sample_job_listings import SAMPLE_JOB_LISTINGS, JOB_MATCHING_SCENARIOS


class TestDeepEvalIntegration:
    """Test DeepEval integration with multi-agent system"""
    
    @pytest.fixture
    def evaluator(self):
        return MultiAgentEvaluator()
    
    @pytest.fixture
    def resume_analysis_test_cases(self):
        """Create test cases for resume analysis evaluation"""
        test_cases = []
        
        for resume_type, resume_data in SAMPLE_RESUMES.items():
            test_case = LLMTestCase(
                input=f"Analyze the following resume: {resume_data['content']}",
                actual_output=resume_data['expected_analysis'],
                expected_output="Detailed resume analysis with scores and recommendations",
                context=[f"Resume type: {resume_type}"]
            )
            test_cases.append(test_case)
        
        return test_cases
    
    @pytest.fixture 
    def job_search_test_cases(self):
        """Create test cases for job search evaluation"""
        test_cases = []
        
        for category, jobs in SAMPLE_JOB_LISTINGS.items():
            test_case = LLMTestCase(
                input=f"Find {category} jobs",
                actual_output={"job_listings": jobs, "total_jobs_found": len(jobs)},
                expected_output=f"Relevant {category} job listings",
                context=[f"Job category: {category}"]
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def test_resume_analysis_evaluation(self, evaluator, resume_analysis_test_cases):
        """Test resume analysis agent evaluation"""
        
        results = evaluator.evaluate_agent("resume_analyst", resume_analysis_test_cases)
        
        # Validate evaluation results
        assert len(results) == len(resume_analysis_test_cases)
        assert all(isinstance(r.overall_score, float) for r in results)
        assert all(0 <= r.overall_score <= 1 for r in results)
        
        # Check that different resume types get different scores
        scores = [r.overall_score for r in results]
        assert len(set(scores)) > 1, "Different resumes should get different scores"
        
        # Senior engineer resume should score higher than recent graduate
        senior_result = next(r for r in results if "senior" in str(r.test_case_id).lower())
        graduate_result = next(r for r in results if "graduate" in str(r.test_case_id).lower())
        assert senior_result.overall_score > graduate_result.overall_score
    
    def test_job_search_evaluation(self, evaluator, job_search_test_cases):
        """Test job search agent evaluation"""
        
        results = evaluator.evaluate_agent("job_researcher", job_search_test_cases)
        
        # Validate evaluation results
        assert len(results) == len(job_search_test_cases)
        
        # Check performance metrics
        avg_execution_time = sum(r.execution_time for r in results) / len(results)
        assert avg_execution_time < 5.0, "Job search evaluation taking too long"
        
        # Validate relevance scores
        for result in results:
            if "RelevanceMetric" in str(result.metrics_results):
                relevance_data = result.metrics_results.get("Job Search Relevance", {})
                if relevance_data.get("success"):
                    assert relevance_data.get("score", 0) >= 0.7
    
    def test_system_integration_evaluation(self, evaluator):
        """Test complete system integration evaluation"""
        
        # Create integration test case
        integration_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher", "cv_creator"],
            "resume_analysis": SAMPLE_RESUMES["software_engineer_senior"]["expected_analysis"],
            "job_listings": SAMPLE_JOB_LISTINGS["software_engineering"],
            "cv_path": "/tmp/generated_cv.pdf",
            "processing_time": 12.3,
            "performance_summary": {"efficiency_rating": "good"}
        }
        
        test_case = LLMTestCase(
            input="Complete job hunting assistance",
            actual_output=integration_response,
            expected_output="Comprehensive job hunting results",
            context=["Integration test for complete workflow"]
        )
        
        results = evaluator.evaluate_system_integration([test_case])
        
        assert len(results) == 1
        result = results[0]
        
        # System integration should score well for complete workflow
        assert result.overall_score >= 0.7, f"System integration score too low: {result.overall_score}"
        assert result.success is True
    
    def test_performance_evaluation_metrics(self):
        """Test performance evaluation metrics specifically"""
        
        performance_scenarios = [
            {
                "name": "fast_response",
                "data": {
                    "success": True,
                    "processing_time": 3.2,
                    "performance_summary": {"efficiency_rating": "excellent"}
                },
                "expected_score": 0.8
            },
            {
                "name": "slow_response", 
                "data": {
                    "success": True,
                    "processing_time": 18.5,  # Over threshold
                    "performance_summary": {"efficiency_rating": "fair"}
                },
                "expected_score": 0.4
            },
            {
                "name": "failed_response",
                "data": {
                    "success": False,
                    "processing_time": 25.0,
                    "error": "System failure"
                },
                "expected_score": 0.2
            }
        ]
        
        metric = PerformanceEfficiencyMetric(threshold=0.7, max_time=15.0)
        
        for scenario in performance_scenarios:
            test_case = LLMTestCase(
                input="Performance test",
                actual_output=scenario["data"],
                expected_output="Performance measurement"
            )
            
            score = metric.measure(test_case)
            
            # Validate score is in expected range
            if scenario["name"] == "fast_response":
                assert score >= 0.8, f"Fast response should score high: {score}"
            elif scenario["name"] == "slow_response":
                assert score < 0.7, f"Slow response should score low: {score}"
            elif scenario["name"] == "failed_response":
                assert score < 0.5, f"Failed response should score very low: {score}"
    
    def test_comprehensive_system_evaluation(self, evaluator):
        """Test comprehensive system evaluation with report generation"""
        
        # Create diverse test scenarios
        test_scenarios = [
            # Successful complete workflow
            {
                "input": "Complete job hunting help",
                "actual_output": {
                    "success": True,
                    "completed_tasks": ["coordinator", "resume_analyst", "job_researcher", "cv_creator"],
                    "resume_analysis": {"overall_score": 85},
                    "job_listings": SAMPLE_JOB_LISTINGS["software_engineering"][:3],
                    "cv_path": "/tmp/cv.pdf",
                    "processing_time": 11.2,
                    "performance_summary": {"efficiency_rating": "excellent"}
                },
                "expected_output": "Complete job hunting results"
            },
            # Resume analysis only
            {
                "input": "Analyze my resume",
                "actual_output": {
                    "success": True,
                    "completed_tasks": ["coordinator", "resume_analyst"],
                    "resume_analysis": SAMPLE_RESUMES["recent_graduate"]["expected_analysis"],
                    "processing_time": 4.1
                },
                "expected_output": "Resume analysis results"
            },
            # Failed scenario
            {
                "input": "Find jobs with API failure",
                "actual_output": {
                    "success": False,
                    "error": "Job search API unavailable",
                    "completed_tasks": ["coordinator"],
                    "processing_time": 8.3
                },
                "expected_output": "Error handling"
            }
        ]
        
        # Create test cases
        test_cases = [
            LLMTestCase(
                input=scenario["input"],
                actual_output=scenario["actual_output"],
                expected_output=scenario["expected_output"]
            )
            for scenario in test_scenarios
        ]
        
        # Evaluate with different agents
        for agent_name in ["resume_analyst", "job_researcher", "system_integration"]:
            if agent_name in evaluator.metrics_registry:
                evaluator.evaluate_agent(agent_name, test_cases)
        
        # Generate comprehensive report
        report = evaluator.generate_comprehensive_report()
        
        # Validate report structure
        assert isinstance(report, SystemEvaluationReport)
        assert report.total_tests > 0
        assert report.passed_tests >= 0
        assert report.failed_tests >= 0
        assert report.passed_tests + report.failed_tests == report.total_tests
        assert 0 <= report.overall_score <= 1
        assert len(report.agent_scores) > 0
        assert len(report.performance_metrics) > 0
        assert len(report.recommendations) > 0
        
        # Test report export
        report_file = "/tmp/test_evaluation_report.json"
        evaluator.export_report(report, report_file)
        
        # Validate exported report
        assert os.path.exists(report_file)
        with open(report_file, 'r') as f:
            exported_data = json.load(f)
        
        assert "timestamp" in exported_data
        assert "summary" in exported_data
        assert "agent_scores" in exported_data
        assert "recommendations" in exported_data
        
        # Cleanup
        os.unlink(report_file)
    
    def test_job_matching_evaluation(self):
        """Test job matching accuracy evaluation"""
        
        metric = JobMatchingAccuracyMetric(threshold=0.75)
        
        for scenario_name, scenario_data in JOB_MATCHING_SCENARIOS.items():
            test_case = LLMTestCase(
                input=f"Match resume to job: {scenario_name}",
                actual_output={
                    "comparison_results": {
                        "matches": [
                            {
                                "fit_score": scenario_data["expected_match_score"] * 100,
                                "matching_skills": scenario_data["matching_skills"],
                                "missing_skills": scenario_data["missing_skills"],
                                "explanation": scenario_data["explanation"]
                            }
                        ],
                        "average_score": scenario_data["expected_match_score"] * 100
                    }
                },
                expected_output="Job matching analysis"
            )
            
            score = metric.measure(test_case)
            
            # High match scenarios should score well
            if scenario_name == "high_match":
                assert score >= 0.8, f"High match scenario should score well: {score}"
            elif scenario_name == "low_match":
                assert score <= 0.6, f"Low match scenario should score poorly: {score}"
    
    def test_evaluation_error_handling(self, evaluator):
        """Test evaluation system error handling"""
        
        # Test with malformed data
        malformed_test_cases = [
            LLMTestCase(
                input="Test malformed data",
                actual_output=None,  # Invalid output
                expected_output="Should handle gracefully"
            ),
            LLMTestCase(
                input="Test empty data",
                actual_output={},  # Empty output
                expected_output="Should handle gracefully"
            )
        ]
        
        # Should not crash with malformed data
        try:
            results = evaluator.evaluate_agent("resume_analyst", malformed_test_cases)
            assert len(results) == len(malformed_test_cases)
            # Malformed data should result in low scores
            assert all(r.overall_score <= 0.5 for r in results)
        except Exception as e:
            pytest.fail(f"Evaluation should handle malformed data gracefully: {e}")
    
    @pytest.mark.slow
    def test_large_scale_evaluation(self, evaluator):
        """Test evaluation with large number of test cases"""
        
        # Generate many test cases
        large_test_set = []
        for i in range(50):  # 50 test cases
            test_case = LLMTestCase(
                input=f"Large scale test {i}",
                actual_output={
                    "success": i % 5 != 0,  # 80% success rate
                    "processing_time": 2.0 + (i % 10),  # Varying times
                    "test_id": i
                },
                expected_output=f"Test result {i}"
            )
            large_test_set.append(test_case)
        
        # Should handle large evaluation sets
        start_time = datetime.now()
        results = evaluator.evaluate_agent("system_integration", large_test_set)
        end_time = datetime.now()
        
        evaluation_time = (end_time - start_time).total_seconds()
        
        # Validate results
        assert len(results) == 50
        assert evaluation_time < 30.0, f"Large scale evaluation too slow: {evaluation_time}s"
        
        # Generate report for large scale test
        report = evaluator.generate_comprehensive_report()
        assert report.total_tests >= 50