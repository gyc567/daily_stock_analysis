import sys
import re

path = sys.argv[1]
pattern = sys.argv[2]

def match_glob(path, pattern):
    if '*' not in pattern and '?' not in pattern:
        return path == pattern
    
    i = 0
    regex_parts = []
    pattern_len = len(pattern)
    
    while i < pattern_len:
        c = pattern[i]
        
        if c == '*':
            if i + 1 < pattern_len and pattern[i+1] == '*':
                if i + 2 < pattern_len and pattern[i+2] == '/':
                    regex_parts.append('(?:.+/)?')
                    i += 3
                else:
                    regex_parts.append('.*')
                    i += 2
            else:
                regex_parts.append('[^/]*')
                i += 1
        elif c == '?':
            regex_parts.append('[^/]')
            i += 1
        elif c == '.':
            regex_parts.append('\\.')
            i += 1
        else:
            regex_parts.append(re.escape(c))
            i += 1
    
    regex = '^' + ''.join(regex_parts) + '$'
    return bool(re.match(regex, path))

sys.exit(0 if match_glob(path, pattern) else 1)
