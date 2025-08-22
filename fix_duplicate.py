#!/usr/bin/env python3
"""Script to fix duplicate BatchFormatterContext class definition."""

def fix_duplicate_class():
    with open('devsync_ai/core/message_batcher.py', 'r') as f:
        content = f.read()
    
    # Find the first occurrence of BatchFormatterContext class
    first_start = content.find('@dataclass\nclass BatchFormatterContext:')
    if first_start == -1:
        print("First BatchFormatterContext class not found")
        return
    
    # Find the end of the first class (next @dataclass or class definition)
    first_end = content.find('\n\n@dataclass', first_start + 1)
    if first_end == -1:
        first_end = content.find('\n\nclass ', first_start + 1)
    
    if first_end == -1:
        print("Could not find end of first class")
        return
    
    # Find the second occurrence
    second_start = content.find('@dataclass\nclass BatchFormatterContext:', first_end)
    if second_start == -1:
        print("Second BatchFormatterContext class not found")
        return
    
    # Find the end of the second class
    second_end = content.find('\n\n@dataclass', second_start + 1)
    if second_end == -1:
        second_end = content.find('\n\nclass ', second_start + 1)
    
    if second_end == -1:
        print("Could not find end of second class")
        return
    
    # Remove the second occurrence
    new_content = content[:second_start] + content[second_end:]
    
    with open('devsync_ai/core/message_batcher.py', 'w') as f:
        f.write(new_content)
    
    print("Fixed duplicate BatchFormatterContext class")

if __name__ == "__main__":
    fix_duplicate_class()