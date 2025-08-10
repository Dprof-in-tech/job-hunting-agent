"""
Performance and efficiency tests for the multi-agent job hunting system
"""

import pytest
import time
import asyncio
import psutil
import threading
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from api.main import JobHuntingMultiAgent
from tests.evaluation.evaluator import MultiAgentEvaluator
from tests.evaluation.custom_metrics import PerformanceEfficiencyMetric
from deepeval.test_case import LLMTestCase


class TestPerformanceMetrics:
    """Test performance and efficiency metrics"""
    
    @pytest.fixture
    def performance_benchmarks(self):
        return {
            "max_response_time": 15.0,
            "max_memory_usage": 500,  # MB
            "target_throughput": 10,  # requests per minute
            "max_cpu_usage": 0.8,     # 80%
        }
    
    def test_single_request_performance(self, mock_job_hunting_agent, performance_benchmarks):
        """Test performance of single request"""
        
        # Setup mock response
        mock_response = {
            "success": True,
            "processing_time": 3.2,
            "completed_tasks": ["coordinator", "resume_analyst"],
            "performance_summary": {"efficiency_rating": "excellent"}
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        # Measure performance
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        result = mock_job_hunting_agent.process_request(
            "Analyze my resume and provide feedback",
            resume_path="/tmp/test_resume.txt"
        )
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Performance assertions
        response_time = end_time - start_time
        memory_usage = end_memory - start_memory
        
        assert response_time < performance_benchmarks["max_response_time"], \
            f"Response time {response_time:.2f}s exceeds limit {performance_benchmarks['max_response_time']}s"
        
        assert result["success"] is True, "Request should succeed"
        assert "processing_time" in result, "Should report processing time"
    
    @pytest.mark.benchmark(group="agent_performance")
    def test_resume_analysis_benchmark(self, benchmark, mock_job_hunting_agent):
        """Benchmark resume analysis performance"""
        
        mock_response = {
            "success": True,
            "processing_time": 2.1,
            "resume_analysis": {
                "overall_score": 78,
                "strengths": ["Strong technical skills", "Clear experience"],
                "weaknesses": ["Missing keywords", "Formatting issues"]
            }
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        def analyze_resume():
            return mock_job_hunting_agent.process_request(
                "Analyze my resume for software engineering positions",
                resume_path="/tmp/test_resume.txt"
            )
        
        result = benchmark(analyze_resume)
        
        assert result["success"] is True
        assert "resume_analysis" in result
    
    @pytest.mark.benchmark(group="agent_performance")
    def test_job_search_benchmark(self, benchmark, mock_job_hunting_agent):
        """Benchmark job search performance"""
        
        mock_response = {
            "success": True,
            "processing_time": 5.7,
            "job_listings": [
                {"title": "Software Engineer", "company": "TechCorp"},
                {"title": "Python Developer", "company": "StartupInc"}
            ]
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        def search_jobs():
            return mock_job_hunting_agent.process_request(
                "Find software engineering jobs that match my background"
            )
        
        result = benchmark(search_jobs)
        
        assert result["success"] is True
        assert len(result["job_listings"]) > 0
    
    def test_concurrent_request_performance(self, mock_job_hunting_agent):
        """Test performance under concurrent load"""
        
        mock_response = {
            "success": True,
            "processing_time": 4.5,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher"]
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        num_concurrent = 5
        requests = [
            "Analyze my resume",
            "Find relevant jobs",
            "Create optimized CV", 
            "Research job market",
            "Complete job hunting help"
        ]
        
        def make_request(prompt):
            start_time = time.time()
            result = mock_job_hunting_agent.process_request(prompt)
            end_time = time.time()
            return {
                "result": result,
                "response_time": end_time - start_time,
                "prompt": prompt
            }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, req) for req in requests]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Performance assertions
        assert len(results) == num_concurrent
        assert all(r["result"]["success"] for r in results)
        
        response_times = [r["response_time"] for r in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Should complete concurrent requests reasonably fast
        assert avg_response_time < 10.0, f"Average response time {avg_response_time:.2f}s too high"
        assert max_response_time < 15.0, f"Max response time {max_response_time:.2f}s too high"
        assert total_time < 20.0, f"Total concurrent execution time {total_time:.2f}s too high"
    
    def test_memory_usage_under_load(self, mock_job_hunting_agent):
        """Test memory usage under repeated requests"""
        
        mock_response = {
            "success": True,
            "processing_time": 2.8,
            "completed_tasks": ["coordinator", "resume_analyst"]
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_samples = []
        
        # Make multiple requests and monitor memory
        for i in range(10):
            mock_job_hunting_agent.process_request("Test request")
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory - initial_memory)
            time.sleep(0.1)  # Small delay between requests
        
        max_memory_increase = max(memory_samples)
        final_memory_increase = memory_samples[-1]
        
        # Memory should not grow excessively
        assert max_memory_increase < 200, f"Memory usage increased by {max_memory_increase:.1f}MB"
        
        # Should not have significant memory leaks
        assert final_memory_increase < 100, f"Final memory increase {final_memory_increase:.1f}MB suggests leak"
    
    def test_performance_metric_evaluation(self):
        """Test custom performance efficiency metric"""
        
        metric = PerformanceEfficiencyMetric(threshold=0.7, max_time=15.0)
        
        # Test fast, successful response
        test_case_good = LLMTestCase(
            input="Test request",
            actual_output={
                "success": True,
                "processing_time": 5.2,
                "performance_summary": {"efficiency_rating": "excellent"}
            },
            expected_output="Good performance expected"
        )
        
        score_good = metric.measure(test_case_good)
        assert score_good >= 0.7, f"Good performance should score >= 0.7, got {score_good}"
        assert metric.success is True
        
        # Test slow response
        test_case_slow = LLMTestCase(
            input="Test request",
            actual_output={
                "success": True,
                "processing_time": 18.0,  # Exceeds max_time
                "performance_summary": {"efficiency_rating": "fair"}
            },
            expected_output="Slow performance"
        )
        
        score_slow = metric.measure(test_case_slow)
        assert score_slow < 0.7, f"Slow performance should score < 0.7, got {score_slow}"
        
        # Test failed response
        test_case_failed = LLMTestCase(
            input="Test request",
            actual_output={
                "success": False,
                "processing_time": 8.0,
                "error": "Test error"
            },
            expected_output="Failed response"
        )
        
        score_failed = metric.measure(test_case_failed)
        assert score_failed < 0.5, f"Failed response should score poorly, got {score_failed}"


class TestScalabilityAndLoad:
    """Test system scalability and load handling"""
    
    def test_request_queue_performance(self, mock_job_hunting_agent):
        """Test handling of request queue under load"""
        
        request_times = []
        
        def timed_request(request_id):
            start = time.time()
            mock_response = {
                "success": True,
                "processing_time": 3.0,
                "request_id": request_id
            }
            mock_job_hunting_agent.process_request.return_value = mock_response
            
            result = mock_job_hunting_agent.process_request(f"Test request {request_id}")
            end = time.time()
            
            return {
                "request_id": request_id,
                "response_time": end - start,
                "success": result["success"]
            }
        
        # Simulate burst of requests
        num_requests = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(timed_request, i) 
                for i in range(num_requests)
            ]
            results = [future.result() for future in as_completed(futures)]
        
        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        avg_response_time = statistics.mean([r["response_time"] for r in results])
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
        assert avg_response_time < 8.0, f"Average response time {avg_response_time:.2f}s too high under load"
    
    def test_agent_coordination_overhead(self, mock_job_hunting_agent):
        """Test overhead of multi-agent coordination"""
        
        # Single agent mock response
        single_agent_response = {
            "success": True,
            "processing_time": 2.0,
            "completed_tasks": ["resume_analyst"]
        }
        
        # Multi-agent mock response
        multi_agent_response = {
            "success": True,
            "processing_time": 6.5,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher", "cv_creator"]
        }
        
        # Test single agent performance
        mock_job_hunting_agent.process_request.return_value = single_agent_response
        start_single = time.time()
        result_single = mock_job_hunting_agent.process_request("Simple resume analysis")
        time_single = time.time() - start_single
        
        # Test multi-agent performance
        mock_job_hunting_agent.process_request.return_value = multi_agent_response
        start_multi = time.time()
        result_multi = mock_job_hunting_agent.process_request("Complete job hunting assistance")
        time_multi = time.time() - start_multi
        
        # Coordination overhead should be reasonable
        coordination_overhead = time_multi - time_single
        overhead_ratio = coordination_overhead / time_single
        
        # Overhead should not be more than 3x the single agent time
        assert overhead_ratio < 3.0, f"Coordination overhead ratio {overhead_ratio:.2f} too high"
        
        assert result_single["success"] is True
        assert result_multi["success"] is True
        assert len(result_multi["completed_tasks"]) > len(result_single["completed_tasks"])


class TestResourceUsage:
    """Test resource usage patterns"""
    
    def test_cpu_usage_monitoring(self, mock_job_hunting_agent):
        """Monitor CPU usage during operations"""
        
        mock_response = {
            "success": True,
            "processing_time": 4.0,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher"]
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        # Monitor CPU usage
        process = psutil.Process()
        cpu_samples = []
        
        def monitor_cpu():
            for _ in range(10):  # 5 seconds of monitoring
                cpu_samples.append(process.cpu_percent(interval=0.5))
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Execute request
        result = mock_job_hunting_agent.process_request("Test CPU usage")
        
        monitor_thread.join()
        
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # CPU usage should be reasonable
        assert avg_cpu < 50.0, f"Average CPU usage {avg_cpu:.1f}% too high"
        assert max_cpu < 80.0, f"Peak CPU usage {max_cpu:.1f}% too high"
        assert result["success"] is True
    
    @pytest.mark.timeout(30)
    def test_response_time_consistency(self, mock_job_hunting_agent):
        """Test consistency of response times"""
        
        mock_response = {
            "success": True,
            "processing_time": 3.5,
            "completed_tasks": ["coordinator", "resume_analyst"]
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        response_times = []
        
        # Make multiple identical requests
        for i in range(10):
            start_time = time.time()
            result = mock_job_hunting_agent.process_request("Consistent timing test")
            end_time = time.time()
            
            response_times.append(end_time - start_time)
            assert result["success"] is True
        
        # Analyze consistency
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        coefficient_of_variation = std_dev / avg_time
        
        # Response times should be reasonably consistent
        assert coefficient_of_variation < 0.3, \
            f"Response time variability {coefficient_of_variation:.3f} too high (CV > 0.3)"
        
        assert avg_time < 10.0, f"Average response time {avg_time:.2f}s too high"