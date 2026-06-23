"""Tests für Event-Entscheidungen (Item 13)."""
import pytest
import packet_clicker as pc


def _choice(cid):
    return dict(next(c for c in pc.CHOICE_EVENTS if c["id"] == cid))


def test_choice_events_defined():
    ids = {c["id"] for c in pc.CHOICE_EVENTS}
    assert {"ddos_choice", "peer_choice", "patch_choice"} <= ids
    for c in pc.CHOICE_EVENTS:
        assert len(c["options"]) == 2


def test_rfc_cost_option_blocks_event(game):
    game.event_choice = _choice("ddos_choice")
    game.rfc_points = 20.0
    game.resolve_event_choice(0)            # "Scrubbing-Center": -8 RFC, kein Event
    assert game.rfc_points == pytest.approx(12.0)
    assert game.event is None
    assert game.event_choice is None


def test_endure_option_applies_event(game):
    game.event_choice = _choice("ddos_choice")
    game.resolve_event_choice(1)            # "Aushalten" → DDoS-Event aktiv
    assert game.event is not None
    assert game.event["id"] == "ddos"
    assert game.event_choice is None


def test_peering_option_costs_packets_and_buffs(game):
    game.event_choice = _choice("peer_choice")
    game.packets = 1000.0
    game.resolve_event_choice(0)            # -20% Pakete, dann Peering-Buff
    assert game.packets == pytest.approx(800.0)
    assert game.event["id"] == "peering"


def test_decline_option_does_nothing(game):
    game.event_choice = _choice("peer_choice")
    game.packets = 1000.0
    game.resolve_event_choice(1)            # "Ablehnen"
    assert game.packets == pytest.approx(1000.0)
    assert game.event is None
    assert game.event_choice is None


def test_choice_event_blocks_normal_events_until_resolved(game, monkeypatch):
    import pygame
    # Event-Trigger faellig machen
    game.total_packets = 100
    game.event = None
    game.event_choice = None
    game.next_event = pygame.time.get_ticks() - 1000
    monkeypatch.setattr(pc.random, "random", lambda: 0.0)   # < CHOICE_EVENT_PROB
    monkeypatch.setattr(pc.random, "choice", lambda seq: seq[0])
    game.update(16)
    assert game.event_choice is not None
    assert game.event is None     # normales Event bleibt aus, bis entschieden


def test_event_choice_renders(game):
    game.event_choice = _choice("patch_choice")
    pc.draw_event_choice(game)                 # darf nicht crashen
    _, _, rects = pc._event_choice_rects()
    assert len(rects) == 2
    pc.event_choice_click(game, rects[0].centerx, rects[0].centery)
    assert game.event_choice is None           # Wahl wurde aufgeloest
