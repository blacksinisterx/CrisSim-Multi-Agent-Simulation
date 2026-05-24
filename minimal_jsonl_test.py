#!/usr/bin/env python3
"""
Minimal test for JSONL logging
"""
import os
import json
from pathlib import Path

def minimal_jsonl_test():
    """Test JSONL creation manually without full imports"""
    
    # Create test log directory
    strategy = "react"
    run_id = "test_minimal"
    tick = 1
    
    log_dir = Path("logs") / f"strategy={strategy}" / f"run={run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"tick{tick:03d}.jsonl"
    
    print(f"📁 Creating JSONL at: {log_path}")
    
    # Test conversation
    conversation = [
        {"role": "system", "content": "You are a crisis management AI assistant."},
        {"role": "user", "content": "Crisis context: Handle emergency situation"},
        {"role": "assistant", "content": "FINAL_JSON: {\"commands\":[{\"agent\":\"15\",\"action\":\"move\",\"target\":[5,5]}]}"}
    ]
    
    # Write JSONL
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            for message in conversation:
                json_line = json.dumps(message, ensure_ascii=False)
                f.write(json_line + '\n')
        
        print(f"✅ JSONL file created successfully!")
        
        # Verify
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📄 File contains {len(lines)} lines:")
        for i, line in enumerate(lines):
            try:
                parsed = json.loads(line.strip())
                role = parsed.get('role', 'unknown')
                content_len = len(parsed.get('content', ''))
                print(f"  Line {i+1}: {role} ({content_len} chars)")
            except Exception as e:
                print(f"  ❌ Line {i+1}: Error - {e}")
        
        print(f"📂 Directory structure created:")
        print(f"  logs/strategy={strategy}/run={run_id}/tick{tick:03d}.jsonl")
        
    except Exception as e:
        print(f"❌ Error creating JSONL: {e}")

if __name__ == "__main__":
    minimal_jsonl_test()
