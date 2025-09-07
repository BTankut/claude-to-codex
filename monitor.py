#!/usr/bin/env python3
"""
ClaudeToCodex Monitor - Real-time execution monitoring
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import threading
import queue
import time
from datetime import datetime
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'claudetocodex-monitor-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global queue for messages
message_queue = queue.Queue()
current_execution = {
    'task': None,
    'plan': [],
    'current_step': 0,
    'status': 'idle',
    'logs': []
}

@app.route('/')
def index():
    """Main monitoring page"""
    return render_template('monitor.html')

@app.route('/api/status')
def get_status():
    """Get current execution status"""
    return json.dumps(current_execution)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"✅ Monitor client connected: {request.sid}")
    emit('status', current_execution)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"❌ Monitor client disconnected: {request.sid}")

def broadcast_update(event_type, data):
    """Broadcast update to all connected clients"""
    socketio.emit(event_type, data)
    
def log_message(level, message, details=None):
    """Add log message and broadcast"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,  # info, success, warning, error
        'message': message,
        'details': details
    }
    current_execution['logs'].append(log_entry)
    
    # Keep only last 100 logs
    if len(current_execution['logs']) > 100:
        current_execution['logs'] = current_execution['logs'][-100:]
    
    broadcast_update('log', log_entry)

# Modified orchestrator integration
class MonitoredOrchestrator:
    """Wrapper for CodexOrchestrator with monitoring"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.original_execute_command = orchestrator.execute_codex_command
        self.original_set_plan = orchestrator.set_task_plan
        self.original_execute_plan = orchestrator.execute_plan
        
        # Monkey patch methods
        orchestrator.execute_codex_command = self.monitored_execute_command
        orchestrator.set_task_plan = self.monitored_set_plan
        orchestrator.execute_plan = self.monitored_execute_plan
    
    def monitored_set_plan(self, plan):
        """Monitor plan setting"""
        current_execution['plan'] = plan
        current_execution['status'] = 'planning'
        current_execution['current_step'] = 0
        
        log_message('info', f"📋 Plan received: {len(plan)} steps")
        for i, step in enumerate(plan, 1):
            log_message('info', f"  {i}. {step.get('description', 'Step')}")
        
        broadcast_update('plan_set', {'plan': plan})
        return self.original_set_plan(plan)
    
    def monitored_execute_command(self, instruction, context=""):
        """Monitor command execution"""
        current_execution['status'] = 'executing'
        
        # Log Claude → Codex communication
        log_message('info', "🤖 Claude → Codex", {
            'instruction': instruction[:200] + '...' if len(instruction) > 200 else instruction,
            'has_context': bool(context)
        })
        
        broadcast_update('executing', {
            'step': current_execution['current_step'],
            'instruction': instruction[:100]
        })
        
        # Execute original
        result = self.original_execute_command(instruction, context)
        
        # Log Codex response
        if result['success']:
            log_message('success', "✅ Codex completed task", {
                'stdout_preview': (result.get('stdout', '')[:200] or '').strip(),
                'returncode': result.get('returncode', 0)
            })
        else:
            log_message('error', "❌ Codex execution failed", {
                'error': result.get('error', 'Unknown error'),
                'stderr': (result.get('stderr', '')[:200] or '').strip()
            })
        
        broadcast_update('executed', {
            'step': current_execution['current_step'],
            'success': result['success']
        })
        
        return result
    
    def monitored_execute_plan(self):
        """Monitor plan execution"""
        current_execution['status'] = 'running'
        current_execution['logs'] = []
        
        log_message('info', "🚀 Starting plan execution")
        broadcast_update('execution_started', {})
        
        # Execute with step tracking
        results = []
        for i, step in enumerate(self.orchestrator.task_plan, 1):
            current_execution['current_step'] = i
            
            log_message('info', f"📍 Step {i}/{len(self.orchestrator.task_plan)}: {step.get('description', '')}")
            broadcast_update('step_started', {'step': i, 'description': step.get('description', '')})
            
            # Execute step
            instruction = step.get('instruction', '')
            context = step.get('context', '')
            result = self.orchestrator.execute_codex_command(instruction, context)
            
            results.append({
                'step': i,
                'description': step.get('description', ''),
                'result': result
            })
            
            if not result['success'] and step.get('critical', True):
                log_message('error', f"🛑 Critical step failed, stopping execution")
                break
            
            time.sleep(1)  # Brief pause between steps
        
        # Generate report
        report = self.orchestrator.generate_report(results)
        
        current_execution['status'] = 'completed'
        log_message('success', f"📊 Execution completed: {report['summary']['success_rate']}")
        
        broadcast_update('execution_completed', {'report': report})
        return report

def run_monitor(port=5555):
    """Run the monitoring server"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          ClaudeToCodex Monitor - Real-time Viewer           ║
╚══════════════════════════════════════════════════════════════╝

🌐 Monitor URL: http://localhost:{port}
📡 WebSocket: ws://localhost:{port}/socket.io/

Ready to monitor Claude ↔ Codex communication!
    """)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_monitor()