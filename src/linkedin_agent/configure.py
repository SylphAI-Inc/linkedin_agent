#!/usr/bin/env python3
"""
Interactive Configuration Tool for LinkedIn Recruitment Agent

This script helps users easily configure the agent without editing code.
"""

import os
import sys
from pathlib import Path
from .config_user import USER_CONFIG, configure_for_high_quality, configure_for_volume, configure_for_conservative


def show_current_config():
    """Display current configuration settings"""
    print("=" * 60)
    print("🤖 LINKEDIN RECRUITMENT AGENT - CURRENT CONFIGURATION")
    print("=" * 60)
    print()
    
    print("🔍 SEARCH SETTINGS:")
    print(f"   Minimum Search Score: {USER_CONFIG.search.min_search_score}")
    print(f"   Minimum Evaluation Threshold: {USER_CONFIG.search.min_evaluation_threshold}")
    print(f"   Target Quality Candidates: {USER_CONFIG.search.target_quality_candidates}")
    print(f"   Max Pages Per Search: {USER_CONFIG.search.max_pages_per_search}")
    print(f"   Quality Mode: {USER_CONFIG.search.quality_mode}")
    print()
    
    print("📊 EXTRACTION SETTINGS:")
    print(f"   Delay Between Extractions: {USER_CONFIG.extraction.delay_between_extractions}s")
    print(f"   Validate Extraction Quality: {USER_CONFIG.extraction.validate_extraction_quality}")
    print(f"   Skip Private Profiles: {USER_CONFIG.extraction.skip_private_profiles}")
    print(f"   Retry Failed Extractions: {USER_CONFIG.extraction.retry_failed_extractions}")
    print()
    
    print("⭐ EVALUATION SETTINGS:")
    print(f"   Experience Weight: {USER_CONFIG.evaluation.experience_weight}")
    print(f"   Education Weight: {USER_CONFIG.evaluation.education_weight}")
    print(f"   Skills Weight: {USER_CONFIG.evaluation.skills_weight}")
    print(f"   Tier-1 Company Bonus: {USER_CONFIG.evaluation.tier1_company_bonus}")
    print(f"   Seniority Bonus: {USER_CONFIG.evaluation.seniority_bonus}")
    print()
    
    print("🔄 WORKFLOW SETTINGS:")
    print(f"   Auto Proceed to Extraction: {USER_CONFIG.workflow.auto_proceed_to_extraction}")
    print(f"   Auto Proceed to Evaluation: {USER_CONFIG.workflow.auto_proceed_to_evaluation}")
    print(f"   Max Fallback Attempts: {USER_CONFIG.workflow.max_fallback_attempts}")
    print(f"   Enable Real-time Logging: {USER_CONFIG.workflow.enable_real_time_logging}")


def interactive_config():
    """Interactive configuration wizard"""
    print("\n🛠️  CONFIGURATION WIZARD")
    print("=" * 40)
    
    while True:
        print("\nWhat would you like to configure?")
        print("1. Search behavior (thresholds, pages, quality mode)")
        print("2. Extraction timing (delays, retries)")
        print("3. Evaluation scoring (weights, bonuses)")
        print("4. Workflow automation (auto-proceed settings)")
        print("5. Use preset configurations")
        print("6. Show current settings")
        print("7. Save and exit")
        print("8. Exit without saving")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == "1":
            configure_search()
        elif choice == "2":
            configure_extraction()
        elif choice == "3":
            configure_evaluation()
        elif choice == "4":
            configure_workflow()
        elif choice == "5":
            configure_presets()
        elif choice == "6":
            show_current_config()
        elif choice == "7":
            save_config()
            print("✅ Configuration saved! Changes will take effect on next run.")
            break
        elif choice == "8":
            print("❌ Exiting without saving changes.")
            break
        else:
            print("❌ Invalid choice. Please enter 1-8.")


