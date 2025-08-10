"""
Sample resume data for testing
"""

SAMPLE_RESUMES = {
    "software_engineer_senior": {
        "content": """
John Smith
Senior Software Engineer
john.smith@email.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johnsmith

PROFESSIONAL SUMMARY
Senior Software Engineer with 7+ years of experience developing scalable web applications and microservices. 
Expert in Python, JavaScript, and cloud technologies. Proven track record of leading technical teams and 
delivering high-quality software solutions in fast-paced environments.

EXPERIENCE

Senior Software Engineer | TechCorp Inc | 2020 - Present
• Led development of microservices architecture serving 2M+ users daily
• Improved system performance by 40% through optimization and caching strategies  
• Mentored team of 5 junior developers and established code review processes
• Technologies: Python, React, AWS, Docker, Kubernetes, PostgreSQL

Software Engineer | StartupCo | 2018 - 2020
• Built full-stack web applications using Django and React
• Implemented CI/CD pipelines reducing deployment time by 60%
• Collaborated with product team to deliver 15+ feature releases
• Technologies: Python, Django, React, MySQL, Jenkins

Junior Developer | DevSolutions | 2017 - 2018
• Developed REST APIs and frontend components for e-commerce platform
• Participated in agile development process and daily standups
• Maintained 95%+ test coverage across all projects
• Technologies: Python, Flask, JavaScript, SQLite

SKILLS
Programming Languages: Python, JavaScript, TypeScript, SQL
Frameworks: Django, React, Flask, Node.js
Cloud & DevOps: AWS, Docker, Kubernetes, Jenkins, GitHub Actions
Databases: PostgreSQL, MySQL, Redis, MongoDB

EDUCATION
Bachelor of Science in Computer Science
University of Technology | 2017
        """,
        "expected_analysis": {
            "overall_score": 85,
            "strengths": [
                "Strong technical background with 7+ years experience",
                "Leadership experience mentoring team members", 
                "Quantified achievements with specific metrics",
                "Modern technology stack including cloud and DevOps",
                "Clear career progression from junior to senior role"
            ],
            "weaknesses": [
                "Could benefit from more diverse industry experience",
                "Missing some trending technologies like AI/ML",
                "Professional summary could be more compelling"
            ],
            "ats_compatibility": 82
        },
        "target_roles": ["Senior Software Engineer", "Lead Developer", "Technical Lead"],
        "expected_salary_range": "$120,000 - $160,000"
    },
    
    "recent_graduate": {
        "content": """
Sarah Johnson
Software Developer
sarah.johnson@email.com | (555) 987-6543

EDUCATION
Bachelor of Science in Computer Science
State University | May 2023
GPA: 3.7/4.0
Relevant Coursework: Data Structures, Algorithms, Database Systems, Web Development

PROJECTS
E-commerce Web Application (Capstone Project)
• Built full-stack e-commerce platform using React and Node.js
• Implemented user authentication, shopping cart, and payment processing
• Technologies: React, Node.js, Express, MongoDB

Task Management App
• Developed responsive web application for project management
• Features include task creation, assignment, and progress tracking
• Technologies: Vue.js, Python Flask, SQLite

INTERNSHIP EXPERIENCE
Software Development Intern | LocalTech | Summer 2022
• Assisted senior developers with bug fixes and feature implementation
• Participated in code reviews and agile development processes
• Learned version control with Git and collaborative development

SKILLS
Programming Languages: Python, JavaScript, Java, SQL
Web Technologies: HTML, CSS, React, Vue.js, Node.js
Tools: Git, VS Code, Docker basics

CERTIFICATIONS
AWS Cloud Practitioner (In Progress)
        """,
        "expected_analysis": {
            "overall_score": 62,
            "strengths": [
                "Strong educational background with good GPA",
                "Relevant project experience demonstrating practical skills",
                "Modern web development technologies",
                "Shows initiative with AWS certification pursuit"
            ],
            "weaknesses": [
                "Limited professional work experience",
                "Missing industry-standard tools and frameworks", 
                "Needs more quantified achievements",
                "Professional summary section missing"
            ],
            "ats_compatibility": 58
        },
        "target_roles": ["Junior Software Developer", "Frontend Developer", "Entry Level Engineer"],
        "expected_salary_range": "$65,000 - $85,000"
    },
    
    "career_changer": {
        "content": """
Michael Chen
Full Stack Developer
michael.chen@email.com | (555) 555-0123

PROFESSIONAL SUMMARY
Former financial analyst transitioning to software development with intensive coding bootcamp training 
and self-directed learning. Combining analytical skills from finance background with new technical 
expertise in modern web development.

TECHNICAL PROJECTS
Personal Finance Tracker
• Built web application to help users track expenses and investments
• Implemented data visualization using Chart.js and D3.js
• Technologies: React, Node.js, Express, PostgreSQL, Chart.js

Restaurant Management System
• Developed full-stack application for restaurant order management
• Features include menu management, order tracking, and reporting
• Technologies: Python, Django, React, MySQL

EDUCATION & TRAINING
Full Stack Web Development Bootcamp | Code Academy | 2023
600+ hours intensive training in web development fundamentals

Bachelor of Science in Finance | Business University | 2018

RELEVANT EXPERIENCE
Financial Analyst | Investment Firm | 2018 - 2023
• Analyzed financial data and created detailed reports for clients
• Developed Excel macros and automated reporting processes
• Strong analytical and problem-solving skills
• Experience with data analysis and visualization

TECHNICAL SKILLS
Programming: JavaScript, Python, HTML, CSS, SQL
Frameworks: React, Django, Node.js, Express
Databases: PostgreSQL, MySQL
Tools: Git, Docker, Postman

TRANSFERABLE SKILLS
• Strong analytical and problem-solving abilities
• Experience with data analysis and reporting
• Client communication and presentation skills
• Project management and deadline-driven work
        """,
        "expected_analysis": {
            "overall_score": 68,
            "strengths": [
                "Strong analytical background transferable to development",
                "Intensive bootcamp training showing commitment",
                "Good project portfolio demonstrating skills",
                "Quantified previous work experience"
            ],
            "weaknesses": [
                "Limited professional software development experience",
                "Need to better connect finance background to tech skills",
                "Missing some modern development tools and practices",
                "Could benefit from more complex technical projects"
            ],
            "ats_compatibility": 65
        },
        "target_roles": ["Junior Full Stack Developer", "Frontend Developer", "Software Developer"],
        "expected_salary_range": "$75,000 - $95,000"
    }
}

