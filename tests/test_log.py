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
