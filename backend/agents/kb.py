"""Knowledge-base interface used by the agents.

`KeywordKnowledgeBase` is a dependency-free stand-in that reads markdown
runbooks from data/kb/<team>/*.md. The RAG retriever can replace it: anything
with a matching `search()` method works (see `KnowledgeBase`).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

_STOPWORDS = set(
    "a an the and or but to of in on for with is are was were be been it its this that "
    "i my me we our you your can cant can't not no do does did dont don't from at as by "
    "have has had will would should could please help hi hello issue problem today".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS and len(t) > 1]


def section(markdown: str, heading: str) -> str:
    """Body of a '## heading' section, or '' if absent."""
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", markdown, re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else ""


class KnowledgeBase(Protocol):
    def search(self, query: str, team: str | None = None, k: int = 3) -> list[dict[str, Any]]:
        """Return up to k hits: {doc_id, team, title, score, snippet, content}."""
        ...


@dataclass
class _Doc:
    doc_id: str
    team: str
    title: str
    content: str
    tokens: Counter
    title_tokens: set


class KeywordKnowledgeBase:
    def __init__(self, kb_dir: Path):
        self.docs: list[_Doc] = []
        kb_dir = Path(kb_dir)
        if not kb_dir.exists():
            return
        for path in sorted(kb_dir.glob("*/*.md")):
            content = path.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else path.stem
            self.docs.append(
                _Doc(
                    doc_id=f"{path.parent.name}/{path.stem}",
                    team=path.parent.name,
                    title=title,
                    content=content,
                    tokens=Counter(tokenize(content)),
                    title_tokens=set(tokenize(title)),
                )
            )

    def search(self, query: str, team: str | None = None, k: int = 3) -> list[dict[str, Any]]:
        q = set(tokenize(query))
        scored = []
        for doc in self.docs:
            if team and doc.team != team:
                continue
            score = sum(min(doc.tokens[t], 3) for t in q) + 3 * len(q & doc.title_tokens)
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda pair: (-pair[0], pair[1].doc_id))
        return [
            {
                "doc_id": d.doc_id,
                "team": d.team,
                "title": d.title,
                "score": s,
                "snippet": (section(d.content, "Resolution") or d.content)[:300],
                "content": d.content,
            }
            for s, d in scored[:k]
        ]
