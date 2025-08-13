#!/usr/bin/env python3
"""
Test the new 5-step agentic workflow with strategy generation as a tool
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from tools.strategy_creation import create_search_strategy
from tools.candidate_evaluation import evaluate_candidates_quality


def test_strategy_tool():
    """Test the strategy creation tool directly"""
    
    print("🧪 Testing Strategy Creation Tool")
    print("=" * 50)
    
    # Test strategy creation
    result = create_search_strategy(
        query="Senior Software Engineer",
        location="San Francisco"
    )
    
    if result["success"]:
        strategy = result["strategy"]
        print("✅ Strategy creation successful!")
        print(f"📊 Strategy components: {list(strategy.keys())}")
        
        # Check for evaluation criteria
        if "evaluation_criteria" in strategy:
            eval_criteria = strategy["evaluation_criteria"]
            print(f"🎯 Evaluation criteria found with: {list(eval_criteria.keys())}")
            
            # Check specific components
            if "technology_priorities" in eval_criteria:
                tech = eval_criteria["technology_priorities"]
                print(f"💻 Must-have tech: {tech.get('must_have', [])[:3]}")
            
            if "bonus_weights" in eval_criteria:
                weights = eval_criteria["bonus_weights"]
                print(f"⚖️  Bonus multipliers: {list(weights.keys())[:3]}")
        
        return strategy
    else:
        print("❌ Strategy creation failed")
        return None


def test_evaluation_with_strategy():
    """Test evaluation tool with strategy parameter"""
    
    print("\n🧪 Testing Evaluation with Strategy Parameter")
    print("=" * 50)
    
    # Create strategy first
    strategy_result = create_search_strategy("Senior Software Engineer", "San Francisco")
    if not strategy_result["success"]:
        print("❌ Cannot test evaluation - strategy creation failed")
        return False
    
    strategy = strategy_result["strategy"]
    
    # Test candidates with full profiles
    test_candidates = [
        {
            "name": "Alice Johnson",
            "headline": "Senior Software Engineer at Google | Python, React, AWS",
            "url": "https://linkedin.com/in/alice",
            "profile_data": {
                "name": "Alice Johnson",
                "headline": "Senior Software Engineer at Google | Python, React, AWS",
                "about": "Experienced software engineer with 6 years building scalable systems...",
                "experiences": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Google",
                        "start_date": "2021",
                        "end_date": "Present",
                        "bullets": ["Built microservices with Python", "Led team of 4 developers"]
                    }
                ],
                "education": [
                    {
                        "degree": "Bachelor of Science in Computer Science",
                        "school": "Stanford University",
                        "year": "2017"
                    }
                ],
                "skills": ["Python", "React", "AWS", "Docker", "Leadership"]
            }
        }
    ]
    
    # Test evaluation with strategy
    evaluation_result = evaluate_candidates_quality(
        candidates=test_candidates,
        strategy=strategy,
        min_quality_threshold=6.0,
        target_count=1
    )
    
    if evaluation_result.get("success"):
        candidate = evaluation_result["all_evaluated_candidates"][0]
        score = candidate["overall_score"]
        bonuses = candidate.get("strategic_bonuses", {})
        total_bonus = sum(bonuses.values())
        
        print(f"✅ Evaluation successful!")
        print(f"📊 Alice scored: {score}/10.0")
        print(f"🎆 Strategic bonuses: +{total_bonus:.2f}")
        print(f"⚖️  Strategy impact: Significant bonuses applied")
        
        # Validation
        if score > 7.0 and total_bonus > 3.0:
            print("✅ Strategy-driven evaluation working correctly!")
            return True
        else:
            print(f"⚠️  Scores lower than expected - may need tuning")
            return False
    else:
        print(f"❌ Evaluation failed: {evaluation_result.get('error')}")
        return False


def test_agentic_data_flow():
    """Test how data flows between tools in agentic workflow"""
    
    print("\n🧪 Testing Agentic Data Flow")
    print("=" * 50)
    
    print("🔄 Simulating agent workflow:")
    
    # Step 1: Strategy creation
    print("1. 🎯 create_search_strategy(query='Senior Engineer', location='SF')")
    strategy_data = create_search_strategy("Senior Engineer", "SF")
    
    if strategy_data["success"]:
        print("   ✅ Strategy created successfully")
        strategy = strategy_data["strategy"]
        
        # Step 2: Mock extraction results (would come from extract_candidate_profiles)
        print("2. 📥 extract_candidate_profiles() → extracted_data")
        extracted_data = {
            "success": True,
            "results": [
                {
                    "candidate_info": {"name": "Bob Smith", "url": "https://linkedin.com/in/bob"},
                    "profile_data": {
                        "name": "Bob Smith",
                        "headline": "Senior Engineer at Netflix",
                        "experiences": [
                            {"title": "Senior Engineer", "company": "Netflix", "bullets": ["Python development"]}
                        ],
                        "skills": ["Python", "JavaScript", "AWS"]
                    }
                }
            ]
        }
        print("   ✅ Extraction results ready")
        
        # Step 3: Evaluation with strategy
        print("3. 🎯 evaluate_candidates_quality(candidates=extracted_data['results'], strategy=strategy_data['strategy'])")
        evaluation_result = evaluate_candidates_quality(
            candidates=extracted_data["results"],
            strategy=strategy,
            min_quality_threshold=6.0
        )
        
        if evaluation_result.get("success"):
            print("   ✅ Evaluation completed with strategy")
            candidate = evaluation_result["all_evaluated_candidates"][0]
            print(f"   📊 Score: {candidate['overall_score']}/10.0")
            
            # Check strategic bonuses
            bonuses = candidate.get("strategic_bonuses", {})
            if bonuses:
                total_bonus = sum(bonuses.values())
                print(f"   🎆 Strategic bonuses: +{total_bonus:.2f}")
                print("   ✅ Strategy successfully passed between tools!")
                return True
            else:
                print("   ⚠️  No strategic bonuses - strategy may not be applied")
                return False
        else:
            print(f"   ❌ Evaluation failed: {evaluation_result.get('error')}")
            return False
    else:
        print("   ❌ Strategy creation failed")
        return False


def main():
    """Run all tests"""
    
    print("🚀 TESTING NEW AGENTIC WORKFLOW SYSTEM")
    print("=" * 60)
    
    results = []
    
    # Test 1: Strategy tool
    try:
        strategy = test_strategy_tool()
        results.append(("Strategy Tool", strategy is not None))
    except Exception as e:
        print(f"❌ Strategy tool test failed: {e}")
        results.append(("Strategy Tool", False))
    
    # Test 2: Evaluation with strategy
    try:
        eval_success = test_evaluation_with_strategy()
        results.append(("Evaluation with Strategy", eval_success))
    except Exception as e:
        print(f"❌ Evaluation test failed: {e}")
        results.append(("Evaluation with Strategy", False))
    
    # Test 3: Data flow simulation
    try:
        flow_success = test_agentic_data_flow()
        results.append(("Agentic Data Flow", flow_success))
    except Exception as e:
        print(f"❌ Data flow test failed: {e}")
        results.append(("Agentic Data Flow", False))
    
    # Summary
    print(f"\n📋 TEST RESULTS:")
    print("=" * 30)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 OVERALL: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! Agentic workflow ready for production!")
        print("\n🔄 Ready for agent execution:")
        print("1. create_search_strategy() → strategy_data")
        print("2. smart_candidate_search(strategy=strategy_data['strategy']) → search_results")  
        print("3. extract_candidate_profiles() → extracted_data")
        print("4. evaluate_candidates_quality(candidates=extracted_data['results'], strategy=strategy_data['strategy']) → evaluation")
        print("5. generate_candidate_outreach() → outreach_messages")
    else:
        print("⚠️  Some tests failed - check implementation before production")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()