"""Tests für die reine Spiel-Logik (Preise, Pakete/s, Klickkraft, Prestige)."""
import pytest
import packet_clicker as pc


# ── Upgrade-Preise ────────────────────────────────────────────────────
def test_upgrade_price_base(game):
    # Ohne Besitz = Basispreis aus der Definition.
    assert game.upgrade_price("hub") == 50


def test_upgrade_price_scales_with_owned(game):
    # Preis skaliert mit 1.20 ** Anzahl.
    game.owned = {"hub": 3}
    assert game.upgrade_price("hub") == int(50 * (1.20 ** 3))


# ── Tier-Progression (inkl. höhere Tiers ab IXP) ──────────────────────
def test_tier_list_extended():
    ids = [u["id"] for u in pc.UPGRADES]
    assert ids[:10] == ["hub", "switch", "router", "firewall", "dns",
                        "loadbal", "cdn", "datacenter", "cloud", "asn"]
    # Neue Endgame-Tiers hängen hinten dran.
    assert ids[10:] == ["ixp", "tier1", "subsea", "satellite", "quantum"]


def test_prices_and_pps_strictly_increasing():
    prices = [u["base_price"] for u in pc.UPGRADES]
    ppss   = [u["pps"] for u in pc.UPGRADES]
    assert prices == sorted(prices) and len(set(prices)) == len(prices)
    assert ppss == sorted(ppss) and len(set(ppss)) == len(ppss)


def test_higher_tiers_not_challenge_gated(game):
    # Tiers oberhalb der Firewall haben keine Unlock-Challenge.
    for uid in ("ixp", "tier1", "subsea", "satellite", "quantum"):
        assert uid not in pc.TIER_CHALLENGE
        assert game.needs_challenge(uid) is False


# ── Pakete/s ──────────────────────────────────────────────────────────
def test_raw_pps_sums_owned(game):
    game.owned = {"hub": 2}          # hub = 0.5 pps
    assert game.raw_pps() == pytest.approx(1.0)


def test_raw_pps_applies_research_multiplier(game):
    game.owned = {"hub": 2}          # 1.0 pps
    game.research_done = {"subnet"}  # pps_mult 1.15
    game._invalidate_fx()
    assert game.raw_pps() == pytest.approx(1.0 * 1.15)


def test_cdn_multiplier_only_hits_cdn_tiers(game):
    game.owned = {"cdn": 1}          # cdn = 5000 pps, hat cdn-Flag
    game.research_done = {"anycast"} # cdn_mult 2.20
    game._invalidate_fx()
    assert game.raw_pps() == pytest.approx(5000 * 2.20)


def test_pps_multiplies_by_prestige(game):
    game.owned = {"hub": 2}          # raw 1.0
    game.prestige_mult = 4.0
    assert game.pps == pytest.approx(4.0)


def test_pps_zero_without_upgrades(game):
    assert game.pps == pytest.approx(0.0)


# ── Klickkraft ────────────────────────────────────────────────────────
def test_click_power_base(game):
    # Ohne Upgrades: (1 + 0) * 1.0 = 1.0
    assert game.click_power == pytest.approx(1.0)


def test_click_power_scales_with_pps_and_prestige(game):
    game.owned = {"hub": 10}         # raw_pps = 5.0
    game.prestige_mult = 2.0
    # (1 + 5.0 * 0.1) * 2.0 = 3.0
    assert game.click_power == pytest.approx(3.0)


# ── RFC-Rate ──────────────────────────────────────────────────────────
def test_rfc_rate_zero_until_unlocked(game):
    game.owned = {"hub": 1, "switch": 1}
    assert game.rfc_rate == pytest.approx(0.0)


def test_rfc_rate_counts_tiers_and_research(game):
    game.rfc_unlocked = True
    game.owned = {"hub": 1, "switch": 1}   # 2 einzigartige Tiers
    game.research_done = {"osi"}           # 1 Forschung
    assert game.rfc_rate == pytest.approx(0.08 * 2 + 0.02 * 1)


# ── Prestige ──────────────────────────────────────────────────────────
def test_prestige_doubles_multiplier_and_resets(game, monkeypatch):
    monkeypatch.setattr(game, "save", lambda: None)
    game.owned = {"hub": 5}
    game.packets = 9999.0
    game.prestige_mult = 1.0
    game.do_prestige()
    assert game.prestige == 1
    assert game.prestige_mult == pytest.approx(2.0)
    assert game.owned == {}
    assert game.packets == pytest.approx(0.0)


def test_prestige_bonus_research_triples(game, monkeypatch):
    monkeypatch.setattr(game, "save", lambda: None)
    game.research_done = {"hyperscale"}    # prestige_bonus 1.5 → 2.0 * 1.5
    game._invalidate_fx()
    game.prestige_mult = 1.0
    game.do_prestige()
    assert game.prestige_mult == pytest.approx(3.0)
