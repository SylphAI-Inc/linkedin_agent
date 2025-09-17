# 🚀 LinkedIn Recruitment Agent

**A production-ready AI agent for automated LinkedIn candidate sourcing** using AdalFlow's modern Agent + Runner architecture with Chrome DevTools Protocol (CDP) browser automation and **Global State Architecture** for scalable performance.

## ✨ What This Does

Transforms manual LinkedIn recruiting:
```
❌ BEFORE: Manual process (hours per search)
1. Navigate to LinkedIn people search
2. Enter "Product Manager", select location  
3. Scroll through results, click each profile
4. Read profiles, take notes, decide if good candidate
5. Send DMs to interesting candidates

✅ AFTER: Automated AI agent (minutes per search)  
1. Run: linkedin-agent --query "Product Manager" --limit 10
2. Agent finds, extracts, and scores candidates automatically
3. Get structured results with names, titles, profiles, LinkedIn URLs
```

## 🧠 How It Works - Global State Architecture

### **🚀 Global State Architecture**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  AdalFlow Agent  │───▶│ Chrome Browser  │
│ "Find PMs in SF"│    │   (Lightweight)  │    │   via CDP       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                         │
                                │                         │
                       ┌──────────────────┐               │
                       │  Function Tools  │◀──────────────┘
                       │  • strategy      │
                       │  • search        │               
                       │  • extract       │               
                       │  • evaluate      │               
                       │  • outreach      │               
                       └──────────┬───────┘               
                                │                         
                                ▼                         
                   ┌─────────────────────────────┐        
                   │    🌐 GLOBAL STATE          │        
                   │  ┌─────────────────────────┐│        
                   │  │ Strategy Data           ││        
                   │  │ Search Results          ││        
                   │  │ Extracted Profiles      ││        
                   │  │ Evaluation Scores       ││        
                   │  │ Outreach Messages       ││        
                   │  └─────────────────────────┘│        
                   └─────────────────────────────┘        
```

**Key Benefits:**
- 🚀 **Scalable**: Handles 100+ candidates without timeouts
- ⚡ **Fast**: No large data in agent parameters  
- 🔄 **Persistent**: Data flows seamlessly across workflow phases
- 🎯 **Lightweight**: Agent gets status messages, not full datasets

### **🔄 4-Phase Agentic Workflow**

1. **🔍 SEARCH**: Smart LinkedIn search with quality scoring → Global State  
2. **📊 EXTRACT**: Full profile data extraction → Global State
3. **⭐ EVALUATE**: Comprehensive candidate scoring → Global State
4. **💌 OUTREACH**: Personalized message generation → Global State

**🎯 Each phase:**
- Gets lightweight status messages (not large data)
- Automatically retrieves data from Global State
- Stores results back to Global State  
- Enables seamless 100+ candidate processing

### **🔧 Technical Stack**
- **AdalFlow**: Modern Agent + Runner architecture with Global State
- **CDP**: Chrome DevTools Protocol for real browser control
- **Global State**: Centralized data management for scalability
- **JavaScript Injection**: Live DOM manipulation and data extraction
- **Quality Scoring**: AI-powered candidate evaluation system
- **Real-time Logging**: Comprehensive workflow monitoring

## 📦 Installation

### Prerequisites
- Python 3.12+
- Poetry (dependency management)
- OpenAI API key
- Chrome/Chromium browser

### Setup
Clone adalflow
```bash
git clone https://github.com/SylphAI-Inc/AdalFlow
```

```bash
# Clone and install
# Update the pyproject.toml pointing to the adaflow directory 
git clone <your-repo>
cd linkedin_agent
poetry lock # Optional
poetry install
```

```bash
eval $(poetry env activate)

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Test installation
linkedin-agent --help
linkedin-config --help
```

### CLI Commands Available
After installation, you have two professional CLI tools:
- **`linkedin-agent`** - Main recruitment agent
- **`linkedin-config`** - Configuration management tool

## 🚀 Usage

### **Basic Usage**
```bash
# Find Product Managers in San Francisco (new main.py entry point)
linkedin-agent --query "Backend engineer" --location "San Francisco Bay Area" --limit 5

# With job description for enhanced targeting
linkedin-agent --job-description example_job_description.txt --limit 10

# Find Software Engineers (any location)  
linkedin-agent --query "Software Engineer" --limit 10

