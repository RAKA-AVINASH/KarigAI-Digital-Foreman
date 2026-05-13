#!/usr/bin/env python3
"""
Simple syntax validation script for the voice engine components.
"""

import ast
import sys
import os

def validate_file(filepath):
    """Validate Python file syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(content)
        print(f"✓ {filepath} - Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {filepath} - Syntax Error: {e}")
        return False
    except Exception as e:
        print(f"✗ {filepath} - Error: {e}")
        return False

def main():
    """Validate all voice engine related files."""
    files_to_check = [
        "app/core/voice_engine.py",
        "app/core/audio_preprocessing.py",
        "app/services/voice_service.py",
        "tests/test_voice_engine.py"
    ]
    
    all_valid = True
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            if not validate_file(filepath):
                all_valid = False
        else:
            print(f"✗ {filepath} - File not found")
            all_valid = False
    
    if all_valid:
        print("\n✓ All files have valid syntax!")
        return 0
    else:
        print("\n✗ Some files have syntax errors!")
        return 1

if __name__ == "__main__":
    sys.exit(main())