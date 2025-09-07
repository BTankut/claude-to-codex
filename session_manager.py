#!/usr/bin/env python3
"""
Codex Session Manager - Resume and manage Codex sessions
Integrates with codex-resume-tool for session continuation
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

class CodexSessionManager:
    """Manage Codex sessions and provide resume capability"""
    
    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir or os.getcwd()
        self.session_dir = Path.home() / '.codex' / 'sessions'
        self.resume_tool_path = Path.home() / 'CascadeProjects' / 'codex-resume-tool'
        self.last_session_file = None
        
    def find_project_sessions(self) -> List[Path]:
        """Find all Codex sessions for current project"""
        if not self.session_dir.exists():
            return []
        
        sessions = []
        for session_file in self.session_dir.glob('*.jsonl'):
            try:
                with open(session_file, 'r') as f:
                    content = f.read()
                    # Check if session belongs to this project
                    if f'<cwd>{self.project_dir}</cwd>' in content:
                        sessions.append(session_file)
            except:
                continue
        
        return sorted(sessions, key=lambda f: f.stat().st_mtime, reverse=True)
    
    def get_latest_session(self) -> Optional[Path]:
        """Get the most recent session for this project"""
        sessions = self.find_project_sessions()
        return sessions[0] if sessions else None
    
    def extract_context_summary(self, session_file: Path, max_lines: int = 50) -> str:
        """Extract a summary of the session context"""
        if not session_file.exists():
            return ""
        
        summary_lines = []
        messages = []
        
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        
                        # Extract user/assistant messages
                        if data.get('type') == 'message':
                            role = data.get('role', '')
                            content = data.get('content', '')
                            
                            if role in ['user', 'assistant'] and content:
                                # Truncate long messages
                                if len(content) > 200:
                                    content = content[:200] + "..."
                                messages.append(f"{role}: {content}")
                                
                                if len(messages) >= max_lines:
                                    break
                    except:
                        continue
            
            # Get last N messages for context
            if messages:
                summary_lines = messages[-max_lines:]
                return "\n".join(summary_lines)
            
        except Exception as e:
            print(f"Error reading session: {e}")
        
        return ""
    
    def create_resume_context(self, session_file: Path) -> str:
        """Create a context string for resuming a session"""
        if not session_file.exists():
            return ""
        
        context = f"""
=== RESUMING PREVIOUS SESSION ===
Session file: {session_file.name}
Project: {self.project_dir}
Modified: {datetime.fromtimestamp(session_file.stat().st_mtime).isoformat()}

=== RECENT CONTEXT ===
{self.extract_context_summary(session_file)}

=== CONTINUATION ===
Continue from where we left off. The previous context shows what was being worked on.
"""
        return context
    
    def resume_with_tool(self) -> bool:
        """Use codex-resume-tool to resume session"""
        if not self.resume_tool_path.exists():
            print("⚠️ codex-resume-tool not found")
            return False
        
        resume_script = self.resume_tool_path / 'codex-resume.py'
        if not resume_script.exists():
            print("⚠️ codex-resume.py not found")
            return False
        
        try:
            # Run codex-resume tool
            result = subprocess.run(
                ['python3', str(resume_script)],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Session resumed with codex-resume-tool")
                return True
            else:
                print(f"❌ Resume failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error running resume tool: {e}")
            return False
    
    def save_session_checkpoint(self, task: str, plan: List[Dict], results: List[Dict]):
        """Save a checkpoint of current execution for later resume"""
        checkpoint_dir = Path.home() / '.claudetocodex' / 'checkpoints'
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'project_dir': self.project_dir,
            'task': task,
            'plan': plan,
            'results': results,
            'session_file': str(self.last_session_file) if self.last_session_file else None
        }
        
        checkpoint_file = checkpoint_dir / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        print(f"💾 Checkpoint saved: {checkpoint_file.name}")
        return checkpoint_file
    
    def load_latest_checkpoint(self) -> Optional[Dict]:
        """Load the most recent checkpoint for this project"""
        checkpoint_dir = Path.home() / '.claudetocodex' / 'checkpoints'
        if not checkpoint_dir.exists():
            return None
        
        checkpoints = []
        for cp_file in checkpoint_dir.glob('checkpoint_*.json'):
            try:
                with open(cp_file, 'r') as f:
                    data = json.load(f)
                    if data.get('project_dir') == self.project_dir:
                        checkpoints.append((cp_file, data))
            except:
                continue
        
        if not checkpoints:
            return None
        
        # Return most recent
        checkpoints.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
        return checkpoints[0][1]
    
    def prompt_for_resume(self) -> Optional[str]:
        """Ask Codex to find and resume a specific context"""
        prompt = f"""
Please check your session history for work in directory: {self.project_dir}

If you find previous context related to this project, please:
1. Load that context
2. Summarize what was being worked on
3. Continue from where we left off

If no previous context is found, indicate that we're starting fresh.
"""
        return prompt


def main():
    """CLI for session management"""
    import sys
    
    manager = CodexSessionManager()
    
    if len(sys.argv) < 2:
        print("""
Usage:
  session_manager.py list      - List project sessions
  session_manager.py latest    - Show latest session info
  session_manager.py resume    - Resume latest session
  session_manager.py context   - Show session context
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        sessions = manager.find_project_sessions()
        print(f"📁 Found {len(sessions)} sessions for {manager.project_dir}")
        for session in sessions[:5]:
            print(f"  - {session.name} ({session.stat().st_size // 1024}KB)")
    
    elif command == 'latest':
        session = manager.get_latest_session()
        if session:
            print(f"📄 Latest session: {session.name}")
            print(f"  Size: {session.stat().st_size // 1024}KB")
            print(f"  Modified: {datetime.fromtimestamp(session.stat().st_mtime).isoformat()}")
        else:
            print("❌ No sessions found")
    
    elif command == 'resume':
        if manager.resume_with_tool():
            print("✅ Session resumed")
        else:
            # Fallback to prompt method
            prompt = manager.prompt_for_resume()
            print("📝 Use this prompt to resume:")
            print(prompt)
    
    elif command == 'context':
        session = manager.get_latest_session()
        if session:
            context = manager.extract_context_summary(session)
            print("📋 Recent context:")
            print(context)
        else:
            print("❌ No sessions found")
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == '__main__':
    main()