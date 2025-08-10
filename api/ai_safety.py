"""
AI Safety Module for Multi-Agent Job Hunting System
Provides bias detection, hallucination prevention, and ethical AI safeguards
"""

import re
import json
import hashlib
import logging
import statistics
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

# Optional ML libraries for enhanced AI safety (graceful degradation if not available)
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    ML_LIBS_AVAILABLE = True
except ImportError:
    ML_LIBS_AVAILABLE = False
    TfidfVectorizer = None
    np = None

try:
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    TextBlob = None

try:
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    nltk = None

try:
    FAIRLEARN_AVAILABLE = True
except ImportError:
    FAIRLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

# Download required NLTK data if available
if NLTK_AVAILABLE and nltk:
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except:
            logger.warning("Could not download NLTK punkt tokenizer")



@dataclass
class BiasDetectionResult:
    """Result of bias detection analysis"""
    bias_detected: bool
    bias_type: str
    bias_score: float
    affected_groups: List[str]
    explanation: str
    mitigation_suggestions: List[str]

@dataclass
class HallucinationCheck:
    """Result of hallucination detection"""
    verified: bool
    confidence_score: float
    verification_sources: List[str]
    flagged_claims: List[str]
    reliability_score: float

    def __init__(self, verified=True, confidence_score=0.85, verification_sources=None, 
                 flagged_claims=None, reliability_score=0.8):
        self.verified = verified
        self.confidence_score = confidence_score
        self.verification_sources = verification_sources or []
        self.flagged_claims = flagged_claims or []
        self.reliability_score = reliability_score

@dataclass
class SafetyAssessment:
    """Overall AI safety assessment"""
    safety_score: float
    bias_check: BiasDetectionResult
    hallucination_check: HallucinationCheck
    ethical_concerns: List[str]
    transparency_level: str
    recommendations: List[str]

