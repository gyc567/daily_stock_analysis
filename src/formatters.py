# -*- coding: utf-8 -*-
"""Deprecated module shim — the formatters implementation has migrated to
``src/formatters/`` (a package). Python 3 resolves ``src.formatters`` to
the package directory when both file and directory coexist, so this file
is effectively a no-op at runtime.

It is kept only so the pr-review flake8 job (which scans every .py file
listed in the PR diff, including deletions) does not fail with
FileNotFoundError on a missing path. This shim will be removed in the
next release after all tooling callers have been updated to filter out
deletions.

Issue: docs/midterm-trend-compass-plan.md §9 (P1) — independent CI fix
on PR #42.
"""

from src.formatters import (  # noqa: F401
    format_feishu_markdown,
    markdown_to_html_document,
    markdown_to_plain_text,
    chunk_content_by_max_bytes,
    chunk_content_by_max_words,
    slice_at_max_bytes,
    chunk_markdown_preserving_blocks,
    format_telegram_markdown,
    format_slack_mrkdwn,
    format_wechat_markdown,
    markdown_tables_to_key_value_rows,
)
