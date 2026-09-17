"""Memory recall intent detection and boilerplate filtering for ToM memory layer.

Canonical home for _is_recall_intent, _is_boilerplate_memory (System G: Memory).
Relocated from interface/chat_adapter.py.
"""
from __future__ import annotations

from typing import Any, Dict


def _is_recall_intent(user_text: str) -> bool:
    """Disabled — all queries go through the LLM.

    Previously used string patterns to short-circuit LLM and dump raw
    document chunks as responses.  Let the LLM answer every query
    with ToM's tree state shaping the response.
    """
    return False


def _is_boilerplate_memory(mem: Dict[str, Any]) -> bool:
    """Filter boilerplate chunks using structural patterns only.

    Language-agnostic: no hardcoded section names or title strings.
    Detects boilerplate via content structure:
    1. Anchor-link heavy (ToC-like): >= 5 internal anchor links
    2. Heading-ref heavy: content is mostly heading references with minimal prose
    """
    content = str(mem.get("content", "") or "")
    if not content:
        return False

    # Check 1: Many internal anchor links [...]( #...) = ToC / index pattern
    toc_link_count = content.count('](#')
    if toc_link_count >= 5:
        return True

    # Check 2: Content is mostly short lines that are markdown links/refs
    # (catches ToC variants without parenthesised anchors)
    lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
    if len(lines) >= 8:
        def _is_link_line(ln: str) -> bool:
            s = ln.lstrip('-* ')
            while s and (s[0].isdigit() or s[0] == '.'):
                s = s[1:]
            return s.lstrip().startswith('[')
        link_lines = sum(1 for ln in lines if _is_link_line(ln))
        if link_lines >= len(lines) * 0.6:
            return True

    return False
