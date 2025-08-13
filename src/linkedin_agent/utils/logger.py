"""
Enhanced Logging System for LinkedIn Agent Workflow
Provides file-based logging with better organization and readability
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class WorkflowLogger:
    """Enhanced logger that writes to both console and files with improved formatting"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamp for this session
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup different log files
        self.setup_loggers()
        
        # Current workflow phase for context
        self.current_phase = "initialization"
        self.workflow_id = None
        
    def setup_loggers(self):
        """Setup different loggers for different purposes"""
        
        # Main workflow logger
        self.main_logger = self._create_logger(
            "workflow_main",
            self.log_dir / f"workflow_{self.session_timestamp}.log",
            level=logging.INFO
        )
        
        # Debug logger (more detailed)
        self.debug_logger = self._create_logger(
            "workflow_debug", 
            self.log_dir / f"debug_{self.session_timestamp}.log",
            level=logging.DEBUG
        )
        
        # Agent steps logger (for agent execution tracking)
        self.agent_logger = self._create_logger(
            "agent_steps",
            self.log_dir / f"agent_steps_{self.session_timestamp}.log", 
            level=logging.INFO
        )
        
        # Error logger
        self.error_logger = self._create_logger(
            "workflow_errors",
            self.log_dir / f"errors_{self.session_timestamp}.log",
            level=logging.ERROR
        )
        
    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """Create a logger with both file and console handlers"""
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # File handler with immediate flushing for real-time logging
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Create a custom handler that flushes immediately
        class FlushingFileHandler(logging.FileHandler):
            def emit(self, record):
                super().emit(record)
                self.flush()  # Force immediate write to disk
        
        # Replace with flushing handler
        file_handler = FlushingFileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler (only for main and error loggers)
        if name in ['workflow_main', 'workflow_errors']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def set_workflow_context(self, workflow_id: str, phase: str):
        """Set context for better log organization"""
        self.workflow_id = workflow_id
        self.current_phase = phase
        
    def info(self, message: str, phase: Optional[str] = None, also_debug: bool = False):
        """Log info message with phase context"""
        phase = phase or self.current_phase
        formatted_msg = f"[{phase.upper()}] {message}"
        
        self.main_logger.info(formatted_msg)
        if also_debug:
            self.debug_logger.info(formatted_msg)
    
    def debug(self, message: str, phase: Optional[str] = None):
        """Log debug message"""
        phase = phase or self.current_phase
        formatted_msg = f"[{phase.upper()}] {message}"
        self.debug_logger.debug(formatted_msg)
    
    def error(self, message: str, phase: Optional[str] = None, exception: Optional[Exception] = None):
        """Log error message"""
        phase = phase or self.current_phase
        formatted_msg = f"[{phase.upper()}] ❌ {message}"
        
        if exception:
            formatted_msg += f"\n   Exception: {str(exception)}"
            formatted_msg += f"\n   Type: {type(exception).__name__}"
        
        self.error_logger.error(formatted_msg)
        self.main_logger.error(formatted_msg)
    
    def agent_step(self, step_num: int, function_name: str, args: Dict[str, Any], result: Any):
        """Log agent execution step"""
        step_msg = f"Step {step_num}: {function_name}"
        
        # Log function call
        if args:
            args_str = ", ".join([f"{k}={v}" for k, v in args.items() if k not in ['job_description']])
            if len(args_str) > 100:
                args_str = args_str[:97] + "..."
            step_msg += f"({args_str})"
        
        self.agent_logger.info(f"🤖 {step_msg}")
        
        # Log result summary
        if isinstance(result, dict):
            if result.get('success'):
                summary = []
                if 'candidates_found' in result:
                    summary.append(f"found {result['candidates_found']} candidates")
                if 'extracted_count' in result:
                    summary.append(f"extracted {result['extracted_count']} profiles")
                if 'candidates_evaluated' in result:
                    summary.append(f"evaluated {result['candidates_evaluated']} candidates")
                if 'outreach_generated' in result:
                    summary.append(f"generated {result['outreach_generated']} outreach")
                
                if summary:
                    self.agent_logger.info(f"   ✅ Result: {', '.join(summary)}")
            else:
                error_msg = result.get('error', 'Unknown error')
                self.agent_logger.info(f"   ❌ Error: {error_msg}")
        
    def progress_update(self, message: str, step: Optional[str] = None):
        """Log real-time progress updates"""
        step_prefix = f"[{step}] " if step else ""
        progress_msg = f"🔄 {step_prefix}{message}"
        
        # Log to both main and debug for visibility
        self.main_logger.info(progress_msg)
        self.debug_logger.info(progress_msg)
        
        # Force flush to ensure immediate visibility
        for handler in self.main_logger.handlers:
            handler.flush()
        for handler in self.debug_logger.handlers:
            handler.flush()
    
    def workflow_summary(self, total_candidates: int, duration: float, success: bool):
        """Log workflow completion summary"""
        summary_msg = f"""
{'='*60}
WORKFLOW COMPLETION SUMMARY
{'='*60}
Success: {'✅ Yes' if success else '❌ No'}
Total Candidates: {total_candidates}
Duration: {duration:.1f} seconds
Session: {self.session_timestamp}
Log Files:
  • Main: logs/workflow_{self.session_timestamp}.log
  • Debug: logs/debug_{self.session_timestamp}.log  
  • Agent Steps: logs/agent_steps_{self.session_timestamp}.log
  • Errors: logs/errors_{self.session_timestamp}.log
{'='*60}"""
        
        self.main_logger.info(summary_msg)
    
    def phase_start(self, phase: str, description: str = ""):
        """Log phase start with clear separation"""
        self.current_phase = phase
        separator = "="*50
        phase_msg = f"\n{separator}\n🚀 PHASE: {phase.upper()}"
        if description:
            phase_msg += f" - {description}"
        phase_msg += f"\n{separator}"
        
        self.main_logger.info(phase_msg)
        self.debug_logger.info(phase_msg)
    
    def phase_end(self, phase: str, success: bool, summary: str = ""):
        """Log phase completion"""
        status = "✅ COMPLETED" if success else "❌ FAILED" 
        phase_msg = f"🏁 {phase.upper()} {status}"
        if summary:
            phase_msg += f" - {summary}"
            
        self.main_logger.info(phase_msg)
        self.debug_logger.info(phase_msg)


