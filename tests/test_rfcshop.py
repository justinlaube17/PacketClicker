"""Tests für den RFC-Shop (wiederholbare, skalierende Upgrades)."""
import pytest
import packet_clicker as pc


def test_cost_scales_with_level(game):
    base = next(s for s in pc.RFC_SHOP if s["id"] == "overclock")["base"]
    assert game.rfc_upgrade_cost("overclock") == base
    game.rfc_upgrades["overclock"] = 2
    mult = next(s for s in pc.RFC_SHOP if s["id"] == "overclock")["mult"]
    assert game.rfc_upgrade_cost("overclock") == int(base * mult ** 2)


def test_buy_spends_rfc_and_levels_up(game):
    game.rfc_points = 1000.0
    cost = game.rfc_upgrade_cost("pipelining")
    assert game.buy_rfc_upgrade("pipelining") is True
    assert game.rfc_upgrades["pipelining"] == 1
    assert game.rfc_points == pytest.approx(1000.0 - cost)


def test_buy_fails_without_enough_rfc(game):
    game.rfc_points = 0.0
    assert game.buy_rfc_upgrade("overclock") is False
    assert game.rfc_upgrades.get("overclock", 0) == 0


def test_overclock_boosts_click_mult(game):
    game.rfc_upgrades = {"overclock": 3}
    game._invalidate_fx()
    assert game.fx["click_mult"] == pytest.approx(1 + pc.RFC_OC_STEP * 3)


def test_pipelining_boosts_pps_mult(game):
    game.rfc_upgrades = {"pipelining": 4}
    game._invalidate_fx()
    assert game.fx["pps_mult"] == pytest.approx(1 + pc.RFC_PP_STEP * 4)


def test_autoresolver_generates_packets(game):
    game.owned = {}                       # click_power = 1.0
    game.rfc_upgrades = {"autoresolver": 2}   # 1.0 Auto-Klicks/s
    game._invalidate_fx()
    game.packets = 0.0
    game.update(1000)                     # 1 Sekunde
    # auto (1.0) * click_power (1.0) * 1s = 1.0 Pakete
    assert game.packets == pytest.approx(1.0, abs=0.05)


def test_rfc_upgrades_persist(game):
    game.rfc_upgrades = {"overclock": 5, "autoresolver": 2}
    game.save()
    g2 = pc.Game()
    assert g2.rfc_upgrades == {"overclock": 5, "autoresolver": 2}


def test_rfc_shop_renders(game):
    game.show_rfc_shop = True
    game.rfc_points = 500.0
    pc.draw_rfc_shop(game)                # darf nicht crashen
    rows, close = pc._rfc_shop_row_rects()
    assert len(rows) == len(pc.RFC_SHOP)
    # Klick auf erste Kauf-Schaltfläche kauft Stufe 1
    pc.rfc_shop_click(game, rows[0].centerx, rows[0].centery)
    assert game.rfc_upgrades.get(pc.RFC_SHOP[0]["id"], 0) == 1