class AIFairnessMonitor:
    """Monitors AI system for bias and fairness issues"""
    
    def __init__(self):
        self.protected_attributes = {
            'gender': ['male', 'female', 'woman', 'man', 'gender', 'she', 'he'],
            'race': ['african', 'asian', 'hispanic', 'latino', 'white', 'black', 'arab'],
            'age': ['young', 'old', 'senior', 'junior', 'aged', 'elderly'],
            'religion': ['christian', 'muslim', 'jewish', 'hindu', 'buddhist', 'islam'],
            'nationality': ['american', 'indian', 'chinese', 'mexican', 'european'],
            'education': ['harvard', 'mit', 'stanford', 'community college', 'bootcamp']
        }
        
        # Bias detection patterns
        self.bias_patterns = {
            'name_bias': [
                r'\b(mohammed|muhammad|ahmed|jose|wang|patel|smith|johnson)\b',
                r'\b(jennifer|susan|michael|david|maria|carlos)\b'
            ],
            'education_bias': [
                r'\b(ivy league|elite university|prestigious|top-tier)\b',
                r'\b(community college|technical school|online degree)\b'
            ],
            'experience_bias': [
                r'\b(career gap|time off|parental leave|sabbatical)\b',
                r'\b(non-traditional|unconventional|alternative path)\b'
            ]
        }
        
        # Historical scoring data for bias detection
        self.scoring_history: Dict[str, List[float]] = defaultdict(list)
        self.demographic_scores: Dict[str, List[float]] = defaultdict(list)
    
    def detect_name_bias(self, resume_text: str, score: float) -> BiasDetectionResult:
        """Detect potential name-based bias in scoring"""
        
        # Extract likely names from resume
        name_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # First Last
            r'^([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)',  # First M. Last
        ]
        
        detected_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, resume_text[:200])  # Check first 200 chars
            detected_names.extend(matches)
        
        if not detected_names:
            return BiasDetectionResult(
                bias_detected=False, bias_type="name", bias_score=0.0,
                affected_groups=[], explanation="No names detected for analysis",
                mitigation_suggestions=[]
            )
        
        # Categorize names by likely demographic (simplified heuristic)
        likely_demographics = self._categorize_names(detected_names)
        
        # Check for scoring disparities
        bias_score = self._calculate_demographic_disparity(likely_demographics, score)
        
        has_bias = bias_score > 0.2  # 20% disparity threshold
        
        return BiasDetectionResult(
            bias_detected=has_bias,
            bias_type="name_bias",
            bias_score=bias_score,
            affected_groups=list(likely_demographics.keys()),
            explanation=f"Name-based scoring analysis shows {bias_score:.2f} disparity score",
            mitigation_suggestions=[
                "Use blind resume review processes",
                "Focus on skills and experience over demographic markers",
                "Regular bias auditing of scoring patterns"
            ] if has_bias else []
        )
    
    def detect_content_bias(self, resume_analysis: Dict[str, Any]) -> BiasDetectionResult:
        """Detect bias in resume content analysis"""
        
        try:
            from api.utils import make_serializable
            serializable_analysis = make_serializable(resume_analysis)
            analysis_text = json.dumps(serializable_analysis).lower()
        except Exception:
            analysis_text = str(resume_analysis).lower()
        bias_flags = []
        bias_score = 0.0
        
        # Check for biased language patterns
        for bias_type, patterns in self.bias_patterns.items():
            for pattern in patterns:
                if re.search(pattern, analysis_text, re.IGNORECASE):
                    bias_flags.append(bias_type)
                    bias_score += 0.1
        
        # Check for unfair penalization patterns
        unfair_penalties = [
            'career gap', 'time off', 'parental leave', 'family obligations',
            'non-traditional background', 'alternative education'
        ]
        
        weaknesses = resume_analysis.get('weaknesses', [])
        if isinstance(weaknesses, list):
            weakness_text = ' '.join(str(w).lower() for w in weaknesses)
            for penalty in unfair_penalties:
                if penalty in weakness_text:
                    bias_flags.append('unfair_penalization')
                    bias_score += 0.15
        
        has_bias = bias_score > 0.1 or len(bias_flags) > 0
        
        return BiasDetectionResult(
            bias_detected=has_bias,
            bias_type="content_bias",
            bias_score=min(bias_score, 1.0),
            affected_groups=bias_flags,
            explanation=f"Content analysis detected {len(bias_flags)} potential bias indicators",
            mitigation_suggestions=[
                "Review analysis criteria for fairness",
                "Remove demographic-related penalization",
                "Focus on job-relevant qualifications only",
                "Implement bias training for analysis criteria"
            ] if has_bias else []
        )
    
    def _categorize_names(self, names: List[str]) -> Dict[str, int]:
        """Simple heuristic to categorize names by likely demographics"""
        
        # This is a simplified approach - in production, use more sophisticated
        # demographic inference or remove name-based analysis entirely
        categories = defaultdict(int)
        
        common_patterns = {
            'western': ['smith', 'johnson', 'williams', 'brown', 'jones', 'garcia'],
            'asian': ['wang', 'li', 'zhang', 'chen', 'patel', 'kumar'],
            'arabic': ['mohammed', 'ahmed', 'omar', 'hassan', 'ali'],
            'hispanic': ['rodriguez', 'martinez', 'lopez', 'gonzalez', 'perez']
        }
        
        for name in names:
            name_lower = name.lower()
            for category, patterns in common_patterns.items():
                if any(pattern in name_lower for pattern in patterns):
                    categories[category] += 1
                    break
            else:
                categories['other'] += 1
        
        return dict(categories)
    
    def detect_resume_scoring_bias(self, resume_text: str, score: float, 
                                 recommendations: List[str]) -> BiasDetectionResult:
        """Detect potential bias in resume scoring (convenience method)"""
        # This combines name bias and content bias detection
        name_bias = self.detect_name_bias(resume_text, score)
        
        # Simple content analysis for scoring bias
        content_bias_score = 0.0
        bias_flags = []
        
        # Check for unfair penalization in recommendations
        unfair_terms = ['career gap', 'non-traditional', 'alternative background']
        for recommendation in recommendations:
            for term in unfair_terms:
                if term.lower() in recommendation.lower():
                    content_bias_score += 0.1
                    bias_flags.append('unfair_penalization')
        
        overall_bias_detected = name_bias.bias_detected or content_bias_score > 0
        combined_score = max(name_bias.bias_score, content_bias_score)
        
        return BiasDetectionResult(
            bias_detected=overall_bias_detected,
            bias_type='resume_scoring',
            bias_score=combined_score,
            affected_groups=name_bias.affected_groups + bias_flags,
            explanation=f"Resume scoring analysis: name_bias={name_bias.bias_detected}, content_bias={content_bias_score > 0}",
            mitigation_suggestions=name_bias.mitigation_suggestions + [
                "Review scoring criteria for fairness",
                "Use structured evaluation rubrics"
            ] if overall_bias_detected else []
        )
    
    def detect_job_listing_bias(self, job_listings: str, role: str) -> BiasDetectionResult:
        """Detect bias in job listings"""
        biased_language = [
            'rockstar', 'ninja', 'guru', 'culture fit', 'young team',
            'digital native', 'fresh graduate'
        ]
        
        bias_score = 0.0
        detected_terms = []
        
        job_text_lower = job_listings.lower()
        for term in biased_language:
            if term in job_text_lower:
                bias_score += 0.1
                detected_terms.append(term)
        
        bias_detected = bias_score > 0
        
        return BiasDetectionResult(
            bias_detected=bias_detected,
            bias_type='job_listing_language',
            bias_score=min(bias_score, 1.0),
            affected_groups=['age', 'culture', 'education'] if bias_detected else [],
            explanation=f"Found {len(detected_terms)} potentially biased terms in job listings",
            mitigation_suggestions=[
                "Use inclusive language in job descriptions",
                "Focus on required skills and qualifications",
                "Avoid cultural or age-related terminology"
            ] if bias_detected else []
        )
    
    def _calculate_demographic_disparity(self, demographics: Dict[str, int], score: float) -> float:
        """Calculate disparity in scoring across demographics"""
        
        # Store scores by demographic for historical analysis
        for demo, count in demographics.items():
            self.demographic_scores[demo].append(score)
        
        # Calculate disparity if we have enough historical data
        if len(self.demographic_scores) < 2:
            return 0.0
        
        scores_by_demo = {}
        for demo, scores in self.demographic_scores.items():
            if len(scores) >= 5:  # Need at least 5 samples
                scores_by_demo[demo] = statistics.mean(scores)
        
        if len(scores_by_demo) < 2:
            return 0.0
        
        # Calculate coefficient of variation as disparity measure
        mean_scores = list(scores_by_demo.values())
        if statistics.mean(mean_scores) == 0:
            return 0.0
        
        disparity = statistics.stdev(mean_scores) / statistics.mean(mean_scores)
        return min(disparity, 1.0)

