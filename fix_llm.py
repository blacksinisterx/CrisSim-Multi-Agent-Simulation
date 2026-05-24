#!/usr/bin/env python3
"""Quick fix for LLM client to enable Ollama integration for reasoning strategies"""

import os

def fix_reasoning_strategies():
    """Fix the reasoning strategy files to support Ollama"""
    
    # File paths
    files_to_fix = [
        "reasoning/react.py",
        "reasoning/cot.py", 
        "reasoning/reflexion.py"
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"✅ Fixing {file_path}")
            
            # Read the file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace the provider check to include ollama
            old_check = 'os.getenv("LLM_PROVIDER", "mock").lower() in ["gemini", "groq"]'
            new_check = 'os.getenv("LLM_PROVIDER", "mock").lower() in ["gemini", "groq", "ollama"]'
            
            if old_check in content and new_check not in content:
                content = content.replace(old_check, new_check)
                print(f"   Updated provider check to include Ollama")
            
            # Update the log message to show provider
            old_log = 'Using LLM-powered ReAct strategy with Gemini 2.5 Flash'
            if old_log in content:
                new_log = f'Using LLM-powered ReAct strategy with {{provider.upper()}} provider'
                content = content.replace(f'"{old_log}"', f'f"Using LLM-powered ReAct strategy with {{provider.upper()}} provider"')
                # Add provider variable
                if 'provider = os.getenv("LLM_PROVIDER", "mock").lower()' not in content:
                    content = content.replace(
                        'if use_llm:\n        try:',
                        'if use_llm:\n        try:\n            provider = os.getenv("LLM_PROVIDER", "mock").lower()'
                    )
                print(f"   Updated logging to show dynamic provider")
            
            # Write back the file
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"   ✅ {file_path} fixed successfully")
        else:
            print(f"   ❌ {file_path} not found")

if __name__ == "__main__":
    print("🔧 Fixing reasoning strategies to support Ollama...")
    fix_reasoning_strategies()
    print("✅ All fixes applied!")
    print("\n🚀 Now the reasoning strategies should use Ollama when LLM_PROVIDER=ollama")
