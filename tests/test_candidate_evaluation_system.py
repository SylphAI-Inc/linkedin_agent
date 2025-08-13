#!/usr/bin/env python3
"""
Test the enhanced CandidateEvaluationTool with strategic bonuses and strategy-driven scoring
"""

import json
from tools.candidate_evaluation import evaluate_candidates_quality


def test_strategic_evaluation_system():
    """Test the complete strategic evaluation system"""
    
    print("🧪 Testing Enhanced Candidate Evaluation System")
    print("=" * 60)
    
    # 1. Create a realistic strategy (similar to what StrategyGenerator would create)
    test_strategy = {
        "headline_analysis": {
            "target_job_titles": ["Senior Software Engineer", "Staff Engineer", "Backend Engineer"],
            "alternative_titles": ["Full Stack Developer", "Software Developer", "Backend Developer"],
            "seniority_keywords": ["senior", "staff", "lead", "principal"],
            "company_indicators": ["google", "facebook", "netflix", "uber", "stripe"],
            "tech_stack_signals": ["python", "javascript", "react", "docker", "kubernetes", "aws", "postgresql"]
        },
        "profile_evaluation_context": {
            "focus_areas": ["Technical skills and tech stack", "Work experience and project impact", "Leadership and mentoring"],
            "quality_indicators": ["relevant experience", "top-tier companies", "technical depth"],
            "ideal_candidate_description": "Senior Software Engineer with full-stack experience at top tech companies"
        },
        "search_filtering": {
            "minimum_headline_score": 6.0,
            "negative_headline_patterns": ["intern", "student", "entry level"]
        },
        "original_query": "Senior Software Engineer"
    }
    
    # 2. Create test candidates with varying strategic alignment
    test_candidates = [
        {
            # High strategic alignment candidate
            "name": "Alex Chen",
            "headline": "Senior Software Engineer at Google | Full-stack developer specializing in Python & React",
            "url": "https://linkedin.com/in/alexchen",
            "profile_data": {
                "name": "Alex Chen",
                "headline": "Senior Software Engineer at Google | Full-stack developer specializing in Python & React",
                "location": "San Francisco, CA",
                "about": "Passionate full-stack engineer with 6 years of experience building scalable web applications. Led multiple cross-functional teams and mentored junior developers. Expert in Python, React, and cloud architectures.",
                "experiences": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Google",
                        "start_date": "2021",
                        "end_date": "Present",
                        "bullets": ["Led development of user analytics platform serving 100M+ users", "Implemented microservices architecture using Python and Kubernetes", "Mentored 5 junior engineers"]
                    },
                    {
                        "title": "Software Engineer",
                        "company": "Netflix",
                        "start_date": "2019",
                        "end_date": "2021",
                        "bullets": ["Built recommendation engine backend using Python and PostgreSQL", "Implemented CI/CD pipelines with Docker"]
                    },
                    {
                        "title": "Junior Software Developer",
                        "company": "Startup Inc",
                        "start_date": "2017",
                        "end_date": "2019",
                        "bullets": ["Developed React frontend applications", "Collaborated with design team"]
                    }
                ],
                "education": [
                    {
                        "degree": "Bachelor of Science in Computer Science",
                        "school": "Stanford University",
                        "year": "2017"
                    }
                ],
                "skills": ["Python", "JavaScript", "React", "Node.js", "PostgreSQL", "Docker", "Kubernetes", "AWS", "System Design", "Leadership", "Microservices", "REST APIs", "GraphQL"]
            }
        },
        {
            # Medium strategic alignment candidate
            "name": "Jordan Smith",
            "headline": "Full Stack Developer at Startup | React & Node.js enthusiast",
            "url": "https://linkedin.com/in/jordansmith",
            "profile_data": {
                "name": "Jordan Smith",
                "headline": "Full Stack Developer at Startup | React & Node.js enthusiast",
                "location": "Austin, TX",
                "about": "Full-stack developer with 4 years of experience in web development. Enjoy working with modern JavaScript frameworks and building user-friendly applications.",
                "experiences": [
                    {
                        "title": "Full Stack Developer",
                        "company": "TechStartup",
                        "start_date": "2020",
                        "end_date": "Present",
                        "bullets": ["Built e-commerce platform using React and Node.js", "Implemented user authentication and payment systems"]
                    },
                    {
                        "title": "Frontend Developer",
                        "company": "WebAgency",
                        "start_date": "2018",
                        "end_date": "2020",
                        "bullets": ["Developed responsive websites using React and CSS", "Collaborated with UX designers"]
                    }
                ],
                "education": [
                    {
                        "degree": "Bachelor of Arts in Computer Science",
                        "school": "University of Texas at Austin",
                        "year": "2018"
                    }
                ],
                "skills": ["JavaScript", "React", "Node.js", "HTML", "CSS", "MongoDB", "Git", "Agile"]
            }
        },
        {
            # Lower strategic alignment candidate
            "name": "Casey Johnson",
            "headline": "Software Developer | Java & Spring Boot",
            "url": "https://linkedin.com/in/caseyjohnson",
            "profile_data": {
                "name": "Casey Johnson",
                "headline": "Software Developer | Java & Spring Boot",
                "location": "Denver, CO",
                "about": "Software developer focused on backend systems using Java technologies.",
                "experiences": [
                    {
                        "title": "Software Developer",
                        "company": "Enterprise Corp",
                        "start_date": "2020",
                        "end_date": "Present",
                        "bullets": ["Maintained legacy Java applications", "Fixed bugs and implemented small features"]
                    }
                ],
                "education": [
                    {
                        "degree": "Bachelor of Science in Information Technology",
                        "school": "Community College",
                        "year": "2019"
                    }
                ],
                "skills": ["Java", "Spring Boot", "MySQL", "Git"]
            }
        }
    ]
    
    # 3. Test the evaluation system
    print(f"📊 Testing evaluation with {len(test_candidates)} candidates...")
    print(f"🎯 Strategy focus: {test_strategy['original_query']}")
    print(f"🏢 Target companies: {', '.join(test_strategy['headline_analysis']['company_indicators'])}")
    print(f"⚙️  Key technologies: {', '.join(test_strategy['headline_analysis']['tech_stack_signals'][:5])}")
    print()
    
    # Run the evaluation
    evaluation_results = evaluate_candidates_quality(
        candidates=test_candidates,
        strategy=test_strategy,
        min_quality_threshold=6.0,
        target_count=2
    )
    
    # 4. Analyze and display results
    if evaluation_results.get("success"):
        print("✅ EVALUATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        print(f"📈 Quality Statistics:")
        stats = evaluation_results["quality_stats"]
        print(f"   Average Score: {stats['average_score']}")
        print(f"   Score Range: {stats['min_score']} - {stats['max_score']}")
        print(f"   Above Threshold: {stats['above_threshold']}/{evaluation_results['candidates_evaluated']}")
        print(f"   Quality Sufficient: {'✅ Yes' if evaluation_results['quality_sufficient'] else '❌ No'}")
        print()
        
        print(f"🎯 Strategic Evaluation Results:")
        print("-" * 40)
        
        # Display detailed results for each candidate
        for candidate in evaluation_results["all_evaluated_candidates"]:
            print(f"\n👤 {candidate['name']}")
            print(f"   Overall Score: {candidate['overall_score']}/10.0")
            print(f"   Meets Threshold: {'✅' if candidate['meets_threshold'] else '❌'}")
            
            # Component scores
            print(f"   Component Scores:")
            for component, score in candidate["component_scores"].items():
                print(f"     • {component.replace('_', ' ').title()}: {score}/10.0")
            
            # Strategic bonuses
            if "strategic_bonuses" in candidate:
                print(f"   Strategic Bonuses:")
                for bonus_type, bonus_value in candidate["strategic_bonuses"].items():
                    if bonus_value > 0:
                        print(f"     • {bonus_type.replace('_', ' ').title()}: +{bonus_value}")
            
            # Final multiplier
            if "final_multiplier" in candidate:
                multiplier_pct = (candidate["final_multiplier"] - 1.0) * 100
                if multiplier_pct > 0:
                    print(f"   Strategic Multiplier: +{multiplier_pct:.1f}%")
            
            # Strengths and concerns
            if candidate.get("strengths"):
                print(f"   Strengths: {', '.join(candidate['strengths'])}")
            if candidate.get("concerns"):
                print(f"   Concerns: {', '.join(candidate['concerns'])}")
        
        print(f"\n🔄 Fallback Recommendation:")
        print(f"   Action: {evaluation_results['fallback_recommendation']}")
        print(f"   Reasoning: {evaluation_results['fallback_reasoning']}")
        
        # 5. Validate results make sense
        print(f"\n🧪 VALIDATION CHECKS:")
        print("-" * 30)
        
        candidates = evaluation_results["all_evaluated_candidates"]
        
        # Check that strategic alignment affects scores
        alex_score = next(c["overall_score"] for c in candidates if c["name"] == "Alex Chen")
        jordan_score = next(c["overall_score"] for c in candidates if c["name"] == "Jordan Smith") 
        casey_score = next(c["overall_score"] for c in candidates if c["name"] == "Casey Johnson")
        
        print(f"✅ Score ordering check: Alex({alex_score}) > Jordan({jordan_score}) > Casey({casey_score})")
        assert alex_score > jordan_score > casey_score, "Strategic alignment should affect score ordering"
        
        # Check bonuses are being applied
        alex_bonuses = next(c.get("strategic_bonuses", {}) for c in candidates if c["name"] == "Alex Chen")
        alex_total_bonuses = sum(alex_bonuses.values()) if alex_bonuses else 0
        
        print(f"✅ Strategic bonuses check: Alex received {alex_total_bonuses:.1f} total bonus points")
        assert alex_total_bonuses > 5.0, "High alignment candidate should receive significant bonuses"
        
        # Check weights are dynamic
        if candidates[0].get("scoring_weights"):
            weights = candidates[0]["scoring_weights"]
            print(f"✅ Dynamic weights check: Experience={weights['experience_quality']:.2f}, Skills={weights['skills_relevance']:.2f}")
        
        print(f"\n🎉 ALL VALIDATION CHECKS PASSED!")
        
        return True
        
    else:
        print(f"❌ EVALUATION FAILED: {evaluation_results.get('error', 'Unknown error')}")
        return False


if __name__ == "__main__":
    success = test_strategic_evaluation_system()
    if success:
        print(f"\n✅ Enhanced Candidate Evaluation System is working correctly!")
    else:
        print(f"\n❌ Test failed - check the evaluation system!")