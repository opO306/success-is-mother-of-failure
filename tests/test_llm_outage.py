import dataclasses
import json

import pytest
import requests

import engine.llm_agent as llm_agent
import run_primal
from engine import recorder as recording
from engine.config import SimulationConfig
from engine.primal.prompts import DayDeclaration


class _Reply:
    def __init__(self, content="", status=200, body=None):
        self.content, self.status_code, self.body = content, status, body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)

    def json(self):
        if self.body is not None:
            return self.body
        return {"message": {"content": self.content}, "prompt_eval_count": 5, "eval_count": 7, "done_reason": "stop"}


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(llm_agent, "_outage_since", {})
    monkeypatch.setattr(llm_agent.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(llm_agent.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))
    return now


def _server(monkeypatch, replies):
    """Each post takes the next reply; an exception is raised, the last reply repeats."""
    posts = []

    def post(*args, **kwargs):
        posts.append(kwargs)
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(requests, "post", post)
    return posts


GUARDED = dataclasses.replace(SimulationConfig(), llm_stop_when_unreachable=True, llm_max_retries=2, llm_outage_wait_seconds=60)


def test_a_server_that_drops_for_a_while_is_waited_for_and_its_silence_uses_up_no_attempts(monkeypatch, clock):
    posts = _server(monkeypatch, [requests.ConnectionError("down"), requests.Timeout("slow"), _Reply(status=503),
                                  _Reply('{"plan": "물을 마신다"}')])
    decision = llm_agent.call_llm_decision("p", DayDeclaration, GUARDED, temperature=0.7)
    assert decision.plan == "물을 마신다"
    assert len(posts) == 4 > GUARDED.llm_max_retries
    assert clock[0] > 0 and llm_agent._outage_since == {}


def test_a_server_silent_past_the_wait_stops_the_run_and_later_calls_do_not_wait_again(monkeypatch, clock):
    posts = _server(monkeypatch, [requests.ConnectionError("down")])
    with pytest.raises(llm_agent.LLMUnreachable):
        llm_agent.call_llm_decision("p", DayDeclaration, GUARDED, temperature=0.7)
    assert clock[0] >= GUARDED.llm_outage_wait_seconds
    before = len(posts)
    with pytest.raises(llm_agent.LLMUnreachable):
        llm_agent.call_llm_decision("p", DayDeclaration, GUARDED, temperature=0.7)
    assert len(posts) == before + 1


def test_an_answer_the_server_rejects_or_mangles_is_this_answers_failure_not_an_outage(monkeypatch, clock):
    posts = _server(monkeypatch, [_Reply(status=400), _Reply('{"plan": "끝나지 않은')])
    assert llm_agent.call_llm_decision("p", DayDeclaration, GUARDED, temperature=0.7) is None
    assert len(posts) == GUARDED.llm_max_retries and clock[0] == 0


def test_without_the_guard_an_unreachable_server_still_falls_back_as_the_older_worlds_expect(monkeypatch, clock):
    posts = _server(monkeypatch, [requests.ConnectionError("down")])
    config = dataclasses.replace(GUARDED, llm_stop_when_unreachable=False)
    assert llm_agent.call_llm_decision("p", DayDeclaration, config, temperature=0.7) is None
    assert len(posts) == config.llm_max_retries and clock[0] == 0


def test_a_run_whose_server_goes_silent_marks_the_broken_day_and_names_the_last_whole_one(monkeypatch, tmp_path):
    real_start = recording.start_run
    monkeypatch.setattr(recording, "start_run", lambda label, meta: real_start(label, meta, root=tmp_path))
    monkeypatch.setattr(run_primal, "check_servers", lambda llm: None)
    monkeypatch.setattr(requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("no ollama")))
    guarded = []

    def step_day(world, snapshot_dir=None):
        guarded.append(world.config.llm.llm_stop_when_unreachable)
        if len(guarded) > 1:
            raise llm_agent.LLMUnreachable("http://pod:8000 has not answered for 600s")
        world.day += 1
        return {"day": world.day - 1, "season": "봄", "alive": 3, "events": [], "structures": 0, "plantings": 0, "leaks": {}}

    monkeypatch.setattr(run_primal, "step_day", step_day)
    with pytest.raises(SystemExit) as stopped:
        run_primal.run_world(0, 5, None)
    assert guarded == [True, True]
    run_dir = next(tmp_path.iterdir())
    aborted = json.loads((run_dir / "aborted.jsonl").read_text(encoding="utf-8"))
    first_day = json.loads((run_dir / "meta.jsonl").read_text(encoding="utf-8"))["start_day"]
    assert aborted["day"] == first_day + 1
    assert aborted["resume_from"].endswith(f"day_{first_day:03d}.pkl") and "--resume" in str(stopped.value)
    assert "서버가 응답하지 않아 중단됨" in (run_dir / "digest.md").read_text(encoding="utf-8")
    assert recording.active() is None


def test_the_run_does_not_start_when_a_server_lacks_its_model(monkeypatch):
    seen = []

    def get(url, timeout=None, headers=None):
        seen.append((url, headers))
        return _Reply(body={"data": [{"id": "big"}]})

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("LLM_API_KEY", "secret")
    config = dataclasses.replace(SimulationConfig(), llm_backend="openai", llm_host="http://pod:8000/", llm_model="big", clerk_model="small")
    with pytest.raises(SystemExit, match="small"):
        run_primal.check_servers(config)
    assert seen[0] == ("http://pod:8000/v1/models", {"Authorization": "Bearer secret"})
    run_primal.check_servers(dataclasses.replace(config, clerk_model=None))
