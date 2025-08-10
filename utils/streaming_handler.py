"""Streaming execution handler for real-time LinkedIn agent feedback"""

import sys
import time
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path


class StreamingHandler:
    """Handles real-time streaming feedback during LinkedIn agent execution"""
    
    def __init__(self, output_file: Optional[Path] = None, enable_file_logging: bool = True):
        self.output_file = output_file
        self.enable_file_logging = enable_file_logging
        self.start_time = datetime.now()
        self.step_count = 0
        self.candidates_found = 0
        self.current_candidate = None
        self.step_history = []
        
        # Status tracking
        self.status = "initializing"
        self.current_action = None
        self.last_update = datetime.now()
        
        # Callbacks for custom handling
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback function to be called on each update"""
        self.callbacks.append(callback)
    
    def log_step(self, step_type: str, details: Dict[str, Any], status: str = "in_progress"):
        """Log a single agent step with details"""
        self.step_count += 1
        self.status = status
        self.current_action = step_type
        self.last_update = datetime.now()
        
        step_info = {
            "step": self.step_count,
            "timestamp": self.last_update.isoformat(),
            "type": step_type,
            "status": status,
            "details": details,
            "elapsed_seconds": (self.last_update - self.start_time).total_seconds()
        }
        
        self.step_history.append(step_info)
        
        # Real-time console output
        self._print_step_update(step_info)
        
        # File logging
        if self.enable_file_logging and self.output_file:
            self._write_to_file(step_info)
        
        # Call registered callbacks
        for callback in self.callbacks:
            try:
                callback(step_info)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def log_navigation(self, url: str, page_title: str = ""):
        """Log navigation to a URL"""
        self.log_step("navigation", {
            "action": "navigate",
            "url": url,
            "page_title": page_title
        })
    
    def log_search_start(self, query: str, location: str, limit: int):
        """Log the start of a people search"""
        self.log_step("search_start", {
            "action": "search_people", 
            "query": query,
            "location": location,
            "limit": limit
        })
    
    def log_search_results(self, results_count: int, results_preview: List[Dict[str, Any]]):
        """Log search results found"""
        self.log_step("search_results", {
            "action": "search_complete",
            "results_count": results_count,
            "results_preview": results_preview[:3]  # First 3 results only
        })
    
    def log_candidate_start(self, candidate_index: int, candidate_info: Dict[str, Any]):
        """Log starting to process a candidate"""
        self.current_candidate = candidate_info
        self.log_step("candidate_start", {
            "action": "process_candidate",
            "candidate_index": candidate_index + 1,
            "candidate_name": candidate_info.get("name", "Unknown"),
            "candidate_title": candidate_info.get("subtitle", "Unknown"), 
            "candidate_url": candidate_info.get("url", "")
        })
    
    def log_profile_extraction(self, candidate_name: str, extraction_success: bool, profile_data: Optional[Dict[str, Any]] = None):
        """Log profile extraction results"""
        details = {
            "action": "extract_complete_profile",
            "candidate_name": candidate_name,
            "extraction_success": extraction_success
        }
        
        if extraction_success and profile_data:
            # Add summary of extracted data quality
            details.update({
                "has_name": bool(profile_data.get("name")),
                "has_headline": bool(profile_data.get("headline")),
                "has_about": bool(profile_data.get("about")),
                "has_experience": bool(profile_data.get("experience")),
                "has_education": bool(profile_data.get("education")),
                "has_location": bool(profile_data.get("location")),
                "data_quality_score": self._calculate_data_quality(profile_data)
            })
        
        status = "completed" if extraction_success else "failed"
        self.log_step("profile_extraction", details, status)
        
        if extraction_success:
            self.candidates_found += 1
    
    def log_completion(self, final_results: List[Dict[str, Any]]):
        """Log workflow completion with final results"""
        self.candidates_found = len(final_results)
        self.status = "completed"
        self.current_action = "workflow_complete"
        
        # Count successful extractions (candidates with profile_details)
        successful_extractions = len([c for c in final_results if c.get("profile_details")])
        
        details = {
            "total_candidates_found": len(final_results),  # Fixed key name
            "successful_extractions": successful_extractions,  # Added expected key
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),  # Added duration
            "candidates": [{"name": r.get("name", "Unknown"), "url": r.get("url", "")} 
                          for r in final_results[:5]]  # Show first 5
        }
        
        self.log_step("completion", details, "completed")
    
    def log_outreach_evaluation(self, outreach_summary: Dict[str, Any]):
        """Log outreach evaluation results"""
        details = {
            "total_evaluated": outreach_summary.get("total_evaluated", 0),
            "recommended_for_outreach": outreach_summary.get("recommended_for_outreach", 0),
            "outreach_rate": outreach_summary.get("outreach_rate", "0%"),
            "outreach_file": outreach_summary.get("saved_to", "Not saved")
        }
        
        self.log_step("outreach_evaluation", details, "completed")
        print(f"📨 Outreach evaluation complete: {details['recommended_for_outreach']}/{details['total_evaluated']} candidates recommended")
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Log an error that occurred"""
        details = {
            "action": "error",
            "error_type": error_type,
            "error_message": str(error_message)
        }
        
        if context:
            details["context"] = context
        
        self.log_step("error", details, "error")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": self.status,
            "current_action": self.current_action,
            "step_count": self.step_count,
            "candidates_found": self.candidates_found,
            "duration_seconds": duration,
            "last_update": self.last_update.isoformat()
        }
    
    def _print_step_update(self, step_info: Dict[str, Any]):
        """Print a formatted step update to console"""
        step_num = step_info["step"]
        step_type = step_info["type"]
        details = step_info["details"]
        status = step_info["status"]
        elapsed = step_info["elapsed_seconds"]
        
        # Status emoji
        status_emoji = {
            "in_progress": "⏳",
            "completed": "✅", 
            "failed": "❌",
            "error": "🚨"
        }.get(status, "📋")
        
        # Format based on step type
        if step_type == "navigation":
            print(f"{status_emoji} Step {step_num}: Navigating to {details.get('url', 'unknown')}")
            
        elif step_type == "search_start":
            print(f"{status_emoji} Step {step_num}: Searching for '{details['query']}' in {details['location']}")
            
        elif step_type == "search_results":
            count = details['results_count']
            print(f"{status_emoji} Step {step_num}: Found {count} candidates")
            for i, result in enumerate(details.get('results_preview', []), 1):
                name = result.get('name', 'Unknown')
                title = result.get('subtitle', 'Unknown')
                print(f"   {i}. {name} - {title}")
                
        elif step_type == "candidate_start":
            idx = details['candidate_index']
            name = details['candidate_name'] 
            print(f"{status_emoji} Step {step_num}: Processing candidate #{idx}: {name}")
            
        elif step_type == "profile_extraction":
            name = details['candidate_name']
            success = details['extraction_success']
            if success:
                quality = details.get('data_quality_score', 0)
                print(f"{status_emoji} Step {step_num}: Extracted profile for {name} (quality: {quality}/5)")
            else:
                print(f"{status_emoji} Step {step_num}: Failed to extract profile for {name}")
                
        elif step_type == "completion":
            total = details['total_candidates_found']
            success = details['successful_extractions'] 
            duration = details['duration_seconds']
            print(f"{status_emoji} Step {step_num}: Workflow complete! {success}/{total} profiles extracted in {duration:.1f}s")
            
        elif step_type == "error":
            error_type = details['error_type']
            message = details['error_message']
            print(f"{status_emoji} Step {step_num}: ERROR - {error_type}: {message}")
            
        else:
            action = details.get('action', step_type)
            print(f"{status_emoji} Step {step_num}: {action}")
        
        # Show elapsed time for longer operations
        if elapsed > 5:
            print(f"    ⏱️  Total elapsed: {elapsed:.1f}s")
    
    def _calculate_data_quality(self, profile_data: Dict[str, Any]) -> int:
        """Calculate data quality score out of 5"""
        score = 0
        
        # Check for key fields
        key_fields = ['name', 'headline', 'about', 'experience', 'education']
        for field in key_fields:
            value = profile_data.get(field)
            if value and len(str(value).strip()) > 20:  # Non-trivial content
                score += 1
        
        return score
    
    def _write_to_file(self, step_info: Dict[str, Any]):
        """Write step info to log file"""
        if not self.output_file:
            return
        
        try:
            # Ensure parent directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to file
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(step_info) + "\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")


