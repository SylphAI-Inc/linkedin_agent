# 📝 Enhanced Logging System

The LinkedIn Agent now includes a comprehensive file-based logging system that captures all workflow execution details.

## 📁 Log Files

Each workflow run creates 4 separate log files with timestamps:

- **`workflow_YYYYMMDD_HHMMSS.log`** - Main workflow events (shows in console too)
- **`debug_YYYYMMDD_HHMMSS.log`** - Detailed debug information 
- **`agent_steps_YYYYMMDD_HHMMSS.log`** - Agent execution steps and results
- **`errors_YYYYMMDD_HHMMSS.log`** - Error messages and exceptions

## 🔍 Viewing Logs

### Quick View (Latest Session)
```bash
# View main workflow log
python view_logs.py

# View debug details
python view_logs.py --type debug

# View agent execution steps
python view_logs.py --type agent_steps

# View all errors
python view_logs.py --type errors

# View all log types
python view_logs.py --type all

# Show more lines
python view_logs.py --lines 100
```

### Manual File Access
```bash
# View latest workflow log
ls -la logs/workflow_*.log | tail -1
cat logs/workflow_20250812_180916.log

# View all logs from a session
ls logs/*_20250812_180916.log
```

## 📊 What Gets Logged

### Main Workflow Log
- Phase transitions (Strategy → Search → Extract → Evaluate → Outreach)
- High-level progress and results
- Final summary with metrics

### Debug Log  
- Data structure details during merge operations
- Global state debugging information
- Function parameter details
- Data flow analysis

### Agent Steps Log
- Each agent function call with parameters
- Function results and success/failure status
- Step-by-step execution tracking

### Error Log
- All errors and exceptions
- Stack traces and error context
- Failed operations with details

## 🎯 Benefits

1. **Terminal Too Long?** - All logs saved to files, no need to scroll back
2. **Debug Issues** - Detailed logs help identify exactly where problems occur  
3. **Track Progress** - See complete workflow execution history
4. **Performance Analysis** - Duration tracking and timing information
5. **Error Investigation** - Full error context and stack traces

## 🔧 Configuration

The logging system is automatically initialized in `main.py` and used throughout:

```python
from utils.logger import init_logging, log_info, log_debug, log_error

# Initialize (done automatically)
logger = init_logging()

# Use throughout code
log_info("Process started")
log_debug("Detailed debug info") 
log_error("Something failed", exception=e)
```

## 📂 Log Location

All logs are stored in the `logs/` directory in the project root:
```
linkedin_agent/
├── logs/
│   ├── workflow_20250812_180916.log
│   ├── debug_20250812_180916.log
│   ├── agent_steps_20250812_180916.log
│   └── errors_20250812_180916.log
└── view_logs.py
```

The logs are automatically organized by timestamp and cleaned up (old logs remain for historical reference).