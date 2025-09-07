#!/usr/bin/env python3
"""
Codex Process Manager - Manage Codex sessions and processes
"""

import subprocess
import psutil
import json
import os
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class CodexProcessManager:
    """Manage Codex processes and sessions"""
    
    def __init__(self):
        self.pid_file = Path.home() / '.claudetocodex' / 'pids.json'
        self.session_dir = Path.home() / '.codex' / 'sessions'
        self.pid_file.parent.mkdir(exist_ok=True)
        self.active_pids = self.load_pids()
        
    def load_pids(self) -> Dict:
        """Load tracked PIDs from file"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_pids(self):
        """Save tracked PIDs to file"""
        with open(self.pid_file, 'w') as f:
            json.dump(self.active_pids, f, indent=2)
    
    def find_codex_processes(self) -> List[Dict]:
        """Find all running Codex processes"""
        codex_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # Check if it's a Codex process
                if 'codex' in cmdline.lower() or 'openai-codex' in cmdline.lower():
                    codex_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'created': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                        'cpu_percent': proc.cpu_percent(interval=0.1),
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'status': proc.status()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return codex_processes
    
    def track_pid(self, pid: int, task: str, project_dir: str = None):
        """Track a new Codex PID"""
        self.active_pids[str(pid)] = {
            'task': task,
            'project_dir': project_dir,
            'started': datetime.now().isoformat(),
            'status': 'active'
        }
        self.save_pids()
        print(f"📌 Tracking Codex PID {pid} for task: {task}")
    
    def kill_process(self, pid: int, force: bool = False):
        """Kill a specific Codex process"""
        try:
            proc = psutil.Process(pid)
            
            # Try graceful termination first
            if not force:
                proc.terminate()
                print(f"🔄 Terminating PID {pid} gracefully...")
                time.sleep(2)
            
            # Force kill if still running
            if proc.is_running():
                proc.kill()
                print(f"⚠️ Force killed PID {pid}")
            else:
                print(f"✅ PID {pid} terminated")
            
            # Remove from tracking
            if str(pid) in self.active_pids:
                del self.active_pids[str(pid)]
                self.save_pids()
                
        except psutil.NoSuchProcess:
            print(f"❌ PID {pid} not found")
            if str(pid) in self.active_pids:
                del self.active_pids[str(pid)]
                self.save_pids()
        except Exception as e:
            print(f"❌ Error killing PID {pid}: {e}")
    
    def cleanup_stale_processes(self, threshold_hours: int = 24):
        """Kill Codex processes older than threshold"""
        current_time = time.time()
        killed_count = 0
        
        for proc in self.find_codex_processes():
            age_hours = (current_time - psutil.Process(proc['pid']).create_time()) / 3600
            
            if age_hours > threshold_hours:
                print(f"🧹 Cleaning stale process PID {proc['pid']} (age: {age_hours:.1f}h)")
                self.kill_process(proc['pid'])
                killed_count += 1
        
        return killed_count
    
    def cleanup_high_cpu(self, cpu_threshold: float = 90.0):
        """Kill Codex processes with high CPU usage"""
        killed_count = 0
        
        for proc in self.find_codex_processes():
            if proc['cpu_percent'] > cpu_threshold:
                print(f"🔥 Killing high CPU process PID {proc['pid']} (CPU: {proc['cpu_percent']:.1f}%)")
                self.kill_process(proc['pid'], force=True)
                killed_count += 1
        
        return killed_count
    
    def get_latest_session(self, project_dir: str = None) -> Optional[Path]:
        """Get the latest Codex session file"""
        if not self.session_dir.exists():
            return None
        
        # Search in nested date folders
        session_files = list(self.session_dir.rglob('*.jsonl'))
        
        if project_dir:
            # Filter sessions by project directory (multiple formats)
            filtered = []
            for file in session_files:
                try:
                    with open(file, 'r') as f:
                        content = f.read()
                        if (f'<cwd>{project_dir}</cwd>' in content or 
                            f'"cwd":"{project_dir}"' in content or
                            project_dir in content):
                            filtered.append(file)
                except:
                    continue
            session_files = filtered
        
        if not session_files:
            return None
        
        # Return most recent
        return max(session_files, key=lambda f: f.stat().st_mtime)
    
    def get_session_info(self, session_file: Path) -> Dict:
        """Get information about a session file"""
        if not session_file.exists():
            return {}
        
        info = {
            'file': str(session_file),
            'size_mb': session_file.stat().st_size / 1024 / 1024,
            'modified': datetime.fromtimestamp(session_file.stat().st_mtime).isoformat(),
            'lines': 0,
            'messages': 0,
            'has_context': False
        }
        
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    info['lines'] += 1
                    if '"role":"user"' in line or '"role":"assistant"' in line:
                        info['messages'] += 1
                    if 'context' in line.lower():
                        info['has_context'] = True
        except:
            pass
        
        return info
    
    def status_report(self) -> Dict:
        """Generate a status report of all Codex processes"""
        processes = self.find_codex_processes()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'active_processes': len(processes),
            'tracked_pids': len(self.active_pids),
            'total_cpu': sum(p['cpu_percent'] for p in processes),
            'total_memory_mb': sum(p['memory_mb'] for p in processes),
            'processes': processes,
            'tracked': self.active_pids
        }
        
        return report
    
    def print_status(self):
        """Print a formatted status report"""
        report = self.status_report()
        
        print("\n" + "="*60)
        print("📊 CODEX PROCESS STATUS")
        print("="*60)
        print(f"🕐 Time: {report['timestamp']}")
        print(f"🔢 Active Processes: {report['active_processes']}")
        print(f"📌 Tracked PIDs: {report['tracked_pids']}")
        print(f"💻 Total CPU: {report['total_cpu']:.1f}%")
        print(f"💾 Total Memory: {report['total_memory_mb']:.1f} MB")
        
        if report['processes']:
            print("\n📋 Running Processes:")
            for proc in report['processes']:
                print(f"  PID {proc['pid']}: CPU={proc['cpu_percent']:.1f}%, "
                      f"Mem={proc['memory_mb']:.1f}MB, Status={proc['status']}")
                if str(proc['pid']) in report['tracked']:
                    task = report['tracked'][str(proc['pid'])]['task']
                    print(f"    Task: {task}")
        else:
            print("\n✅ No Codex processes running")
        
        print("="*60)


def main():
    """CLI for process management"""
    import sys
    
    manager = CodexProcessManager()
    
    if len(sys.argv) < 2:
        print("""
