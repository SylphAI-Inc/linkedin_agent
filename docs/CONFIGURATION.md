# 🔧 LinkedIn Agent Configuration Guide

## Overview

The LinkedIn Recruitment Agent includes a comprehensive configuration system that allows you to customize every aspect of the recruitment workflow without modifying code. This guide covers all configuration options, presets, and advanced customization techniques.

## 🚀 Quick Start

### View Current Configuration
```bash
python configure.py --show
```

### Apply Preset Configurations
```bash
# For high-quality candidates (fewer but better)
python configure.py --preset-high-quality

# For volume recruiting (more candidates)
python configure.py --preset-volume

# For careful, thorough approach
python configure.py --preset-conservative
```

### Interactive Configuration
```bash
python configure.py
```

## 📊 Configuration Categories

### 🔍 Search Configuration

Controls how the agent searches for candidates on LinkedIn.

| Parameter | Default | Description | Range |
|-----------|---------|-------------|--------|
| `min_search_score` | 7.0 | Minimum quality score for candidates during search | 0.0-10.0 |
| `min_evaluation_threshold` | 6.0 | Minimum score for final evaluation pass | 0.0-10.0 |
| `target_quality_candidates` | 5 | Target number of quality candidates | 1-50 |
| `max_pages_per_search` | 3 | LinkedIn pages to search | 1-10 |
| `quality_mode` | "adaptive" | Search strategy mode | "adaptive", "quality_first", "fast" |
| `extend_search_when_insufficient` | True | Try more pages if quality is low | True/False |
| `use_heap_backups` | True | Use backup candidates from heap | True/False |
| `fallback_to_lower_threshold` | True | Lower threshold if needed | True/False |

**Quality Modes:**
- **"adaptive"**: Extends search intelligently for quality candidates
- **"quality_first"**: Prioritizes quality over quantity, may search more pages
- **"fast"**: Respects hard limits, faster but may miss quality candidates

### 📊 Extraction Configuration

Controls profile data extraction behavior.

| Parameter | Default | Description | Range |
|-----------|---------|-------------|--------|
| `delay_between_extractions` | 1.0 | Seconds between profile extractions | 0.5-10.0 |
| `extraction_timeout` | 30.0 | Max seconds per profile extraction | 10.0-120.0 |
| `validate_extraction_quality` | True | Check if extraction worked well | True/False |
| `min_profile_completeness` | 0.6 | Minimum profile data completeness | 0.0-1.0 |
| `skip_private_profiles` | True | Skip profiles we can't access | True/False |
| `retry_failed_extractions` | 1 | How many times to retry failures | 0-5 |

### ⭐ Evaluation Configuration

Controls candidate scoring and evaluation.

| Parameter | Default | Description | Range |
|-----------|---------|-------------|--------|
| `experience_weight` | 0.3 | How much experience matters | 0.0-1.0 |
| `education_weight` | 0.2 | How much education matters | 0.0-1.0 |
| `skills_weight` | 0.2 | How much skills matter | 0.0-1.0 |
| `profile_completeness_weight` | 0.1 | How much complete profiles matter | 0.0-1.0 |
| `strategic_alignment_weight` | 0.2 | How much strategy matching matters | 0.0-1.0 |
| `tier1_company_bonus` | 2.0 | Bonus for Google, Meta, etc. | 0.0-5.0 |
| `seniority_bonus` | 2.0 | Bonus for senior/lead/principal | 0.0-5.0 |
| `tech_stack_bonus` | 1.0 | Bonus for matching tech skills | 0.0-3.0 |
| `excellent_score_threshold` | 9.0 | What's considered excellent | 5.0-10.0 |
| `good_score_threshold` | 7.0 | What's considered good | 3.0-9.0 |
| `acceptable_score_threshold` | 5.0 | What's considered acceptable | 1.0-7.0 |

### 🔄 Workflow Configuration

Controls overall workflow behavior and automation.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_proceed_to_extraction` | True | Go to extraction when search done |
| `auto_proceed_to_evaluation` | True | Go to evaluation when extraction done |
| `auto_proceed_to_outreach` | True | Go to outreach when evaluation done |
| `max_fallback_attempts` | 2 | How many fallbacks to try |
| `prefer_heap_backups_over_new_search` | True | Try heap before new search |
| `min_candidates_for_outreach` | 3 | Need this many for outreach |
| `require_quality_sufficient` | False | Force quality requirements |
| `enable_real_time_logging` | True | Show detailed progress |
| `save_intermediate_results` | True | Save results after each phase |

## 🎚️ Preset Configurations

### High Quality Preset
```bash
python configure.py --preset-high-quality
```

**Best for:** Executive search, specialized roles, quality over quantity

**Changes:**
- `min_search_score`: 7.0 → 8.0
- `min_evaluation_threshold`: 6.0 → 7.5  
- `target_quality_candidates`: 5 → 3
- `quality_mode`: "adaptive" → "quality_first"
- `excellent_score_threshold`: 9.0 → 9.5

### Volume Preset
```bash
python configure.py --preset-volume
```

**Best for:** High-volume recruiting, entry-level positions, casting a wide net

**Changes:**
- `min_search_score`: 7.0 → 6.0
- `min_evaluation_threshold`: 6.0 → 5.0
- `target_quality_candidates`: 5 → 10
- `max_pages_per_search`: 3 → 5
- `quality_mode`: "adaptive" → "fast"

### Conservative Preset
```bash
python configure.py --preset-conservative
```

**Best for:** Compliance-sensitive environments, careful recruiting

**Changes:**
- `delay_between_extractions`: 1.0 → 2.0
- `retry_failed_extractions`: 1 → 2
- `max_fallback_attempts`: 2 → 3
- `extend_search_when_insufficient`: True (stays)
- `fallback_to_lower_threshold`: True → False

## 🔧 Configuration Methods

### 1. Interactive Configuration Wizard
```bash
python configure.py
```

Provides a menu-driven interface to configure all settings.

### 2. Direct File Editing
Edit `config_user.py` directly:

```python
from config_user import USER_CONFIG

