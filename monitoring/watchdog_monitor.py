# ============================================================
# ENTROPY - File System Monitor
# monitoring\watchdog_monitor.py
#
# WHAT THIS DOES:
# Watches folders for file activity.
# When a file is created, modified, deleted, or renamed,
# this module captures the event and stores it.
# ============================================================

import os
import sys
import time
import json
import hashlib
import psutil
import logging
from datetime import datetime
from collections import deque, defaultdict
from threading import Lock

# Add parent folder to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Setup Logging ────────────────────────────────────────────
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s [%(levelname)s] %(message)s",
    handlers = [
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Fix Windows terminal encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log = logging.getLogger("FileMonitor")


# ============================================================
# EVENT STORE
# Stores all captured file events in memory.
# Other components (AI engine) will read from here.
# ============================================================

class EventStore:
    """
    Thread-safe storage for file system events.
    
    Think of this as a shared notebook.
    The monitor WRITES events into it.
    The AI engine READS events from it.
    """
    
    def __init__(self, max_events=1000):
        self.events    = deque(maxlen=max_events)
        self.lock      = Lock()
        self.callbacks = []
    
    def add_event(self, event):
        """Add a new event to the store."""
        with self.lock:
            self.events.append(event)
        
        # Notify all registered callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                log.error(f"Callback error: {e}")
    
    def get_recent_events(self, n=50):
        """Get the most recent N events."""
        with self.lock:
            return list(self.events)[-n:]
    
    def get_all_events(self):
        """Get all stored events."""
        with self.lock:
            return list(self.events)
    
    def register_callback(self, func):
        """
        Register a function to be called when a new event arrives.
        The AI engine will register itself here.
        """
        self.callbacks.append(func)
    
    def clear(self):
        """Clear all events."""
        with self.lock:
            self.events.clear()


# ============================================================
# PROCESS FINDER
# When a file event occurs, we want to know WHICH process
# caused it. We use fast lookup only (no slow file handle scan).
# ============================================================

class ProcessFinder:
    """
    Best-effort process identification.
    
    Uses fast recent-process scan.
    Slow file handle scanning is disabled for performance.
    """
    
    def __init__(self):
        self.process_cache = {}
    
    def get_process_info(self, file_path):
        """Fast lookup — returns most recently started suspicious process."""
        return self._find_recent_suspicious()
    
    def _find_recent_suspicious(self):
        """Find the most recently started non-whitelisted process."""
        suspicious = []
        current_time = time.time()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time', 
                                              'exe', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Skip whitelisted processes using a case-insensitive
                    # comparison. Keep the creation time in the event so the
                    # response layer can detect PID reuse before terminating.
                    process_name = proc_info.get('name') or ''
                    whitelist = {name.lower() for name in config.WHITELISTED_PROCESSES}
                    if process_name.lower() in whitelist:
                        continue

                    # Only consider recently started processes (last 60s).
                    create_time = proc_info.get('create_time')
                    if create_time is None:
                        continue
                    age = current_time - create_time
                    if age < 60:
                        suspicious.append({
                            'pid'        : proc_info['pid'],
                            'name'       : process_name,
                            'create_time': create_time,
                            # This scanner finds a recent process; it does
                            # not prove that the process caused this file
                            # event. Automatic termination must therefore
                            # remain disabled for this attribution source.
                            'identity_verified': False,
                            'age_seconds': round(age, 2),
                            'exe'        : proc_info.get('exe'),
                            'status'     : proc_info.get('status'),
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            log.debug(f"Recent process scan error: {e}")
        
        # Return the most recently started one
        if suspicious:
            suspicious.sort(key=lambda x: x['age_seconds'])
            return suspicious[0]
        
        return None


# ============================================================
# SPEED TRACKER
# Tracks how many files are being modified per second.
# This is a key ransomware indicator.
# ============================================================

class SpeedTracker:
    """
    Tracks the rate of file modifications.
    
    Normal user:     1-3 files modified per minute
    Ransomware:      10-100 files modified per second
    
    We track events in a sliding time window.
    """
    
    def __init__(self, window_seconds=10):
        self.window   = window_seconds
        self.events   = deque()
        self.lock     = Lock()
    
    def record_event(self):
        """Record that a file event just happened."""
        now = time.time()
        with self.lock:
            self.events.append(now)
            self._cleanup_old(now)
    
    def get_rate(self):
        """
        Get the current rate of events per second.
        Based on events in the last window_seconds.
        """
        now = time.time()
        with self.lock:
            self._cleanup_old(now)
            if self.window > 0:
                return len(self.events) / self.window
            return 0
    
    def get_count_in_window(self):
        """Get the total count of events in the current window."""
        now = time.time()
        with self.lock:
            self._cleanup_old(now)
            return len(self.events)
    
    def _cleanup_old(self, now):
        """Remove events older than the window."""
        cutoff = now - self.window
        while self.events and self.events[0] < cutoff:
            self.events.popleft()


# ============================================================
# FILE EVENT HANDLER
# This is the core of the watchdog integration.
# watchdog calls these methods when file events occur.
# ============================================================

class EntropyEventHandler(FileSystemEventHandler):
    """
    Handles file system events detected by watchdog.
    
    When a file is created/modified/deleted/renamed,
    watchdog calls the corresponding method here.
    We then build a structured event and store it.
    """
    
    def __init__(self, event_store, speed_tracker, process_finder):
        super().__init__()
        self.event_store    = event_store
        self.speed_tracker  = speed_tracker
        self.process_finder = process_finder
        
        # Track file counts per process (PID → count)
        self.file_counts = defaultdict(int)
    
    def on_created(self, event):
        """Called when a file or folder is created."""
        if event.is_directory:
            return
        self._handle_event("CREATED", event.src_path)
    
    def on_modified(self, event):
        """Called when a file or folder is modified."""
        if event.is_directory:
            return
        self._handle_event("MODIFIED", event.src_path)
    
    def on_deleted(self, event):
        """Called when a file or folder is deleted."""
        if event.is_directory:
            return
        self._handle_event("DELETED", event.src_path)
    
    def on_moved(self, event):
        """Called when a file or folder is renamed/moved."""
        if event.is_directory:
            return
        self._handle_event("RENAMED", event.src_path, 
                           dest_path=event.dest_path)
    
    def _handle_event(self, event_type, file_path, dest_path=None):
        """
        Core event handler.
        Builds a structured event dictionary and stores it.
        
        This is called for ALL file events.
        """
        
        # Skip temporary files and system files
        if self._should_ignore(file_path):
            return
        
        # Record this event in speed tracker
        self.speed_tracker.record_event()
        
        # Get current speed
        current_rate  = self.speed_tracker.get_rate()
        events_in_win = self.speed_tracker.get_count_in_window()
        
        # Try to find which process caused this
        process_info = self.process_finder.get_process_info(file_path)
        
        # Get file extension
        _, ext = os.path.splitext(file_path)
        
        # Check if file still exists (for size/hash)
        file_size = None
        if event_type != "DELETED" and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
            except Exception:
                pass
        
        # Build the event dictionary
        # This is what the AI engine will receive
        event = {
            # ── Identity ──────────────────────────────
            'event_id'       : self._generate_event_id(),
            'timestamp'      : datetime.now().isoformat(),
            'unix_timestamp' : time.time(),
            
            # ── What happened ─────────────────────────
            'event_type'     : event_type,
            'file_path'      : file_path,
            'dest_path'      : dest_path,
            'file_extension' : ext.lower(),
            'file_size'      : file_size,
            
            # ── Speed indicators ──────────────────────
            'events_per_sec' : round(current_rate, 2),
            'events_in_window': events_in_win,
            
            # ── Process information ───────────────────
            'process'        : process_info,
            
            # ── Initial analysis flags ────────────────
            'is_suspicious_speed' : current_rate > config.FILES_PER_SECOND_THRESHOLD,
            'ext_changed'    : self._check_ext_changed(file_path, dest_path),
            
            # ── Status ────────────────────────────────
            'entropy_score'  : None,
            'ai_decision'    : None,
            'action_taken'   : None,
        }
        
        # Store the event
        self.event_store.add_event(event)
        
        # Log to terminal
        self._log_event(event)
    
    def _should_ignore(self, file_path):
        """
        Returns True if we should ignore this file event.
        
        We ignore:
        - Temporary files (start with ~ or end with .tmp)
        - System files
        - Our own quarantine folder
        - Log files
        - Files in hidden folders
        """
        
        path_lower = file_path.lower()
        
        # Ignore temporary files
        ignore_extensions = ['.tmp', '.temp', '.log', '.lock']
        for ext in ignore_extensions:
            if path_lower.endswith(ext):
                return True
        
        # Ignore temp file patterns
        filename = os.path.basename(file_path)
        if filename.startswith('~') or filename.startswith('.'):
            return True
        
        # Ignore our own quarantine folder
        if config.QUARANTINE_DIR.lower() in path_lower:
            return True
        
        # Ignore our own log folder
        if config.LOG_DIR.lower() in path_lower:
            return True
        
        return False
    
    def _check_ext_changed(self, src_path, dest_path):
        """
        Check if file extension changed.
        
        Ransomware often renames:
        photo.jpg → photo.jpg.locked
        document.docx → document.encrypted
        
        This is a strong ransomware indicator.
        """
        if not dest_path:
            return False
        
        _, src_ext  = os.path.splitext(src_path)
        _, dest_ext = os.path.splitext(dest_path)
        
        return src_ext.lower() != dest_ext.lower()
    
    def _generate_event_id(self):
        """Generate a unique ID for this event."""
        timestamp = str(time.time()).encode()
        return hashlib.md5(timestamp).hexdigest()[:12]
    
    def _log_event(self, event):
        """Print a formatted log line for this event."""
        
        # Use plain text symbols (no emoji - Windows terminal safe)
        symbols = {
            'CREATED' : '[+]',
            'MODIFIED': '[~]',
            'DELETED' : '[-]',
            'RENAMED' : '[>]',
        }
        
        symbol = symbols.get(event['event_type'], '[?]')
        
        # Build log message
        filename = os.path.basename(event['file_path'])
        rate     = event['events_per_sec']
        
        msg = (f"{symbol} {event['event_type']:8} | "
               f"{filename:40} | "
               f"{rate:.1f} events/sec")
        
        # Highlight suspicious speed
        if event['is_suspicious_speed']:
            msg += " *** HIGH SPEED ***"
        
        log.info(msg)


# ============================================================
# FILE MONITOR
# The main class that puts everything together.
# ============================================================

class FileMonitor:
    """
    Main file monitoring class.
    
    Creates and manages:
    - EventStore (stores all events)
    - SpeedTracker (tracks modification rate)
    - ProcessFinder (identifies processes)
    - EntropyEventHandler (handles watchdog events)
    - Observer (watchdog's file system watcher)
    """
    
    def __init__(self):
        # Initialize components
        self.event_store    = EventStore(max_events=1000)
        self.speed_tracker  = SpeedTracker(window_seconds=10)
        self.process_finder = ProcessFinder()
        
        # Create event handler
        self.handler = EntropyEventHandler(
            self.event_store,
            self.speed_tracker,
            self.process_finder
        )
        
        # Create watchdog observer
        self.observer = Observer()
        self.running  = False
    
    def start(self):
        """
        Start monitoring all configured folders.
        """
        log.info("=" * 60)
        log.info("  ENTROPY File Monitor Starting")
        log.info("=" * 60)
        
        # Schedule monitoring for each folder in config
        folders_watched = 0
        for folder in config.WATCH_FOLDERS:
            if os.path.exists(folder):
                self.observer.schedule(
                    self.handler,
                    folder,
                    recursive=True
                )
                log.info(f"[WATCHING] {folder}")
                folders_watched += 1
            else:
                log.warning(f"[SKIP] Folder not found: {folder}")
        
        if folders_watched == 0:
            log.error("No valid folders to watch! Check config.py WATCH_FOLDERS")
            return
        
        # Start the observer
        self.observer.start()
        self.running = True
        
        log.info(f"")
        log.info(f"Monitoring {folders_watched} folder(s)")
        log.info(f"Speed threshold: {config.FILES_PER_SECOND_THRESHOLD} files/sec")
        log.info(f"Entropy threshold: {config.ENTROPY_THRESHOLD}")
        log.info(f"")
        log.info(f"Waiting for file activity...")
        log.info(f"Press Ctrl+C to stop")
        log.info(f"")
    
    def stop(self):
        """Stop monitoring."""
        log.info("Stopping file monitor...")
        self.observer.stop()
        self.observer.join()
        self.running = False
        log.info("File monitor stopped.")
    
    def get_stats(self):
        """Get current monitoring statistics."""
        return {
            'total_events'    : len(self.event_store.get_all_events()),
            'current_rate'    : self.speed_tracker.get_rate(),
            'events_in_window': self.speed_tracker.get_count_in_window(),
            'is_running'      : self.running,
        }
    
    def register_callback(self, func):
        """
        Register a callback function.
        Called whenever a new file event is detected.
        The AI engine uses this to receive events.
        """
        self.event_store.register_callback(func)


# ============================================================
# STANDALONE TEST
# Run this file directly to test the monitor alone.
# ============================================================

if __name__ == "__main__":
    
    print()
    print("=" * 60)
    print("  ENTROPY - File Monitor Test")
    print("=" * 60)
    print()
    print("This will monitor your configured folders.")
    print("Try creating, editing, or deleting files.")
    print("You should see events appear below.")
    print()
    
    # Create monitor
    monitor = FileMonitor()
    
    # Register a simple test callback
    def on_event(event):
        """This is called every time a file event happens."""
        pass    # The handler already logs to terminal
    
    monitor.register_callback(on_event)
    
    # Start monitoring
    monitor.start()
    
    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(5)
            
            # Print stats every 30 seconds
            stats = monitor.get_stats()
            log.info(f"[STATS] Total events: {stats['total_events']} | "
                    f"Current rate: {stats['current_rate']:.2f}/sec")
    
    except KeyboardInterrupt:
        print()
        print("Stopping...")
        monitor.stop()
        
        # Show final stats
        stats = monitor.get_stats()
        print()
        print(f"Final Stats:")
        print(f"  Total events captured: {stats['total_events']}")
        print()
        
        # Show last 5 events
        recent = monitor.event_store.get_recent_events(5)
        if recent:
            print("Last 5 events:")
            for e in recent:
                print(f"  {e['event_type']:8} | {e['file_path']}")