# Global logger instance
_workflow_logger: Optional[WorkflowLogger] = None

def get_logger() -> WorkflowLogger:
    """Get the global workflow logger instance"""
    global _workflow_logger
    if _workflow_logger is None:
        _workflow_logger = WorkflowLogger()
    return _workflow_logger

def init_logging(log_dir: str = "logs") -> WorkflowLogger:
    """Initialize the logging system"""
    global _workflow_logger
    _workflow_logger = WorkflowLogger(log_dir)
    return _workflow_logger

# Convenience functions
def log_info(message: str, phase: Optional[str] = None, also_debug: bool = False):
    """Log info message"""
    get_logger().info(message, phase, also_debug)

def log_debug(message: str, phase: Optional[str] = None):
    """Log debug message"""
    get_logger().debug(message, phase)

def log_error(message: str, phase: Optional[str] = None, exception: Optional[Exception] = None):
    """Log error message"""
    get_logger().error(message, phase, exception)

def log_agent_step(step_num: int, function_name: str, args: Dict[str, Any], result: Any):
    """Log agent step"""
    get_logger().agent_step(step_num, function_name, args, result)

def log_phase_start(phase: str, description: str = ""):
    """Log phase start"""
    get_logger().phase_start(phase, description)

def log_phase_end(phase: str, success: bool, summary: str = ""):
    """Log phase end"""
    get_logger().phase_end(phase, success, summary)

def log_progress(message: str, step: Optional[str] = None):
    """Log real-time progress update"""
    get_logger().progress_update(message, step)