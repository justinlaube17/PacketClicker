"""Tests für die neuen höheren-Tier-Minigames (DNS Resolver, Load Balancer)."""
import pytest
import packet_clicker as pc


def _start(game, uid, unlocked):
    """Startet ein Minigame mit erfüllten Voraussetzungen und ohne Tutorial."""
    game.unlocked = set(unlocked)
    game.mg_tutorials_seen = {pc.TIER_CHALLENGE[uid]}   # Tutorial überspringen
    game.start_minigame(uid)
    mg = game.minigame
    assert mg is not None, f"start_minigame({uid}) hat nichts gesetzt"
    mg["tutorial"] = False
    mg["feedback"] = None
    return mg


# ── Zuweisung & Gating ────────────────────────────────────────────────
def test_challenge_map_has_new_types():
    assert pc.TIER_CHALLENGE["dns"] == "dns_resolver"
    assert pc.TIER_CHALLENGE["loadbal"] == "load_balancer"


def test_dns_challenge_requires_firewall(game):
    game.unlocked = {"hub", "switch", "router"}
    assert game.is_challenge_available("dns") is False
    game.unlocked = {"hub", "switch", "router", "firewall"}
    assert game.is_challenge_available("dns") is True


def test_loadbal_challenge_requires_dns(game):
    game.unlocked = {"hub", "switch", "router", "firewall"}
    assert game.is_challenge_available("loadbal") is False
    game.unlocked |= {"dns"}
    assert game.is_challenge_available("loadbal") is True


# ── DNS Resolver ──────────────────────────────────────────────────────
def test_dns_pick_correct_scores(game):
    mg = _start(game, "dns", {"hub", "switch", "router", "firewall"})
    mg["query"] = {"zone": [], "name": "x.acme.net",
                   "options": ["a", "b", "c", "d"], "correct": 2}
    game.dns_pick(2)
    assert mg["score"] == 1
    assert mg["feedback"]["type"] == "correct"


def test_dns_pick_wrong_loses_life(game):
    mg = _start(game, "dns", {"hub", "switch", "router", "firewall"})
    mg["query"] = {"zone": [], "name": "x", "options": ["a", "b", "c", "d"], "correct": 1}
    lives0 = mg["lives"]
    game.dns_pick(0)
    assert mg["lives"] == lives0 - 1
    assert mg["feedback"]["type"] == "wrong"


def test_dns_reaching_goal_wins(game):
    mg = _start(game, "dns", {"hub", "switch", "router", "firewall"})
    mg["score"] = pc.MG_DNS_GOAL - 1
    mg["query"] = {"zone": [], "name": "x", "options": ["a", "b"], "correct": 0}
    game.dns_pick(0)
    assert mg["result"] == "won"


# ── Load Balancer ─────────────────────────────────────────────────────
def test_lb_assign_accepts_when_room(game):
    mg = _start(game, "loadbal", {"hub", "switch", "router", "firewall", "dns"})
    mg["loads"] = [0.0, 0.0, 0.0]
    mg["request"] = {"weight": 30.0}
    game.lb_assign(0)
    assert mg["score"] == 1
    assert mg["loads"][0] == pytest.approx(30.0)


def test_lb_overflow_loses_life(game):
    mg = _start(game, "loadbal", {"hub", "switch", "router", "firewall", "dns"})
    mg["loads"] = [80.0, 0.0, 0.0]
    mg["request"] = {"weight": 30.0}        # 80 + 30 > 100 → Overflow
    lives0 = mg["lives"]
    game.lb_assign(0)
    assert mg["lives"] == lives0 - 1
    assert mg["feedback"]["type"] == "overflow"


def test_lb_reaching_goal_wins(game):
    mg = _start(game, "loadbal", {"hub", "switch", "router", "firewall", "dns"})
    mg["score"] = pc.MG_LB_GOAL - 1
    mg["loads"] = [0.0, 0.0, 0.0]
    mg["request"] = {"weight": 20.0}
    game.lb_assign(1)
    assert mg["result"] == "won"


# ── Dispatch & Abschluss ──────────────────────────────────────────────
def test_mg_option_dispatches_to_active_game(game):
    mg = _start(game, "dns", {"hub", "switch", "router", "firewall"})
    mg["query"] = {"zone": [], "name": "x", "options": ["a", "b", "c", "d"], "correct": 3}
    game.mg_option(3)            # generischer Zahltasten-Handler → dns_pick
    assert mg["score"] == 1


def test_finish_minigame_unlocks_and_counts(game):
    mg = _start(game, "dns", {"hub", "switch", "router", "firewall"})
    won0 = game.minigames_won
    mg["result"] = "won"
    game._finish_minigame()
    assert "dns" in game.unlocked
    assert game.minigames_won == won0 + 1
    assert game.minigame is None