# Modify search settings
USER_CONFIG.search.min_search_score = 8.5
USER_CONFIG.search.target_quality_candidates = 3

# Modify extraction settings
USER_CONFIG.extraction.delay_between_extractions = 2.0

# Modify evaluation settings
USER_CONFIG.evaluation.tier1_company_bonus = 3.0
```

### 3. Environment Variables
```bash
# Set environment variables (override config file)
export MIN_SEARCH_SCORE=8.0
export MIN_EVALUATION_THRESHOLD=7.0
export TARGET_QUALITY_CANDIDATES=3
export MAX_PAGES_PER_SEARCH=5
export EXTRACTION_DELAY=2.0

# Run with overrides
python main.py --query "Senior Engineer" --limit 5
```

### 4. Programmatic Configuration
```python
from config_user import configure_for_high_quality, USER_CONFIG

# Apply preset
configure_for_high_quality()

# Then customize further
USER_CONFIG.search.target_quality_candidates = 2
USER_CONFIG.evaluation.tier1_company_bonus = 4.0
```

## 📈 Configuration Use Cases

### Executive Search Configuration
```python
# High standards, thorough process
USER_CONFIG.search.min_search_score = 8.5
USER_CONFIG.search.min_evaluation_threshold = 8.0
USER_CONFIG.search.target_quality_candidates = 2
USER_CONFIG.search.quality_mode = "quality_first"
USER_CONFIG.extraction.delay_between_extractions = 3.0
USER_CONFIG.evaluation.tier1_company_bonus = 3.0
USER_CONFIG.evaluation.seniority_bonus = 3.0
```

### High-Volume Recruiting Configuration
```python
# Speed and quantity focused
USER_CONFIG.search.min_search_score = 6.0
USER_CONFIG.search.min_evaluation_threshold = 5.0
USER_CONFIG.search.target_quality_candidates = 15
USER_CONFIG.search.max_pages_per_search = 6
USER_CONFIG.search.quality_mode = "fast"
USER_CONFIG.extraction.delay_between_extractions = 0.5
```

### Startup Tech Recruiting Configuration
```python
# Balance of quality and speed for tech roles
USER_CONFIG.search.min_search_score = 7.5
USER_CONFIG.search.target_quality_candidates = 5
USER_CONFIG.evaluation.experience_weight = 0.4
USER_CONFIG.evaluation.skills_weight = 0.3
USER_CONFIG.evaluation.tech_stack_bonus = 2.0
USER_CONFIG.evaluation.tier1_company_bonus = 1.5  # Less emphasis on big tech
```

### Conservative/Compliance Configuration
```python
# Careful, documented process
USER_CONFIG.extraction.delay_between_extractions = 2.5
USER_CONFIG.extraction.retry_failed_extractions = 3
USER_CONFIG.workflow.max_fallback_attempts = 1
USER_CONFIG.workflow.save_intermediate_results = True
USER_CONFIG.search.fallback_to_lower_threshold = False
```

## 🔍 Configuration Testing

### Verify Configuration Works
```bash
# Run configuration verification tests
python test_config_verification.py
python test_config_functional.py
```

### Test Configuration Impact
```bash
# Test with high quality preset
python configure.py --preset-high-quality
python main.py --query "Senior Engineer" --limit 3

# Test with volume preset  
python configure.py --preset-volume
python main.py --query "Software Engineer" --limit 10

