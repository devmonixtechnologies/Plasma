"""
Global usage tracker that persists usage data to $HOME/.cai/usage.json
"""

import json
import os
import threading
import time
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import atexit

# Import fcntl only on Unix-like systems
if platform.system() != 'Windows':
    import fcntl

class GlobalUsageTracker:
    """
    Singleton class that tracks usage globally across all CAI executions.
    Persists data to $HOME/.cai/usage.json
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Check if tracking is disabled
        self.enabled = os.getenv("CAI_DISABLE_USAGE_TRACKING", "").lower() != "true"
        
        if not self.enabled:
            # Create minimal structure to avoid errors
            self.usage_data = {"global_totals": {}, "model_usage": {}, "daily_usage": {}, "sessions": []}
            self.session_id = None
            return
        
        self.usage_file = Path.home() / ".cai" / "usage.json"
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing usage data
        self.usage_data = self._load_usage_data()
        
        # Track current session
        self.session_id = None
        self.session_start_time = datetime.now().isoformat()
        
        # Register cleanup on exit
        atexit.register(self._save_usage_data)
    
    def _load_usage_data(self) -> Dict[str, Any]:
        """Load existing usage data from file with file locking"""
        if self.usage_file.exists():
            max_retries = 5
            retry_delay = 0.1
            
            for attempt in range(max_retries):
                try:
                    with open(self.usage_file, 'r') as f:
                        # Try to get shared lock for reading (Unix only)
                        if platform.system() != 'Windows':
                            fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                        data = json.load(f)
                        if platform.system() != 'Windows':
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        return data
                except (IOError, OSError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                    else:
                        # If we can't read after retries, start fresh
                        print(f"Warning: Could not read usage data after {max_retries} attempts")
                        break
                except json.JSONDecodeError:
                    # If file is corrupted, start fresh but backup the old one
                    backup_path = self.usage_file.with_suffix(f'.json.backup.{int(time.time())}')
                    try:
                        self.usage_file.rename(backup_path)
                        print(f"Corrupted usage.json backed up to {backup_path}")
                    except:
                        pass
                    break
        
        # Default structure
        return {
            "global_totals": {
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_requests": 0,
                "total_sessions": 0
            },
            "model_usage": {},  # Usage per model
            "daily_usage": {},  # Usage per day
            "sessions": []      # Individual session records
        }
    
    def _save_usage_data(self):
        """Save usage data to file with file locking for concurrent access"""
        if not self.enabled:
            return
            
        # Don't hold the lock during file I/O to avoid blocking on interrupts
        data_copy = None
        try:
            # Before saving, check if file exists and has higher values
            # This prevents overwriting with lower values due to concurrency
            if self.usage_file.exists():
                try:
                    current_file_data = self._load_usage_data()
                    if current_file_data:
                        file_total_cost = current_file_data["global_totals"].get("total_cost", 0)
                        memory_total_cost = self.usage_data["global_totals"].get("total_cost", 0)
                        
                        # If file has higher cost, merge it first
                        if file_total_cost > memory_total_cost:
                            # Reload and merge
                            with self._lock:
                                self.usage_data = current_file_data
                                # Now our in-memory data has the latest from file
                except:
                    pass  # If we can't read, continue with save
            
            # Quickly copy data under lock
            with self._lock:
                data_copy = json.dumps(self.usage_data, indent=2, sort_keys=True)
            
            # Do file I/O outside of lock
            if data_copy:
                # Ensure directory exists
                self.usage_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Use file locking to handle concurrent access from multiple CAI instances
                max_retries = 5
                retry_delay = 0.1
                
                for attempt in range(max_retries):
                    try:
                        # Write to temporary file first with exclusive lock
                        temp_file = self.usage_file.with_suffix(f'.json.tmp.{os.getpid()}')
                        with open(temp_file, 'w') as f:
                            # Try to get exclusive lock (Unix only)
                            if platform.system() != 'Windows':
                                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            f.write(data_copy)
                            if platform.system() != 'Windows':
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        
                        # Before atomic rename, do one final check
                        # Read the current file one more time
                        if self.usage_file.exists():
                            try:
                                with open(self.usage_file, 'r') as f:
                                    if platform.system() != 'Windows':
                                        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                                    final_check_data = json.load(f)
                                    if platform.system() != 'Windows':
                                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                                
                                final_file_cost = final_check_data["global_totals"].get("total_cost", 0)
                                our_cost = json.loads(data_copy)["global_totals"].get("total_cost", 0)
                                
                                # Only save if our cost is >= file cost
                                if our_cost < final_file_cost:
                                    # Don't overwrite with lower value
                                    if os.getenv("CAI_DEBUG", "1") == "2":
                                        print(f"Skipping save: file cost ({final_file_cost}) > our cost ({our_cost})")
                                    return
                            except:
                                pass  # If we can't read, continue with save
                        
                        # Atomic rename with retry for concurrent access
                        for rename_attempt in range(3):
                            try:
                                temp_file.replace(self.usage_file)
                                break
                            except OSError:
                                if rename_attempt < 2:
                                    time.sleep(0.05)
                                else:
                                    raise
                        break
                    except (IOError, OSError) as e:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                        else:
                            print(f"Warning: Could not save usage data after {max_retries} attempts: {e}")
                    finally:
                        # Clean up temp file if it still exists
                        if temp_file.exists():
                            try:
                                temp_file.unlink()
                            except:
                                pass
                
        except KeyboardInterrupt:
            # Don't block on Ctrl+C, just skip saving this time
            pass
        except Exception:
            # Silently ignore other errors to not disrupt the main program
            pass
    
    def start_session(self, session_id: str, agent_name: Optional[str] = None):
        """Start tracking a new session"""
        if not self.enabled:
            return
            
        try:
            # Reload data first to ensure we have the latest
            current_data = self._load_usage_data()
            if current_data:
                self.usage_data = current_data
            
            self.session_id = session_id
            self.session_start_time = datetime.now().isoformat()
            
            # Check if session already exists (in case of restart)
            session_exists = any(s["session_id"] == session_id for s in self.usage_data["sessions"])
            
            if not session_exists:
                # Initialize session data
                session_data = {
                    "session_id": session_id,
                    "start_time": self.session_start_time,
                    "end_time": None,
                    "agent_name": agent_name,
                    "total_cost": 0.0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_requests": 0,
                    "models_used": []
                }
                
                with self._lock:
                    self.usage_data["sessions"].append(session_data)
                    self.usage_data["global_totals"]["total_sessions"] += 1
                
                # Save outside of lock to avoid blocking
                self._save_usage_data()
            
        except KeyboardInterrupt:
            # Don't block the main program on Ctrl+C
            raise
        except Exception:
            # Silently continue if tracking fails - don't disrupt the main program
            pass
    
    def track_usage(self, 
                   model_name: str,
                   input_tokens: int,
                   output_tokens: int,
                   cost: float,
                   agent_name: Optional[str] = None):
        """Track usage for a single model interaction with proper synchronization"""
        if not self.enabled:
            return
            
        try:
            # For concurrent access safety, reload data before updating
            # This ensures we don't lose updates from other CAI instances
            current_data = self._load_usage_data()
            
            with self._lock:
                # IMPORTANT: Don't just take the max - we need to properly sync the data
                # If the file has been updated by another instance, use those values as the base
                if current_data:
                    # Check if the file data is newer than our in-memory data
                    # We do this by checking if the totals in the file are larger
                    file_total_cost = current_data["global_totals"].get("total_cost", 0)
                    memory_total_cost = self.usage_data["global_totals"].get("total_cost", 0)
                    
                    # If file has more data, use it as the base
                    if file_total_cost > memory_total_cost:
                        self.usage_data = current_data
                    # If our memory has more data but file exists, we might have a sync issue
                    # In this case, we should still respect the file data for shared fields
                    elif file_total_cost > 0 and file_total_cost < memory_total_cost:
                        # Another instance might have reset or we have stale data
                        # Use the file as the authoritative source
                        self.usage_data = current_data
                
                # Now update with new usage
                self.usage_data["global_totals"]["total_cost"] += cost
                self.usage_data["global_totals"]["total_input_tokens"] += input_tokens
                self.usage_data["global_totals"]["total_output_tokens"] += output_tokens
                self.usage_data["global_totals"]["total_requests"] += 1
                
                # Update model-specific usage
                if model_name not in self.usage_data["model_usage"]:
                    self.usage_data["model_usage"][model_name] = {
                        "total_cost": 0.0,
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_requests": 0
                    }
                
                model_stats = self.usage_data["model_usage"][model_name]
                model_stats["total_cost"] += cost
                model_stats["total_input_tokens"] += input_tokens
                model_stats["total_output_tokens"] += output_tokens
                model_stats["total_requests"] += 1
                
                # Update daily usage
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in self.usage_data["daily_usage"]:
                    self.usage_data["daily_usage"][today] = {
                        "total_cost": 0.0,
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_requests": 0
                    }
                
                daily_stats = self.usage_data["daily_usage"][today]
                daily_stats["total_cost"] += cost
                daily_stats["total_input_tokens"] += input_tokens
                daily_stats["total_output_tokens"] += output_tokens
                daily_stats["total_requests"] += 1
                
                # Update current session if active
                if self.session_id and self.usage_data["sessions"]:
                    # Find current session (should be the last one)
                    for session in reversed(self.usage_data["sessions"]):
                        if session["session_id"] == self.session_id:
                            session["total_cost"] += cost
                            session["total_input_tokens"] += input_tokens
                            session["total_output_tokens"] += output_tokens
                            session["total_requests"] += 1
                            
                            # Track models used
                            if model_name not in session["models_used"]:
                                session["models_used"].append(model_name)
                            
                            # Update agent name if provided
                            if agent_name and not session.get("agent_name"):
                                session["agent_name"] = agent_name
                            
                            break
            
            # Save after every update for better consistency across instances
            self._save_usage_data()
                
        except KeyboardInterrupt:
            # Don't block on Ctrl+C
            raise
        except Exception as e:
            # Log the error but continue
            import traceback
            if os.getenv("CAI_DEBUG", "1") == "2":
                print(f"Error tracking usage: {e}")
                traceback.print_exc()
            pass
    
    def end_session(self, final_cost: Optional[float] = None):
        """End the current session"""
        if not self.enabled:
            return
            
        try:
            # Reload data to get latest updates
            current_data = self._load_usage_data()
            if current_data:
                self.usage_data = current_data
            
            if self.session_id and self.usage_data["sessions"]:
                with self._lock:
                    # Find and update current session
                    for session in reversed(self.usage_data["sessions"]):
                        if session["session_id"] == self.session_id:
                            session["end_time"] = datetime.now().isoformat()
                            if final_cost is not None:
                                session["total_cost"] = final_cost
                            break
                
                # Save outside of lock
                self._save_usage_data()
            
            self.session_id = None
            
        except KeyboardInterrupt:
            # Don't block on Ctrl+C
            raise
        except Exception:
            # Silently continue if tracking fails
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of usage statistics"""
        with self._lock:
            return {
                "global_totals": self.usage_data["global_totals"].copy(),
                "top_models": sorted(
                    [(model, stats["total_cost"]) 
                     for model, stats in self.usage_data["model_usage"].items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "recent_sessions": self.usage_data["sessions"][-10:]
            }

# Global instance
GLOBAL_USAGE_TRACKER = GlobalUsageTracker()