class AgentProgressTracker:
    """Higher-level progress tracking for the LinkedIn agent workflow"""
    
    def __init__(self, query: str, location: str, limit: int, enable_streaming: bool = True):
        self.query = query
        self.location = location  
        self.limit = limit
        self.enable_streaming = enable_streaming
        
        # Initialize streaming handler if enabled
        if enable_streaming:
            log_file = Path(f"logs/agent_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
            self.streamer = StreamingHandler(output_file=log_file)
        else:
            self.streamer = None
    
    def start_workflow(self):
        """Mark the start of the workflow"""
        if self.streamer:
            print(f"\n🔍 Starting LinkedIn recruitment workflow")
            print(f"Query: {self.query}")
            print(f"Location: {self.location}")  
            print(f"Target candidates: {self.limit}")
            print("=" * 60)
    
    def log_navigation(self, url: str, page_title: str = ""):
        if self.streamer:
            self.streamer.log_navigation(url, page_title)
    
    def log_search_start(self):
        if self.streamer:
            self.streamer.log_search_start(self.query, self.location, self.limit)
    
    def log_search_results(self, results: List[Dict[str, Any]]):
        if self.streamer:
            self.streamer.log_search_results(len(results), results)
    
    def log_candidate_processing(self, index: int, candidate: Dict[str, Any]):
        if self.streamer:
            self.streamer.log_candidate_start(index, candidate)
    
    def log_profile_extraction(self, name: str, success: bool, data: Optional[Dict] = None):
        if self.streamer:
            self.streamer.log_profile_extraction(name, success, data)
    
    def log_completion(self, candidates: List[Dict[str, Any]]):
        if self.streamer:
            self.streamer.log_completion(candidates)  # Fixed: pass candidates directly
            print("=" * 60)
            print(f"✅ Workflow completed successfully!")
    
    def log_outreach_evaluation(self, outreach_summary: Dict[str, Any]):
        """Log outreach evaluation results"""
        if self.streamer:
            self.streamer.log_outreach_evaluation(outreach_summary)
        
        # Also print a summary to console
        total = outreach_summary.get("total_evaluated", 0)
        recommended = outreach_summary.get("recommended_for_outreach", 0)
        rate = outreach_summary.get("outreach_rate", "0%")
        
        print(f"📨 Outreach evaluation complete: {recommended}/{total} candidates recommended ({rate})")
    
    def log_error(self, error_type: str, message: str, context: Optional[Dict] = None):
        if self.streamer:
            self.streamer.log_error(error_type, message, context)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        if self.streamer:
            return self.streamer.get_status_summary()
        return {"streaming_disabled": True}


# Example usage and testing
if __name__ == "__main__":
    # Test the streaming handler
    handler = StreamingHandler(enable_file_logging=False)
    
    print("Testing StreamingHandler...")
    
    # Simulate a workflow
    handler.log_navigation("https://linkedin.com", "LinkedIn")
    time.sleep(1)
    
    handler.log_search_start("python developer", "San Francisco", 3)
    time.sleep(1)
    
    fake_results = [
        {"name": "John Doe", "subtitle": "Senior Python Developer", "url": "..."},
        {"name": "Jane Smith", "subtitle": "Full Stack Engineer", "url": "..."}
    ]
    handler.log_search_results(2, fake_results)
    time.sleep(1)
    
    handler.log_candidate_start(0, fake_results[0])
    time.sleep(1)
    
    fake_profile = {
        "name": "John Doe",
        "headline": "Senior Python Developer at TechCorp", 
        "about": "Experienced developer with 8+ years in Python, Django, and AWS...",
        "experience": "TechCorp: Senior Developer (2020-present)...",
        "education": "BS Computer Science, Stanford University"
    }
    handler.log_profile_extraction("John Doe", True, fake_profile)
    
    handler.log_completion(2, 1)
    
    print("\n📊 Final Status:")
    print(json.dumps(handler.get_status_summary(), indent=2))