# Compare results and behavior
```

## 📊 Configuration Impact on Workflow

### Search Phase Impact
- **min_search_score**: Higher = fewer but better candidates from LinkedIn pages
- **max_pages_per_search**: More pages = more candidates but slower
- **quality_mode**: "quality_first" may search beyond page limit for quality

### Extraction Phase Impact
- **delay_between_extractions**: Higher = slower but more respectful of LinkedIn
- **retry_failed_extractions**: More retries = better data but slower
- **validate_extraction_quality**: Validation adds time but ensures data quality

### Evaluation Phase Impact
- **min_evaluation_threshold**: Higher threshold = fewer candidates pass evaluation
- **scoring weights**: Adjust what matters most in candidate assessment
- **strategic bonuses**: Higher bonuses = more impact on final scores

### Workflow Decision Impact
- **auto_proceed_***: False = manual approval needed between phases
- **max_fallback_attempts**: More attempts = higher chance of finding candidates
- **prefer_heap_backups**: True = try existing candidates before new search

## 🚨 Common Configuration Scenarios

### "Not Finding Enough Candidates"
```python
# Lower thresholds and search more pages
USER_CONFIG.search.min_search_score = 6.0
USER_CONFIG.search.min_evaluation_threshold = 5.5
USER_CONFIG.search.max_pages_per_search = 5
USER_CONFIG.search.quality_mode = "adaptive"
```

### "Too Many Low-Quality Candidates"
```python
# Raise thresholds and focus on quality
USER_CONFIG.search.min_search_score = 8.0
USER_CONFIG.search.min_evaluation_threshold = 7.5
USER_CONFIG.search.quality_mode = "quality_first"
USER_CONFIG.evaluation.tier1_company_bonus = 2.5
```

### "Search Taking Too Long"
```python
# Speed up the process
USER_CONFIG.search.max_pages_per_search = 2
USER_CONFIG.search.quality_mode = "fast"
USER_CONFIG.extraction.delay_between_extractions = 0.8
USER_CONFIG.workflow.max_fallback_attempts = 1
```

### "LinkedIn Rate Limiting Issues"
```python
# Be more conservative with timing
USER_CONFIG.extraction.delay_between_extractions = 3.0
USER_CONFIG.extraction.retry_failed_extractions = 1
USER_CONFIG.search.max_pages_per_search = 2
```

## 💡 Best Practices

### 1. Start with Presets
- Use `--preset-high-quality` for specialized roles
- Use `--preset-volume` for high-volume recruiting
- Use `--preset-conservative` for sensitive environments

### 2. Gradual Adjustments
- Make small changes (0.5 point threshold adjustments)
- Test impact before making major changes
- Monitor candidate quality vs quantity trade-offs

### 3. Environment-Specific Configuration
- Use environment variables for deployment
- Document configuration choices for compliance
- Test configuration changes in dev before production

### 4. Monitor and Adjust
- Review logs to understand configuration impact
- Adjust based on recruiter feedback
- Balance speed vs quality based on business needs

## 🔧 Troubleshooting Configuration

### Configuration Not Taking Effect
1. Check function signatures use `Optional` parameters
2. Verify imports in function files: `from config_user import get_*_config`
3. Ensure functions call config when parameters are `None`
4. Test with `python test_config_verification.py`

### Environment Variables Not Working
1. Verify variable names match those in `UserConfig.load_from_env()`
2. Check data types (string "8.0" for float, "True" for boolean)
3. Ensure environment variables are set before running agent

### Preset Configurations Not Applying
1. Import functions: `from config_user import configure_for_*`
2. Call preset before running agent workflow
3. Verify changes with `python configure.py --show`

## 📚 Advanced Configuration

### Custom Evaluation Weights
```python
# Create domain-specific evaluation profiles
def configure_for_data_science():
    USER_CONFIG.evaluation.education_weight = 0.4  # PhD matters more
    USER_CONFIG.evaluation.skills_weight = 0.4     # Technical skills critical
    USER_CONFIG.evaluation.experience_weight = 0.2  # Less emphasis on years

def configure_for_sales():
    USER_CONFIG.evaluation.experience_weight = 0.5  # Track record matters
    USER_CONFIG.evaluation.education_weight = 0.1   # Less emphasis on education
    USER_CONFIG.evaluation.strategic_alignment_weight = 0.4  # Culture fit critical
```

### Dynamic Configuration
```python
def configure_based_on_role(role_type):
    if "senior" in role_type.lower():
        USER_CONFIG.search.min_search_score = 8.0
        USER_CONFIG.evaluation.seniority_bonus = 3.0
    elif "junior" in role_type.lower():
        USER_CONFIG.search.min_search_score = 6.5
        USER_CONFIG.evaluation.education_weight = 0.4
    elif "lead" in role_type.lower():
        USER_CONFIG.search.min_search_score = 8.5
        USER_CONFIG.evaluation.seniority_bonus = 4.0
```

### Configuration Profiles
```python
# Save and load configuration profiles
def save_config_profile(profile_name):
    import json
    config_data = {
        "search": USER_CONFIG.search.__dict__,
        "extraction": USER_CONFIG.extraction.__dict__,
        "evaluation": USER_CONFIG.evaluation.__dict__,
        "workflow": USER_CONFIG.workflow.__dict__
    }
    with open(f"config_profiles/{profile_name}.json", "w") as f:
        json.dump(config_data, f, indent=2)

def load_config_profile(profile_name):
    import json
    with open(f"config_profiles/{profile_name}.json", "r") as f:
        config_data = json.load(f)
    # Apply loaded configuration...
```

This configuration system makes the LinkedIn Agent highly adaptable to any recruiting scenario while maintaining ease of use! 🚀