import desk.log as log


def test_record_and_render(tmp_path, monkeypatch):
    p = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(log, "LOG_PATH", str(p))
    monkeypatch.setattr(log, "LOG_DIR", str(tmp_path))
    log.record("steward", "sell_put", "Sold the TEST 240 put because the week looks ordinary.",
               symbol="TEST260904P00240000", credit=1.85)
    log.record("risk", "veto", "Vetoed: sleeve cap.", gate="sleeve-cap")
    rows = log.rows(str(p))
    assert len(rows) == 2 and rows[0]["credit"] == 1.85
    md = log.render(str(p))
    assert "🛑" in md and "sell_put" in md and md.startswith("# The desk")


def test_the_cli_door_refuses_to_read_an_unauthenticated_account(monkeypatch):
    """The CLI falls back to its own ~/.config/alpaca profile when the env is
    empty — a DIFFERENT paper account on at least one machine. Reading another
    account's positions would make a sweep try to close what this account does
    not hold, so the door must fail instead (run.read_positions then uses the
    SDK, authenticated from the same .env the desk trades with)."""
    import pytest
    from desk import cli
    for v in ("ALPACA_API_KEY_ID", "ALPACA_API_KEY", "ALPACA_API_SECRET_KEY", "ALPACA_SECRET_KEY"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="refusing to let the CLI fall back"):
        cli._run("account", "get")
