#!/usr/bin/env python3
"""
Script to add return type annotations to FastAPI endpoints.

This script analyzes FastAPI router functions and adds return type hints
based on the response_model specified in the router decorator.

Usage:
    python add_return_types.py
"""

import re
import glob
from pathlib import Path

def extract_response_model(decorator_line: str) -> str:
    """Extract response_model from decorator line."""
    match = re.search(r'response_model=(\w+)', decorator_line)
    if match:
        return match.group(1)
    return ""

def process_file(file_path: Path) -> int:
    """Process a single Python file and add return types."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    modified = False
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a router decorator
        if '@router.' in line and ('get(' in line or 'post(' in line or 'put(' in line or 'delete(' in line or 'patch(' in line):
            # Extract response_model if present
            response_model = extract_response_model(line)

            # Look ahead for the function definition
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('def ') and not lines[j].strip().startswith('async def '):
                j += 1

            if j < len(lines):
                func_line = lines[j]

                # Check if function already has return type
                if '-> ' not in func_line and response_model:
                    # Find the end of the function signature
                    paren_count = func_line.count('(') - func_line.count(')')
                    k = j

                    while paren_count > 0 and k < len(lines) - 1:
                        k += 1
                        paren_count += lines[k].count('(') - lines[k].count(')')

                    # Add return type before the colon
                    if k < len(lines):
                        end_line = lines[k]
                        if ':' in end_line and '-> ' not in end_line:
                            # Insert return type
                            colon_pos = end_line.rindex(':')
                            lines[k] = end_line[:colon_pos] + f' -> {response_model}' + end_line[colon_pos:]
                            modified = True
                            print(f"  Added return type {response_model} to function at line {k+1}")

        new_lines.append(line)
        i += 1

    if modified:
        file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        return 1
    return 0

def main():
    """Main function to process all API files."""
    # Find all Python files in API directories
    v1_files = glob.glob('backend/app/api/v1/*.py')
    admin_files = glob.glob('backend/app/api/admin/*.py')
    auth_files = glob.glob('backend/app/api/auth.py')

    all_files = v1_files + admin_files + ([auth_files[0]] if auth_files else [])

    print(f"Found {len(all_files)} API files to process...")

    modified_count = 0
    for file_path_str in sorted(all_files):
        file_path = Path(file_path_str)
        if file_path.name == '__init__.py':
            continue

        print(f"\nProcessing {file_path.name}...")
        result = process_file(file_path)
        modified_count += result

    print(f"\n✅ Complete! Modified {modified_count} files.")
    print("\nNote: This script adds return type annotations based on response_model.")
    print("You should manually:")
    print("  1. Add 'from typing import Annotated' to imports")
    print("  2. Convert Query parameters to use Annotated syntax")
    print("  3. Review and test all changes")

if __name__ == '__main__':
    main()
