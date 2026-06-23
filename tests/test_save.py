"""Tests für Save-Versionierung, Migration und Save/Load-Roundtrip."""
import json
import pytest
import packet_clicker as pc


# ── Migration ─────────────────────────────────────────────────────────
def test_migrate_legacy_adds_version(game):
    legacy = {"packets": 10.0, "total": 100.0, "owned": {"hub": 2}}
    out = pc.migrate_save(dict(legacy))
    assert out["version"] == pc.SAVE_VERSION


def test_migrate_owned_tiers_become_unlocked():
    legacy = {"packets": 1.0, "owned": {"hub": 2, "switch": 1}}
    out = pc.migrate_save(dict(legacy))
    assert set(out["unlocked"]) >= {"hub", "switch"}


def test_migrate_firewall_unlocks_rfc():
    legacy = {"packets": 1.0, "owned": {"firewall": 1}}
    out = pc.migrate_save(dict(legacy))
    assert out["rfc_unlocked"] is True


def test_migrate_is_idempotent():
    legacy = {"packets": 1.0, "owned": {"hub": 1}}
    once = pc.migrate_save(dict(legacy))
    twice = pc.migrate_save(dict(once))
    assert twice["version"] == pc.SAVE_VERSION
    assert set(twice["unlocked"]) == set(once["unlocked"])


def test_migrate_keeps_current_version_untouched():
    current = {"packets": 1.0, "owned": {}, "unlocked": ["hub"],
               "version": pc.SAVE_VERSION}
    out = pc.migrate_save(dict(current))
    assert out["version"] == pc.SAVE_VERSION
    assert set(out["unlocked"]) == {"hub"}


# ── Roundtrip ─────────────────────────────────────────────────────────
def test_save_writes_version(game, tmp_path):
    game.save()
    with open(pc.SAVE_PATH) as f:
        d = json.load(f)
    assert d["version"] == pc.SAVE_VERSION


def test_save_load_roundtrip(game):
    game.owned = {"hub": 5, "switch": 2}
    game.packets = 1234.5
    game.total_packets = 9999.0
    game.prestige = 2
    game.prestige_mult = 4.0
    game.research_done = {"osi", "subnet"}
    game.unlocked = {"hub", "switch", "router"}
    game.save()

    # Frisches Game lädt vom selben (gepatchten) SAVE_PATH.
    g2 = pc.Game()
    assert g2.owned == {"hub": 5, "switch": 2}
    assert g2.packets == pytest.approx(1234.5)
    assert g2.total_packets == pytest.approx(9999.0)
    assert g2.prestige == 2
    assert g2.prestige_mult == pytest.approx(4.0)
    assert g2.research_done == {"osi", "subnet"}
    assert g2.unlocked == {"hub", "switch", "router"}


def test_load_missing_file_keeps_defaults(game):
    # SAVE_PATH der Fixture existiert nicht → Defaults aus __init__.
    assert game.owned == {}
    assert game.packets == pytest.approx(0.0)
    assert game.prestige == 0