class HallucinationDetector:
    """Detects AI hallucinations and verifies content reliability"""
    
    def __init__(self):
        self.known_facts = {
            'salary_ranges': {
                'software_engineer': (60000, 200000),
                'data_scientist': (70000, 250000),
                'product_manager': (80000, 180000),
                'designer': (50000, 150000)
            },
            'common_skills': {
                'software_engineer': ['python', 'javascript', 'react', 'sql', 'git'],
                'data_scientist': ['python', 'r', 'sql', 'machine learning', 'statistics'],
                'product_manager': ['strategy', 'analytics', 'communication', 'roadmap'],
            },
            'unrealistic_claims': [
                'guaranteed job placement', 'instant hiring', '500% salary increase',
                'no experience required for senior role', 'work 1 hour per week'
            ]
        }
        
        # Initialize fact-checking database (if ML libraries available)
        if ML_LIBS_AVAILABLE and TfidfVectorizer:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        else:
            self.vectorizer = None
            
        self.verified_statements = []
        self.false_statements = []
    
    def check_market_claims(self, market_data: Dict[str, Any]) -> HallucinationCheck:
        """Verify market claims and data consistency"""
        flagged_claims = []
        reliability_score = 1.0
        
        # Check for unrealistic job counts
        total_jobs = market_data.get('total_jobs_found', 0)
        role = market_data.get('role_researched', '')
        
        if total_jobs > 1000:
            flagged_claims.append("Suspiciously high job count")
            reliability_score -= 0.2
        
        # Check demand level consistency
        demand_level = market_data.get('market_insights', {}).get('demand_level', '')
        if demand_level == 'High' and total_jobs < 5:
            flagged_claims.append("Inconsistent demand level vs job count")
            reliability_score -= 0.3
        
        return HallucinationCheck(
            verified=len(flagged_claims) == 0,
            confidence_score=reliability_score,
            verification_sources=['market_analysis'],
            flagged_claims=flagged_claims,
            reliability_score=max(0.0, reliability_score)
        )
    
    def check_salary_claims(self, job_data: Dict[str, Any]) -> HallucinationCheck:
        """Verify salary information against known ranges"""
        
        flagged_claims = []
        reliability_score = 1.0
        
        for job in job_data.get('job_listings', []):
            salary_str = job.get('salary', '')
            if not salary_str:
                continue
            
            # Extract salary numbers
            salary_numbers = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', salary_str)
            if len(salary_numbers) >= 2:
                try:
                    min_salary = int(salary_numbers[0].replace(',', ''))
                    max_salary = int(salary_numbers[1].replace(',', ''))
                    
                    # Check against known ranges
                    job_title = job.get('title', '').lower()
                    for role, (known_min, known_max) in self.known_facts['salary_ranges'].items():
                        if role in job_title:
                            # Flag if salary is unrealistic (>50% outside known range)
                            if min_salary < known_min * 0.5 or max_salary > known_max * 1.5:
                                flagged_claims.append(
                                    f"Suspicious salary range for {role}: ${min_salary:,}-${max_salary:,}"
                                )
                                reliability_score -= 0.2
                            break
                    
                except (ValueError, IndexError):
                    flagged_claims.append(f"Invalid salary format: {salary_str}")
                    reliability_score -= 0.1
        
        # Check market data claims
        market_data = job_data.get('job_market_data', {})
        if 'avg_salary' in market_data:
            avg_salary_str = market_data['avg_salary']
            salary_match = re.search(r'\$(\d{1,3}(?:,\d{3})*)', avg_salary_str)
            if salary_match:
                avg_salary = int(salary_match.group(1).replace(',', ''))
                if avg_salary > 500000 or avg_salary < 20000:
                    flagged_claims.append(f"Unrealistic average salary: ${avg_salary:,}")
                    reliability_score -= 0.3
        
        return HallucinationCheck(
            verified=len(flagged_claims) == 0,
            confidence_score=reliability_score,
            verification_sources=['internal_salary_database'],
            flagged_claims=flagged_claims,
            reliability_score=max(0.0, reliability_score)
        )
    
    def check_market_claims(self, job_market_data: Dict[str, Any]) -> HallucinationCheck:
        """Verify job market claims and trends"""
        
        flagged_claims = []
        reliability_score = 1.0
        
        # Check demand claims
        demand_level = job_market_data.get('demand_level', '').lower()
        total_jobs = job_market_data.get('total_jobs_found', 0)
        
        # Cross-check demand with actual job count
        if demand_level == 'very high' and total_jobs < 10:
            flagged_claims.append("Claims 'very high' demand but found few jobs")
            reliability_score -= 0.3
        elif demand_level == 'low' and total_jobs > 100:
            flagged_claims.append("Claims 'low' demand but found many jobs")
            reliability_score -= 0.2
        
        # Check for unrealistic growth claims
        growth_trend = job_market_data.get('growth_trend', '')
        if re.search(r'(\d+)%', growth_trend):
            growth_match = re.search(r'(\d+)%', growth_trend)
            if growth_match:
                growth_rate = int(growth_match.group(1))
                if growth_rate > 100:  # >100% growth is suspicious
                    flagged_claims.append(f"Unrealistic growth rate: {growth_rate}%")
                    reliability_score -= 0.4
        
        # Check trending skills reasonableness
        trending_skills = job_market_data.get('trending_skills', [])
        if len(trending_skills) > 20:  # Too many trending skills is suspicious
            flagged_claims.append("Unusually high number of 'trending' skills")
            reliability_score -= 0.1
        
        # Check for contradictory information
        if 'recommendations' in job_market_data:
            recommendations = job_market_data['recommendations']
            if isinstance(recommendations, list):
                rec_text = ' '.join(recommendations).lower()
                for unrealistic in self.known_facts['unrealistic_claims']:
                    if unrealistic in rec_text:
                        flagged_claims.append(f"Unrealistic claim: {unrealistic}")
                        reliability_score -= 0.5
        
        return HallucinationCheck(
            verified=len(flagged_claims) == 0,
            confidence_score=reliability_score,
            verification_sources=['job_count_analysis', 'trend_analysis'],
            flagged_claims=flagged_claims,
            reliability_score=max(0.0, reliability_score)
        )
    
    def check_resume_analysis_consistency(self, resume_analysis: Dict[str, Any]) -> HallucinationCheck:
        """Check resume analysis for internal consistency and reasonableness"""
        
        flagged_claims = []
        reliability_score = 1.0
        
        # Check score consistency
        overall_score = resume_analysis.get('overall_score', 0)
        if isinstance(overall_score, (int, float)):
            if overall_score > 100 or overall_score < 0:
                flagged_claims.append(f"Invalid score range: {overall_score}")
                reliability_score -= 0.5
            
            # Check if score matches qualitative assessment
            strengths_count = len(resume_analysis.get('strengths', []))
            weaknesses_count = len(resume_analysis.get('weaknesses', []))
            
            if overall_score > 90 and weaknesses_count > strengths_count:
                flagged_claims.append("High score but more weaknesses than strengths")
                reliability_score -= 0.2
            elif overall_score < 30 and strengths_count > weaknesses_count * 2:
                flagged_claims.append("Low score but significantly more strengths")
                reliability_score -= 0.2
        
        # Check for contradictory statements
        strengths = resume_analysis.get('strengths', [])
        weaknesses = resume_analysis.get('weaknesses', [])
        
        if isinstance(strengths, list) and isinstance(weaknesses, list):
            strength_text = ' '.join(str(s).lower() for s in strengths)
            weakness_text = ' '.join(str(w).lower() for w in weaknesses)
            
            # Look for contradictions
            contradictions = [
                ('strong technical skills', 'lacks technical skills'),
                ('excellent communication', 'poor communication'),
                ('extensive experience', 'limited experience'),
                ('well formatted', 'formatting issues')
            ]
            
            for strength_phrase, weakness_phrase in contradictions:
                if strength_phrase in strength_text and weakness_phrase in weakness_text:
                    flagged_claims.append(f"Contradiction: {strength_phrase} vs {weakness_phrase}")
                    reliability_score -= 0.15
        
        # Check improvements reasonableness
        improvements = resume_analysis.get('improvements', [])
        if isinstance(improvements, list) and len(improvements) > 10:
            flagged_claims.append("Unusually high number of improvement suggestions")
            reliability_score -= 0.1
        
        return HallucinationCheck(
            verified=len(flagged_claims) == 0,
            confidence_score=reliability_score,
            verification_sources=['consistency_analysis'],
            flagged_claims=flagged_claims,
            reliability_score=max(0.0, reliability_score)
        )

