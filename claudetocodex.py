#!/usr/bin/env python3
"""
ClaudeToCodex - Main Entry Point
=================================
Claude (Master) to Codex (Slave) orchestration system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from codex_master import MasterController, master_execute_task, TASK_TEMPLATES

def main():
    """Ana giriş noktası"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                     ClaudeToCodex v1.0                       ║
║            Claude (Master) → Codex (Slave) System            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  claudetocodex.py <command> [args]")
        print("\nKomutlar:")
        print("  quick <instruction>  - Tek komut çalıştır")
        print("  project <name>       - Yeni proje oluştur")
        print("  feature <desc>       - Özellik ekle")
        print("  debug <issue>        - Bug fix")
        print("  refactor <target>    - Kod refactoring")
        print("\nÖrnek:")
        print("  python3 claudetocodex.py quick 'List all Python files'")
        print("  python3 claudetocodex.py project 'Flask REST API'")
        return
    
    command = sys.argv[1].lower()
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    master = MasterController()
    
    if command == "quick":
        # Hızlı tek komut
        if not args:
            print("❌ Instruction gerekli!")
            return
        print(f"\n🚀 Hızlı komut: {args}")
        result = master.quick_task(args)
        print(f"✅ Tamamlandı: {result.get('success', False)}")
        
    elif command in ["project", "feature", "debug", "refactor"]:
        # Template based görevler
        task_map = {
            "project": "create_project",
            "feature": "add_feature", 
            "debug": "debug_fix",
            "refactor": "refactor"
        }
        
        if not args:
            print(f"❌ {command} için açıklama gerekli!")
            return
            
        print(f"\n🎯 Görev tipi: {command}")
        print(f"📝 Açıklama: {args}")
        
        result = master_execute_task(
            task_type=task_map[command],
            task_description=args
        )
        
        if result:
            print(f"\n✅ Görev tamamlandı!")
            print(f"📊 Başarı oranı: {result.get('summary', {}).get('success_rate', 'N/A')}")
    else:
        print(f"❌ Bilinmeyen komut: {command}")


if __name__ == "__main__":
    main()