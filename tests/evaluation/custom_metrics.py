"""
Custom DeepEval metrics for evaluating the multi-agent job hunting system
"""

import json
import re
from typing import List, Dict, Any, Optional
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from deepeval.scorer import Scorer


class ResumeAnalysisAccuracyMetric(BaseMetric):
    """
    Custom metric to evaluate the accuracy of resume analysis
    """
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure resume analysis accuracy"""
        try:
            # Parse the actual output
            if isinstance(test_case.actual_output, str):
                try:
                    analysis = json.loads(test_case.actual_output)
                except json.JSONDecodeError:
                    analysis = {"raw_output": test_case.actual_output}
            else:
                analysis = test_case.actual_output
            
            score = 0.0
            max_score = 100.0
            
            # Check for required components
            required_fields = ["strengths", "weaknesses", "improvements", "overall_score"]
            field_weight = 20.0
            
            for field in required_fields:
                if field in analysis and analysis[field]:
                    if field == "overall_score":
                        # Validate score is reasonable (0-100)
                        try:
                            score_val = float(analysis[field])
                            if 0 <= score_val <= 100:
                                score += field_weight
                        except (ValueError, TypeError):
                            pass
                    else:
                        # Check if content is meaningful (not empty or too short)
                        content = str(analysis[field])
                        if len(content.strip()) >= 10:  # Minimum meaningful content
                            score += field_weight
            
            # Additional quality checks
            if "ats_compatibility" in analysis:
                score += 10.0
            
            if "keyword_analysis" in analysis:
                score += 10.0
            
            self.score = score / max_score
            self.success = self.score >= self.threshold
            self.reason = f"Resume analysis score: {self.score:.2f} (threshold: {self.threshold})"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating resume analysis: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "Resume Analysis Accuracy"


class JobSearchRelevanceMetric(BaseMetric):
    """
    Custom metric to evaluate job search relevance
    """
    
    def __init__(self, threshold: float = 0.75, min_jobs: int = 3):
        self.threshold = threshold
        self.min_jobs = min_jobs
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure job search relevance"""
        try:
            # Parse job listings from output
            if isinstance(test_case.actual_output, dict):
                job_listings = test_case.actual_output.get("job_listings", [])
            else:
                # Try to extract from string
                job_listings = []
            
            if not job_listings:
                self.score = 0.0
                self.success = False
                self.reason = "No job listings found"
                return self.score
            
            # Evaluate relevance
            total_score = 0.0
            job_count = len(job_listings)
            
            # Quantity check
            quantity_score = min(job_count / self.min_jobs, 1.0) * 30
            total_score += quantity_score
            
            # Quality checks per job
            quality_score = 0.0
            for job in job_listings:
                job_score = 0.0
                
                # Required fields
                if job.get("title"): job_score += 20
                if job.get("company"): job_score += 15
                if job.get("location"): job_score += 10
                if job.get("description"): 
                    desc_length = len(str(job.get("description", "")))
                    job_score += min(desc_length / 100, 1.0) * 25  # Up to 25 points for description
                
                # Bonus for additional fields
                if job.get("salary"): job_score += 10
                if job.get("apply_url"): job_score += 10
                
                quality_score += min(job_score, 100)
            
            if job_count > 0:
                quality_score = (quality_score / job_count) * 0.7  # 70% weight for quality
                total_score += quality_score
            
            self.score = total_score / 100
            self.success = self.score >= self.threshold
            self.reason = f"Job search relevance: {self.score:.2f} ({job_count} jobs found)"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating job search: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "Job Search Relevance"


