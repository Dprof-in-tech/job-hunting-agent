"""
Sample job listings for testing job search and matching functionality
"""

SAMPLE_JOB_LISTINGS = {
    "software_engineering": [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp Inc",
            "location": "San Francisco, CA",
            "description": "We are seeking a Senior Software Engineer to join our platform engineering team. You will be responsible for designing and building scalable microservices that serve millions of users daily. The ideal candidate has 5+ years of experience with Python, React, and cloud technologies. Experience with AWS, Docker, and Kubernetes is highly preferred. You will work closely with product managers and designers to deliver high-quality features. Strong problem-solving skills and experience mentoring junior developers are essential.",
            "salary": "$140,000 - $180,000",
            "apply_url": "https://techcorp.com/careers/senior-software-engineer",
            "source": "company_website",
            "date_found": "2024-01-15",
            "requirements": [
                "5+ years software development experience",
                "Expert-level Python and JavaScript skills",
                "Experience with React and modern frontend frameworks",
                "AWS cloud platform experience", 
                "Docker and Kubernetes knowledge",
                "Bachelor's degree in Computer Science or related field"
            ],
            "benefits": [
                "Competitive salary and equity",
                "Comprehensive health insurance",
                "Flexible work arrangements",
                "Professional development budget",
                "Unlimited PTO"
            ]
        },
        {
            "title": "Full Stack Developer",
            "company": "InnovateCo",
            "location": "Remote",
            "description": "Join our remote-first team as a Full Stack Developer working on cutting-edge fintech applications. You'll build both frontend interfaces and backend APIs using modern technologies. We're looking for someone with 3+ years of experience who is passionate about creating exceptional user experiences. Experience with React, Node.js, and PostgreSQL is required. Knowledge of financial systems and regulatory compliance is a plus.",
            "salary": "$100,000 - $130,000",
            "apply_url": "https://innovateco.com/jobs/fullstack-developer",
            "source": "job_board",
            "date_found": "2024-01-14",
            "requirements": [
                "3+ years full stack development experience",
                "Proficiency in React and Node.js",
                "Strong database skills with PostgreSQL",
                "RESTful API development experience",
                "Understanding of authentication and security"
            ],
            "benefits": [
                "Remote-first culture",
                "Health, dental, and vision insurance",
                "401(k) with company matching",
                "Home office stipend",
                "Learning and development budget"
            ]
        },
        {
            "title": "Lead Software Engineer",
            "company": "ScaleUp Labs",
            "location": "Austin, TX",
            "description": "We're seeking a Lead Software Engineer to drive technical excellence and mentor our growing engineering team. You'll architect solutions for complex problems while providing technical leadership across multiple projects. The role requires 7+ years of experience with strong expertise in Python, distributed systems, and cloud architecture. Experience leading technical teams and making architectural decisions is essential. You'll work directly with CTO and product leadership to shape our technical roadmap.",
            "salary": "$160,000 - $200,000",
            "apply_url": "https://scaleuplabs.com/careers/lead-engineer",
            "source": "company_website", 
            "date_found": "2024-01-13",
            "requirements": [
                "7+ years software engineering experience",
                "Technical leadership and mentoring experience",
                "Expert knowledge of Python and distributed systems",
                "Experience with microservices architecture",
                "Strong communication and collaboration skills",
                "BS/MS in Computer Science or equivalent experience"
            ],
            "benefits": [
                "Competitive salary and significant equity",
                "Premium healthcare coverage",
                "Flexible PTO and sabbatical options",
                "Professional conference and training budget",
                "Stock options with high growth potential"
            ]
        }
    ],
    
    "data_science": [
        {
            "title": "Senior Data Scientist",
            "company": "DataDriven Corp",
            "location": "Seattle, WA",
            "description": "We're looking for a Senior Data Scientist to join our AI/ML team and drive data-driven decision making across the organization. You'll develop machine learning models for recommendation systems, fraud detection, and customer analytics. The ideal candidate has 5+ years of experience with Python, TensorFlow, and statistical analysis. PhD in a quantitative field preferred. Experience with big data technologies and A/B testing is highly valued.",
            "salary": "$150,000 - $190,000", 
            "apply_url": "https://datadriven.com/jobs/senior-data-scientist",
            "source": "job_board",
            "date_found": "2024-01-15",
            "requirements": [
                "5+ years data science experience",
                "PhD in Statistics, Mathematics, or related field",
                "Expert-level Python and R skills",
                "Experience with TensorFlow, PyTorch, or similar",
                "Strong statistical analysis and modeling skills",
                "Experience with big data technologies (Spark, Hadoop)"
            ]
        },
        {
            "title": "Machine Learning Engineer",
            "company": "AI Solutions Inc",
            "location": "Remote",
            "description": "Join our ML engineering team to build and deploy production machine learning systems at scale. You'll work on computer vision, NLP, and predictive analytics projects serving millions of users. Looking for someone with strong software engineering skills and ML expertise. Experience with MLOps, model deployment, and cloud platforms is essential.",
            "salary": "$130,000 - $170,000",
            "apply_url": "https://aisolutions.com/careers/ml-engineer",
            "source": "recruiter",
            "date_found": "2024-01-12",
            "requirements": [
                "4+ years ML engineering experience",
                "Strong Python and software engineering skills",
                "Experience with model deployment and MLOps",
                "Cloud platform experience (AWS, GCP, or Azure)",
                "Computer vision or NLP expertise preferred"
            ]
        }
    ],
    
    "entry_level": [
        {
            "title": "Junior Software Developer",
            "company": "GrowthTech",
            "location": "Chicago, IL",
            "description": "We're seeking a motivated Junior Software Developer to join our development team. This is an excellent opportunity for a recent graduate or career changer to gain experience building web applications. You'll work alongside senior developers on exciting projects using modern technologies. We're looking for someone with fundamental programming skills and eagerness to learn. Bootcamp graduates and self-taught developers are welcome to apply.",
            "salary": "$70,000 - $85,000",
            "apply_url": "https://growthtech.com/jobs/junior-developer",
            "source": "company_website",
            "date_found": "2024-01-14",
            "requirements": [
                "0-2 years professional development experience",
                "Fundamental programming skills in any language",
                "Understanding of web development concepts",
                "Strong problem-solving abilities",
                "Excellent communication and teamwork skills",
                "Bachelor's degree or bootcamp certification preferred"
            ]
        },
        {
            "title": "Frontend Developer - Entry Level",
            "company": "StartupCo",
            "location": "Remote",
            "description": "Join our fast-growing startup as an Entry Level Frontend Developer. You'll help build beautiful, responsive web applications using React and modern CSS. We're looking for someone passionate about user experience and frontend technologies. This role offers excellent growth opportunities and mentorship from senior developers. Portfolio of projects required.",
            "salary": "$65,000 - $80,000",
            "apply_url": "https://startupco.com/careers/frontend-dev",
            "source": "job_board",
            "date_found": "2024-01-13",
            "requirements": [
                "0-1 years professional frontend experience",
                "Proficiency in HTML, CSS, and JavaScript",
                "Experience with React or similar framework",
                "Portfolio demonstrating frontend projects",
                "Understanding of responsive design principles"
            ]
        }
    ]
}

