#!/usr/bin/env python3
"""
Codex Orchestrator - Master-Slave CLI System
=============================================
Bu sistem Claude'u Master, Codex'i Slave olarak kullanır.
Claude planlama yapar, Codex execution yapar.
"""

import subprocess
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import tempfile
import shlex

class CodexOrchestrator:
    def __init__(self, working_dir=None):
        self.codex_path = os.path.expanduser("~/.npm-global/bin/codex")
        self.working_dir = working_dir or os.getcwd()
        self.execution_log = []
        self.task_plan = []
        self.current_task = None
        
    def verify_codex(self) -> bool:
        """Codex CLI'ın kurulu ve erişilebilir olduğunu doğrula"""
        if not os.path.exists(self.codex_path):
            print("❌ Codex CLI bulunamadı!")
            return False
        
        try:
            result = subprocess.run(
                [self.codex_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ Codex CLI hazır: {result.stdout.strip()}")
                return True
        except Exception as e:
            print(f"❌ Codex CLI erişim hatası: {e}")
            return False
    
    def execute_codex_command(self, instruction: str, context: str = "") -> Dict:
        """Codex'e komut gönder ve sonucu al"""
        timestamp = datetime.now().isoformat()
        
        full_instruction = f"{context}\n\n{instruction}" if context else instruction
        
        try:
            # Codex parametreleri (stdin kullanımı için)
            cmd_args = [
                self.codex_path,
                'exec',
                '--dangerously-bypass-approvals-and-sandbox',
                '--skip-git-repo-check',
                '--json'
            ]
            
            # Environment variables (terminal UI'ları devre dışı)
            env = os.environ.copy()
            env['NO_COLOR'] = '1'
            env['FORCE_COLOR'] = '0'
            env['TERM'] = 'dumb'
            
            print(f"\n🤖 Codex'e gönderiliyor: {instruction[:100]}...")
            
            # stdin üzerinden prompt gönder
            process = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_dir,
                env=env,
                text=True
            )
            
            # Instruction'ı stdin'e gönder
            stdout, stderr = process.communicate(input=full_instruction, timeout=300)  # 5 dakika timeout
            
            result = {
                'timestamp': timestamp,
                'instruction': instruction,
                'stdout': stdout,
                'stderr': stderr,
                'returncode': process.returncode,
                'success': process.returncode == 0
            }
            
            self.execution_log.append(result)
            
            if result['success']:
                print(f"✅ Codex görevi tamamladı")
            else:
                print(f"⚠️ Codex hatası: {stderr[:200]}")
            
            return result
            
        except subprocess.TimeoutExpired:
            print("⏱️ Codex zaman aşımına uğradı")
            process.kill()
            return {
                'timestamp': timestamp,
                'instruction': instruction,
                'error': 'Timeout after 5 minutes',
                'success': False
            }
        except Exception as e:
            print(f"❌ Execution hatası: {e}")
            return {
                'timestamp': timestamp,
                'instruction': instruction,
                'error': str(e),
                'success': False
            }
    
    def set_task_plan(self, plan: List[Dict]):
        """Master'dan gelen görevi planı ayarla"""
        self.task_plan = plan
        print(f"\n📋 Görev planı alındı: {len(plan)} adım")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step.get('description', 'Adım')}")
    
    def execute_plan(self) -> Dict:
        """Planı adım adım Codex'e yaptır"""
        results = []
        
        for i, step in enumerate(self.task_plan, 1):
            print(f"\n{'='*60}")
            print(f"📍 Adım {i}/{len(self.task_plan)}: {step.get('description', '')}")
            print(f"{'='*60}")
            
            instruction = step.get('instruction', '')
            context = step.get('context', '')
            
            if not instruction:
                print("⚠️ Instruction eksik, adım atlanıyor")
                continue
            
            result = self.execute_codex_command(instruction, context)
            results.append({
                'step': i,
                'description': step.get('description', ''),
                'result': result
            })
            
            # Hata durumunda dur
            if not result['success'] and step.get('critical', True):
                print(f"🛑 Kritik hata! Plan durduruluyor.")
                break
            
            # Adımlar arası bekleme
            if i < len(self.task_plan):
                time.sleep(2)
        
        return self.generate_report(results)
    
    def generate_report(self, results: List[Dict]) -> Dict:
        """Execution özet raporu oluştur"""
        total_steps = len(self.task_plan)
        completed_steps = sum(1 for r in results if r['result']['success'])
        
        report = {
            'summary': {
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'success_rate': f"{(completed_steps/total_steps)*100:.1f}%" if total_steps > 0 else "0%",
                'execution_time': datetime.now().isoformat()
            },
            'steps': results,
            'logs': self.execution_log
        }
        
        # Raporu kaydet
        report_file = f"codex_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"📊 EXECUTION RAPORU")
        print(f"{'='*60}")
        print(f"✅ Tamamlanan: {completed_steps}/{total_steps}")
        print(f"📈 Başarı Oranı: {report['summary']['success_rate']}")
        print(f"💾 Detaylı rapor: {report_file}")
        
        return report
    
    def interactive_mode(self):
        """Test için interaktif mod"""
        print("\n🎮 Codex Orchestrator - Interactive Mode")
        print("Commands: 'exit' to quit, 'plan' to set plan, or direct instruction")
        
        while True:
            cmd = input("\n> ").strip()
            
            if cmd == 'exit':
                break
            elif cmd == 'plan':
                # Örnek plan
                self.set_task_plan([
                    {
                        'description': 'Proje dosyalarını listele',
                        'instruction': 'List all files in the current directory',
                        'critical': False
                    },
                    {
                        'description': 'README dosyası oluştur',
                        'instruction': 'Create a README.md file with project description',
                        'critical': True
                    }
                ])
                self.execute_plan()
            else:
                # Direkt komut
                self.execute_codex_command(cmd)


# CLI arayüzü için helper fonksiyonlar
def create_task_plan_from_master(task_description: str) -> List[Dict]:
    """
    Master (Claude) tarafından oluşturulacak plan formatı
    Bu fonksiyon Master tarafından çağrılacak
    """
    # Örnek plan yapısı
    return [
        {
            'description': 'Step description',
            'instruction': 'Exact instruction for Codex',
            'context': 'Additional context if needed',
            'critical': True  # False ise hata durumunda devam et
        }
    ]


if __name__ == "__main__":
    orchestrator = CodexOrchestrator()
    
    if not orchestrator.verify_codex():
        print("Codex CLI kurulumu gerekli!")
        sys.exit(1)
    
    # Test için interaktif mod
    orchestrator.interactive_mode()