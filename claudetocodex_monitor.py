#!/usr/bin/env python3
"""
ClaudeToCodex with Monitoring - Execute tasks with real-time monitoring
"""

import sys
import os
import threading
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from codex_orchestrator import CodexOrchestrator
from codex_master import MasterController, TASK_TEMPLATES
from monitor import MonitoredOrchestrator, run_monitor, log_message, current_execution, broadcast_update
import webbrowser

def start_monitor_server():
    """Start monitoring server in background thread"""
    thread = threading.Thread(target=run_monitor, kwargs={'port': 5555})
    thread.daemon = True
    thread.start()
    time.sleep(2)  # Give server time to start
    
    # Open browser
    webbrowser.open('http://localhost:5555')
    print("📊 Monitor opened in browser: http://localhost:5555")

def execute_with_monitoring(task_type, task_description, custom_steps=None):
    """Execute task with monitoring enabled"""
    
    # Start monitor server
    start_monitor_server()
    
    # Create orchestrator with monitoring
    orchestrator = CodexOrchestrator()
    monitored = MonitoredOrchestrator(orchestrator)
    
    # Create master controller
    master = MasterController()
    master.orchestrator = orchestrator  # Use monitored orchestrator
    
    # Set task info for monitor
    current_execution['task'] = task_description
    broadcast_update('task_set', {'task': task_description})
    
    # Get steps
    if custom_steps:
        steps = custom_steps
    elif task_type in TASK_TEMPLATES:
        steps = TASK_TEMPLATES[task_type]
    else:
        log_message('error', f"Unknown task type: {task_type}")
        return None
    
    # Create and execute plan
    log_message('info', f"🎯 Task: {task_description}")
    plan = master.create_plan(task_description, steps)
    
    # Wait a bit for user to see the plan
    time.sleep(3)
    
    # Execute
    log_message('info', "🚀 Starting execution...")
    report = master.execute(plan)
    
    return report

def main():
    """Main entry point with monitoring"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           ClaudeToCodex with Real-time Monitoring            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  claudetocodex_monitor.py <command> [args]")
        print("\nCommands:")
        print("  quick <instruction>  - Single command")
        print("  project <name>       - Create project")
        print("  feature <desc>       - Add feature")
        print("  debug <issue>        - Fix bug")
        print("  refactor <target>    - Refactor code")
        print("\nExample:")
        print("  python3 claudetocodex_monitor.py project 'Todo API'")
        return
    
    command = sys.argv[1].lower()
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    if not args:
        print(f"❌ Description required for {command}")
        return
    
    # Map commands to task types
    task_map = {
        "project": "create_project",
        "feature": "add_feature",
        "debug": "debug_fix",
        "refactor": "refactor"
    }
    
    if command == "quick":
        # Quick single command
        start_monitor_server()
        orchestrator = CodexOrchestrator()
        monitored = MonitoredOrchestrator(orchestrator)
        
        current_execution['task'] = args
        current_execution['status'] = 'executing'
        
        log_message('info', f"🚀 Quick command: {args}")
        result = orchestrator.execute_codex_command(args)
        
        if result['success']:
            log_message('success', "✅ Command completed successfully")
        else:
            log_message('error', "❌ Command failed")
        
        print("\n✨ Check the monitor for details!")
        input("Press Enter to exit...")
        
    elif command in task_map:
        # Template-based task
        result = execute_with_monitoring(
            task_type=task_map[command],
            task_description=args
        )
        
        if result:
            print(f"\n✅ Task completed!")
            print(f"📊 Success rate: {result.get('summary', {}).get('success_rate', 'N/A')}")
        
        print("\n✨ Check the monitor for full details!")
        input("Press Enter to exit...")
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()