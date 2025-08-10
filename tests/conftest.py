"""
Pytest configuration and shared fixtures for multi-agent system testing
"""

import pytest
import os
import tempfile
import json
from unittest.mock import MagicMock, patch
from faker import Faker
from typing import Dict, Any, List
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.main import JobHuntingMultiAgent
from api.agents.base import MultiAgentState

fake = Faker()

@pytest.fixture(scope="session")
def test_config():
    """Test configuration and environment setup"""
    return {
        "openai_api_key": "test_key_12345",
        "scraper_api_key": "test_scraper_key",
        "test_timeout": 30,
        "mock_responses": True
    }

@pytest.fixture
def sample_resume_content():
    """Sample resume content for testing"""
    return """
    John Doe
    Software Engineer
    
    Experience:
    - Senior Software Engineer at Tech Corp (2020-2024)
    - Built scalable web applications using Python, React, and AWS
    - Led team of 5 developers on microservices architecture
    - Improved system performance by 40%
    
    Skills:
    Python, JavaScript, React, AWS, Docker, Kubernetes, PostgreSQL
    
    Education:
    BS Computer Science, University of Technology (2018)
    """

@pytest.fixture
def sample_resume_file():
    """Create a temporary resume file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""
        John Doe
        Software Engineer
        john.doe@email.com
        
        Experience:
        - Senior Software Engineer at Tech Corp (2020-2024)
        - Full Stack Developer at StartupCo (2018-2020)
        
        Skills: Python, JavaScript, React, AWS, Docker
        """)
        f.flush()
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def sample_job_listings():
    """Sample job listings for testing"""
    return [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp Inc",
            "location": "San Francisco, CA",
            "description": "We are looking for a Senior Software Engineer with 5+ years of experience in Python, React, and AWS. The role involves building scalable web applications and leading technical decisions.",
            "salary": "$120,000 - $160,000",
            "apply_url": "https://example.com/job1",
            "source": "test",
            "date_found": "2024-01-15"
        },
        {
            "title": "Full Stack Developer",
            "company": "Startup Inc",
            "location": "Remote",
            "description": "Join our growing team as a Full Stack Developer. Work with modern technologies including JavaScript, React, Node.js, and AWS. Perfect for someone with 3+ years of experience.",
            "salary": "$90,000 - $120,000",
            "apply_url": "https://example.com/job2",
            "source": "test",
            "date_found": "2024-01-14"
        }
    ]

@pytest.fixture
def sample_multi_agent_state():
    """Sample MultiAgentState for testing"""
    return {
        "messages": [],
        "user_request": "Please analyze my resume and find relevant job opportunities",
        "resume_path": "/tmp/test_resume.txt",
        "resume_content": "John Doe - Software Engineer...",
        "resume_analysis": {},
        "job_market_data": {},
        "job_listings": [],
        "cv_path": "",
        "comparison_results": {},
        "coordinator_plan": {},
        "completed_tasks": [],
        "next_agent": "coordinator"
    }

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API responses"""
    def _mock_response(content: str):
        mock_response = MagicMock()
        mock_response.content = content
        return mock_response
    return _mock_response

@pytest.fixture
def mock_job_hunting_agent():
    """Mock JobHuntingMultiAgent with controlled responses"""
    with patch('api.main.JobHuntingMultiAgent') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Set up default mock responses
        mock_instance.process_request.return_value = {
            "success": True,
            "session_id": "test_session_123",
            "user_id": "test_user_123",
            "messages": [],
            "completed_tasks": ["coordinator", "resume_analyst"],
            "processing_time": 2.5,
            "performance_summary": {"agents_used": 2, "efficiency_rating": "excellent"}
        }
        
        yield mock_instance

@pytest.fixture
def performance_benchmarks():
    """Performance benchmarks for testing"""
    return {
        "max_response_time": 15.0,  # seconds
        "max_memory_usage": 500,    # MB
        "min_success_rate": 0.9,    # 90%
        "max_error_rate": 0.1,      # 10%
        "target_throughput": 10,    # requests per minute
    }

@pytest.fixture
def evaluation_criteria():
    """Evaluation criteria for different agent types"""
    return {
        "resume_analyst": {
            "accuracy_threshold": 0.8,
            "completeness_threshold": 0.85,
            "relevance_threshold": 0.8,
            "required_sections": ["strengths", "weaknesses", "improvements", "score"]
        },
        "job_researcher": {
            "accuracy_threshold": 0.75,
            "relevance_threshold": 0.8,
            "minimum_jobs": 5,
            "max_response_time": 10.0
        },
        "cv_creator": {
            "format_score_threshold": 0.9,
            "content_quality_threshold": 0.8,
            "ats_optimization_threshold": 0.85,
            "file_generation_success": True
        },
        "job_matcher": {
            "accuracy_threshold": 0.8,
            "fit_score_threshold": 0.7,
            "explanation_quality_threshold": 0.75
        }
    }

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "test_key_12345")
    monkeypatch.setenv("SCRAPER_API_KEY", "test_scraper_key")
    monkeypatch.setenv("TESTING", "true")

@pytest.fixture
def test_data_generator():
    """Generate various test data scenarios"""
    def generate_user_requests(count: int = 5) -> List[str]:
        requests = [
            "Analyze my resume and provide feedback",
            "Find software engineering jobs that match my background",
            "Create an optimized CV for tech companies",
            "I need complete job hunting help - analyze, search, and create CV",
            "Research the job market for data science positions"
        ]
        return requests[:count]
    
    def generate_resume_variations() -> List[str]:
        return [
            "Experienced software engineer with 5 years in Python and React",
            "Recent graduate with internship experience in web development", 
            "Career changer from finance to technology with bootcamp training",
            "Senior developer with expertise in machine learning and AI",
            "Product manager transitioning to technical roles"
        ]
    
    return {
        "user_requests": generate_user_requests,
        "resume_variations": generate_resume_variations
    }

class MockDeepEvalMetric:
    """Mock DeepEval metric for testing"""
    def __init__(self, name: str, threshold: float = 0.8):
        self.name = name
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False
    
    def measure(self, test_case) -> float:
        # Simulate evaluation logic
        if hasattr(test_case, 'actual_output') and test_case.actual_output:
            self.score = 0.85  # Mock good score
            self.success = True
            self.reason = f"Mock evaluation passed for {self.name}"
        else:
            self.score = 0.3
            self.success = False
            self.reason = f"Mock evaluation failed for {self.name}"
        return self.score

@pytest.fixture
def mock_deepeval_metrics():
    """Mock DeepEval metrics for testing"""
    return {
        "accuracy": MockDeepEvalMetric("accuracy", 0.8),
        "relevance": MockDeepEvalMetric("relevance", 0.75),
        "completeness": MockDeepEvalMetric("completeness", 0.85),
        "coherence": MockDeepEvalMetric("coherence", 0.8)
    }