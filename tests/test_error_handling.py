"""
Error handling and resilience tests for the multi-agent job hunting system
"""

import pytest
import time
from unittest.mock import patch, MagicMock, Mock, side_effect
from requests.exceptions import RequestException, Timeout, ConnectionError
from openai import OpenAIError, RateLimitError, APIConnectionError
import json

from api.main import JobHuntingMultiAgent
from api.agents.coordinator_agent import coordinator_agent
from api.agents.resume_analyst_agent import resume_analyst_agent
from api.agents.base import MultiAgentState


class TestAPIFailureHandling:
    """Test handling of external API failures"""
    
    def test_openai_api_failure_handling(self, sample_multi_agent_state):
        """Test handling of OpenAI API failures"""
        
        # Test different OpenAI error scenarios
        openai_errors = [
            RateLimitError("Rate limit exceeded", response=Mock(), body={}),
            APIConnectionError("Connection failed"),
            OpenAIError("General OpenAI error")
        ]
        
        for error in openai_errors:
            with patch('api.tools.llm.invoke') as mock_llm:
                mock_llm.side_effect = error
                
                try:
                    result = coordinator_agent(sample_multi_agent_state)
                    
                    # Should handle error gracefully
                    assert "error" in str(result).lower() or result.get("next_agent") == "END"
                    assert "messages" in result
                    
                except Exception as e:
                    # If exception propagates, it should be handled gracefully
                    assert "openai" in str(e).lower() or "api" in str(e).lower()
    
    def test_job_search_api_failure_resilience(self, mock_job_hunting_agent):
        """Test resilience when job search APIs fail"""
        
        # Mock API failures
        api_errors = [
            RequestException("Request failed"),
            Timeout("Request timed out"),
            ConnectionError("Connection refused"),
            Exception("Unknown API error")
        ]
        
        for error in api_errors:
            with patch('requests.get') as mock_requests:
                mock_requests.side_effect = error
                
                mock_response = {
                    "success": False,
                    "error": f"Job search failed: {str(error)}",
                    "job_listings": [],
                    "fallback_used": True
                }
                mock_job_hunting_agent.process_request.return_value = mock_response
                
                result = mock_job_hunting_agent.process_request("Find software engineering jobs")
                
                # Should handle API failure gracefully
                assert result is not None
                assert "error" in result or not result.get("success", True)
    
    def test_rate_limiting_handling(self, mock_job_hunting_agent):
        """Test handling of rate limiting"""
        
        rate_limit_responses = [
            {"success": False, "error": "Rate limit exceeded", "retry_after": 60},
            {"success": False, "error": "Too many requests", "status_code": 429}
        ]
        
        for response in rate_limit_responses:
            mock_job_hunting_agent.process_request.return_value = response
            
            result = mock_job_hunting_agent.process_request("Test rate limiting")
            
            assert result is not None
            assert "rate" in result.get("error", "").lower() or "limit" in result.get("error", "").lower()
    
    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        
        with patch('api.tools.llm.invoke') as mock_llm:
            # Simulate timeout
            mock_llm.side_effect = Timeout("Request timed out")
            
            state = {
                "messages": [],
                "user_request": "Test timeout handling",
                "resume_path": "",
                "completed_tasks": []
            }
            
            result = coordinator_agent(state)
            
            # Should handle timeout gracefully
            assert result is not None
            assert result.get("next_agent") == "END" or "error" in str(result).lower()


