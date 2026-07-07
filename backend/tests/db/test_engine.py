"""Tests for the DB engine's startup resilience (`wait_for_db`)."""

from __future__ import annotations

import pytest

from app.db import engine as engine_mod
from app.db.engine import get_engine, wait_for_db


class _FakeConn:
    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *_a: object) -> bool:
        return False

    def execute(self, _stmt: object) -> None:
        return None


class _FlakyEngine:
    """Fails its first ``fails`` connects (like a cold Turso 502), then succeeds."""

    def __init__(self, fails: int) -> None:
        self.fails = fails
        self.calls = 0

    def connect(self) -> _FakeConn:
        self.calls += 1
        if self.calls <= self.fails:
            raise ValueError("Hrana: `api error: `status=502 Bad Gateway`")
        return _FakeConn()


def test_wait_for_db_returns_on_healthy_engine() -> None:
    # The real SQLite test engine connects instantly, so no retries occur.
    wait_for_db(get_engine())


def test_wait_for_db_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_mod.time, "sleep", lambda _s: None)
    eng = _FlakyEngine(fails=3)
    wait_for_db(eng, attempts=6, base_delay=0.01)  # type: ignore[arg-type]
    assert eng.calls == 4  # 3 failures + 1 success


def test_wait_for_db_gives_up_after_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_mod.time, "sleep", lambda _s: None)
    eng = _FlakyEngine(fails=99)
    with pytest.raises(RuntimeError, match="unreachable after 3 attempts"):
        wait_for_db(eng, attempts=3, base_delay=0.01)  # type: ignore[arg-type]
    assert eng.calls == 3  # no extra attempt beyond the cap


def test_wait_for_db_caps_backoff_at_max_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(engine_mod.time, "sleep", lambda s: slept.append(s))
    eng = _FlakyEngine(fails=99)
    with pytest.raises(RuntimeError):
        wait_for_db(eng, attempts=8, base_delay=1.0, max_delay=5.0)  # type: ignore[arg-type]
    # 7 sleeps (one per failed attempt except the last), exponential then clamped to 5.0.
    assert slept == [1.0, 2.0, 4.0, 5.0, 5.0, 5.0, 5.0]
    assert max(slept) <= 5.0
