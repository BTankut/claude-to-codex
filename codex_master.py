#!/usr/bin/env python3
"""
Codex Master Controller
========================
Claude tarafından kullanılacak master kontrol scripti.
Görev planlaması yapar ve Codex'e iletir.
"""

import json
import subprocess
import sys
from typing import List, Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from codex_orchestrator import CodexOrchestrator

class MasterController:
    def __init__(self):
        self.orchestrator = CodexOrchestrator()
        self.current_task = None
        
    def create_plan(self, task: str, steps: List[Dict]) -> Dict:
        """
        Görev planı oluştur
        
        Örnek kullanım:
        plan = master.create_plan(
            task="Create a Python web scraper",
            steps=[
                {
                    'description': 'Create project structure',
                    'instruction': 'Create a new directory called web_scraper with src and tests folders',
                    'critical': True
                },
                {
                    'description': 'Install dependencies',
                    'instruction': 'Create requirements.txt with requests and beautifulsoup4',
                    'critical': True
                },
                {
                    'description': 'Create main scraper file',
                    'instruction': 'Create src/scraper.py with a basic web scraper class',
                    'critical': True
                }
            ]
        )
        """
        self.current_task = {
            'task': task,
            'steps': steps,
            'total_steps': len(steps)
        }
        
        print(f"\n🎯 GÖREV: {task}")
        print(f"📝 Plan: {len(steps)} adım")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step['description']}")
        
        return self.current_task
    
    def execute(self, plan: Dict = None) -> Dict:
        """Planı Codex'e yaptır"""
        if plan:
            self.current_task = plan
        
        if not self.current_task:
            print("❌ Önce bir plan oluşturun!")
            return {'error': 'No plan defined'}
        
        # Orchestrator'a planı ver
        self.orchestrator.set_task_plan(self.current_task['steps'])
        
        # Planı çalıştır
        report = self.orchestrator.execute_plan()
        
        return report
    
    def quick_task(self, instruction: str) -> Dict:
        """Tek adımlık hızlı görev"""
        result = self.orchestrator.execute_codex_command(instruction)
        return result


# Master tarafından kullanılacak template planlar
TASK_TEMPLATES = {
    'create_project': [
        {
            'description': 'Create project directory structure',
            'instruction': 'Create a well-organized project structure with src, tests, docs folders',
            'critical': True
        },
        {
            'description': 'Initialize git repository',
            'instruction': 'Initialize a git repository and create .gitignore file',
            'critical': False
        },
        {
            'description': 'Create README',
            'instruction': 'Create a comprehensive README.md with project description',
            'critical': True
        }
    ],
    
    'add_feature': [
        {
            'description': 'Analyze existing code',
            'instruction': 'Analyze the current codebase structure and identify integration points',
            'critical': True
        },
        {
            'description': 'Implement feature',
            'instruction': 'Implement the requested feature following existing patterns',
            'critical': True
        },
        {
            'description': 'Add tests',
            'instruction': 'Create unit tests for the new feature',
            'critical': False
        }
    ],
    
    'debug_fix': [
        {
            'description': 'Identify the issue',
            'instruction': 'Analyze the error and identify root cause',
            'critical': True
        },
        {
            'description': 'Fix the bug',
            'instruction': 'Implement the fix for the identified issue',
            'critical': True
        },
        {
            'description': 'Verify fix',
            'instruction': 'Test that the fix resolves the issue',
            'critical': True
        }
    ],
    
    'refactor': [
        {
            'description': 'Analyze code quality',
            'instruction': 'Identify areas that need refactoring',
            'critical': True
        },
        {
            'description': 'Refactor code',
            'instruction': 'Refactor the code following best practices',
            'critical': True
        },
        {
            'description': 'Ensure tests pass',
            'instruction': 'Run tests to ensure refactoring didn\'t break functionality',
            'critical': True
        }
    ]
}


def master_execute_task(task_type: str, task_description: str, custom_steps: List[Dict] = None):
    """
    Master tarafından çağrılacak ana fonksiyon
    
    Kullanım:
    result = master_execute_task(
        task_type='create_project',
        task_description='Create a Flask web application',
        custom_steps=[...]  # Opsiyonel
    )
    """
    master = MasterController()
    
    # Template veya custom steps kullan
    if custom_steps:
        steps = custom_steps
    elif task_type in TASK_TEMPLATES:
        steps = TASK_TEMPLATES[task_type]
    else:
        print(f"❌ Unknown task type: {task_type}")
        return None
    
    # Plan oluştur
    plan = master.create_plan(task_description, steps)
    
    # Onay iste
    print(f"\n❓ Bu planı Codex'e yaptırmak istiyor musunuz? (y/n): ", end='')
    if input().lower() == 'y':
        return master.execute(plan)
    else:
        print("❌ İptal edildi")
        return None


if __name__ == "__main__":
    # Test örneği
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        master = MasterController()
        result = master.quick_task(task)
        print(f"\nSonuç: {result['success']}")
    else:
        print("Kullanım: python codex-master.py <görev>")
        print("\nÖrnek:")
        print("  python codex-master.py 'List all Python files in current directory'")