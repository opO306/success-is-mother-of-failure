from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    tick: int
    text: str
    source: str | None = None  # who said it; None means the person experienced it directly


@dataclass
class Knowledge:
    """What one person knows. Never a copy of the truth."""

    entries: list[Entry] = field(default_factory=list)
    unread: int = 0

    def add(self, tick: int, text: str, source: str | None = None, incoming: bool = True) -> None:
        self.entries.append(Entry(tick=tick, text=text, source=source))
        if incoming:
            self.unread += 1

    def mark_read(self) -> None:
        self.unread = 0

    def recent(self, n: int) -> list[Entry]:
        return self.entries[-n:] if n > 0 else []


def format_entries(entries: list[Entry]) -> list[str]:
    return [f"[틱 {e.tick}] {e.text}" for e in entries]