Usage:
  process_manager.py status       - Show all Codex processes
  process_manager.py kill <pid>   - Kill specific process
  process_manager.py cleanup      - Kill stale processes (>24h)
  process_manager.py cleanup-cpu  - Kill high CPU processes (>90%)
  process_manager.py killall      - Kill all Codex processes
  process_manager.py session      - Show latest session info
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        manager.print_status()
        
    elif command == 'kill' and len(sys.argv) > 2:
        pid = int(sys.argv[2])
        manager.kill_process(pid)
        
    elif command == 'cleanup':
        killed = manager.cleanup_stale_processes()
        print(f"✅ Cleaned up {killed} stale processes")
        
    elif command == 'cleanup-cpu':
        killed = manager.cleanup_high_cpu()
        print(f"✅ Killed {killed} high CPU processes")
        
    elif command == 'killall':
        processes = manager.find_codex_processes()
        for proc in processes:
            manager.kill_process(proc['pid'])
        print(f"✅ Killed {len(processes)} processes")
        
    elif command == 'session':
        session = manager.get_latest_session()
        if session:
            info = manager.get_session_info(session)
            print(f"📁 Latest session: {info['file']}")
            print(f"  Size: {info['size_mb']:.2f} MB")
            print(f"  Messages: {info['messages']}")
            print(f"  Modified: {info['modified']}")
        else:
            print("❌ No session files found")
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == '__main__':
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("❌ psutil required. Install with: pip install psutil")
        exit(1)
    
    main()