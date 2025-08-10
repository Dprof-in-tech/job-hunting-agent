"""
Integration tests for complete multi-agent workflows
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from deepeval.test_case import LLMTestCase

from api.main import JobHuntingMultiAgent
from tests.evaluation.evaluator import MultiAgentEvaluator
from tests.evaluation.custom_metrics import (
    ResumeAnalysisAccuracyMetric,
    JobSearchRelevanceMetric,
    CVGenerationQualityMetric,
    SystemCoherenceMetric
)


class TestCompleteWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.fixture
    def integration_evaluator(self):
        """Evaluator for integration testing"""
        return MultiAgentEvaluator()
    
    def test_complete_job_hunting_workflow(self, mock_job_hunting_agent, integration_evaluator):
        """Test complete job hunting workflow with all agents"""
        
        # Mock comprehensive response
        complete_response = {
            "success": True,
            "session_id": "integration_test_001",
            "user_id": "test_user",
            "messages": [
                {"content": "📋 **Coordination Plan Created**\n\nStrategy: Comprehensive job hunting assistance", "timestamp": "2024-01-15T10:00:00Z"},
                {"content": "📊 **Resume Analysis Complete**\n\nOverall Score: 78/100", "timestamp": "2024-01-15T10:01:30Z"},
                {"content": "🔍 **Job Search Complete**\n\nFound 15 relevant opportunities", "timestamp": "2024-01-15T10:03:45Z"},
                {"content": "📝 **CV Creation Complete**\n\nOptimized CV generated successfully", "timestamp": "2024-01-15T10:06:15Z"}
            ],
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher", "cv_creator"],
            "resume_analysis": {
                "overall_score": 78,
                "strengths": [
                    "Strong technical skills in Python and JavaScript",
                    "Clear progression in software engineering roles",
                    "Good educational background"
                ],
                "weaknesses": [
                    "Missing industry-specific keywords",
                    "Could better quantify achievements",
                    "Professional summary needs strengthening"
                ],
                "improvements": [
                    "Add more technical keywords relevant to target roles",
                    "Include specific metrics and numbers for achievements",
                    "Strengthen the professional summary section",
                    "Improve ATS compatibility with better formatting"
                ],
                "ats_compatibility": 72,
                "keyword_analysis": {
                    "missing_keywords": ["React", "AWS", "Docker", "Kubernetes"],
                    "present_keywords": ["Python", "JavaScript", "Software Engineering"]
                }
            },
            "job_market_data": {
                "total_jobs_found": 15,
                "market_insights": {
                    "avg_salary_range": "$85k - $130k",
                    "top_companies": ["TechCorp", "InnovateCo", "DevSolutions"],
                    "trending_skills": ["React", "Python", "AWS", "Docker"]
                },
                "location_distribution": {
                    "Remote": 8,
                    "San Francisco, CA": 4,
                    "New York, NY": 2,
                    "Austin, TX": 1
                }
            },
            "job_listings": [
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp Inc",
                    "location": "San Francisco, CA",
                    "description": "We are looking for a Senior Software Engineer with 5+ years of experience in Python, React, and AWS. The role involves building scalable web applications.",
                    "salary": "$120,000 - $160,000",
                    "apply_url": "https://techcorp.com/jobs/senior-software-engineer",
                    "source": "company_website",
                    "date_found": "2024-01-15"
                },
                {
                    "title": "Full Stack Developer",
                    "company": "StartupCo",
                    "location": "Remote",
                    "description": "Join our remote team as a Full Stack Developer. Work with React, Node.js, and modern cloud technologies.",
                    "salary": "$90,000 - $120,000",
                    "apply_url": "https://startupco.com/careers/fullstack",
                    "source": "job_board",
                    "date_found": "2024-01-15"
                }
            ],
            "cv_path": "/tmp/optimized_cv_test_user.pdf",
            "cv_content": "Professional CV with optimized sections including contact info, professional summary, experience, skills, and education",
            "processing_time": 12.5,
            "performance_summary": {
                "agents_used": 4,
                "total_processing_time": 12.5,
                "avg_time_per_agent": 3.1,
                "efficiency_rating": "good"
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = complete_response
        
        # Execute complete workflow
        result = mock_job_hunting_agent.process_request(
            "I need comprehensive job hunting assistance. Please analyze my resume, research job opportunities, and create an optimized CV.",
            resume_path="/tmp/test_resume.pdf"
        )
        
        # Validate workflow completion
        assert result["success"] is True
        assert len(result["completed_tasks"]) == 4
        assert "coordinator" in result["completed_tasks"]
        assert "resume_analyst" in result["completed_tasks"]
        assert "job_researcher" in result["completed_tasks"]
        assert "cv_creator" in result["completed_tasks"]
        
        # Validate data flow between agents
        assert "resume_analysis" in result
        assert "job_listings" in result
        assert "cv_path" in result
        assert result["resume_analysis"]["overall_score"] > 0
        assert len(result["job_listings"]) > 0
        assert result["cv_path"] != ""
        
        # Evaluate with custom metrics
        test_case = LLMTestCase(
            input="Complete job hunting assistance request",
            actual_output=result,
            expected_output="Comprehensive job hunting results"
        )
        
        # Test system coherence
        coherence_metric = SystemCoherenceMetric(threshold=0.8)
        coherence_score = coherence_metric.measure(test_case)
        assert coherence_score >= 0.8, f"System coherence score {coherence_score} below threshold"
        
    def test_resume_analysis_only_workflow(self, mock_job_hunting_agent):
        """Test workflow with resume analysis only"""
        
        analysis_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst"],
            "resume_analysis": {
                "overall_score": 82,
                "strengths": ["Strong technical background", "Clear experience progression"],
                "weaknesses": ["Missing keywords", "Needs better formatting"],
                "improvements": ["Add relevant keywords", "Improve ATS compatibility"],
                "ats_compatibility": 75
            },
            "processing_time": 4.2,
            "performance_summary": {"agents_used": 2, "efficiency_rating": "excellent"}
        }
        
        mock_job_hunting_agent.process_request.return_value = analysis_response
        
        result = mock_job_hunting_agent.process_request(
            "Please analyze my resume and provide detailed feedback",
            resume_path="/tmp/test_resume.pdf"
        )
        
        # Validate resume analysis workflow
        assert result["success"] is True
        assert "resume_analysis" in result
        assert result["resume_analysis"]["overall_score"] > 0
        assert len(result["resume_analysis"]["strengths"]) > 0
        assert len(result["resume_analysis"]["weaknesses"]) > 0
        
        # Test resume analysis accuracy
        test_case = LLMTestCase(
            input="Resume analysis request",
            actual_output=result["resume_analysis"],
            expected_output="Detailed resume analysis"
        )
        
        accuracy_metric = ResumeAnalysisAccuracyMetric(threshold=0.8)
        accuracy_score = accuracy_metric.measure(test_case)
        assert accuracy_score >= 0.7, f"Resume analysis accuracy {accuracy_score} too low"
    
    def test_job_search_only_workflow(self, mock_job_hunting_agent):
        """Test workflow with job search only"""
        
        search_response = {
            "success": True,
            "completed_tasks": ["coordinator", "job_researcher"],
            "job_market_data": {
                "total_jobs_found": 12,
                "search_query": "software engineer python",
                "market_insights": {"avg_salary": "$105k", "demand": "high"}
            },
            "job_listings": [
                {
                    "title": "Python Developer",
                    "company": "DataCorp",
                    "location": "Remote",
                    "description": "Python developer role with Django and FastAPI experience required",
                    "salary": "$95,000 - $115,000"
                },
                {
                    "title": "Backend Engineer",
                    "company": "CloudTech",
                    "location": "Seattle, WA", 
                    "description": "Backend engineering role focusing on microservices and API development",
                    "salary": "$110,000 - $140,000"
                }
            ],
            "processing_time": 6.8
        }
        
        mock_job_hunting_agent.process_request.return_value = search_response
        
        result = mock_job_hunting_agent.process_request(
            "Find Python developer jobs that match my background"
        )
        
        # Validate job search workflow
        assert result["success"] is True
        assert "job_listings" in result
        assert len(result["job_listings"]) > 0
        assert "job_market_data" in result
        
        # Test job search relevance
        test_case = LLMTestCase(
            input="Job search request for Python developer",
            actual_output=result,
            expected_output="Relevant Python developer jobs"
        )
        
        relevance_metric = JobSearchRelevanceMetric(threshold=0.75, min_jobs=2)
        relevance_score = relevance_metric.measure(test_case)
        assert relevance_score >= 0.7, f"Job search relevance {relevance_score} too low"
    
    def test_cv_generation_workflow(self, mock_job_hunting_agent):
        """Test workflow with CV generation"""
        
        cv_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "cv_creator"],
            "resume_analysis": {
                "overall_score": 76,
                "strengths": ["Technical skills", "Experience"],
                "weaknesses": ["Formatting", "Keywords"]
            },
            "cv_path": "/tmp/optimized_cv_user123.pdf",
            "cv_content": "Professionally formatted CV with optimized sections, keywords, and ATS-friendly structure",
            "cv_improvements": [
                "Added relevant keywords for ATS optimization",
                "Improved professional summary",
                "Enhanced formatting for readability",
                "Quantified achievements with metrics"
            ],
            "processing_time": 8.4
        }
        
        mock_job_hunting_agent.process_request.return_value = cv_response
        
        result = mock_job_hunting_agent.process_request(
            "Create an optimized CV based on my resume",
            resume_path="/tmp/test_resume.pdf"
        )
        
        # Validate CV generation workflow
        assert result["success"] is True
        assert "cv_path" in result
        assert result["cv_path"] != ""
        assert "cv_content" in result
        
        # Test CV generation quality
        test_case = LLMTestCase(
            input="CV generation request",
            actual_output=result,
            expected_output="Optimized CV file"
        )
        
        quality_metric = CVGenerationQualityMetric(threshold=0.8)
        quality_score = quality_metric.measure(test_case)
        assert quality_score >= 0.7, f"CV generation quality {quality_score} too low"


class TestWorkflowEdgeCases:
    """Test edge cases in workflow execution"""
    
    def test_empty_resume_workflow(self, mock_job_hunting_agent):
        """Test workflow with empty or minimal resume"""
        
        minimal_response = {
            "success": False,
            "error": "Resume file is empty or unreadable",
            "completed_tasks": ["coordinator"],
            "recovery_suggestions": [
                "Please upload a valid resume file",
                "Supported formats: PDF, DOCX, TXT",
                "Ensure file is not corrupted"
            ],
            "fallback_options": {
                "job_search_available": True,
                "manual_resume_entry": True
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = minimal_response
        
        result = mock_job_hunting_agent.process_request(
            "Analyze my resume",
            resume_path="/tmp/empty_resume.txt"
        )
        
        # Should handle empty resume gracefully
        assert result is not None
        assert "error" in result or not result.get("success", True)
        assert "recovery_suggestions" in result or "fallback_options" in result
    
    def test_no_jobs_found_workflow(self, mock_job_hunting_agent):
        """Test workflow when no jobs are found"""
        
        no_jobs_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher"],
            "resume_analysis": {"overall_score": 85},
            "job_market_data": {
                "total_jobs_found": 0,
                "search_attempts": 3,
                "searched_sources": ["indeed", "linkedin", "company_websites"]
            },
            "job_listings": [],
            "recommendations": [
                "Try broadening your search criteria",
                "Consider remote opportunities",
                "Look into related job titles",
                "Consider contract or freelance work"
            ],
            "alternative_strategies": {
                "networking_suggestions": True,
                "skill_development_areas": ["React", "AWS", "Docker"],
                "industry_insights": "High demand for full-stack developers"
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = no_jobs_response
        
        result = mock_job_hunting_agent.process_request(
            "Find jobs for a very specific niche role"
        )
        
        # Should provide helpful guidance even when no jobs found
        assert result["success"] is True
        assert result["job_market_data"]["total_jobs_found"] == 0
        assert len(result["job_listings"]) == 0
        assert "recommendations" in result or "alternative_strategies" in result
    
    def test_partial_workflow_completion(self, mock_job_hunting_agent):
        """Test workflow with partial completion due to agent failures"""
        
        partial_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst"],
            "failed_tasks": ["job_researcher", "cv_creator"],
            "partial_completion": True,
            "resume_analysis": {"overall_score": 79},
            "job_listings": [],
            "cv_path": "",
            "failure_reasons": {
                "job_researcher": "API rate limit exceeded",
                "cv_creator": "PDF generation service unavailable"
            },
            "completed_features": ["resume_analysis"],
            "failed_features": ["job_search", "cv_generation"],
            "retry_suggestions": [
                "Job search can be retried in 1 hour",
                "CV generation available via alternative method"
            ]
        }
        
        mock_job_hunting_agent.process_request.return_value = partial_response
        
        result = mock_job_hunting_agent.process_request(
            "Complete job hunting assistance"
        )
        
        # Should handle partial completion gracefully
        assert result["success"] is True  # Partial success is still success
        assert "partial_completion" in result
        assert "failed_tasks" in result
        assert len(result["completed_tasks"]) > 0
        assert "failure_reasons" in result
    
    def test_user_interruption_handling(self, mock_job_hunting_agent):
        """Test handling of user interruption during workflow"""
        
        interrupted_response = {
            "success": False,
            "interrupted": True,
            "completed_tasks": ["coordinator", "resume_analyst"],
            "interrupted_at": "job_researcher",
            "progress_saved": True,
            "resume_state": {
                "session_id": "interrupted_session_123",
                "resumable": True,
                "completed_data": {
                    "resume_analysis": {"overall_score": 81}
                }
            },
            "message": "Workflow interrupted by user. Progress has been saved."
        }
        
        mock_job_hunting_agent.process_request.return_value = interrupted_response
        
        result = mock_job_hunting_agent.process_request("Simulate user interruption")
        
        # Should handle interruption gracefully
        assert result is not None
        assert "interrupted" in result
        assert "progress_saved" in result or "resume_state" in result


class TestDataFlowValidation:
    """Test data flow between agents"""
    
    def test_coordinator_to_agents_data_flow(self, mock_job_hunting_agent):
        """Test data flow from coordinator to other agents"""
        
        coordinated_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher"],
            "coordinator_plan": {
                "primary_goal": "Complete job hunting assistance",
                "agents_needed": ["resume_analyst", "job_researcher", "cv_creator"],
                "execution_order": ["resume_analyst", "job_researcher", "cv_creator"],
                "reasoning": "User needs comprehensive help"
            },
            "data_flow": {
                "coordinator_to_resume_analyst": {
                    "user_request": "analyze resume",
                    "resume_path": "/tmp/test_resume.pdf"
                },
                "resume_analyst_to_job_researcher": {
                    "target_roles": ["Software Engineer", "Full Stack Developer"],
                    "key_skills": ["Python", "JavaScript", "React"]
                },
                "job_researcher_to_cv_creator": {
                    "trending_keywords": ["React", "AWS", "Docker"],
                    "market_insights": {"avg_salary": "$110k"}
                }
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = coordinated_response
        
        result = mock_job_hunting_agent.process_request("Complete job hunting help")
        
        # Validate coordinator planning
        assert result["success"] is True
        assert "coordinator_plan" in result
        assert "data_flow" in result
        
        plan = result["coordinator_plan"]
        assert "primary_goal" in plan
        assert "agents_needed" in plan
        assert "execution_order" in plan
    
    def test_resume_analysis_to_job_search_integration(self, mock_job_hunting_agent):
        """Test integration between resume analysis and job search"""
        
        integrated_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher"],
            "resume_analysis": {
                "overall_score": 83,
                "target_roles": ["Senior Software Engineer", "Lead Developer"],
                "key_skills": ["Python", "React", "AWS", "Docker"],
                "experience_level": "Senior (5+ years)"
            },
            "job_search_parameters": {
                "roles": ["Senior Software Engineer", "Lead Developer"],
                "keywords": ["Python", "React", "AWS", "Docker"],
                "experience_level": "Senior",
                "location_preferences": ["Remote", "San Francisco", "Seattle"]
            },
            "job_listings": [
                {
                    "title": "Senior Software Engineer",
                    "match_score": 92,
                    "matching_skills": ["Python", "React", "AWS"],
                    "description": "Senior role requiring Python, React, and AWS experience"
                }
            ],
            "integration_quality": {
                "skill_match_accuracy": 0.95,
                "role_alignment": 0.88,
                "search_relevance": 0.92
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = integrated_response
        
        result = mock_job_hunting_agent.process_request("Find jobs based on my resume analysis")
        
        # Validate integration between agents
        assert result["success"] is True
        assert "resume_analysis" in result
        assert "job_search_parameters" in result
        assert "integration_quality" in result
        
        # Check that job search used resume analysis data
        resume_skills = result["resume_analysis"]["key_skills"]
        search_keywords = result["job_search_parameters"]["keywords"]
        
        # Keywords should be derived from resume skills
        skill_overlap = set(resume_skills).intersection(set(search_keywords))
        assert len(skill_overlap) > 0, "Job search should use skills from resume analysis"
    
    def test_end_to_end_data_consistency(self, mock_job_hunting_agent):
        """Test data consistency across complete workflow"""
        
        consistent_response = {
            "success": True,
            "completed_tasks": ["coordinator", "resume_analyst", "job_researcher", "cv_creator", "job_matcher"],
            "data_consistency_report": {
                "skill_consistency": {
                    "resume_skills": ["Python", "React", "AWS"],
                    "job_keywords": ["Python", "React", "AWS", "Docker"],
                    "cv_skills": ["Python", "React", "AWS", "Docker"],
                    "consistency_score": 0.92
                },
                "role_consistency": {
                    "resume_target": "Senior Software Engineer",
                    "job_searches": ["Senior Software Engineer", "Lead Developer"],
                    "cv_positioning": "Senior Software Engineer",
                    "consistency_score": 0.88
                },
                "overall_consistency": 0.90
            },
            "workflow_validation": {
                "all_agents_completed": True,
                "data_flow_intact": True,
                "no_data_loss": True,
                "consistency_threshold_met": True
            }
        }
        
        mock_job_hunting_agent.process_request.return_value = consistent_response
        
        result = mock_job_hunting_agent.process_request("Complete workflow with data validation")
        
        # Validate end-to-end consistency
        assert result["success"] is True
        assert "data_consistency_report" in result
        assert "workflow_validation" in result
        
        consistency = result["data_consistency_report"]
        assert consistency["overall_consistency"] >= 0.8, "Data consistency too low"
        
        validation = result["workflow_validation"]
        assert validation["all_agents_completed"] is True
        assert validation["data_flow_intact"] is True
        assert validation["no_data_loss"] is True