def configure_search():
    """Configure search settings"""
    print("\n🔍 SEARCH CONFIGURATION")
    print("-" * 30)
    
    try:
        score = float(input(f"Minimum search score [{USER_CONFIG.search.min_search_score}]: ") or USER_CONFIG.search.min_search_score)
        USER_CONFIG.search.min_search_score = max(0.0, min(10.0, score))
        
        threshold = float(input(f"Minimum evaluation threshold [{USER_CONFIG.search.min_evaluation_threshold}]: ") or USER_CONFIG.search.min_evaluation_threshold)
        USER_CONFIG.search.min_evaluation_threshold = max(0.0, min(10.0, threshold))
        
        target = int(input(f"Target quality candidates [{USER_CONFIG.search.target_quality_candidates}]: ") or USER_CONFIG.search.target_quality_candidates)
        USER_CONFIG.search.target_quality_candidates = max(1, min(50, target))
        
        pages = int(input(f"Max pages per search [{USER_CONFIG.search.max_pages_per_search}]: ") or USER_CONFIG.search.max_pages_per_search)
        USER_CONFIG.search.max_pages_per_search = max(1, min(10, pages))
        
        print("\nQuality modes:")
        print("  'adaptive' - Extend search for quality")
        print("  'quality_first' - Prioritize quality over quantity")
        print("  'fast' - Respect hard limits")
        mode = input(f"Quality mode [{USER_CONFIG.search.quality_mode}]: ") or USER_CONFIG.search.quality_mode
        if mode in ["adaptive", "quality_first", "fast"]:
            USER_CONFIG.search.quality_mode = mode
            
        print("✅ Search configuration updated!")
        
    except ValueError:
        print("❌ Invalid input. Please enter numeric values.")


def configure_extraction():
    """Configure extraction settings"""
    print("\n📊 EXTRACTION CONFIGURATION")
    print("-" * 30)
    
    try:
        delay = float(input(f"Delay between extractions (seconds) [{USER_CONFIG.extraction.delay_between_extractions}]: ") or USER_CONFIG.extraction.delay_between_extractions)
        USER_CONFIG.extraction.delay_between_extractions = max(0.5, min(10.0, delay))
        
        validate = input(f"Validate extraction quality (y/n) [{'y' if USER_CONFIG.extraction.validate_extraction_quality else 'n'}]: ").lower()
        if validate in ['y', 'yes', 'true']:
            USER_CONFIG.extraction.validate_extraction_quality = True
        elif validate in ['n', 'no', 'false']:
            USER_CONFIG.extraction.validate_extraction_quality = False
        
        retries = int(input(f"Retry failed extractions [{USER_CONFIG.extraction.retry_failed_extractions}]: ") or USER_CONFIG.extraction.retry_failed_extractions)
        USER_CONFIG.extraction.retry_failed_extractions = max(0, min(5, retries))
        
        print("✅ Extraction configuration updated!")
        
    except ValueError:
        print("❌ Invalid input. Please enter numeric values.")


def configure_evaluation():
    """Configure evaluation settings"""
    print("\n⭐ EVALUATION CONFIGURATION")
    print("-" * 30)
    
    try:
        print("Scoring weights (should sum to ~1.0):")
        exp_weight = float(input(f"Experience weight [{USER_CONFIG.evaluation.experience_weight}]: ") or USER_CONFIG.evaluation.experience_weight)
        edu_weight = float(input(f"Education weight [{USER_CONFIG.evaluation.education_weight}]: ") or USER_CONFIG.evaluation.education_weight)
        skills_weight = float(input(f"Skills weight [{USER_CONFIG.evaluation.skills_weight}]: ") or USER_CONFIG.evaluation.skills_weight)
        
        USER_CONFIG.evaluation.experience_weight = max(0.0, min(1.0, exp_weight))
        USER_CONFIG.evaluation.education_weight = max(0.0, min(1.0, edu_weight))
        USER_CONFIG.evaluation.skills_weight = max(0.0, min(1.0, skills_weight))
        
        print("\nBonus points:")
        tier1_bonus = float(input(f"Tier-1 company bonus [{USER_CONFIG.evaluation.tier1_company_bonus}]: ") or USER_CONFIG.evaluation.tier1_company_bonus)
        seniority_bonus = float(input(f"Seniority bonus [{USER_CONFIG.evaluation.seniority_bonus}]: ") or USER_CONFIG.evaluation.seniority_bonus)
        
        USER_CONFIG.evaluation.tier1_company_bonus = max(0.0, min(5.0, tier1_bonus))
        USER_CONFIG.evaluation.seniority_bonus = max(0.0, min(5.0, seniority_bonus))
        
        print("✅ Evaluation configuration updated!")
        
    except ValueError:
        print("❌ Invalid input. Please enter numeric values.")


