"""
Formatters module - text formatting utilities for notifications
"""

import re
from typing import List

# Constants
MIN_MAX_BYTES = 1024
PAGE_MARKER_SAFE_BYTES = 64


def format_feishu_markdown(content: str) -> str:
    """Format content for Feishu markdown"""
    return content


def markdown_to_html_document(markdown_text: str) -> str:
    """Convert markdown to HTML document"""
    html = markdown_text.replace('\n\n', '</p><p>')
    return f'<html><body><p>{html}</p></body></html>'


def markdown_to_plain_text(markdown_text: str) -> str:
    """Convert markdown to plain text"""
    text = markdown_text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    return text


def chunk_content_by_max_bytes(
    content: str, max_bytes: int = 4096, add_page_marker: bool = False
) -> List[str]:
    """Split content into chunks by max bytes.

    Args:
        content: Text to split.
        max_bytes: Maximum bytes per chunk.
        add_page_marker: If True, add a page separator marker between chunks.
    """
    chunks: List[str] = []
    current = ""
    for line in content.split('\n'):
        test = current + '\n' + line if current else line
        if len(test.encode('utf-8')) <= max_bytes:
            current = test
        else:
            if current:
                chunks.append(current)
            current = line
    if current:
        chunks.append(current)

    if add_page_marker and len(chunks) > 1:
        marker = '\n\n[page separator]\n\n'
        return [chunks[0]] + [marker + c for c in chunks[1:]]
    return chunks


def chunk_content_by_max_words(content: str, max_words: int = 1000) -> List[str]:
    """Split content into chunks by max words"""
    words = content.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(' '.join(words[i:i + max_words]))
    return chunks


def slice_at_max_bytes(content: str, max_bytes: int = 4096) -> str:
    """Slice content at max bytes"""
    encoded = content.encode('utf-8')
    if len(encoded) <= max_bytes:
        return content
    return encoded[:max_bytes].decode('utf-8', errors='ignore')
