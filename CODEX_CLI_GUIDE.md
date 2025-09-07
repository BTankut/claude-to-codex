# 🔐 Codex CLI Complete Guide - Hard-Earned Knowledge

> **⚠️ IMPORTANT**: This document contains critical information about Codex CLI usage that was obtained through extensive testing and troubleshooting. These configurations have been proven to work in production.

## 📋 Table of Contents
1. [Critical Parameters](#critical-parameters)
2. [STDIN Usage](#stdin-usage)
3. [Environment Variables](#environment-variables)
4. [Working Directory](#working-directory)
5. [Process Management](#process-management)
6. [Session Management](#session-management)
7. [Common Issues and Solutions](#common-issues)
8. [Best Practices](#best-practices)

---

## 🎯 Critical Parameters

### The Golden Command
```bash
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json
```

### Parameter Breakdown

| Flag | Purpose | Critical? |
|------|---------|-----------|
| `exec` | Non-interactive execution mode | ✅ Yes |
| `--dangerously-bypass-approvals-and-sandbox` | Bypass ALL security prompts | ✅ Yes |
| `--skip-git-repo-check` | Skip git repository validation | ✅ Yes |
| `--json` | Output in JSON format | ✅ Yes |
| `--sandbox workspace-write` | Alternative sandbox mode | ⚠️ Sometimes |

### Sandbox Modes
```bash
# Available modes (discovered through testing)
--sandbox read-only           # Default, can't write files
--sandbox workspace-write      # Can write in working directory
--sandbox danger-full-access   # Full system access
```

---

## 📥 STDIN Usage (CRITICAL!)

### ⚠️ Most Important Discovery
**Codex expects prompts via STDIN, not as command arguments!**

### Correct Implementation (Python)
```python
import subprocess

# CORRECT: Using STDIN
process = subprocess.Popen(
    [
        codex_path,
        'exec',
        '--dangerously-bypass-approvals-and-sandbox',
        '--skip-git-repo-check',
        '--json'
    ],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=working_directory,
    env=env,
    text=True
)

# Send instruction via STDIN
stdout, stderr = process.communicate(input=instruction)
```

### Async Version
```python
import asyncio

process = await asyncio.create_subprocess_exec(
    codex_cmd, 
    "exec", 
    "--dangerously-bypass-approvals-and-sandbox", 
    "--skip-git-repo-check", 
    "--json",
    cwd=self.working_directory,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=env
)

# Send prompt via STDIN
stdout, stderr = await process.communicate(input=instruction.encode('utf-8'))
```

### ❌ WRONG: Command argument approach
```python
# THIS WILL NOT WORK!
subprocess.run([codex_cmd, 'exec', instruction])  # ❌ WRONG
```

---

## 🌍 Environment Variables

### Disable Terminal UI Elements
```python
env = os.environ.copy()
env['NO_COLOR'] = '1'           # Disable colors
env['FORCE_COLOR'] = '0'        # Force disable colors
env['TERM'] = 'dumb'            # Simple terminal mode
env['CODEX_AUTO_APPROVE'] = 'true'  # Auto-approve (sometimes works)
```

### Complete Environment Setup
```python
import os

def get_codex_env():
    """Get optimized environment for Codex execution"""
    env = os.environ.copy()
    
    # Terminal UI
    env['NO_COLOR'] = '1'
    env['FORCE_COLOR'] = '0'
    env['TERM'] = 'dumb'
    
    # Codex specific
    env['CODEX_AUTO_APPROVE'] = 'true'
    env['CODEX_DISABLE_TELEMETRY'] = '1'
    
    # Prevent interactive prompts
    env['CI'] = 'true'
    env['DEBIAN_FRONTEND'] = 'noninteractive'
    
    return env
```

---

## 📁 Working Directory

### Trust Issues and Solutions

#### Problem: "Not inside a trusted directory"
```bash
# Error message:
Not inside a trusted directory and --skip-git-repo-check was not specified.
```

#### Solution 1: Skip Git Check
```bash
codex exec --skip-git-repo-check "your command"
```

#### Solution 2: Initialize Git Repo
```bash
cd /your/project/directory
git init
```

#### Solution 3: Trust Directory Manually
```bash
# Run codex once manually in the directory
cd /your/project/directory
codex  # Answer 'yes' to trust prompt
exit
```

### Working Directory Best Practices
```python
import os

class CodexExecutor:
    def __init__(self, working_dir=None):
        self.working_dir = working_dir or os.getcwd()
        
        # Ensure directory exists
        os.makedirs(self.working_dir, exist_ok=True)
        
        # Initialize git if needed
        if not os.path.exists(os.path.join(self.working_dir, '.git')):
            subprocess.run(['git', 'init'], cwd=self.working_dir)
```

---

## 🔄 Process Management

### Critical Issue: Zombie Codex Processes
**Codex can leave processes running at 100% CPU!**

### Detection
```bash
# Find all Codex processes
ps aux | grep -E "codex|node.*codex" | grep -v grep

# Using Python with psutil
import psutil

for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent']):
    cmdline = ' '.join(proc.info['cmdline'] or [])
    if 'codex' in cmdline.lower():
        print(f"PID: {proc.info['pid']}, CPU: {proc.cpu_percent()}%")
```

### Cleanup Script
```python
def cleanup_codex_processes(cpu_threshold=90.0, age_hours=24):
    """Kill problematic Codex processes"""
    import psutil
    import time
    
    current_time = time.time()
    
    for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            if 'codex' in cmdline.lower():
                # Check CPU usage
                cpu = proc.cpu_percent(interval=0.1)
                
                # Check age
                age = (current_time - proc.info['create_time']) / 3600
                
                if cpu > cpu_threshold or age > age_hours:
                    print(f"Killing PID {proc.info['pid']} (CPU: {cpu}%, Age: {age:.1f}h)")
                    proc.terminate()
                    time.sleep(2)
                    if proc.is_running():
                        proc.kill()
        except:
            continue
```

### Prevention
```python
# Always use timeout
process.communicate(input=instruction, timeout=300)  # 5 minutes

# Always cleanup on exit
import atexit

def cleanup():
    # Kill any remaining Codex processes
    cleanup_codex_processes()

atexit.register(cleanup)
```

---

## 💾 Session Management

### Codex Session Location
```bash
~/.codex/sessions/*.jsonl
```

### Session Structure
```json
{"type": "message", "role": "user", "content": "...", "timestamp": "..."}
{"type": "function_call", "name": "...", "arguments": "..."}
{"type": "function_call_output", "output": "..."}
```

### Finding Project Sessions
```python
from pathlib import Path
import json

def find_project_sessions(project_dir):
    """Find all Codex sessions for a project"""
    session_dir = Path.home() / '.codex' / 'sessions'
    sessions = []
    
    for session_file in session_dir.glob('*.jsonl'):
        with open(session_file, 'r') as f:
            content = f.read()
            # Check if session belongs to project
            if f'<cwd>{project_dir}</cwd>' in content:
                sessions.append(session_file)
    
    return sessions
```

### Resume Previous Session

#### Method 1: Using codex-resume-tool
```bash
# If you have codex-resume-tool installed
cd /your/project
python ~/CascadeProjects/codex-resume-tool/codex-resume.py
```

#### Method 2: Ask Codex to Load Context
```python
resume_prompt = """
Please check your session history for work in directory: /path/to/project

Load the most recent context and continue from where we left off.
If you find previous context, summarize what was being worked on.
"""
```

#### Method 3: Manual Context Injection
```python
def load_session_context(session_file):
    """Extract context from session file"""
    messages = []
    
    with open(session_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('type') == 'message':
                    messages.append(f"{data['role']}: {data['content'][:200]}")
            except:
                continue
    
    # Create context prompt
    context = "\n".join(messages[-50:])  # Last 50 messages
    return f"Previous context:\n{context}\n\nContinue from here."
```

---

## ❗ Common Issues and Solutions

### Issue 1: "Reading prompt from stdin..."
**Problem**: Codex shows this message and hangs.  
**Solution**: You're not sending input via STDIN properly.

### Issue 2: SSL Certificate Errors
**Problem**: SSL verification fails.  
**Solution**: 
```python
# For testing only (not production!)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### Issue 3: Sandbox Restrictions
**Problem**: "Can't write files in read-only sandbox"  
**Solution**: Use `--dangerously-bypass-approvals-and-sandbox`

### Issue 4: Token Limit Exceeded
**Problem**: Codex has ~2M token context but can fill up.  
**Solution**: 
- Use session management
- Clear old context periodically
- Start fresh session when needed

### Issue 5: Multiple Approval Prompts
**Problem**: Codex asks for approval 30+ times.  
**Solution**: Use bypass flags and environment variables.

---

## ✅ Best Practices

### 1. Always Use Exec Mode
```bash
codex exec  # Non-interactive, predictable
# NOT: codex  # Interactive, creates persistent session
```

### 2. Always Set Timeout
```python
process.communicate(input=instruction, timeout=300)
```

### 3. Always Clean Up
```python
try:
    result = execute_codex(instruction)
finally:
    cleanup_processes()
```

### 4. Track Your PIDs
```python
pid = process.pid
track_pid(pid, task_name)
# ... work ...
kill_pid(pid)
```

### 5. Use JSON Output
```bash
--json  # Structured, parseable output
```

### 6. Log Everything
```python
import logging

logging.info(f"Executing: {instruction[:100]}")
logging.info(f"Result: {result['success']}")
logging.info(f"Output: {result['stdout'][:200]}")
```

---

## 🚀 Complete Working Example

```python
#!/usr/bin/env python3
"""Complete working Codex CLI integration"""

import subprocess
import os
import json
import time
import psutil
from pathlib import Path

class CodexCLI:
    def __init__(self, working_dir=None):
        self.working_dir = working_dir or os.getcwd()
        self.codex_path = os.path.expanduser("~/.npm-global/bin/codex")
        
    def execute(self, instruction):
        """Execute instruction with all best practices"""
        
        # Setup environment
        env = os.environ.copy()
        env['NO_COLOR'] = '1'
        env['FORCE_COLOR'] = '0'
        env['TERM'] = 'dumb'
        
        # Build command
        cmd = [
            self.codex_path,
            'exec',
            '--dangerously-bypass-approvals-and-sandbox',
            '--skip-git-repo-check',
            '--json'
        ]
        
        # Execute with STDIN
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.working_dir,
            env=env,
            text=True
        )
        
        try:
            # Send via STDIN with timeout
            stdout, stderr = process.communicate(
                input=instruction, 
                timeout=300
            )
            
            # Parse JSON output
            result = {
                'success': process.returncode == 0,
                'stdout': stdout,
                'stderr': stderr,
                'pid': process.pid
            }
            
            return result
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {'success': False, 'error': 'Timeout'}
        
        finally:
            # Ensure process is dead
            if process.poll() is None:
                process.kill()

# Usage
codex = CodexCLI("/path/to/project")
result = codex.execute("Create a README.md file")
print(f"Success: {result['success']}")
```

---

## 📚 References

- Tested in: Politerm-3, ai-ping-pong-orchestrator, claude-to-codex projects
- Codex CLI version: 0.29.0
- Platform: macOS, Linux
- Python version: 3.8+

---

## 🔮 Future Discoveries

This document will be updated as new findings emerge. The Codex CLI is constantly evolving, and new flags or behaviors may be discovered.

**Last Updated**: January 2025  
**Maintainer**: BTankut  
**Repository**: [claude-to-codex](https://github.com/BTankut/claude-to-codex)

---

> **Remember**: These configurations were hard-earned through extensive testing. When in doubt, use the complete set of bypass flags and STDIN communication!