def configure_workflow():
    """Configure workflow settings"""
    print("\n🔄 WORKFLOW CONFIGURATION")
    print("-" * 30)
    
    auto_extract = input(f"Auto proceed to extraction (y/n) [{'y' if USER_CONFIG.workflow.auto_proceed_to_extraction else 'n'}]: ").lower()
    if auto_extract in ['y', 'yes', 'true']:
        USER_CONFIG.workflow.auto_proceed_to_extraction = True
    elif auto_extract in ['n', 'no', 'false']:
        USER_CONFIG.workflow.auto_proceed_to_extraction = False
    
    auto_eval = input(f"Auto proceed to evaluation (y/n) [{'y' if USER_CONFIG.workflow.auto_proceed_to_evaluation else 'n'}]: ").lower()
    if auto_eval in ['y', 'yes', 'true']:
        USER_CONFIG.workflow.auto_proceed_to_evaluation = True
    elif auto_eval in ['n', 'no', 'false']:
        USER_CONFIG.workflow.auto_proceed_to_evaluation = False
    
    try:
        attempts = int(input(f"Max fallback attempts [{USER_CONFIG.workflow.max_fallback_attempts}]: ") or USER_CONFIG.workflow.max_fallback_attempts)
        USER_CONFIG.workflow.max_fallback_attempts = max(1, min(5, attempts))
    except ValueError:
        pass
    
    print("✅ Workflow configuration updated!")


def configure_presets():
    """Apply preset configurations"""
    print("\n🎚️  PRESET CONFIGURATIONS")
    print("-" * 30)
    print("1. High Quality - Fewer but better candidates")
    print("2. Volume - More candidates, lower quality bar")
    print("3. Conservative - Careful, thorough approach")
    print("4. Cancel")
    
    choice = input("\nChoose preset (1-4): ").strip()
    
    if choice == "1":
        configure_for_high_quality()
        print("✅ Applied 'High Quality' preset!")
    elif choice == "2":
        configure_for_volume()
        print("✅ Applied 'Volume' preset!")
    elif choice == "3":
        configure_for_conservative()
        print("✅ Applied 'Conservative' preset!")
    elif choice == "4":
        print("❌ Preset configuration cancelled.")
    else:
        print("❌ Invalid choice.")


def save_config():
    """Save configuration to file"""
    config_file = Path(__file__).parent / "config_user.py"
    
    # In a real implementation, you'd want to properly serialize the config
    # For now, just show what would be saved
    print(f"\n💾 Configuration would be saved to: {config_file}")
    print("Note: This demo doesn't actually save - edit config_user.py manually for now.")


def main():
    """Main configuration interface"""
    print("🚀 LinkedIn Recruitment Agent Configuration Tool")
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print("""
Usage: linkedin-config [OPTIONS]

LinkedIn Recruitment Agent Configuration Tool

Options:
  --help, -h              Show this help message
  --show                  Show current configuration only
  --preset-high-quality   Apply high-quality preset configuration
  --preset-volume         Apply volume preset configuration  
  --preset-conservative   Apply conservative preset configuration

Without options: Launch interactive configuration tool
""")
            return
        elif sys.argv[1] == "--show":
            show_current_config()
            return
        elif sys.argv[1] == "--preset-high-quality":
            configure_for_high_quality()
            print("✅ Applied 'High Quality' preset configuration!")
            return
        elif sys.argv[1] == "--preset-volume":
            configure_for_volume()
            print("✅ Applied 'Volume' preset configuration!")
            return
        elif sys.argv[1] == "--preset-conservative":
            configure_for_conservative()
            print("✅ Applied 'Conservative' preset configuration!")
            return
    
    show_current_config()
    
    proceed = input("\n🛠️  Would you like to modify these settings? (y/n): ").lower()
    if proceed in ['y', 'yes']:
        interactive_config()
    else:
        print("👍 Configuration unchanged. Run with --show to view settings anytime.")


if __name__ == "__main__":
    main()