# Find Data Scientists with specific location
linkedin-agent --query "Data Scientist" --location "New York" --limit 3
```

### **Advanced Usage**
```bash
# Configure for high-quality candidates (fewer but better)
linkedin-config --preset-high-quality
linkedin-agent --job-description example_job_description.txt --limit 3

# Configure for volume (more candidates)  
linkedin-config --preset-volume
linkedin-agent --query "Software Engineer" --limit 15

# Custom configuration
linkedin-config  # Interactive wizard

# Test and debug
python tests/test_global_state_workflow.py
python test_search_debug.py
```

## 📋 Example Output

```
🚀 PHASE: SEARCH - Smart LinkedIn Search  
🔍 Candidates found on page 1:
   1. Madeline Zhang - Senior Software Engineer @Airbnb | Ex-Google
   2. Sravya Madipalli - Senior Manager, Data Science @ Grammarly...
   ✅ Madeline Zhang (Score: 10.07) - Added to candidate pool
   ❌ Di Wu (Score: 3.83) - Below minimum threshold (7.0)
✅ Page 1 processed: 6/10 candidates added to pool

🚀 PHASE: EXTRACT - Profile Data Extraction
🔄 Extracting Madeline Zhang (1/3)
🔄 Extracting Sravya Madipalli (2/3)  
✅ Successfully stored 3 profiles in global state

🚀 PHASE: EVALUATE - Quality Assessment
📊 Average Quality: 8.32
📊 Quality Range: 7.41 - 10.07
📊 Above Threshold: 3/3
✅ Quality Sufficient: Yes

🚀 PHASE: OUTREACH - Personalized Messages
📊 Generated outreach for 3 quality candidates

📊 Final result: Successfully processed 3 candidates
```

## 🏗️ Architecture Deep Dive

### **Global State Architecture Pattern**
```python
# Global State enables scalable workflows
from core.workflow_state import get_workflow_state

# Phase 1: Search → Global State  
search_result = smart_candidate_search(query, location, target_count=10)
# Returns: {"success": True, "candidates_found": 25} (lightweight)

# Phase 2: Extract → Global State
extract_result = extract_candidate_profiles()
# Returns: {"success": True, "extracted_count": 25} (lightweight)

# Phase 3: Evaluate → Global State
eval_result = evaluate_candidates_quality()
# Returns: {"success": True, "quality_sufficient": True} (lightweight)

# Phase 4: Outreach → Global State
outreach_result = generate_candidate_outreach()
# Returns: {"success": True, "messages_generated": 10} (lightweight)

# All data flows through Global State - no large parameters!
```

### **Browser Automation**
```python
# Direct Chrome control via CDP
w = WebTool(port=9222)
w.connect()  # WebSocket to ws://127.0.0.1:9222/devtools/...
w.go("https://www.linkedin.com/search/results/people/")
w.js("document.querySelector('.search-box').value = 'Product Manager'")
candidates = w.js("return extractCandidateData()")
```

### **Smart LinkedIn Integration**
```python
# Reverse-engineered selectors (2024)
containers = document.querySelectorAll('.search-results-container li')  # NEW
# vs old: document.querySelectorAll('.reusable-search__result-container')  # DEPRECATED

# Pattern-matched extraction
name = line.substring(0, line.indexOf('View')).trim()  # "John SmithView John Smith's profile"
```

## ✅ Production Features

### **✅ Robust & Reliable**
- **Global State**: Scalable to 100+ candidates without timeouts
- **Quality Scoring**: AI-powered candidate evaluation with strategic bonuses
- **Smart Search**: Real-time candidate filtering and quality assessment
- **Real-time Logging**: Comprehensive workflow monitoring across 4 log files
- **Intelligent Fallbacks**: Automatic quality threshold adjustments

### **✅ Anti-Detection**  
- **Human-like Timing**: Configurable delays (MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
- **Proper User Agents**: Real Chrome browser (not headless signatures)
- **Session Management**: Persistent user data directory
- **Rate Limiting**: Built-in cooldowns between searches

### **✅ LinkedIn Expertise**
- **Current Selectors**: Reverse-engineered 2024 LinkedIn HTML structure
- **Profile Extraction**: Comprehensive data: name, title, location, experience
- **Search Accuracy**: Handles LinkedIn's complex search result format
- **Authentication Handling**: Works with logged-in LinkedIn sessions
