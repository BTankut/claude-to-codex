#!/usr/bin/env python3
"""
ClaudeToCodex Monitor V2 - Real-time WebSocket monitoring
Based on proven WebSocket broadcast patterns
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import time
from datetime import datetime
import os
import sys
from typing import List, Dict, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'claudetocodex-monitor-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
current_execution = {
    'task': None,
    'plan': [],
    'current_step': 0,
    'total_steps': 0,
    'status': 'idle',
    'logs': [],
    'start_time': None,
    'end_time': None
}

# Connected clients tracking
connected_clients = set()

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
    client_id = request.sid
    connected_clients.add(client_id)
    print(f"✅ Client connected: {client_id} | Total: {len(connected_clients)}")
    
    # Send current state to new client
    emit('state_update', current_execution)
    emit('connection_status', {'connected': True, 'client_id': client_id})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    if client_id in connected_clients:
        connected_clients.remove(client_id)
    print(f"❌ Client disconnected: {client_id} | Total: {len(connected_clients)}")

def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected clients"""
    if not connected_clients:
        print("⚠️ No clients connected to broadcast to")
        return
    
    print(f"📡 Broadcasting to {len(connected_clients)} clients: {message.get('type')}")
    
    # Emit to all connected clients (room=None means broadcast to all)
    socketio.emit('message', message, room=None)

def log_and_broadcast(level: str, message: str, details: Dict = None):
    """Log message and broadcast to all clients"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,  # info, success, warning, error
        'message': message,
        'details': details or {}
    }
    
    # Add to logs
    current_execution['logs'].append(log_entry)
    
    # Keep only last 100 logs
    if len(current_execution['logs']) > 100:
        current_execution['logs'] = current_execution['logs'][-100:]
    
    # Broadcast log entry
    broadcast_message({
        'type': 'log',
        'data': log_entry
    })

class MonitoredOrchestratorV2:
    """Enhanced wrapper for CodexOrchestrator with WebSocket broadcasting"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        
        # Store original methods
        self._original_execute_command = orchestrator.execute_codex_command
        self._original_set_plan = orchestrator.set_task_plan
        self._original_execute_plan = orchestrator.execute_plan
        
        # Patch methods to add monitoring
        orchestrator.execute_codex_command = self._monitored_execute_command
        orchestrator.set_task_plan = self._monitored_set_plan
        orchestrator.execute_plan = self._monitored_execute_plan
        
        print("🔌 MonitoredOrchestratorV2 initialized - methods patched")
    
    def _monitored_set_plan(self, plan):
        """Monitor plan setting with broadcast"""
        current_execution['plan'] = plan
        current_execution['total_steps'] = len(plan)
        current_execution['current_step'] = 0
        current_execution['status'] = 'planning'
        current_execution['start_time'] = datetime.now().isoformat()
        
        # Broadcast plan set event
        broadcast_message({
            'type': 'plan_set',
            'data': {
                'plan': plan,
                'total_steps': len(plan)
            }
        })
        
        log_and_broadcast('info', f"📋 Plan received: {len(plan)} steps")
        for i, step in enumerate(plan, 1):
            log_and_broadcast('info', f"  {i}. {step.get('description', 'Step')}")
        
        # Call original
        return self._original_set_plan(plan)
    
    def _monitored_execute_command(self, instruction, context=""):
        """Monitor command execution with broadcast"""
        current_execution['status'] = 'executing'
        
        # Broadcast Claude → Codex message
        broadcast_message({
            'type': 'claude_to_codex',
            'data': {
                'instruction': instruction[:200] + '...' if len(instruction) > 200 else instruction,
                'context': bool(context),
                'timestamp': datetime.now().isoformat()
            }
        })
        
        log_and_broadcast('info', "🤖 Claude → Codex", {
            'instruction_preview': instruction[:100] + '...' if len(instruction) > 100 else instruction
        })
        
        # Execute original
        start_time = time.time()
        result = self._original_execute_command(instruction, context)
        execution_time = time.time() - start_time
        
        # Broadcast Codex response
        broadcast_message({
            'type': 'codex_response',
            'data': {
                'success': result['success'],
                'execution_time': f"{execution_time:.2f}s",
                'timestamp': datetime.now().isoformat()
            }
        })
        
        if result['success']:
            log_and_broadcast('success', "✅ Codex completed task", {
                'execution_time': f"{execution_time:.2f}s"
            })
        else:
            log_and_broadcast('error', "❌ Codex execution failed", {
                'error': result.get('error', 'Unknown error')[:200]
            })
        
        return result
    
    def _monitored_execute_plan(self):
        """Monitor plan execution with broadcast"""
        current_execution['status'] = 'running'
        current_execution['start_time'] = datetime.now().isoformat()
        
        broadcast_message({
            'type': 'execution_started',
            'data': {
                'total_steps': len(self.orchestrator.task_plan),
                'timestamp': datetime.now().isoformat()
            }
        })
        
        log_and_broadcast('info', "🚀 Starting plan execution")
        
        # Track results
        results = []
        
        # Execute each step with monitoring
        for i, step in enumerate(self.orchestrator.task_plan, 1):
            current_execution['current_step'] = i
            
            # Broadcast step start
            broadcast_message({
                'type': 'step_started',
                'data': {
                    'step': i,
                    'total': len(self.orchestrator.task_plan),
                    'description': step.get('description', ''),
                    'timestamp': datetime.now().isoformat()
                }
            })
            
            log_and_broadcast('info', f"📍 Step {i}/{len(self.orchestrator.task_plan)}: {step.get('description', '')}")
            
            # Execute step
            instruction = step.get('instruction', '')
            context = step.get('context', '')
            result = self.orchestrator.execute_codex_command(instruction, context)
            
            results.append({
                'step': i,
                'description': step.get('description', ''),
                'result': result
            })
            
            # Broadcast step complete
            broadcast_message({
                'type': 'step_completed',
                'data': {
                    'step': i,
                    'success': result['success'],
                    'timestamp': datetime.now().isoformat()
                }
            })
            
            # Stop if critical step failed
            if not result['success'] and step.get('critical', True):
                log_and_broadcast('error', "🛑 Critical step failed, stopping execution")
                break
            
            time.sleep(0.5)  # Brief pause for visibility
        
        # Generate report
        report = self.orchestrator.generate_report(results)
        
        # Update state
        current_execution['status'] = 'completed'
        current_execution['end_time'] = datetime.now().isoformat()
        
        # Broadcast completion
        broadcast_message({
            'type': 'execution_completed',
            'data': {
                'success_rate': report['summary']['success_rate'],
                'completed_steps': report['summary']['completed_steps'],
                'total_steps': report['summary']['total_steps'],
                'timestamp': datetime.now().isoformat()
            }
        })
        
        log_and_broadcast('success', f"📊 Execution completed: {report['summary']['success_rate']}")
        
        return report

def emit_direct_message(agent: str, content: str):
    """Helper to emit direct messages from Codex orchestrator"""
    broadcast_message({
        'type': 'message',
        'data': {
            'agent': agent,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
    })

def run_monitor_v2(port=5555):
    """Run the monitoring server V2"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        ClaudeToCodex Monitor V2 - WebSocket Broadcast       ║
╚══════════════════════════════════════════════════════════════╝

🌐 Monitor URL: http://localhost:{port}
📡 WebSocket: ws://localhost:{port}/socket.io/
🔄 Auto-broadcast enabled for all events

Ready to monitor Claude ↔ Codex communication!
    """)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_monitor_v2()