class EthicalAIGuardian:
    """Ensures ethical AI behavior and decision-making"""
    
    def __init__(self):
        self.ethical_principles = {
            'fairness': 'AI systems should treat all users fairly regardless of demographics',
            'transparency': 'AI decisions should be explainable and understandable',
            'accountability': 'AI systems should have clear responsibility chains',
            'privacy': 'Personal data should be protected and used appropriately',
            'beneficence': 'AI should benefit users and society',
            'non_maleficence': 'AI should not cause harm',
            'autonomy': 'Users should maintain control over AI-assisted decisions'
        }
        
        self.career_impact_thresholds = {
            'low': 'General advice or information',
            'medium': 'Specific recommendations that could influence decisions',
            'high': 'Life-changing career advice or major direction changes',
            'critical': 'Advice affecting financial security or major life decisions'
        }
        
        self.ethical_violations: List[Dict[str, Any]] = []
    
    def assess_career_impact(self, ai_output: Dict[str, Any]) -> str:
        """Assess the potential career impact of AI advice"""
        
        # Analyze the content to determine impact level
        impact_indicators = {
            'critical': [
                'career change', 'quit your job', 'major transition', 'significant risk',
                'investment required', 'relocate', 'salary negotiation'
            ],
            'high': [
                'job search', 'resume overhaul', 'skill development', 'certification',
                'networking strategy', 'interview preparation'
            ],
            'medium': [
                'improve resume', 'add skills', 'consider opportunities', 'market research'
            ],
            'low': [
                'general advice', 'information only', 'background research'
            ]
        }
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            content_text = str(ai_output).lower()
        
        for impact_level in ['critical', 'high', 'medium', 'low']:
            for indicator in impact_indicators[impact_level]:
                if indicator in content_text:
                    return impact_level
        
        return 'low'
    
    def check_ethical_compliance(self, ai_output: Dict[str, Any], user_context: Dict[str, Any] = None) -> List[str]:
        """Check AI output for ethical compliance"""
        
        ethical_concerns = []
        
        # 1. Check for discriminatory content
        if self._contains_discriminatory_content(ai_output):
            ethical_concerns.append("Potential discriminatory content detected")
        
        # 2. Check for overconfident claims
        if self._contains_overconfident_claims(ai_output):
            ethical_concerns.append("AI making overconfident claims without appropriate caveats")
        
        # 3. Check for appropriate disclaimers
        if not self._has_appropriate_disclaimers(ai_output):
            ethical_concerns.append("Missing appropriate disclaimers for AI-generated advice")
        
        # 4. Check career impact vs. oversight level
        impact_level = self.assess_career_impact(ai_output)
        if impact_level in ['high', 'critical'] and not self._has_human_oversight_flag(ai_output):
            ethical_concerns.append("High-impact advice provided without human oversight recommendation")
        
        # 5. Check for transparent uncertainty
        if not self._expresses_appropriate_uncertainty(ai_output):
            ethical_concerns.append("AI advice lacks appropriate uncertainty expression")
        
        return ethical_concerns
    
    def _contains_discriminatory_content(self, ai_output: Dict[str, Any]) -> bool:
        """Check for potentially discriminatory content"""
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            # Fallback to string representation if serialization fails
            content_text = str(ai_output).lower()
        
        discriminatory_patterns = [
            r'\b(too old|too young)\b',
            r'\b(cultural fit)\b',
            r'\b(native speaker)\b',
            r'\b(family obligations)\b',
            r'\b(maternity|paternity)\b',
            r'\b(traditional gender roles)\b'
        ]
        
        for pattern in discriminatory_patterns:
            if re.search(pattern, content_text):
                return True
        
        return False
    
    def _contains_overconfident_claims(self, ai_output: Dict[str, Any]) -> bool:
        """Check for overconfident AI claims"""
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            content_text = str(ai_output).lower()
        
        overconfident_patterns = [
            r'\b(guaranteed|certainly|definitely|absolutely)\b.*\b(success|job|hired|salary)\b',
            r'\b(will definitely|must|always|never)\b',
            r'\b(perfect match|ideal candidate|best choice)\b'
        ]
        
        for pattern in overconfident_patterns:
            if re.search(pattern, content_text):
                return True
        
        return False
    
    def _has_appropriate_disclaimers(self, ai_output: Dict[str, Any]) -> bool:
        """Check if output has appropriate AI disclaimers"""
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            content_text = str(ai_output).lower()
        
        disclaimer_indicators = [
            'ai-generated', 'computer-generated', 'automated analysis',
            'suggestions only', 'consider consulting', 'professional advice'
        ]
        
        return any(indicator in content_text for indicator in disclaimer_indicators)
    
    def _has_human_oversight_flag(self, ai_output: Dict[str, Any]) -> bool:
        """Check if high-impact advice includes human oversight recommendation"""
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            content_text = str(ai_output).lower()
        
        oversight_indicators = [
            'consult with', 'seek professional advice', 'human expert',
            'career counselor', 'professional guidance', 'expert review'
        ]
        
        return any(indicator in content_text for indicator in oversight_indicators)
    
    def _expresses_appropriate_uncertainty(self, ai_output: Dict[str, Any]) -> bool:
        """Check if AI appropriately expresses uncertainty"""
        
        try:
            from api.utils import make_serializable
            serializable_output = make_serializable(ai_output) if isinstance(ai_output, dict) else ai_output
            content_text = json.dumps(serializable_output).lower()
        except Exception:
            content_text = str(ai_output).lower()
        
        uncertainty_indicators = [
            'might', 'could', 'possibly', 'potentially', 'approximately',
            'estimated', 'likely', 'uncertain', 'variable', 'depends on'
        ]
        
        return any(indicator in content_text for indicator in uncertainty_indicators)