class CVGenerationQualityMetric(BaseMetric):
    """
    Custom metric to evaluate CV generation quality
    """
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure CV generation quality"""
        try:
            output = test_case.actual_output
            
            # Check if CV was generated
            cv_generated = False
            cv_path = ""
            
            if isinstance(output, dict):
                cv_path = output.get("cv_path", "")
                cv_generated = bool(cv_path)
            
            if not cv_generated:
                self.score = 0.0
                self.success = False
                self.reason = "No CV file was generated"
                return self.score
            
            score = 0.0
            
            # File generation (40% weight)
            score += 40.0
            
            # Check for expected CV sections in response
            cv_content = output.get("cv_content", "")
            if cv_content:
                # Look for standard CV sections
                sections = ["experience", "skills", "education", "summary", "contact"]
                section_score = 0
                for section in sections:
                    if section.lower() in cv_content.lower():
                        section_score += 1
                score += (section_score / len(sections)) * 30.0  # 30% weight
            
            # ATS optimization indicators
            ats_indicators = ["keywords", "format", "readable"]
            ats_score = 0
            output_text = str(output).lower()
            for indicator in ats_indicators:
                if indicator in output_text:
                    ats_score += 1
            score += (ats_score / len(ats_indicators)) * 30.0  # 30% weight
            
            self.score = score / 100
            self.success = self.score >= self.threshold
            self.reason = f"CV generation quality: {self.score:.2f} (file: {bool(cv_path)})"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating CV generation: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "CV Generation Quality"


class JobMatchingAccuracyMetric(BaseMetric):
    """
    Custom metric to evaluate job matching accuracy
    """
    
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure job matching accuracy"""
        try:
            output = test_case.actual_output
            
            if isinstance(output, dict):
                comparison_results = output.get("comparison_results", {})
            else:
                comparison_results = {}
            
            if not comparison_results:
                self.score = 0.0
                self.success = False
                self.reason = "No job matching results found"
                return self.score
            
            score = 0.0
            
            # Check for match scores
            if "matches" in comparison_results:
                matches = comparison_results["matches"]
                if matches and len(matches) > 0:
                    score += 40.0  # Base score for having matches
                    
                    # Evaluate match quality
                    total_match_score = 0
                    valid_matches = 0
                    
                    for match in matches:
                        if isinstance(match, dict):
                            match_score = match.get("fit_score", 0)
                            if isinstance(match_score, (int, float)) and 0 <= match_score <= 100:
                                total_match_score += match_score
                                valid_matches += 1
                    
                    if valid_matches > 0:
                        avg_match_score = total_match_score / valid_matches
                        score += (avg_match_score / 100) * 40.0  # 40% based on match quality
            
            # Check for explanations
            if "explanations" in comparison_results or "analysis" in comparison_results:
                score += 20.0  # 20% for providing explanations
            
            self.score = score / 100
            self.success = self.score >= self.threshold
            self.reason = f"Job matching accuracy: {self.score:.2f}"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating job matching: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "Job Matching Accuracy"


class SystemCoherenceMetric(BaseMetric):
    """
    Custom metric to evaluate overall system coherence and workflow
    """
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure system coherence"""
        try:
            output = test_case.actual_output
            
            if not isinstance(output, dict):
                self.score = 0.0
                self.success = False
                self.reason = "Invalid system output format"
                return self.score
            
            score = 0.0
            
            # Check for successful completion
            if output.get("success", False):
                score += 30.0
            
            # Check for agent coordination
            completed_tasks = output.get("completed_tasks", [])
            if completed_tasks and len(completed_tasks) > 1:
                score += 25.0  # Multi-agent coordination
                
                # Check for logical agent sequence
                if "coordinator" in completed_tasks:
                    score += 15.0
            
            # Check for comprehensive results
            result_components = [
                "resume_analysis",
                "job_listings", 
                "cv_path",
                "comparison_results"
            ]
            
            component_score = 0
            for component in result_components:
                if component in output and output[component]:
                    component_score += 1
            
            score += (component_score / len(result_components)) * 30.0
            
            self.score = score / 100
            self.success = self.score >= self.threshold
            self.reason = f"System coherence: {self.score:.2f} ({len(completed_tasks)} agents)"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating system coherence: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "System Coherence"


class PerformanceEfficiencyMetric(BaseMetric):
    """
    Custom metric to evaluate system performance and efficiency
    """
    
    def __init__(self, threshold: float = 0.7, max_time: float = 15.0):
        self.threshold = threshold
        self.max_time = max_time
        self.scorer = Scorer()
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure performance efficiency"""
        try:
            output = test_case.actual_output
            
            if not isinstance(output, dict):
                self.score = 0.0
                self.success = False
                self.reason = "Invalid output for performance measurement"
                return self.score
            
            score = 0.0
            
            # Time efficiency (50% weight)
            processing_time = output.get("processing_time", self.max_time)
            if processing_time <= self.max_time:
                time_score = max(0, (self.max_time - processing_time) / self.max_time)
                score += time_score * 50.0
            
            # Success rate (25% weight)
            if output.get("success", False):
                score += 25.0
            
            # Agent efficiency (25% weight)
            performance_summary = output.get("performance_summary", {})
            efficiency_rating = performance_summary.get("efficiency_rating", "")
            
            if efficiency_rating == "excellent":
                score += 25.0
            elif efficiency_rating == "good":
                score += 20.0
            elif efficiency_rating == "fair":
                score += 15.0
            
            self.score = score / 100
            self.success = self.score >= self.threshold
            self.reason = f"Performance efficiency: {self.score:.2f} (time: {processing_time:.2f}s)"
            
            return self.score
            
        except Exception as e:
            self.score = 0.0
            self.success = False
            self.reason = f"Error evaluating performance: {str(e)}"
            return self.score
    
    @property
    def __name__(self):
        return "Performance Efficiency"