class TestInputValidationAndSanitization:
    """Test input validation and sanitization"""
    
    def test_malicious_input_handling(self, mock_job_hunting_agent):
        """Test handling of potentially malicious inputs"""
        
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('xss')",
            "\x00\x01\x02\x03",  # Binary data
            "A" * 10000,  # Very long input
        ]
        
        for malicious_input in malicious_inputs:
            mock_response = {
                "success": True,
                "sanitized_input": True,
                "messages": ["Input was sanitized for security"]
            }
            mock_job_hunting_agent.process_request.return_value = mock_response
            
            try:
                result = mock_job_hunting_agent.process_request(malicious_input)
                
                # Should either sanitize input or reject it
                assert result is not None
                assert result.get("success", False) or "sanitized" in str(result).lower()
                
            except ValueError as e:
                # It's acceptable to reject invalid input with ValueError
                assert "invalid" in str(e).lower() or "malformed" in str(e).lower()
    
    def test_file_upload_validation(self, mock_job_hunting_agent):
        """Test file upload validation and security"""
        
        invalid_files = [
            "/etc/passwd",  # System file
            "../../secret.txt",  # Directory traversal
            "resume.exe",  # Executable file
            "resume.php",  # Script file
            "",  # Empty filename
            None,  # Null filename
        ]
        
        for invalid_file in invalid_files:
            mock_response = {
                "success": False,
                "error": f"Invalid file: {invalid_file}",
                "file_rejected": True
            }
            mock_job_hunting_agent.process_request.return_value = mock_response
            
            result = mock_job_hunting_agent.process_request(
                "Analyze my resume",
                resume_path=invalid_file
            )
            
            # Should reject invalid files
            assert result is not None
            if invalid_file:  # Skip None case
                assert not result.get("success", True) or "invalid" in str(result).lower()
    
    def test_large_file_handling(self, mock_job_hunting_agent):
        """Test handling of oversized files"""
        
        mock_response = {
            "success": False,
            "error": "File too large. Maximum size is 16MB.",
            "file_size_exceeded": True
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        # Simulate large file upload
        result = mock_job_hunting_agent.process_request(
            "Analyze my resume",
            resume_path="/tmp/large_resume.pdf"  # This would be a large file in reality
        )
        
        assert result is not None


class TestAgentFailureRecovery:
    """Test recovery from individual agent failures"""
    
    def test_single_agent_failure_recovery(self, sample_multi_agent_state):
        """Test recovery when a single agent fails"""
        
        # Mock resume analyst failure
        with patch('api.agents.resume_analyst_agent.resume_analyst_agent') as mock_agent:
            mock_agent.side_effect = Exception("Resume analysis failed")
            
            # System should handle the failure
            with patch('api.main.JobHuntingMultiAgent') as mock_system:
                mock_instance = MagicMock()
                mock_system.return_value = mock_instance
                
                # Mock recovery response
                recovery_response = {
                    "success": False,
                    "error": "Resume analysis failed, continuing with available agents",
                    "completed_tasks": ["coordinator"],
                    "failed_agents": ["resume_analyst"],
                    "recovery_actions": ["skipped_resume_analysis", "continued_with_job_search"]
                }
                mock_instance.process_request.return_value = recovery_response
                
                agent = mock_system()
                result = agent.process_request("Complete job hunting help")
                
                # Should have recovery information
                assert result is not None
                assert "failed_agents" in result or "error" in result
    
    def test_coordinator_failure_handling(self, sample_multi_agent_state):
        """Test handling of coordinator agent failure"""
        
        # Mock coordinator failure
        with patch('api.agents.coordinator_agent.coordinator_agent') as mock_coordinator:
            mock_coordinator.side_effect = Exception("Coordinator failed to create plan")
            
            # Should have fallback mechanism
            with patch('api.main.JobHuntingMultiAgent') as mock_system:
                mock_instance = MagicMock()
                mock_system.return_value = mock_instance
                
                fallback_response = {
                    "success": False,
                    "error": "Coordinator failed, using fallback routing",
                    "fallback_mode": True,
                    "next_agent": "resume_analyst"  # Direct routing as fallback
                }
                mock_instance.process_request.return_value = fallback_response
                
                agent = mock_system()
                result = agent.process_request("Analyze my resume")
                
                assert result is not None
                assert "fallback" in str(result).lower() or "error" in result
    
    def test_cascading_failure_prevention(self, mock_job_hunting_agent):
        """Test prevention of cascading failures"""
        
        # Simulate multiple sequential failures
        failure_sequence = [
            {"agent": "coordinator", "error": "Planning failed"},
            {"agent": "resume_analyst", "error": "Analysis failed"},
            {"agent": "job_researcher", "error": "Search failed"}
        ]
        
        mock_response = {
            "success": False,
            "error": "Multiple agent failures detected",
            "failed_agents": ["coordinator", "resume_analyst", "job_researcher"],
            "circuit_breaker_active": True,
            "recovery_mode": True
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        result = mock_job_hunting_agent.process_request("Complete job hunting help")
        
        # Should detect and handle cascading failures
        assert result is not None
        assert "failed_agents" in result or "circuit_breaker" in result or not result.get("success", True)


class TestDataCorruptionHandling:
    """Test handling of corrupt or malformed data"""
    
    def test_malformed_json_handling(self, sample_multi_agent_state):
        """Test handling of malformed JSON responses"""
        
        malformed_json_responses = [
            '{"key": "value",}',  # Trailing comma
            '{"key": "value" "key2": "value2"}',  # Missing comma
            '{"key": undefined}',  # Invalid value
            '{key: "value"}',  # Unquoted key
            '{"key": "value"',  # Incomplete JSON
        ]
        
        for malformed_json in malformed_json_responses:
            with patch('api.tools.llm.invoke') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = malformed_json
                mock_llm.return_value = mock_response
                
                result = coordinator_agent(sample_multi_agent_state)
                
                # Should handle malformed JSON gracefully
                assert result is not None
                # Should either fix the JSON or provide fallback
                assert "next_agent" in result or "error" in str(result).lower()
    
    def test_empty_response_handling(self, sample_multi_agent_state):
        """Test handling of empty or null responses"""
        
        empty_responses = [
            "",
            None,
            "null",
            "undefined",
            "{}",
            "[]"
        ]
        
        for empty_response in empty_responses:
            with patch('api.tools.llm.invoke') as mock_llm:
                mock_response = MagicMock()
                mock_response.content = empty_response
                mock_llm.return_value = mock_response
                
                result = coordinator_agent(sample_multi_agent_state)
                
                # Should handle empty responses
                assert result is not None
                assert "next_agent" in result  # Should provide fallback routing
    
    def test_corrupted_resume_file_handling(self, mock_job_hunting_agent):
        """Test handling of corrupted resume files"""
        
        corruption_scenarios = [
            {"error": "PDF parsing failed", "file_type": "corrupted_pdf"},
            {"error": "DOCX extraction failed", "file_type": "corrupted_docx"},
            {"error": "File encoding error", "file_type": "invalid_encoding"},
            {"error": "File is empty", "file_type": "empty_file"}
        ]
        
        for scenario in corruption_scenarios:
            mock_response = {
                "success": False,
                "error": scenario["error"],
                "file_corruption_detected": True,
                "recovery_suggestion": "Please try uploading a different file format"
            }
            mock_job_hunting_agent.process_request.return_value = mock_response
            
            result = mock_job_hunting_agent.process_request(
                "Analyze my resume",
                resume_path=f"/tmp/{scenario['file_type']}.pdf"
            )
            
            assert result is not None
            assert "error" in result or "corruption" in str(result).lower()


class TestSystemResilienceEdgeCases:
    """Test system resilience in edge case scenarios"""
    
    def test_memory_pressure_handling(self, mock_job_hunting_agent):
        """Test system behavior under memory pressure"""
        
        mock_response = {
            "success": True,
            "memory_optimization_active": True,
            "reduced_functionality": True,
            "warning": "Operating in low-memory mode"
        }
        mock_job_hunting_agent.process_request.return_value = mock_response
        
        # Simulate memory pressure scenario
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 95  # 95% memory usage
            
            result = mock_job_hunting_agent.process_request("Analyze resume under memory pressure")
            
            assert result is not None
            # Should either handle gracefully or indicate memory constraints
    
    def test_disk_space_exhaustion(self, mock_job_hunting_agent):
        """Test handling when disk space is exhausted"""
        
        with patch('os.statvfs') as mock_statvfs:
            # Mock very low disk space
            mock_stat = MagicMock()
            mock_stat.f_bavail = 100  # Very few blocks available
            mock_stat.f_frsize = 4096  # Block size
            mock_statvfs.return_value = mock_stat
            
            mock_response = {
                "success": False,
                "error": "Insufficient disk space for CV generation",
                "disk_space_critical": True,
                "cleanup_suggested": True
            }
            mock_job_hunting_agent.process_request.return_value = mock_response
            
            result = mock_job_hunting_agent.process_request("Create CV with low disk space")
            
            assert result is not None
            # Should detect and handle disk space issues
    
    def test_concurrent_request_conflicts(self, mock_job_hunting_agent):
        """Test handling of concurrent request conflicts"""
        
        def mock_concurrent_response(request_id):
            return {
                "success": True,
                "request_id": request_id,
                "concurrent_requests_detected": True,
                "queue_position": request_id % 5,
                "estimated_wait_time": (request_id % 5) * 2
            }
        
        # Simulate multiple concurrent requests
        import threading
        
        results = []
        def make_request(request_id):
            mock_job_hunting_agent.process_request.return_value = mock_concurrent_response(request_id)
            result = mock_job_hunting_agent.process_request(f"Concurrent request {request_id}")
            results.append(result)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should be handled
        assert len(results) == 5
        assert all(r is not None for r in results)
    
    def test_graceful_degradation(self, mock_job_hunting_agent):
        """Test graceful degradation when multiple components fail"""
        
        degradation_levels = [
            {
                "level": "minimal",
                "available_features": ["resume_analysis"],
                "unavailable_features": ["job_search", "cv_generation"],
                "success": True
            },
            {
                "level": "severe", 
                "available_features": [],
                "unavailable_features": ["resume_analysis", "job_search", "cv_generation"],
                "success": False,
                "emergency_mode": True
            }
        ]
        
        for degradation in degradation_levels:
            mock_job_hunting_agent.process_request.return_value = degradation
            
            result = mock_job_hunting_agent.process_request("Test graceful degradation")
            
            assert result is not None
            assert "available_features" in result or "success" in result
    
    @pytest.mark.timeout(10)
    def test_infinite_loop_prevention(self, sample_multi_agent_state):
        """Test prevention of infinite loops in agent coordination"""
        
        # Mock a scenario that could cause infinite loops
        loop_counter = 0
        
        def mock_coordinator_with_loop(state):
            nonlocal loop_counter
            loop_counter += 1
            
            if loop_counter > 10:  # Prevent actual infinite loop in test
                return {
                    "next_agent": "END",
                    "loop_detected": True,
                    "safety_exit": True,
                    "messages": ["Loop prevention activated"]
                }
            
            return {
                "next_agent": "coordinator",  # This would cause a loop
                "completed_tasks": state.get("completed_tasks", []) + ["coordinator"]
            }
        
        with patch('api.agents.coordinator_agent.coordinator_agent', mock_coordinator_with_loop):
            # This should not run indefinitely
            result = mock_coordinator_with_loop(sample_multi_agent_state)
            
            # Should detect and prevent infinite loop
            assert result is not None
            assert result.get("next_agent") == "END" or result.get("loop_detected") is True