class AITransparencyEngine:
    """Provides explanations and transparency for AI decisions"""
    
    def __init__(self):
        self.explanation_templates = {
            'resume_scoring': "Resume score of {score}/100 based on: {factors}",
            'job_matching': "Job match score of {score}% considering: {criteria}",
            'market_analysis': "Market analysis based on: {sources} with confidence: {confidence}",
            'career_advice': "Career recommendations considering: {factors} (AI-generated)"
        }
    
    def explain_resume_score(self, resume_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Provide explanation for resume scoring"""
        
        score = resume_analysis.get('overall_score', 0)
        
        # Extract scoring factors
        factors = []
        if 'strengths' in resume_analysis:
            factors.append(f"{len(resume_analysis['strengths'])} strengths identified")
        if 'weaknesses' in resume_analysis:
            factors.append(f"{len(resume_analysis['weaknesses'])} areas for improvement")
        if 'ats_compatibility' in resume_analysis:
            factors.append(f"ATS compatibility: {resume_analysis['ats_compatibility']}/100")
        
        explanation = {
            'score_explanation': self.explanation_templates['resume_scoring'].format(
                score=score,
                factors=', '.join(factors) if factors else 'general analysis'
            ),
            'scoring_criteria': [
                'Content quality and relevance',
                'Professional experience alignment',
                'Skills assessment',
                'Format and presentation',
                'ATS compatibility'
            ],
            'confidence_level': self._calculate_confidence_level(resume_analysis),
            'limitations': [
                'AI analysis may not capture all nuances',
                'Human review recommended for final decisions',
                'Scoring based on general best practices'
            ]
        }
        
        return explanation
    
    def explain_job_matching(self, job_match_results: Dict[str, Any]) -> Dict[str, Any]:
        """Provide explanation for job matching decisions"""
        
        matches = job_match_results.get('matches', [])
        
        explanations = []
        for match in matches:
            score = match.get('fit_score', 0)
            matching_skills = match.get('matching_skills', [])
            missing_skills = match.get('missing_skills', [])
            
            explanation = {
                'match_score': f"{score}/100",
                'matching_factors': matching_skills[:5],  # Top 5
                'gaps_identified': missing_skills[:3],    # Top 3
                'recommendation': self._get_match_recommendation(score)
            }
            explanations.append(explanation)
        
        return {
            'match_explanations': explanations,
            'methodology': 'Skills alignment and experience level matching',
            'confidence_factors': [
                'Skills overlap percentage',
                'Experience level alignment',
                'Industry relevance',
                'Role responsibility match'
            ],
            'limitations': [
                'Based on available job description data',
                'Cannot assess company culture fit',
                'Should be verified through research'
            ]
        }
    
    def _calculate_confidence_level(self, analysis: Dict[str, Any]) -> str:
        """Calculate confidence level for AI analysis"""
        
        # Simple confidence calculation based on available data
        confidence_factors = 0
        
        if analysis.get('overall_score') is not None:
            confidence_factors += 1
        if analysis.get('strengths'):
            confidence_factors += 1
        if analysis.get('weaknesses'):
            confidence_factors += 1
        if analysis.get('improvements'):
            confidence_factors += 1
        
        confidence_levels = ['Low', 'Medium-Low', 'Medium', 'Medium-High', 'High']
        return confidence_levels[min(confidence_factors, 4)]
    
    def _get_match_recommendation(self, score: float) -> str:
        """Get recommendation based on match score"""
        
        if score >= 85:
            return "Excellent match - strongly recommended to apply"
        elif score >= 70:
            return "Good match - recommended to apply with tailored application"
        elif score >= 50:
            return "Moderate match - consider with additional skill development"
        else:
            return "Limited match - may require significant skill development"

class AISafetyCoordinator:
    """Main coordinator for all AI safety measures"""
    
    def __init__(self):
        self.fairness_monitor = AIFairnessMonitor()
        self.hallucination_detector = HallucinationDetector()
        self.ethical_guardian = EthicalAIGuardian()
        self.transparency_engine = AITransparencyEngine()
        
        # Safety metrics tracking
        self.safety_metrics = {
            'bias_detections': 0,
            'hallucination_flags': 0,
            'ethical_violations': 0,
            'total_assessments': 0
        }
    
    def comprehensive_safety_check(self, ai_output: Dict[str, Any], 
                                 output_type: str = 'general') -> SafetyAssessment:
        """Perform comprehensive AI safety assessment"""
        
        self.safety_metrics['total_assessments'] += 1
        
        # 1. Bias Detection
        bias_result = self._check_for_bias(ai_output, output_type)
        if bias_result.bias_detected:
            self.safety_metrics['bias_detections'] += 1
        
        # 2. Hallucination Detection
        hallucination_result = self._check_for_hallucinations(ai_output, output_type)
        if not hallucination_result.verified:
            self.safety_metrics['hallucination_flags'] += 1
        
        # 3. Ethical Assessment
        ethical_concerns = self.ethical_guardian.check_ethical_compliance(ai_output)
        if ethical_concerns:
            self.safety_metrics['ethical_violations'] += 1
        
        # 4. Calculate overall safety score
        safety_score = self._calculate_safety_score(
            bias_result, hallucination_result, ethical_concerns
        )
        
        # 5. Generate transparency information
        transparency_level = self._assess_transparency(ai_output)
        
        # 6. Generate recommendations
        recommendations = self._generate_safety_recommendations(
            bias_result, hallucination_result, ethical_concerns, safety_score
        )
        
        return SafetyAssessment(
            safety_score=safety_score,
            bias_check=bias_result,
            hallucination_check=hallucination_result,
            ethical_concerns=ethical_concerns,
            transparency_level=transparency_level,
            recommendations=recommendations
        )
    
    def _check_for_bias(self, ai_output: Dict[str, Any], output_type: str) -> BiasDetectionResult:
        """Check AI output for bias"""
        
        if output_type == 'resume_analysis':
            # Check for name bias if resume content available
            resume_content = ai_output.get('resume_content', '')
            score = ai_output.get('overall_score', 0)
            
            if resume_content and score:
                name_bias = self.fairness_monitor.detect_name_bias(resume_content, score)
                if name_bias.bias_detected:
                    return name_bias
            
            # Check content bias
            return self.fairness_monitor.detect_content_bias(ai_output)
        
        # Default: no bias detected for other types
        return BiasDetectionResult(
            bias_detected=False, bias_type="none", bias_score=0.0,
            affected_groups=[], explanation="No bias patterns detected",
            mitigation_suggestions=[]
        )
    
    def _check_for_hallucinations(self, ai_output: Dict[str, Any], 
                                output_type: str) -> HallucinationCheck:
        """Check AI output for hallucinations"""
        
        if output_type == 'job_research':
            return self.hallucination_detector.check_salary_claims(ai_output)
        elif output_type == 'market_analysis':
            return self.hallucination_detector.check_market_claims(ai_output)
        elif output_type == 'resume_analysis':
            return self.hallucination_detector.check_resume_analysis_consistency(ai_output)
        
        # Default: low risk assessment
        return HallucinationCheck(
            verified=True,
            confidence_score=0.8,
            verification_sources=['general_check'],
            flagged_claims=[],
            reliability_score=0.8
        )
    
    def _calculate_safety_score(self, bias_result: BiasDetectionResult,
                              hallucination_result: HallucinationCheck,
                              ethical_concerns: List[str]) -> float:
        """Calculate overall AI safety score"""
        
        score = 1.0
        
        # Bias penalty
        if bias_result.bias_detected:
            score -= bias_result.bias_score * 0.3
        
        # Hallucination penalty
        if not hallucination_result.verified:
            score -= (1 - hallucination_result.reliability_score) * 0.4
        
        # Ethical concerns penalty
        score -= len(ethical_concerns) * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_confidence_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for AI-generated analysis"""
        confidence = 0.8  # Base confidence
        
        # Increase confidence if analysis has specific details
        if analysis.get('specific_improvements'):
            confidence += 0.1
        if analysis.get('overall_score') and isinstance(analysis.get('overall_score'), (int, float)):
            confidence += 0.05
        if analysis.get('strengths') and len(analysis.get('strengths', [])) > 2:
            confidence += 0.05
            
        return min(1.0, confidence)
    
    def _calculate_data_quality_score(self, data: Any) -> float:
        """Calculate data quality score for job listings or other data"""
        if not data:
            return 0.0
        
        score = 0.8  # Base score
        
        # If it's a list of items (like job listings)
        if isinstance(data, list):
            if len(data) > 0:
                score += 0.1
            if len(data) > 5:
                score += 0.1
                
            # Check if items have required fields
            for item in data[:3]:  # Sample first 3 items
                if isinstance(item, dict):
                    if item.get('title'):
                        score += 0.02
                    if item.get('company'):
                        score += 0.02
                    if item.get('location'):
                        score += 0.02
        
        return min(1.0, score)
    
    def _assess_transparency(self, ai_output: Dict[str, Any]) -> str:
        """Assess transparency level of AI output"""
        
        transparency_indicators = 0
        
        # Check for explanations
        if any(key in ai_output for key in ['explanation', 'reasoning', 'methodology']):
            transparency_indicators += 1
        
        # Check for confidence indicators
        if any(key in ai_output for key in ['confidence', 'certainty', 'reliability']):
            transparency_indicators += 1
        
        # Check for source attribution
        if any(key in ai_output for key in ['sources', 'based_on', 'data_from']):
            transparency_indicators += 1
        
        # Check for limitations acknowledgment
        if any(key in ai_output for key in ['limitations', 'caveats', 'disclaimers']):
            transparency_indicators += 1
        
        levels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        return levels[min(transparency_indicators, 4)]
    
    def _generate_safety_recommendations(self, bias_result: BiasDetectionResult,
                                       hallucination_result: HallucinationCheck,
                                       ethical_concerns: List[str],
                                       safety_score: float) -> List[str]:
        """Generate safety improvement recommendations"""
        
        recommendations = []
        
        # Overall safety recommendations
        if safety_score < 0.6:
            recommendations.append("🚨 Low safety score - human review strongly recommended")
        elif safety_score < 0.8:
            recommendations.append("⚠️ Moderate safety concerns - consider human oversight")
        
        # Bias-specific recommendations
        if bias_result.bias_detected:
            recommendations.extend(bias_result.mitigation_suggestions)
        
        # Hallucination-specific recommendations
        if not hallucination_result.verified:
            recommendations.append("🔍 Verify AI claims with multiple sources")
            recommendations.append("📊 Cross-check statistical claims and data")
        
        # Ethical recommendations
        if ethical_concerns:
            recommendations.append("📋 Review output for ethical compliance")
            recommendations.append("👤 Consider human expert consultation")
        
        # Transparency recommendations
        recommendations.append("💡 Provide clear explanations for AI decisions")
        recommendations.append("📈 Include confidence levels and uncertainty")
        
        return recommendations[:6]  # Limit to top 6
    
    def get_safety_metrics(self) -> Dict[str, Any]:
        """Get current safety metrics"""
        
        total = max(self.safety_metrics['total_assessments'], 1)
        
        return {
            'total_assessments': total,
            'bias_detection_rate': self.safety_metrics['bias_detections'] / total,
            'hallucination_rate': self.safety_metrics['hallucination_flags'] / total,
            'ethical_violation_rate': self.safety_metrics['ethical_violations'] / total,
            'overall_safety_rate': 1 - (
                (self.safety_metrics['bias_detections'] + 
                 self.safety_metrics['hallucination_flags'] + 
                 self.safety_metrics['ethical_violations']) / (total * 3)
            )
        }

# Global AI safety coordinator instance
ai_safety_coordinator = AISafetyCoordinator()

def safe_ai_wrapper(agent_name=None, safety_level='medium', output_type='general'):
    """Decorator to add AI safety checks to agent functions"""
    
    def decorator(ai_function):
        # Set function metadata
        ai_function.agent_name = agent_name
        ai_function.safety_level = safety_level
        ai_function.output_type = output_type
        
        def wrapper(*args, **kwargs):
            # Execute original AI function
            result = ai_function(*args, **kwargs)
            
            # Perform safety assessment
            if isinstance(result, dict):
                safety_assessment = ai_safety_coordinator.comprehensive_safety_check(
                    result, output_type=output_type
                )
                
                # Add safety information to result
                result['ai_safety'] = {
                    'agent_name': agent_name,
                    'safety_level_setting': safety_level,
                    'safety_score': safety_assessment.safety_score,
                    'safety_level': 'HIGH' if safety_assessment.safety_score >= 0.8 else
                                   'MEDIUM' if safety_assessment.safety_score >= 0.6 else 'LOW',
                    'has_bias': safety_assessment.bias_check.bias_detected,
                    'has_hallucination': not safety_assessment.hallucination_check.verified,
                    'ethical_concerns': safety_assessment.ethical_concerns,
                    'transparency_level': safety_assessment.transparency_level,
                    'recommendations': safety_assessment.recommendations
                }
                
                # Log safety issues with agent context
                if safety_assessment.safety_score < 0.6:
                    logger.warning(f"Low AI safety score for {agent_name}: {safety_assessment.safety_score:.2f}")
            
            return result
        
        return wrapper
    
    return decorator
