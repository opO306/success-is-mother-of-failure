import json
from pathlib import Path

import pytest

from engine.deterministic import JournalEntry, ResearchJournal, read_journal, verify_journal
from engine.deterministic.research_journal import GENESIS_DIGEST


def test_journal_create_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    ResearchJournal.create(path).close()
    with pytest.raises(FileExistsError):
        ResearchJournal.create(path)


def test_journal_entries_chain_by_digest(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    first = journal.append("observation_recorded", "OBS-1", {"a": 1})
    second = journal.append("observation_recorded", "OBS-2", {"a": 2})
    journal.close()

    assert first.previous_digest == GENESIS_DIGEST
    assert second.previous_digest == first.record_digest
    assert verify_journal(path) == {"final_digest": second.record_digest, "record_count": 2, "valid": True}


def test_journal_rejects_unsupported_event_type(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    with pytest.raises(ValueError, match="unsupported journal event type"):
        journal.append("not_a_real_event", "X-1", {})


def test_tampered_line_fails_verification(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    journal.append("observation_recorded", "OBS-1", {"a": 1})
    journal.close()

    lines = path.read_text(encoding="utf-8").splitlines()
    raw = json.loads(lines[0])
    raw["payload"]["a"] = 999
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="record digest mismatch"):
        verify_journal(path)


def test_reopen_continues_sequence_and_chain(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    journal.append("observation_recorded", "OBS-1", {"a": 1})
    journal.close()

    reopened = ResearchJournal.open(path)
    assert reopened.next_sequence == 1
    reopened.append("observation_recorded", "OBS-2", {"a": 2})
    reopened.close()

    entries = read_journal(path)
    assert [item.sequence for item in entries] == [0, 1]
    assert verify_journal(path)["valid"] is True