# Mock API responses for different job search scenarios
MOCK_JOB_API_RESPONSES = {
    "successful_search": {
        "status_code": 200,
        "data": {
            "jobs": SAMPLE_JOB_LISTINGS["software_engineering"],
            "total_count": 150,
            "page": 1,
            "per_page": 10,
            "search_metadata": {
                "query": "software engineer python",
                "location": "United States",
                "date_posted": "last_7_days"
            }
        }
    },
    
    "no_results": {
        "status_code": 200,
        "data": {
            "jobs": [],
            "total_count": 0,
            "page": 1,
            "per_page": 10,
            "search_metadata": {
                "query": "very specific niche technology",
                "location": "Small Town, Nowhere"
            }
        }
    },
    
    "api_error": {
        "status_code": 500,
        "error": "Internal server error",
        "message": "Job search API temporarily unavailable"
    },
    
    "rate_limited": {
        "status_code": 429,
        "error": "Rate limit exceeded",
        "message": "Too many requests, please try again later",
        "retry_after": 3600
    }
}

# Job matching test data
JOB_MATCHING_SCENARIOS = {
    "high_match": {
        "resume_skills": ["Python", "React", "AWS", "Docker", "PostgreSQL"],
        "job_requirements": ["Python", "JavaScript", "AWS", "Docker", "SQL"],
        "expected_match_score": 0.85,
        "matching_skills": ["Python", "AWS", "Docker"],
        "missing_skills": ["JavaScript"],
        "explanation": "Strong match with 80% skill overlap and relevant experience level"
    },
    
    "medium_match": {
        "resume_skills": ["Python", "Django", "MySQL", "Linux"],
        "job_requirements": ["Python", "React", "PostgreSQL", "AWS"],
        "expected_match_score": 0.65,
        "matching_skills": ["Python"],
        "missing_skills": ["React", "PostgreSQL", "AWS"],
        "explanation": "Partial match with core language alignment but missing key technologies"
    },
    
    "low_match": {
        "resume_skills": ["Java", "Spring", "Oracle", "Maven"],
        "job_requirements": ["Python", "Django", "PostgreSQL", "Docker"],
        "expected_match_score": 0.25,
        "matching_skills": [],
        "missing_skills": ["Python", "Django", "PostgreSQL", "Docker"],
        "explanation": "Low match with different technology stack and programming language"
    }
}

# Market research test data
MARKET_RESEARCH_DATA = {
    "software_engineering": {
        "total_jobs": 1250,
        "avg_salary": "$110,000",
        "salary_range": "$65,000 - $180,000",
        "top_locations": [
            "San Francisco, CA", "Seattle, WA", "New York, NY", "Austin, TX", "Remote"
        ],
        "top_companies": [
            "Google", "Microsoft", "Amazon", "Apple", "Meta", "Netflix"
        ],
        "trending_skills": [
            "Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes"
        ],
        "growth_trend": "+15%",
        "demand_level": "High",
        "competition_level": "High",
        "recommendations": [
            "Strong demand for cloud and containerization skills",
            "Remote work opportunities increasing",
            "Full-stack development highly valued"
        ]
    },
    
    "data_science": {
        "total_jobs": 450,
        "avg_salary": "$135,000",
        "salary_range": "$90,000 - $210,000",
        "top_locations": [
            "San Francisco, CA", "Boston, MA", "Seattle, WA", "New York, NY"
        ],
        "top_companies": [
            "Google", "Microsoft", "Meta", "Netflix", "Uber", "Airbnb"
        ],
        "trending_skills": [
            "Python", "R", "TensorFlow", "PyTorch", "SQL", "AWS", "GCP"
        ],
        "growth_trend": "+22%",
        "demand_level": "Very High",
        "competition_level": "Very High",
        "recommendations": [
            "PhD or advanced degree strongly preferred",
            "MLOps and model deployment skills in high demand",
            "Domain expertise valuable (finance, healthcare, etc.)"
        ]
    }
}