PROBLEMATIC_RESUMES = {
    "poorly_formatted": {
        "content": """
bob smith
email: bobsmith@email.com
phone number is 555-1234

work history:
worked at company A for 2 years did some programming
then worked at company B for 1 year more programming stuff
currently looking for new job

skills: python javascript html css and other things

education: graduated from college in 2019
        """,
        "expected_issues": [
            "Poor formatting and structure",
            "No quantified achievements",
            "Vague job descriptions", 
            "Missing professional summary",
            "Inconsistent formatting",
            "No contact information header"
        ]
    },
    
    "missing_key_sections": {
        "content": """
Jane Doe
Software Developer

I have been working in software development for several years and have experience 
with various programming languages and technologies. I am looking for a new 
opportunity to grow my career.

Some of the things I have worked with include:
- Programming languages
- Web development
- Database systems
- Team collaboration
        """,
        "expected_issues": [
            "Missing contact information",
            "No specific work experience section",
            "Vague skill descriptions",
            "No quantified achievements",
            "Missing education section",
            "No dates or timeline information"
        ]
    }
}

RESUME_VARIATIONS_BY_INDUSTRY = {
    "data_science": {
        "content": """
Dr. Lisa Wong
Senior Data Scientist
lisa.wong@email.com | (555) 234-5678

PROFESSIONAL SUMMARY
PhD-level Data Scientist with 5+ years of experience in machine learning, statistical analysis, and 
data visualization. Expert in Python, R, and cloud-based ML platforms. Proven track record of 
delivering actionable insights that drive business decisions and revenue growth.

EXPERIENCE

Senior Data Scientist | DataTech Corp | 2021 - Present
• Built machine learning models improving customer retention by 25%
• Led cross-functional team of 8 analysts on predictive analytics projects
• Deployed models to production serving 10M+ daily predictions
• Technologies: Python, TensorFlow, AWS SageMaker, Apache Spark

Data Scientist | Analytics Inc | 2019 - 2021
• Developed recommendation systems increasing user engagement by 30%
• Performed A/B testing and statistical analysis for product features
• Created data pipelines processing 100GB+ daily data volumes
• Technologies: Python, scikit-learn, PostgreSQL, Airflow

EDUCATION
PhD in Statistics | Research University | 2019
MS in Mathematics | State University | 2016

SKILLS
Programming: Python, R, SQL, Scala
ML/AI: TensorFlow, PyTorch, scikit-learn, XGBoost
Cloud: AWS, GCP, Azure
Databases: PostgreSQL, MongoDB, Snowflake
        """,
        "target_roles": ["Senior Data Scientist", "ML Engineer", "Principal Data Scientist"]
    },
    
    "devops_engineer": {
        "content": """
Alex Rodriguez
DevOps Engineer
alex.rodriguez@email.com | (555) 345-6789

PROFESSIONAL SUMMARY
DevOps Engineer with 6+ years of experience in cloud infrastructure, automation, and CI/CD. 
Expert in AWS, Kubernetes, and Infrastructure as Code. Passionate about building scalable, 
reliable systems and improving development workflows.

EXPERIENCE

Senior DevOps Engineer | CloudFirst | 2020 - Present
• Managed AWS infrastructure serving 50M+ requests daily
• Reduced deployment time from 2 hours to 15 minutes with automated CI/CD
• Implemented monitoring and alerting reducing incident response time by 60%
• Technologies: AWS, Kubernetes, Terraform, Jenkins, Prometheus

DevOps Engineer | StartupScale | 2018 - 2020
• Built container orchestration platform using Docker and Kubernetes
• Automated infrastructure provisioning saving 20+ hours weekly
• Maintained 99.9% uptime across all production services
• Technologies: Docker, Kubernetes, AWS, Ansible, GitLab CI

SKILLS
Cloud Platforms: AWS, GCP, Azure
Container Orchestration: Kubernetes, Docker, ECS
Infrastructure as Code: Terraform, CloudFormation, Ansible
CI/CD: Jenkins, GitLab CI, GitHub Actions
Monitoring: Prometheus, Grafana, ELK Stack
        """,
        "target_roles": ["Senior DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer"]
    }
}