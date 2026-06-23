"""Tests für Offline-Progress, Achievements und Stat-Persistenz (Phase 1)."""
import json
import time
import pytest
import packet_clicker as pc


# ── Offline-Progress ──────────────────────────────────────────────────
def _write_save(path, **extra):
    data = {"version": pc.SAVE_VERSION, "packets": 0.0, "total": 0.0,
            "owned": {"hub": 10}}     # hub = 0.5 pps → 5.0 pps gesamt
    data.update(extra)
    with open(path, "w") as f:
        json.dump(data, f)


def test_offline_progress_credits_packets(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "s.json"))
    _write_save(pc.SAVE_PATH, last_played=time.time() - 3600)  # 1 h weg
    g = pc.Game()
    assert g.show_offline is True
    assert g.offline_gain == pytest.approx(5.0 * 3600, rel=0.02)
    assert g.packets == pytest.approx(g.offline_gain, rel=0.02)
    assert 3590 <= g.offline_secs <= 3610


def test_offline_below_threshold_does_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "s.json"))
    _write_save(pc.SAVE_PATH, last_played=time.time() - 10)    # < OFFLINE_MIN_SECS
    g = pc.Game()
    assert g.show_offline is False
    assert g.packets == pytest.approx(0.0)


def test_offline_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "s.json"))
    _write_save(pc.SAVE_PATH, last_played=time.time() - 100_000)  # ~27 h weg
    g = pc.Game()
    assert g.offline_secs == pc.OFFLINE_CAP_SECS
    assert g.offline_gain == pytest.approx(5.0 * pc.OFFLINE_CAP_SECS, rel=0.01)


def test_no_offline_without_last_played(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "s.json"))
    _write_save(pc.SAVE_PATH)        # kein last_played
    g = pc.Game()
    assert g.show_offline is False


def test_offline_automation_research_doubles_gain(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "s.json"))
    _write_save(pc.SAVE_PATH, research=["automation"],   # offline_mult 2.0
                last_played=time.time() - 3600)
    g = pc.Game()
    assert g.offline_gain == pytest.approx(5.0 * 3600 * 2, rel=0.02)


# ── Achievements ──────────────────────────────────────────────────────
def test_sync_unlocks_and_toasts(game):
    game.total_clicks = 1
    game.achievements.clear()
    game.ach_toasts.clear()
    game._sync_achievements()
    assert "first_click" in game.achievements
    assert len(game.ach_toasts) == 1


def test_sync_silent_no_toast(game):
    game.total_clicks = 1
    game.achievements.clear()
    game.ach_toasts.clear()
    game._sync_achievements(silent=True)
    assert "first_click" in game.achievements
    assert game.ach_toasts == []


def test_already_earned_not_retoasted(game):
    game.total_clicks = 1
    game.achievements = {"first_click"}
    game.ach_toasts.clear()
    game._sync_achievements()
    assert game.ach_toasts == []


def test_prestige_achievement(game):
    game.prestige = 5
    game.achievements.clear()
    game.ach_toasts.clear()
    game._sync_achievements(silent=True)
    assert {"prestige_1", "prestige_5"} <= game.achievements


# ── Stat-Persistenz ───────────────────────────────────────────────────
def test_stats_survive_save_load(game):
    game.total_clicks = 42
    game.minigames_won = 3
    game.best_combo = 7
    game.events_seen = 11
    game.play_secs = 1234.0
    game.achievements = {"first_click", "first_buy"}
    game.save()

    g2 = pc.Game()
    assert g2.total_clicks == 42
    assert g2.minigames_won == 3
    assert g2.best_combo == 7
    assert g2.events_seen == 11
    assert g2.play_secs == pytest.approx(1234.0)
    assert {"first_click", "first_buy"} <= g2.achievements


# ── Hilfsfunktionen ───────────────────────────────────────────────────
@pytest.mark.parametrize("secs,expected", [
    (5, "5s"),
    (65, "1m 5s"),
    (3661, "1h 1m"),
])
def test_fmt_dur(secs, expected):
    assert pc.fmt_dur(secs) == expected
