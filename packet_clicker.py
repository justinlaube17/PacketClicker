"""
Packet Clicker  —  Netzwerk-Idle-Game
Klicke Pakete, forsche, bau dein Autonomes System aus!
ESC = Beenden  |  Scrollrad = scrollen  |  Tab-Klick = Ansicht wechseln
"""

import pygame, sys, math, random, json, os, array
try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

def _asset(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

def _userdata(name):
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.path.expanduser("~"), "Documents", "PacketClicker")
        os.makedirs(base, exist_ok=True)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

W, H   = 1280, 720
LEFT_W = 460
FPS    = 60

RESOLUTIONS = [(1280, 720), (1600, 900), (1920, 1080)]
FPS_LIMITS  = [30, 60, 120, 144, 0] # 0 for uncapped

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Packet Clicker")
clock  = pygame.time.Clock()

def apply_display_settings(game):
    global W, H, screen, FPS
    W, H = RESOLUTIONS[game.res_idx]
    FPS = FPS_LIMITS[game.fps_idx]
    flags = pygame.FULLSCREEN if game.fullscreen else 0
    screen = pygame.display.set_mode((W, H), flags)

# ── Sound-System (Procedural) ──────────────────────────────────────────
_SR = 44100
def _build_sfx(fn, dur: float):
    buf = array.array('h')
    for i in range(int(_SR * dur)):
        t = i / _SR
        v = int(max(-32767, min(32767, fn(t) * 32767)))
        buf.append(v); buf.append(v)
    return pygame.mixer.Sound(buffer=buf)

def _arp_fn(t, notes, nd, decay=15, amp=0.5):
    i = min(int(t / nd), len(notes) - 1)
    return math.sin(2 * math.pi * notes[i] * t) * math.exp(-(t - i * nd) * decay) * amp

SFX = {}
try:
    pygame.mixer.init()
    SFX = {
        'click':    _build_sfx(lambda t: math.sin(2*math.pi*(800+400*t)*t)*math.exp(-t*60)*0.3, 0.05),
        'buy':      _build_sfx(lambda t: _arp_fn(t, [440, 554, 659], 0.06, decay=20, amp=0.4), 0.2),
        'research': _build_sfx(lambda t: _arp_fn(t, [523, 659, 784, 1046], 0.08, decay=15, amp=0.5), 0.35),
        'event_pos':_build_sfx(lambda t: (math.sin(2*math.pi*880*t)*0.4 + math.sin(2*math.pi*1108*t)*0.3)*math.exp(-t*10)*0.4, 0.4),
        'event_neg':_build_sfx(lambda t: (math.sin(2*math.pi*110*t)*0.6 + math.sin(2*math.pi*123*t)*0.4)*math.exp(-t*5)*0.5, 0.5),
        'prestige': _build_sfx(lambda t: _arp_fn(t, [261, 329, 392, 523, 784, 1046], 0.1, decay=8, amp=0.6), 0.7),
        'error':    _build_sfx(lambda t: (random.uniform(-1,1)*0.2)*math.exp(-t*20), 0.1),
    }

    # ── Hintergrundmusik (BGM) ──
    # Music: "Going Undercover" by Tomasz Kucza (Magnesus) via OpenGameArt.org (CC-BY 4.0)
    MUSIC_END  = pygame.USEREVENT + 1
    INTRO_PATH = _asset("Packet_Clicker.mp3")
    BGM_PATH   = _asset("bgm.ogg")
    _bgm_muted = False

    def _start_bgm_loop():
        if os.path.exists(BGM_PATH):
            try:
                pygame.mixer.music.load(BGM_PATH)
                pygame.mixer.music.set_volume(0.0 if _bgm_muted else 0.35)
                pygame.mixer.music.set_endevent(0)
                pygame.mixer.music.play(loops=-1)
            except: pass

    def start_bgm():
        if os.path.exists(INTRO_PATH):
            try:
                pygame.mixer.music.load(INTRO_PATH)
                pygame.mixer.music.set_volume(0.0 if _bgm_muted else 0.15)
                pygame.mixer.music.set_endevent(MUSIC_END)
                pygame.mixer.music.play(loops=0)
                return
            except: pass
        _start_bgm_loop()

    def set_bgm_muted(muted):
        global _bgm_muted
        _bgm_muted = muted
        pygame.mixer.music.set_volume(0.0 if muted else 0.35)

except:
    MUSIC_END = pygame.USEREVENT + 1
    def _start_bgm_loop(): pass
    def start_bgm(): pass
    def set_bgm_muted(muted): pass

def play_sfx(name):
    game = getattr(sys.modules[__name__], 'CURRENT_GAME', None)
    if game and game.sfx_muted: return
    if name in SFX:
        SFX[name].play()


# ── Farben (Design-Tokens — Cyberpunk/Tech, Cyan + Magenta + Acid) ────
# Hex-Werte direkt aus Packet Clicker Asset-Library.
BG         = (  5,   6,  10)   # #05060a
BG_TOP     = ( 11,  14,  22)   # #0b0e16 — leichte Vertikal-Variation
BG_BOT     = (  3,   4,   8)
PANEL      = ( 15,  19,  32)   # #0f1320
PANEL_HL   = ( 26,  34,  56)   # #1a2238 — panelEdge auch als Highlight
PANEL_TOP  = ( 22,  30,  52)
PANEL_BOT  = ( 11,  15,  26)
BORDER     = ( 26,  34,  56)   # #1a2238 panelEdge
BORDER_A   = (  0, 229, 255)   # cyan  #00e5ff
ACCENT_2   = (255,  43, 214)   # magenta #ff2bd6
WHITE      = (223, 231, 245)   # ink   #dfe7f5
DIM        = (123, 138, 176)   # inkDim #7b8ab0
INK_MUTE   = ( 74,  88, 122)   # inkMute #4a587a
GOLD       = (255, 176,  32)   # warn  #ffb020
GREEN_C    = ( 57, 255,  20)   # acid  #39ff14
RED_C      = (255,  58,  94)   # danger #ff3a5e
ORANGE_C   = (255, 176,  32)
CYAN_C     = (  0, 229, 255)   # cyan
BLUE_C     = ( 91, 241, 255)   # cyan-Brightstop
PURPLE_C   = (106,  20, 255)   # magenta-DarkStop
RFC_COL    = (255,  43, 214)   # magenta für RFC
SHADOW     = (  0,   0,   0)

# ── Fonts (JetBrains Mono / Space Grotesk wenn verfügbar) ─────────────
def _font(size, bold=False, display=False):
    candidates = (
        ("Space Grotesk", "JetBrains Mono", "DejaVu Sans Mono", "Courier New", "monospace")
        if display else
        ("JetBrains Mono", "DejaVu Sans Mono", "Courier New", "monospace")
    )
    for name in candidates:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f is not None: return f
        except Exception:
            pass
    return pygame.font.Font(None, size)

font_xl       = _font(48, bold=True, display=True)
font_big      = _font(34, bold=True)
font_med      = _font(24, bold=True)
font_small    = _font(20)
font_tiny     = _font(17)
font_display  = _font(64, bold=True, display=True)   # Hero-Title mit Outline

SAVE_PATH = _userdata("packet_save.json")

# ── Upgrade-Definitionen ──────────────────────────────────────────────
UPGRADES = [
    {"id": "hub",        "name": "Hub",              "abbr": "HUB", "col": DIM,
     "desc": "Broadcastet alles an jeden. Veraltet, aber billig.",
     "base_price":        50, "pps":       0.5},
    {"id": "switch",     "name": "Switch",            "abbr": "SW",  "col": BLUE_C,
     "desc": "Lernt MAC-Adressen, leitet Frames gezielt weiter.",
     "base_price":       400, "pps":       3},
    {"id": "router",     "name": "Router",            "abbr": "RT",  "col": CYAN_C,
     "desc": "Layer-3-Routing zwischen Subnetzen per IP.",
     "base_price":      3500, "pps":      15},
    {"id": "firewall",   "name": "Firewall",          "abbr": "FW",  "col": RED_C,
     "desc": "Stateful Inspection + Deep Packet Filtering.",
     "base_price":     30000, "pps":      70},
    {"id": "dns",        "name": "DNS-Server",        "abbr": "DNS", "col": GREEN_C,
     "desc": "Loest FQDNs zu IPs auf.",
     "base_price":    250000, "pps":     280},
    {"id": "loadbal",    "name": "Load Balancer",     "abbr": "LB",  "col": ORANGE_C,
     "desc": "Layer-7-Distribution auf Backend-Pools.",
     "base_price":   2000000, "pps":    1200},
    {"id": "cdn",        "name": "CDN-Node",          "abbr": "CDN", "col": GOLD,
     "desc": "Point of Presence nah beim User, minimale RTT.",
     "base_price":  18000000, "pps":    5000, "cdn": True},
    {"id": "datacenter", "name": "Rechenzentrum",     "abbr": "DC",  "col": PURPLE_C,
     "desc": "Tier-3 DC: redundante Power, Kuehlung, Anbindung.",
     "base_price": 150000000, "pps":   20000},
    {"id": "cloud",      "name": "Cloud-Region",      "abbr": "CLD", "col": CYAN_C,
     "desc": "Multi-AZ, Auto-Scaling, 99.99% SLA.",
     "base_price":1500000000, "pps":   85000, "cdn": True},
    {"id": "asn",        "name": "Autonomes System",  "abbr": "ASN", "col": BORDER_A,
     "desc": "Eigene BGP-Routing-Domain (ASN) im globalen Internet.",
     "base_price":15000000000, "pps":  400000},
]

# ── Forschungs-Definitionen ───────────────────────────────────────────
# pos = (Spalte 0-2, Zeile 0-3)
RESEARCH = [
    # Tier 1 – Grundlagen
    {"id": "osi",       "name": "OSI-Modell",      "col": BLUE_C,   "cost":   5,
     "prereqs": [],              "pos": (0, 0),
     "desc": "+15% Pakete/Klick",
     "effect": "click_mult",    "val": 1.15},
    {"id": "subnet",    "name": "Subnetting",       "col": CYAN_C,   "cost":   5,
     "prereqs": [],              "pos": (1, 0),
     "desc": "+15% Pakete/s",
     "effect": "pps_mult",      "val": 1.15},
    {"id": "arp",       "name": "ARP-Caching",      "col": GREEN_C,  "cost":   8,
     "prereqs": [],              "pos": (2, 0),
     "desc": "+20% Pakete/Klick",
     "effect": "click_mult",    "val": 1.20},
    # Tier 2 – Protokolle
    {"id": "qos",       "name": "QoS",              "col": ORANGE_C, "cost":  22,
     "prereqs": ["osi"],         "pos": (0, 1),
     "desc": "+35% Pakete/Klick",
     "effect": "click_mult",    "val": 1.35},
    {"id": "ospf",      "name": "OSPF",              "col": CYAN_C,   "cost":  22,
     "prereqs": ["subnet"],      "pos": (1, 1),
     "desc": "+30% Pakete/s",
     "effect": "pps_mult",      "val": 1.30},
    {"id": "vpn",       "name": "VPN-Tunnel",        "col": PURPLE_C, "cost":  30,
     "prereqs": ["subnet","arp"],"pos": (2, 1),
     "desc": "+25% alle Pakete",
     "effect": "all_mult",      "val": 1.25},
    # Tier 3 – Infrastruktur
    {"id": "bgpcom",    "name": "BGP Communities",  "col": ORANGE_C, "cost":  55,
     "prereqs": ["ospf"],        "pos": (0, 2),
     "desc": "Negative Events 50% kuerzer",
     "effect": "neg_dur",       "val": 0.50},
    {"id": "mpls",      "name": "MPLS",              "col": GOLD,     "cost":  60,
     "prereqs": ["ospf"],        "pos": (1, 2),
     "desc": "+70% Pakete/s",
     "effect": "pps_mult",      "val": 1.70},
    {"id": "zerotrust", "name": "Zero Trust",        "col": RED_C,    "cost":  75,
     "prereqs": ["vpn"],         "pos": (2, 2),
     "desc": "Neg. Events: -60% Wirkung",
     "effect": "neg_eff",       "val": 0.40},
    # Tier 4 – Hyperscale
    {"id": "anycast",   "name": "Anycast",           "col": CYAN_C,   "cost": 110,
     "prereqs": ["mpls","qos"],  "pos": (0, 3),
     "desc": "+120% CDN & Cloud Pakete/s",
     "effect": "cdn_mult",      "val": 2.20},
    {"id": "sdwan",     "name": "SD-WAN",             "col": BORDER_A, "cost": 130,
     "prereqs": ["mpls","zerotrust"],"pos": (1, 3),
     "desc": "+90% alle Pakete",
     "effect": "all_mult",      "val": 1.90},
    {"id": "hyperscale","name": "Hyperscale",        "col": GOLD,     "cost": 220,
     "prereqs": ["anycast","sdwan"],"pos": (2, 3),
     "desc": "Prestige gibt 3x statt 2x",
     "effect": "prestige_bonus","val": 1.50},
]

# ── Ereignisse ────────────────────────────────────────────────────────
EVENTS = [
    {"id": "ddos",    "name": "DDoS-Angriff!",     "col": RED_C,    "dur": 15,
     "desc": "Pakete/s auf 25% reduziert.",          "pps_m": 0.25, "clk_m": 1.0, "negative": True},
    {"id": "bgp",     "name": "BGP-Hijack!",        "col": RED_C,    "dur": 12,
     "desc": "Traffic umgeleitet — nur 30% ankommen.","pps_m": 0.30, "clk_m": 0.3, "negative": True},
    {"id": "maint",   "name": "Wartungsfenster",    "col": ORANGE_C, "dur":  8,
     "desc": "Auto-Routing pausiert.",               "pps_m": 0.0,  "clk_m": 1.0, "negative": True},
    {"id": "flood",   "name": "Paketflut!",         "col": GREEN_C,  "dur": 20,
     "desc": "Doppelte Pakete/s!",                   "pps_m": 2.0,  "clk_m": 1.0, "negative": False},
    {"id": "peering", "name": "Peering-Deal!",      "col": CYAN_C,   "dur": 15,
     "desc": "Neuer Uplink — 3x Pakete/s!",           "pps_m": 3.0,  "clk_m": 1.0, "negative": False},
    {"id": "cache",   "name": "Cache-Hit-Storm!",   "col": BLUE_C,   "dur": 12,
     "desc": "5x Klick-Bonus!",                      "pps_m": 1.0,  "clk_m": 5.0, "negative": False},
    {"id": "zeroday", "name": "Zero-Day-Exploit!",  "col": RED_C,    "dur":  8,
     "desc": "Pakete werden aktiv gestohlen!",        "pps_m":-0.05, "clk_m": 1.0, "negative": True},
]

# ── TCP-Handshake (Wire + Paket) ──────────────────────────────────────
HS_WIRE_Y       = 195      # y-Koordinate der Leitung (ueber Klick-Kreis)
HS_WIRE_MARGIN  = 30       # Innen-Margin am linken/rechten Panel-Rand
HS_TRAVEL_MS    = 1600     # ms pro Phase (Paket-Flugzeit)
HS_PACKET_DRAW  = 11       # visueller Paket-Radius
HS_PACKET_HIT   = 22       # Klick-Toleranz (Hitbox-Radius)
HS_HITZONE_W    = 110      # Sweet-Spot-Breite (mittig, fuer PERFECT)
HS_NEXT_MIN     = 35_000   # ms bis naechste Chance (Min)
HS_NEXT_MAX     = 70_000   # ms bis naechste Chance (Max)
HS_RETRY_DELAY  = 18_000   # ms Cooldown nach Fehlschlag
HS_MIN_TOTAL    = 100      # erst ab so vielen Total-Paketen
HS_BONUS_SECS   = 30       # Reward = pps * BONUS_SECS
HS_BONUS_MIN    = 50       # Sockelbetrag, falls pps niedrig
HS_COMBO_STEP   = 0.25     # +25% Bonus pro Combo-Stufe
HS_COMBO_CAP    = 2.5      # Combo-Multiplikator max
HS_PERFECT_BUFF_MS   = 5000   # Dauer des x2-Klick-Buffs bei 3x PERFECT
HS_PERFECT_BUFF_MULT = 2.0    # Klick-Multiplikator-Wert

# ── Minigames (Tier-Unlock-Challenges) ────────────────────────────────
MG_PANEL_W      = 680
MG_PANEL_H      = 480
MG_FAIL_COST    = 0.25         # 25% der Pakete bei Niederlage
MG_COOLDOWN_MS  = 15_000       # 15s Sperre nach Niederlage
MG_RESULT_DELAY = 1500         # ms Sichtbarkeit der Win/Lose-Anzeige

# Frame-Forwarder Parameter
MG_FF_GOAL          = 10
MG_FF_LIVES         = 3
MG_FF_PORTS         = ["A", "B", "C"]
MG_FF_FALL_BASE     = 2400     # ms Fallzeit bei Score 0
MG_FF_FALL_MIN      = 600      # ms Fallzeit am Ende (Score nahe Goal)
MG_FF_FALL_CURVE    = 1.9      # Exponent: >1 = beschleunigt gegen Ende staerker
MG_FF_RESPAWN_BASE  = 320      # ms Pause zwischen Frames bei Score 0
MG_FF_RESPAWN_MIN   = 90       # ms Pause am Ende
MG_FF_ARENA_H       = 240
MG_FF_FRAME_H       = 44

# Cable-Patch Parameter (Hub-Challenge)
MG_CP_LIVES         = 2
MG_CP_PICK_R        = 16       # Klick-Toleranz fuer Plug-Pickup
MG_CP_SNAP_R        = 30       # Snap-Radius zum Port beim Loslassen
MG_CP_PLUG_R        = 11       # Visueller Plug-Radius
MG_CP_ROW_GAP       = 80
MG_CP_TOP_OFFSET    = 175      # y-Offset 1. Zeile relativ zum Panel
MG_CP_TIME_MS       = 25_000   # Zeitlimit pro Versuch

# Knoten-Bänder: 4 vertikale Bänder zwischen Anchor und Slot.
# An jedem Band wird eine Y-Permutation der drei Kabel angefahren → Mehrfach-Crossings.
MG_CP_BAND_FRACS = [0.18, 0.40, 0.62, 0.84]
MG_CP_JITTER_Y   = 22       # Max Y-Versatz pro Wegpunkt
MG_CP_SEG_PTS    = 14       # Catmull-Rom Samples pro Segment

# Route-Table Racer Parameter
MG_RT_GOAL     = 10
MG_RT_LIVES    = 3
MG_RT_TIME_MS  = 3500       # Startzeit pro Paket (ms)
MG_RT_TIME_MIN = 1200       # Mindestzeit pro Paket

# Packet Inspector (Firewall-Challenge)
MG_PI_GOAL        = 12
MG_PI_LIVES       = 3
MG_PI_TIME_BASE   = 6000      # ms pro Paket am Anfang
MG_PI_TIME_MIN    = 2500      # untere Schranke
MG_PI_TIME_STEP   = 150       # ms speedup je korrektem Hit
MG_PI_INTRO_BONUS = 3000      # erstes Paket bekommt extra Zeit
MG_PI_FLASH_MS    = 850       # Feedback-Pause zwischen Paketen
MG_PI_NEXT_DELAY  = 350       # ms Verzögerung bevor neues Paket spawnt

PI_RULES_POOL = [
    {"id":"telnet",  "text":"BLOCK  dst port 23",       "verdict":"drop",
     "match": lambda p: p["proto"] == "TCP" and p["dst_port"] == 23},
    {"id":"rdp",     "text":"BLOCK  dst port 3389",     "verdict":"drop",
     "match": lambda p: p["proto"] == "TCP" and p["dst_port"] == 3389},
    {"id":"icmp",    "text":"BLOCK  proto ICMP",        "verdict":"drop",
     "match": lambda p: p["proto"] == "ICMP"},
    {"id":"privsrc", "text":"BLOCK  src 10.0.0.0/8",    "verdict":"drop",
     "match": lambda p: p["src_ip"].startswith("10.")},
    {"id":"web",     "text":"ALLOW  dst port 80, 443",  "verdict":"allow",
     "match": lambda p: p["proto"] == "TCP" and p["dst_port"] in (80, 443)},
    {"id":"dns",     "text":"ALLOW  dst port 53",       "verdict":"allow",
     "match": lambda p: p["dst_port"] == 53},
    {"id":"nmap",    "text":"BLOCK  flags = SYN+FIN",   "verdict":"drop",
     "match": lambda p: p.get("flags") == "SYN+FIN"},
]

# Welcher Tier braucht welchen Minigame-Typ?
# Tiers, die hier NICHT auftauchen, sind automatisch freigeschaltet.
TIER_CHALLENGE = {
    "hub":      "cable_patch",
    "switch":   "frame_forwarder",
    "router":   "route_table",
    "firewall": "packet_inspector",
}

def _ff_colors():
    # Mapping wird zur Laufzeit aufgebaut, da Farben oben definiert sind
    return {"A": CYAN_C, "B": GREEN_C, "C": ORANGE_C}

def _hs_wire_coords():
    return HS_WIRE_MARGIN, LEFT_W - HS_WIRE_MARGIN, HS_WIRE_Y

# ── Hilfsfunktionen ───────────────────────────────────────────────────

def fmt(n: float) -> str:
    n = float(n)
    for div, suf in [(1e18,"Qi"),(1e15,"Qa"),(1e12,"T"),(1e9,"B"),(1e6,"M"),(1e3,"K")]:
        if abs(n) >= div:
            return f"{n/div:.2f}{suf}"
    if abs(n) < 1000 and abs(n - round(n)) > 0.05:
        return f"{n:.1f}"
    return f"{int(round(n))}"

# ── Modern-Render-Helpers ─────────────────────────────────────────────
# Surface-Cache: teure Effekte (Gradienten, Glow) werden einmal gerendert.
# WICHTIG: Cache ist beschränkt (FIFO-Eviction), sonst füllt sich der RAM bei
# kontinuierlich animierten Farben (Sinus-Mixing) gnadenlos auf.
_SURF_CACHE: dict = {}
_SURF_CACHE_MAX = 256

def _cache_put(key, surf):
    if len(_SURF_CACHE) >= _SURF_CACHE_MAX:
        # Älteste 32 Einträge wegwerfen (Python 3.7+ dict ist insertion-ordered)
        for old in list(_SURF_CACHE.keys())[:32]:
            del _SURF_CACHE[old]
    _SURF_CACHE[key] = surf
    return surf

def _shade(col, k):
    return tuple(max(0, min(255, int(c * k))) for c in col[:3])

def _mix(a, b, t):
    # t darf außerhalb [0,1] liegen (z.B. 0.3 + 0.35*sin(x) ⇒ leicht negativ).
    # Ergebnis-Komponenten auf gültigen Color-Range clampen.
    return tuple(max(0, min(255, int(a[i]*(1-t) + b[i]*t))) for i in range(3))

def _qcol(col, step=16):
    """Farbe auf Step-Raster quantisieren, damit Cache nicht explodiert."""
    return tuple(max(0, min(255, (c // step) * step)) for c in col[:3])

def gradient_v(w, h, top, bot):
    key = ("gv", w, h, _qcol(top, 8), _qcol(bot, 8))
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h))
    for y in range(h):
        s.fill(_mix(top, bot, y / max(1, h-1)), (0, y, w, 1))
    return _cache_put(key, s)

def glow_surf(r, col, intensity=140, layers=14):
    # Farbe + Intensität quantisieren – visuell identisch, Cache bounded
    qc = _qcol(col, 16)
    qi = (intensity // 10) * 10
    key = ("glow", r, qc, qi, layers)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    size = r * 2 + 4
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(layers, 0, -1):
        rr = int(r * i / layers)
        a  = int(qi * (1 - i/layers) ** 1.4)
        pygame.draw.circle(s, (*qc, a), (size//2, size//2), rr)
    return _cache_put(key, s)

def panel_shadow(w, h, radius=8, blur=10, alpha=160):
    key = ("psh", w, h, radius, blur, alpha)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    pad = blur
    s = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
    for i in range(blur, 0, -1):
        a = int(alpha * (1 - i/blur) ** 1.5)
        pygame.draw.rect(s, (0, 0, 0, a),
                         (pad - i//2, pad - i//2 + 2, w + i, h + i),
                         border_radius=radius + i//3)
    return _cache_put(key, s)

def rounded_rect_alpha(w, h, col, alpha, radius=8):
    key = ("rr", w, h, _qcol(col, 4), alpha, radius)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*col, alpha), s.get_rect(), border_radius=radius)
    return _cache_put(key, s)

def draw_rect_border(surf, col, rect, border=2, radius=8, fill=None,
                     shadow=True, gradient=True, highlight=True):
    """Modernes Panel: Gradient-Füllung, Soft-Shadow, Glas-Highlight, Akzent-Border."""
    r = pygame.Rect(rect)
    if r.w <= 0 or r.h <= 0:
        return
    if fill is not None:
        if shadow and r.w >= 24 and r.h >= 16:
            sh = panel_shadow(r.w, r.h, radius=radius, blur=8, alpha=120)
            surf.blit(sh, (r.x - 8, r.y - 6))
        if gradient:
            top = tuple(min(255, c + 14) for c in fill[:3])
            bot = tuple(max(0, c - 10) for c in fill[:3])
            g = gradient_v(r.w, r.h, top, bot).copy()
            mask = rounded_rect_alpha(r.w, r.h, (255, 255, 255), 255, radius=radius)
            g2 = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            g2.blit(g, (0, 0))
            g2.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(g2, r.topleft)
        else:
            surf.blit(rounded_rect_alpha(r.w, r.h, fill[:3], 230, radius=radius), r.topleft)
        if highlight and r.h >= 18:
            hl_h = max(2, r.h // 4)
            hl = pygame.Surface((r.w, hl_h), pygame.SRCALPHA)
            pygame.draw.rect(hl, (255, 255, 255, 22),
                             (0, 0, r.w, hl_h),
                             border_top_left_radius=radius,
                             border_top_right_radius=radius)
            surf.blit(hl, r.topleft)
    pygame.draw.rect(surf, col, r, border, border_radius=radius)

def draw_glow_border(surf, col, rect, radius=8, intensity=70):
    """Weiches Außen-Glow um einen Rect (Akzent-Highlight)."""
    r = pygame.Rect(rect)
    pad = 8
    s = pygame.Surface((r.w + pad*2, r.h + pad*2), pygame.SRCALPHA)
    for i in range(pad, 0, -1):
        a = int(intensity * (1 - i/pad) ** 1.4)
        pygame.draw.rect(s, (*col, a),
                         (pad - i, pad - i, r.w + i*2, r.h + i*2),
                         2, border_radius=radius + i)
    surf.blit(s, (r.x - pad, r.y - pad))

def text(surf, font, txt, col, x, y, anchor="topleft"):
    s = font.render(str(txt), True, col)
    r = s.get_rect(**{anchor: (x, y)})
    surf.blit(s, r)
    return r

def text_glow(surf, font, txt, col, x, y, anchor="topleft", glow_col=None, intensity=2):
    """Text mit weichem Glow für Highlights / Titel."""
    glow_col = glow_col or col
    s = font.render(str(txt), True, col)
    rect = s.get_rect(**{anchor: (x, y)})
    g = font.render(str(txt), True, glow_col)
    g.set_alpha(70)
    for dx, dy in [(-intensity, 0), (intensity, 0), (0, -intensity), (0, intensity),
                   (-intensity, -intensity), (intensity, intensity),
                   (-intensity, intensity), (intensity, -intensity)]:
        surf.blit(g, (rect.x + dx, rect.y + dy))
    surf.blit(s, rect)
    return rect

# ── FloatingText ──────────────────────────────────────────────────────

class FloatingText:
    def __init__(self, x, y, msg, col=GREEN_C):
        self.x, self.y = float(x), float(y)
        self.msg = msg; self.col = col
        self.vy  = -1.8; self.age = 0; self.ttl = 75

    def update(self):
        self.y += self.vy; self.vy *= 0.95; self.age += 1

    def draw(self, surf):
        alpha = max(0, int(255 * (1 - self.age / self.ttl)))
        s = font_med.render(self.msg, True, self.col)
        s.set_alpha(alpha)
        surf.blit(s, (int(self.x - s.get_width()//2), int(self.y)))

    @property
    def done(self): return self.age >= self.ttl

# ── Netzwerk-Paket (Animation) ────────────────────────────────────────

class NetPacket:
    def __init__(self, sx, sy, tx, ty, col=BORDER_A):
        self.x, self.y   = float(sx), float(sy)
        self.tx, self.ty = float(tx), float(ty)
        self.col = col; self.prog = 0.0
        self.spd = random.uniform(0.025, 0.055)

    def update(self): self.prog = min(1.0, self.prog + self.spd)

    def draw(self, surf):
        t = self.prog
        mx = (self.x + self.tx) / 2
        my = (self.y + self.ty) / 2 - 60
        cx = (1-t)**2*self.x + 2*(1-t)*t*mx + t**2*self.tx
        cy = (1-t)**2*self.y + 2*(1-t)*t*my + t**2*self.ty
        pygame.draw.circle(surf, self.col, (int(cx), int(cy)), 3)

    @property
    def done(self): return self.prog >= 1.0

# ── DDoS-Paket (Mini-Game) ─────────────────────────────────────────────

class DDoSPacket:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(1.5, 3.5)
        self.col = RED_C
        self.radius = 12
        self.hp = 1  # Number of clicks to destroy

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf):
        pygame.draw.circle(surf, self.col, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.radius, 1)
        pygame.draw.line(surf, WHITE, (int(self.x)-6, int(self.y)-6), (int(self.x)+6, int(self.y)+6), 2)
        pygame.draw.line(surf, WHITE, (int(self.x)+6, int(self.y)-6), (int(self.x)-6, int(self.y)+6), 2)

    @property
    def done(self): return self.y > H + 20

# ── Netzwerk-Visualisierung ───────────────────────────────────────────

class NetViz:
    def __init__(self, cx, cy, r):
        self.cx, self.cy, self.r = cx, cy, r
        self._t = 0.0
        self.nodes = [
            {"base_angle": i * math.tau/8 + random.uniform(-0.2, 0.2),
             "speed": random.uniform(0.002, 0.008) * random.choice([-1,1]),
             "dist":  random.uniform(r*0.35, r*0.80),
             "col":   random.choice([BLUE_C, CYAN_C, BORDER_A, GOLD])}
            for i in range(8)
        ]

    def update(self, dt): self._t += dt * 0.001

    def _pos(self, n):
        a = n["base_angle"] + self._t * n["speed"] * 200
        return (int(self.cx + math.cos(a)*n["dist"]),
                int(self.cy + math.sin(a)*n["dist"]))

    def draw(self, surf):
        positions = [self._pos(n) for n in self.nodes]
        for i, p in enumerate(positions):
            for j in range(i+1, len(positions)):
                q = positions[j]
                d = math.hypot(p[0]-q[0], p[1]-q[1])
                if d < self.r * 0.65:
                    alpha = max(0, int(160*(1-d/(self.r*0.65))))
                    pygame.draw.line(surf, (*BORDER_A, alpha), p, q, 1)
        for p, n in zip(positions, self.nodes):
            pygame.draw.circle(surf, n["col"], p, 5)
            pygame.draw.circle(surf, WHITE,    p, 5, 1)

# ── Main Menu Animation ───────────────────────────────────────────────

class MenuBackground:
    def __init__(self):
        self.nodes = []
        for _ in range(60):
            self.nodes.append({
                "x": random.uniform(0, 2500),
                "y": random.uniform(0, 1500),
                "vx": random.uniform(-15, 15),
                "vy": random.uniform(-15, 15),
                "col": random.choice([BLUE_C, CYAN_C, BORDER_A, DIM])
            })
            
    def update(self, dt):
        for n in self.nodes:
            n["x"] += n["vx"] * (dt / 1000.0)
            n["y"] += n["vy"] * (dt / 1000.0)
            if n["x"] < -100: n["x"] = 2600
            elif n["x"] > 2600: n["x"] = -100
            if n["y"] < -100: n["y"] = 1600
            elif n["y"] > 1600: n["y"] = -100

    def draw(self, surf):
        surf.blit(gradient_v(W, H, BG_TOP, BG_BOT), (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        for i, n1 in enumerate(self.nodes):
            for n2 in self.nodes[i+1:]:
                d = math.hypot(n1["x"]-n2["x"], n1["y"]-n2["y"])
                if d < 220:
                    ratio = d / 220.0
                    alpha = int(160 * (1 - ratio) ** 1.4)
                    if alpha <= 4: continue
                    pygame.draw.line(overlay, (*BORDER_A, alpha),
                                     (int(n1["x"]), int(n1["y"])),
                                     (int(n2["x"]), int(n2["y"])), 1)
        surf.blit(overlay, (0, 0))
        for n in self.nodes:
            cx, cy = int(n["x"]), int(n["y"])
            g = glow_surf(10, n["col"], intensity=70, layers=6)
            surf.blit(g, (cx - g.get_width()//2, cy - g.get_height()//2))
            pygame.draw.circle(surf, n["col"], (cx, cy), 3)
            pygame.draw.circle(surf, WHITE, (cx, cy), 1)

# ── Spielzustand ─────────────────────────────────────────────────────

class Game:
    def __init__(self):
        global CURRENT_GAME
        CURRENT_GAME = self
        
        self.packets        = 0.0
        self.total_packets  = 0.0
        self.owned          = {}
        self.prestige       = 0
        self.prestige_mult  = 1.0
        self.rfc_points     = 0.0
        self.research_done  = set()
        self.event          = None
        self.event_until    = 0
        self.next_event     = pygame.time.get_ticks() + 45_000
        self.shop_scroll    = 0
        self.res_scroll     = 0
        self.tab            = "upgrades"   # "upgrades" | "research"
        self._last_save     = pygame.time.get_ticks()
        self.floats         = []
        self.net_packets    = []
        self.ddos_packets   = []
        self.ddos_spawn_timer = 0
        self.click_pulse    = 0.0
        self.click_shockwaves = []   # [{"age":ms, "ttl":ms, "col":(r,g,b)}]
        self.show_debug     = False

        # TCP-Handshake
        self.hs_state       = None     # None | "syn" | "synack" | "ack"
        self.hs_started     = 0        # ms timestamp aktueller Phase
        self.hs_next        = pygame.time.get_ticks() + 60_000
        self.hs_combo       = 0
        self.hs_perfects    = 0        # PERFECT-Hits in aktueller Sequenz
        self.click_buff_until = 0      # ms timestamp – Klick-Multiplikator aktiv bis

        # Tier-Unlock-Challenges
        self.unlocked            = set()     # alle Tiers gelockt, hub via Cable-Patch
        self.minigame            = None      # None oder Minigame-State-Dict
        self.challenge_cooldown  = {}        # uid -> ms timestamp bis wann gesperrt
        self.mg_tutorials_seen   = set()     # Minigame-Typen für die das Tutorial schon gezeigt wurde

        # RFC-Forschung: erst nach Firewall-Kauf zugänglich
        self.rfc_unlocked        = False
        self.show_rfc_intro      = False

        # Einführungs-Popup: nur beim allerersten Start
        self.show_intro          = True
        self.intro_page          = 0

        self.confirm_prestige = False
        self._fx_cache      = None         # cached research effects
        
        self.state          = "menu"       # "menu" | "playing" | "settings"
        self.music_muted    = False
        self.sfx_muted      = False
        self.res_idx        = 0
        self.fps_idx        = 1
        self.fullscreen     = False
        
        self.load()
        set_bgm_muted(self.music_muted)
        apply_display_settings(self)

    # ── Forschungs-Effekte ───────────────────────────────────────────
    def _compute_fx(self):
        fx = {"click_mult":1.0,"pps_mult":1.0,"all_mult":1.0,
              "neg_dur":1.0,"neg_eff":1.0,"cdn_mult":1.0,"prestige_bonus":1.0}
        for r in RESEARCH:
            if r["id"] in self.research_done:
                fx[r["effect"]] *= r["val"]
        return fx

    @property
    def fx(self):
        if self._fx_cache is None:
            self._fx_cache = self._compute_fx()
        return self._fx_cache

    def _invalidate_fx(self):
        self._fx_cache = None

    # ── RFC-Generierung ──────────────────────────────────────────────
    @property
    def rfc_rate(self):
        if not self.rfc_unlocked:
            return 0.0
        unique = sum(1 for u in UPGRADES if self.owned.get(u["id"],0) > 0)
        return 0.08 * unique + 0.02 * len(self.research_done)

    # ── Pakete/s ─────────────────────────────────────────────────────
    def raw_pps(self):
        total = 0.0
        cdn_m = self.fx["cdn_mult"]
        for u in UPGRADES:
            cnt = self.owned.get(u["id"], 0)
            if cnt == 0: continue
            up = u["pps"] * cnt
            if u.get("cdn"):
                up *= cdn_m
            total += up
        return total * self.fx["pps_mult"] * self.fx["all_mult"]

    @property
    def pps(self):
        base = self.raw_pps() * self.prestige_mult
        if self.event:
            m = self.event.get("pps_m", 1.0)
            if m < 0:
                return base          # drain handled separately
            if self.event.get("negative") and m < 1.0:
                neg_eff = self.fx["neg_eff"]
                m = 1.0 - (1.0 - m) * neg_eff
            base *= m
        return base

    @property
    def pps_drain(self):
        if self.event and self.event.get("pps_m", 1.0) < 0:
            return abs(self.event["pps_m"]) * self.raw_pps() * self.prestige_mult
        return 0.0

    @property
    def click_power(self):
        base = (1.0 + self.raw_pps() * 0.1) * self.prestige_mult
        base *= self.fx["click_mult"] * self.fx["all_mult"]
        if self.event:
            m = self.event.get("clk_m", 1.0)
            if self.event.get("negative") and m < 1.0:
                m = 1.0 - (1.0 - m) * self.fx["neg_eff"]
            base *= m
        if pygame.time.get_ticks() < self.click_buff_until:
            base *= HS_PERFECT_BUFF_MULT
        return base

    @property
    def click_buff_remaining(self):
        return max(0, self.click_buff_until - pygame.time.get_ticks())

    # ── Upgrade-Preis ────────────────────────────────────────────────
    def upgrade_price(self, uid):
        u = next(u for u in UPGRADES if u["id"] == uid)
        return int(u["base_price"] * (1.20 ** self.owned.get(uid, 0)))

    # ── Forschung verfügbar? ─────────────────────────────────────────
    def can_research(self, rid):
        r = next(r for r in RESEARCH if r["id"] == rid)
        if rid in self.research_done: return False
        if self.rfc_points < r["cost"]: return False
        return all(p in self.research_done for p in r["prereqs"])

    def prereqs_met(self, rid):
        r = next(r for r in RESEARCH if r["id"] == rid)
        return all(p in self.research_done for p in r["prereqs"])

    # ── Aktionen ─────────────────────────────────────────────────────
    def click(self, mx, my):
        earned = self.click_power
        self.packets       += earned
        self.total_packets += earned
        self.click_pulse    = 1.0
        # Shockwave bei jedem Klick: läuft 600ms vom Kreis nach außen.
        # Liste wird gecappt, sonst sammeln sich bei Click-Spam zu viele große
        # SRCALPHA-Surfaces pro Frame an → Performance/Crash.
        buff_active = self.click_buff_remaining > 0
        sw_col = GOLD if buff_active else BORDER_A
        self.click_shockwaves.append({"age": 0, "ttl": 620, "col": sw_col})
        if buff_active:
            self.click_shockwaves.append({"age": 0, "ttl": 620, "col": ACCENT_2})
        if len(self.click_shockwaves) > 8:
            self.click_shockwaves = self.click_shockwaves[-8:]
        play_sfx('click')
        col = GOLD if (self.event and self.event.get("clk_m",1)>1) else GREEN_C
        self.floats.append(FloatingText(mx, my, f"+{fmt(earned)}", col))
        owned_list = [u for u in UPGRADES if self.owned.get(u["id"],0)>0]
        if owned_list:
            tgt = random.choice(owned_list)
            idx = UPGRADES.index(tgt)
            ty  = self._shop_y(idx)
            if ty > 0:
                self.net_packets.append(NetPacket(mx, my, LEFT_W+30, ty+20, tgt["col"]))

    # ── TCP-Handshake ────────────────────────────────────────────────
    def _hs_packet_pos(self, now):
        """Aktuelle Paketposition auf der Leitung, oder None wenn Paket draussen."""
        if self.hs_state not in ("syn", "synack", "ack"):
            return None
        x1, x2, y = _hs_wire_coords()
        t = (now - self.hs_started) / HS_TRAVEL_MS
        if t < 0 or t > 1.0:
            return None
        if self.hs_state == "synack":
            x = x2 - (x2 - x1) * t   # rechts -> links
        else:
            x = x1 + (x2 - x1) * t   # links -> rechts
        return (int(x), y)

    def _hs_start_phase(self, phase, now):
        self.hs_state   = phase
        self.hs_started = now

    def _update_handshake(self, now):
        if self.hs_state is None:
            if now >= self.hs_next and self.total_packets > HS_MIN_TOTAL:
                self.hs_perfects = 0
                self._hs_start_phase("syn", now)
            return
        # Paket hat das Ende der Leitung erreicht, ohne getroffen worden zu sein
        if now - self.hs_started > HS_TRAVEL_MS:
            self._handshake_fail()

    def try_hs_click(self, mx, my):
        """Klick-Hit-Test auf das fliegende Paket. True = vom Handshake konsumiert."""
        if self.hs_state not in ("syn", "synack", "ack"):
            return False
        now = pygame.time.get_ticks()
        pos = self._hs_packet_pos(now)
        if pos is None:
            return False
        px, py = pos
        if math.hypot(mx - px, my - py) > HS_PACKET_HIT:
            return False
        # Treffer! Sweet-Spot pruefen
        x1, x2, _ = _hs_wire_coords()
        center = (x1 + x2) // 2
        perfect = abs(px - center) <= HS_HITZONE_W // 2
        if perfect:
            self.hs_perfects += 1
            self.floats.append(FloatingText(px, py - 22, "PERFECT", GOLD))
        else:
            self.floats.append(FloatingText(px, py - 22, "HIT", CYAN_C))
        play_sfx('click')
        if self.hs_state == "syn":
            self._hs_start_phase("synack", now)
        elif self.hs_state == "synack":
            self._hs_start_phase("ack", now)
        else:   # ack -> erfolgreich abgeschlossen
            self._handshake_success(mx, my)
        return True

    def _handshake_fail(self):
        cx, cy = LEFT_W // 2, 335
        self.floats.append(FloatingText(cx, cy - 150, "RST — Connection Reset", RED_C))
        self.hs_state = None
        self.hs_combo = 0
        self.hs_perfects = 0
        self.hs_next  = pygame.time.get_ticks() + HS_RETRY_DELAY
        play_sfx('error')

    def _handshake_success(self, mx, my):
        self.hs_combo += 1
        cx, cy = LEFT_W // 2, 335
        base   = max(float(HS_BONUS_MIN), self.pps * HS_BONUS_SECS)
        # Combo (sequenzuebergreifend) + Perfect-Bonus (innerhalb dieser Sequenz)
        mult   = min(HS_COMBO_CAP, 1.0 + HS_COMBO_STEP * (self.hs_combo - 1))
        if self.hs_perfects == 3:
            mult *= 1.5    # alle drei Phasen im Sweet-Spot
        bonus  = base * mult * self.fx["all_mult"]
        self.packets       += bonus
        self.total_packets += bonus
        tag = "  3x PERFECT" if self.hs_perfects == 3 else (f"  x{self.hs_combo} COMBO" if self.hs_combo > 1 else "")
        self.floats.append(FloatingText(cx, cy - 150, f"ESTABLISHED!{tag}", GOLD))
        self.floats.append(FloatingText(mx, my - 30, f"+{fmt(bonus)}", GOLD))
        if self.hs_perfects == 3:
            now = pygame.time.get_ticks()
            self.click_buff_until = max(self.click_buff_until, now + HS_PERFECT_BUFF_MS)
            self.floats.append(FloatingText(cx, cy - 128,
                                            f"x{HS_PERFECT_BUFF_MULT:.0f} KLICK · {HS_PERFECT_BUFF_MS//1000}s",
                                            GOLD))
        play_sfx('prestige')
        self.hs_state = None
        self.hs_next  = pygame.time.get_ticks() + random.randint(HS_NEXT_MIN, HS_NEXT_MAX)

    # ── Tier-Unlock-Minigame ─────────────────────────────────────────
    def needs_challenge(self, uid):
        return (uid in TIER_CHALLENGE) and (uid not in self.unlocked)

    def is_challenge_available(self, uid):
        if uid not in TIER_CHALLENGE: return True
        order = [u["id"] for u in UPGRADES if u["id"] in TIER_CHALLENGE]
        idx = order.index(uid)
        return idx == 0 or order[idx - 1] in self.unlocked

    def challenge_cd_left(self, uid):
        return max(0, self.challenge_cooldown.get(uid, 0) - pygame.time.get_ticks())

    def start_minigame(self, uid):
        if not self.needs_challenge(uid): return
        if not self.is_challenge_available(uid): return
        if self.challenge_cd_left(uid) > 0: return
        mg_type = TIER_CHALLENGE[uid]
        show_tutorial = mg_type not in self.mg_tutorials_seen
        if show_tutorial:
            self.mg_tutorials_seen.add(mg_type)
            self.save()
        if mg_type == "frame_forwarder":
            self.minigame = {
                "type":       "frame_forwarder",
                "target":     uid,
                "score":      0,
                "lives":      MG_FF_LIVES,
                "frame":      None,
                "next_spawn": 0,
                "result":     None,
                "result_at":  0,
                "tutorial":   show_tutorial,
            }
        elif mg_type == "cable_patch":
            self.minigame = self._build_cable_patch(uid)
            self.minigame["tutorial"] = show_tutorial
        elif mg_type == "route_table":
            self.minigame = {
                "type":        "route_table",
                "target":      uid,
                "score":       0,
                "lives":       MG_RT_LIVES,
                "packet_ip":   None,
                "correct":     None,
                "timer_start": 0,
                "timer_ms":    MG_RT_TIME_MS,
                "next_spawn":  pygame.time.get_ticks() + 600,
                "feedback":    None,
                "result":      None,
                "result_at":   0,
                "tutorial":    show_tutorial,
            }
        elif mg_type == "packet_inspector":
            self.minigame = {
                "type":          "packet_inspector",
                "target":        uid,
                "rules":         _pi_build_rules(),
                "score":         0,
                "lives":         MG_PI_LIVES,
                "packet":        None,
                "time_per_pkt":  MG_PI_TIME_BASE,
                "deadline":      0,
                "next_spawn":    pygame.time.get_ticks() + 600 + MG_PI_INTRO_BONUS,
                "feedback":      None,
                "result":        None,
                "result_at":     0,
                "intro":         True,
                "tutorial":      show_tutorial,
            }
        else:
            return
        # Handshake zuruecksetzen waehrend Minigame
        self.hs_state = None
        play_sfx('event_pos')

    def _cp_band_perms(self):
        """Pro Band eine Nicht-Identitäts-Permutation → an jedem Band crossen Kabel."""
        non_identity = [[1,0,2], [0,2,1], [2,1,0], [1,2,0], [2,0,1]]
        # Möglichst unterschiedliche Permutationen aufeinanderfolgend
        result = []
        for _ in range(len(MG_CP_BAND_FRACS)):
            choices = [p for p in non_identity if not result or p != result[-1]]
            result.append(random.choice(choices))
        return result

    def _cp_apply_waypoints(self, cables, band_perms):
        """Setzt waypoints anhand der Band-Permutationen + leichtes Y-Jitter."""
        px, py = _ff_panel_rect()
        y_levels = [py + MG_CP_TOP_OFFSET + lvl * MG_CP_ROW_GAP for lvl in range(3)]
        anchor_x = _cp_anchor_pos(0)[0]
        slot_x   = _cp_slot_pos(0)[0]
        band_xs  = [int(anchor_x + (slot_x - anchor_x) * f) for f in MG_CP_BAND_FRACS]
        for c in cables:
            i = c["pc_idx"]
            wps = []
            for b, bx in enumerate(band_xs):
                lvl = band_perms[b][i]
                jitter = random.randint(-MG_CP_JITTER_Y, MG_CP_JITTER_Y)
                wps.append((bx, y_levels[lvl] + jitter))
            c["waypoints"] = wps

    def _build_cable_patch(self, uid):
        # Slot-Permutation (Endposition der losen Enden) – nur Zyklen
        slot_perm = random.choice([[1, 2, 0], [2, 0, 1]])
        colors    = [BLUE_C, ORANGE_C, GREEN_C]
        cables = []
        for i in range(3):
            slot = _cp_slot_pos(slot_perm[i])
            cables.append({
                "pc_idx":      i,
                "color":       colors[i],
                "waypoints":   [],   # gleich gefüllt
                "end_pos":     slot,
                "start_pos":   slot,
                "placed_port": None,
            })
        self._cp_apply_waypoints(cables, self._cp_band_perms())
        return {
            "type":         "cable_patch",
            "target":       uid,
            "lives":        MG_CP_LIVES,
            "cables":       cables,
            "dragging_idx": None,
            "start_time":   pygame.time.get_ticks(),
            "result":       None,
            "result_at":    0,
        }

    def _cp_reshuffle_curves(self):
        """Re-tangle aller noch nicht plazierten Kabel: neue Band-Permutationen + Jitter."""
        mg = self.minigame
        if mg is None or mg.get("type") != "cable_patch": return
        unplaced = [c for c in mg["cables"] if c["placed_port"] is None]
        if unplaced:
            self._cp_apply_waypoints(unplaced, self._cp_band_perms())

    def cp_pickup(self, pos):
        mg = self.minigame
        if mg is None or mg.get("type") != "cable_patch": return
        if mg["result"] is not None or mg["dragging_idx"] is not None: return
        best_i, best_d = None, None
        for i, c in enumerate(mg["cables"]):
            if c["placed_port"] is not None: continue
            d = math.hypot(pos[0] - c["end_pos"][0], pos[1] - c["end_pos"][1])
            if d <= MG_CP_PICK_R and (best_d is None or d < best_d):
                best_i, best_d = i, d
        if best_i is not None:
            mg["dragging_idx"] = best_i
            play_sfx('click')

    def cp_drag(self, pos):
        mg = self.minigame
        if mg is None or mg.get("type") != "cable_patch": return
        idx = mg["dragging_idx"]
        if idx is None: return
        mg["cables"][idx]["end_pos"] = pos

    def cp_release(self, pos):
        mg = self.minigame
        if mg is None or mg.get("type") != "cable_patch": return
        idx = mg["dragging_idx"]
        if idx is None: return
        cable = mg["cables"][idx]
        mg["dragging_idx"] = None
        target_port = None
        for port_i in range(3):
            ppos = _cp_port_pos(port_i)
            if math.hypot(pos[0] - ppos[0], pos[1] - ppos[1]) <= MG_CP_SNAP_R:
                target_port = port_i
                break
        if target_port is None:
            cable["end_pos"] = cable["start_pos"]
            return
        if target_port == cable["pc_idx"]:
            cable["placed_port"] = target_port
            cable["end_pos"]     = _cp_socket_pos(target_port)
            play_sfx('buy')
            if all(c["placed_port"] is not None for c in mg["cables"]):
                self._mg_set_result("won")
        else:
            mg["lives"] -= 1
            cable["end_pos"] = cable["start_pos"]
            self._cp_reshuffle_curves()
            play_sfx('error')
            self._mg_check_end()

    def abort_minigame(self):
        if self.minigame is None: return
        self._mg_apply_loss(self.minigame["target"])
        self.minigame = None
        play_sfx('event_neg')

    def _mg_apply_loss(self, uid):
        self.packets *= (1.0 - MG_FAIL_COST)
        self.challenge_cooldown[uid] = pygame.time.get_ticks() + MG_COOLDOWN_MS

    def _ff_make_frame(self, score):
        t = min(1.0, score / MG_FF_GOAL)
        fall_ms = MG_FF_FALL_BASE - (MG_FF_FALL_BASE - MG_FF_FALL_MIN) * (t ** MG_FF_FALL_CURVE)
        vy = (MG_FF_ARENA_H - MG_FF_FRAME_H) / fall_ms
        port = random.choice(MG_FF_PORTS)
        target_col = MG_FF_PORTS.index(port)
        # Spawn in einer FALSCHEN Spalte, damit immer gesteuert werden muss
        choices = [i for i in range(len(MG_FF_PORTS)) if i != target_col]
        return {"port": port, "y": 0.0, "vy": vy,
                "col": random.choice(choices)}

    def _ff_respawn_ms(self, score):
        t = min(1.0, score / MG_FF_GOAL)
        return int(MG_FF_RESPAWN_BASE - (MG_FF_RESPAWN_BASE - MG_FF_RESPAWN_MIN) * (t ** MG_FF_FALL_CURVE))

    def _update_minigame(self, dt):
        mg = self.minigame
        if mg is None: return
        if mg.get("tutorial"): return
        now = pygame.time.get_ticks()

        if mg["result"] is not None:
            if now - mg["result_at"] > MG_RESULT_DELAY:
                self._finish_minigame()
            return

        if mg["type"] == "cable_patch":
            if now - mg["start_time"] > MG_CP_TIME_MS:
                self._mg_set_result("lost")
            return

        if mg["type"] == "frame_forwarder":
            if mg["frame"] is None and now >= mg["next_spawn"]:
                mg["frame"] = self._ff_make_frame(mg["score"])
            if mg["frame"] is not None:
                f = mg["frame"]
                f["y"] += f["vy"] * dt
                if f["y"] >= MG_FF_ARENA_H - MG_FF_FRAME_H:
                    landed_port = MG_FF_PORTS[f["col"]]
                    if landed_port == f["port"]:
                        mg["score"] += 1
                        play_sfx('buy')
                        if mg["score"] >= MG_FF_GOAL:
                            self._mg_set_result("won")
                    else:
                        mg["lives"] -= 1
                        play_sfx('error')
                        self._mg_check_end()
                    mg["frame"] = None
                    mg["next_spawn"] = now + self._ff_respawn_ms(mg["score"])

        if mg["type"] == "route_table":
            if mg.get("feedback") and now - mg["feedback"]["at"] > 600:
                mg["feedback"] = None
            if mg["packet_ip"] is not None and mg.get("feedback") is None:
                if now - mg["timer_start"] >= mg["timer_ms"]:
                    mg["lives"] -= 1
                    mg["feedback"]   = {"type": "timeout", "clicked": -1, "correct": mg["correct"], "at": now}
                    mg["packet_ip"]  = None
                    mg["next_spawn"] = now + 700
                    play_sfx('error')
                    self._mg_check_end()
            if mg["packet_ip"] is None and mg["result"] is None and now >= mg["next_spawn"]:
                ip = _rt_random_ip()
                mg["packet_ip"]   = ip
                mg["correct"]     = _rt_match_route(ip)
                mg["timer_start"] = now
                t = min(1.0, mg["score"] / MG_RT_GOAL)
                mg["timer_ms"] = int(MG_RT_TIME_MS - (MG_RT_TIME_MS - MG_RT_TIME_MIN) * t)

        if mg["type"] == "packet_inspector":
            # Feedback-Phase ablaufen lassen
            if mg.get("feedback") and now - mg["feedback"]["at"] > MG_PI_FLASH_MS:
                mg["feedback"] = None
            # Timeout: aktives Paket, kein Feedback, deadline überschritten
            if mg["packet"] is not None and mg.get("feedback") is None:
                if now >= mg["deadline"]:
                    mg["lives"] -= 1
                    mg["feedback"]  = {"type":"timeout","verdict":None,
                                       "expected":mg["packet"]["expected"],
                                       "matched_rule":mg["packet"]["matched_rule"],
                                       "at":now}
                    mg["packet"]    = None
                    mg["next_spawn"] = now + MG_PI_NEXT_DELAY
                    play_sfx('error')
                    self._mg_check_end()
            # Spawn neues Paket
            if mg["packet"] is None and mg["result"] is None and now >= mg["next_spawn"]:
                mg["packet"]   = _pi_make_packet(mg["rules"], mg["score"])
                # Erstes Paket bekommt Bonuszeit
                bonus = MG_PI_INTRO_BONUS if mg.get("intro") else 0
                mg["intro"] = False
                mg["window_ms"] = mg["time_per_pkt"] + bonus
                mg["deadline"]  = now + mg["window_ms"]

    def mg_move(self, direction):
        """direction: -1 = links, +1 = rechts. Tetris-artiges Spalten-Snapping."""
        mg = self.minigame
        if mg is None or mg["result"] is not None: return
        if mg["type"] != "frame_forwarder": return
        f = mg["frame"]
        if f is None: return
        new_col = f["col"] + direction
        if 0 <= new_col < len(MG_FF_PORTS):
            f["col"] = new_col
            play_sfx('click')

    def _mg_check_end(self):
        mg = self.minigame
        if mg is None or mg["result"] is not None: return
        if mg["lives"] <= 0:
            self._mg_set_result("lost")

    def rt_click(self, route_idx):
        mg = self.minigame
        if mg is None or mg.get("type") != "route_table": return
        if mg["result"] is not None or mg["packet_ip"] is None: return
        now = pygame.time.get_ticks()
        if route_idx == mg["correct"]:
            mg["score"] += 1
            mg["feedback"]    = {"type": "correct", "clicked": route_idx, "correct": route_idx, "at": now}
            mg["packet_ip"]   = None
            mg["next_spawn"]  = now + 500
            play_sfx('buy')
            if mg["score"] >= MG_RT_GOAL:
                self._mg_set_result("won")
        else:
            mg["lives"] -= 1
            mg["feedback"]   = {"type": "wrong", "clicked": route_idx, "correct": mg["correct"], "at": now}
            mg["packet_ip"]  = None
            mg["next_spawn"] = now + 700
            play_sfx('error')
            self._mg_check_end()

    def pi_decide(self, verdict):
        """verdict: 'allow' | 'drop'"""
        mg = self.minigame
        if mg is None or mg.get("type") != "packet_inspector": return
        if mg["result"] is not None or mg["packet"] is None: return
        if mg.get("feedback") is not None: return
        now = pygame.time.get_ticks()
        pkt = mg["packet"]
        correct = (verdict == pkt["expected"])
        if correct:
            mg["score"] += 1
            mg["time_per_pkt"] = max(MG_PI_TIME_MIN,
                                     mg["time_per_pkt"] - MG_PI_TIME_STEP)
            mg["feedback"] = {"type":"correct","verdict":verdict,
                              "expected":pkt["expected"],
                              "matched_rule":pkt["matched_rule"],"at":now}
            play_sfx('buy')
            if mg["score"] >= MG_PI_GOAL:
                self._mg_set_result("won")
        else:
            mg["lives"] -= 1
            mg["feedback"] = {"type":"wrong","verdict":verdict,
                              "expected":pkt["expected"],
                              "matched_rule":pkt["matched_rule"],"at":now}
            play_sfx('error')
            self._mg_check_end()
        mg["packet"]     = None
        mg["next_spawn"] = now + MG_PI_NEXT_DELAY

    def _mg_set_result(self, result):
        mg = self.minigame
        mg["result"]    = result
        mg["result_at"] = pygame.time.get_ticks()
        mg["frame"]     = None
        play_sfx('prestige' if result == "won" else 'event_neg')

    def _finish_minigame(self):
        mg = self.minigame
        if mg is None: return
        target = mg["target"]
        won    = (mg["result"] == "won")
        if won:
            self.unlocked.add(target)
            self.save()
        else:
            self._mg_apply_loss(target)
        self.minigame = None

    def buy_upgrade(self, uid):
        price = self.upgrade_price(uid)
        if self.packets < price: return False
        self.packets -= price
        self.owned[uid] = self.owned.get(uid,0) + 1
        self._invalidate_fx()
        play_sfx('buy')
        # Erstkauf einer Firewall schaltet RFC-Forschung frei
        if uid == "firewall" and not self.rfc_unlocked:
            self.rfc_unlocked   = True
            self.show_rfc_intro = True
            play_sfx('research')
            self.save()
        return True

    def do_research(self, rid):
        r = next(r for r in RESEARCH if r["id"] == rid)
        if not self.can_research(rid): return False
        self.rfc_points -= r["cost"]
        self.research_done.add(rid)
        self._invalidate_fx()
        play_sfx('research')
        self.floats.append(FloatingText(LEFT_W + (W-LEFT_W)//2, H//2,
                                        f"Erforscht: {r['name']}", RFC_COL))
        return True

    def do_prestige(self):
        bonus = self.fx["prestige_bonus"]
        self.prestige      += 1
        self.prestige_mult *= (2.0 * bonus)
        self.packets        = 0.0
        self.total_packets  = 0.0
        self.owned          = {}
        self.event          = None
        self.next_event     = pygame.time.get_ticks() + 45_000
        self.hs_state       = None
        self.hs_combo       = 0
        self.hs_perfects    = 0
        self.hs_started     = 0
        self.hs_next        = pygame.time.get_ticks() + 60_000
        self.click_buff_until = 0
        self.minigame         = None
        # unlocked + challenge_cooldown bleiben erhalten – einmal bestandene
        # Challenges muessen nach Prestige nicht wiederholt werden.
        self.confirm_prestige = False
        self._invalidate_fx()
        play_sfx('prestige')
        self.save()

    # ── Update ───────────────────────────────────────────────────────
    def update(self, dt):
        if self.minigame is not None:
            self._update_minigame(dt)
            return
        now = pygame.time.get_ticks()
        self.packets       += self.pps * dt / 1000
        self.total_packets += max(0, self.pps) * dt / 1000
        self.packets       -= self.pps_drain * dt / 1000
        self.packets        = max(0.0, self.packets)
        self.rfc_points    += self.rfc_rate * dt / 1000
        self.click_pulse    = max(0.0, self.click_pulse - dt * 0.004)
        for sw in self.click_shockwaves: sw["age"] += dt
        self.click_shockwaves = [s for s in self.click_shockwaves if s["age"] < s["ttl"]]
        self.floats      = [f for f in self.floats      if not f.done]
        self.net_packets = [p for p in self.net_packets if not p.done]
        self.ddos_packets = [p for p in self.ddos_packets if not p.done]
        for f in self.floats:      f.update()
        for p in self.net_packets: p.update()
        for p in self.ddos_packets: p.update()

        if self.event and self.event.get("id") == "ddos":
            self.ddos_spawn_timer -= dt
            if self.ddos_spawn_timer <= 0:
                self.ddos_packets.append(DDoSPacket(random.uniform(20, W-20), -20))
                self.ddos_spawn_timer = random.uniform(300, 800)

        if self.event and now > self.event_until:
            self.event = None
        self._update_handshake(now)

        if self.event is None and now > self.next_event and self.total_packets > 50:
            ev = random.choice(EVENTS)
            self.event = dict(ev)
            dur = ev["dur"]
            if ev.get("negative") and dur > 0:
                dur = max(1, int(dur * self.fx["neg_dur"]))
                play_sfx('event_neg')
            else:
                play_sfx('event_pos')
            self.event_until = now + dur * 1000
            self.next_event  = now + random.randint(25_000, 80_000)
        if now - self._last_save > 30_000:
            self.save(); self._last_save = now

    # ── Shop-Y für Paket-Animation ────────────────────────────────────
    def _shop_y(self, idx):
        y = 110 + idx * 74 - self.shop_scroll
        return y if 110 < y < H else -1

    # ── Speichern / Laden ─────────────────────────────────────────────
    def save(self):
        try:
            with open(SAVE_PATH, "w") as f:
                json.dump({"packets": self.packets, "total": self.total_packets,
                           "owned": self.owned, "prestige": self.prestige,
                           "prestige_mult": self.prestige_mult,
                           "rfc": self.rfc_points,
                           "research": list(self.research_done),
                           "unlocked": list(self.unlocked),
                           "rfc_unlocked": self.rfc_unlocked,
                           "show_rfc_intro": self.show_rfc_intro,
                           "show_intro": self.show_intro,
                           "mg_tutorials_seen": list(self.mg_tutorials_seen),
                           "music_muted": self.music_muted,
                           "sfx_muted": self.sfx_muted,
                           "res_idx": self.res_idx,
                           "fps_idx": self.fps_idx,
                           "fullscreen": self.fullscreen}, f)
        except Exception: pass

    def load(self):
        try:
            with open(SAVE_PATH) as f:
                d = json.load(f)
            if "packets" not in d: return
            self.packets        = d.get("packets", 0)
            self.total_packets  = d.get("total", 0)
            self.owned          = d.get("owned", {})
            self.prestige       = d.get("prestige", 0)
            self.prestige_mult  = d.get("prestige_mult", 1.0)
            self.rfc_points     = d.get("rfc", 0.0)
            self.research_done  = set(d.get("research", []))
            self.unlocked       = set(d.get("unlocked", ["hub"]))
            # Rueckwaertskompatibilitaet: bereits gekaufte Tiers gelten als freigeschaltet
            for uid, cnt in self.owned.items():
                if cnt > 0:
                    self.unlocked.add(uid)
            self.rfc_unlocked   = d.get("rfc_unlocked", False)
            self.show_rfc_intro      = d.get("show_rfc_intro", False)
            self.show_intro          = d.get("show_intro", False)
            self.mg_tutorials_seen   = set(d.get("mg_tutorials_seen", []))
            # Rueckwaertskompatibilitaet: wer Firewall hat, kennt RFC schon
            if self.owned.get("firewall", 0) > 0:
                self.rfc_unlocked   = True
                if "show_rfc_intro" not in d:
                    self.show_rfc_intro = False
            self.music_muted    = d.get("music_muted", False)
            self.sfx_muted      = d.get("sfx_muted", False)
            self.res_idx        = d.get("res_idx", 0)
            self.fps_idx        = d.get("fps_idx", 1)
            self.fullscreen     = d.get("fullscreen", False)
        except Exception: pass

# ── Zeichenfunktionen ─────────────────────────────────────────────────

def get_highest_tier_index(game: Game):
    for i in range(len(UPGRADES)-1, -1, -1):
        if game.owned.get(UPGRADES[i]["id"], 0) > 0:
            return i
    return -1


def draw_handshake(game: Game):
    if game.hs_state is None:
        return
    now = pygame.time.get_ticks()
    x1, x2, wy = _hs_wire_coords()
    cx_mid = (x1 + x2) // 2

    phase_col = {"syn": CYAN_C, "synack": ORANGE_C, "ack": GREEN_C}[game.hs_state]
    phase_lbl = {"syn": "SYN  →",
                 "synack": "←  SYN-ACK",
                 "ack": "ACK  →"}[game.hs_state]

    # Semi-transparenter Streifen als Backdrop
    strip_h = 44
    strip = pygame.Surface((x2 - x1 + 40, strip_h), pygame.SRCALPHA)
    strip.fill((6, 10, 18, 200))
    screen.blit(strip, (x1 - 20, wy - strip_h // 2))
    pygame.draw.rect(screen, BORDER_A,
                     (x1 - 20, wy - strip_h // 2, x2 - x1 + 40, strip_h),
                     1, border_radius=6)

    # Header
    text(screen, font_tiny, "TCP THREE-WAY HANDSHAKE", phase_col,
         cx_mid, wy - strip_h // 2 + 2, "midtop")

    # Gepunktete Leitung
    for x in range(x1, x2, 6):
        pygame.draw.line(screen, BORDER, (x, wy), (x + 3, wy), 1)

    # Sweet-Spot (Hit-Zone)
    hz_x = cx_mid - HS_HITZONE_W // 2
    hz_surf = pygame.Surface((HS_HITZONE_W, 18), pygame.SRCALPHA)
    hz_surf.fill((*GREEN_C, 35))
    screen.blit(hz_surf, (hz_x, wy - 9))
    pygame.draw.rect(screen, GREEN_C, (hz_x, wy - 9, HS_HITZONE_W, 18), 1, border_radius=3)

    # Endpunkte
    pygame.draw.rect(screen, PANEL, (x1 - 14, wy - 7, 14, 14), border_radius=2)
    pygame.draw.rect(screen, CYAN_C, (x1 - 14, wy - 7, 14, 14), 1, border_radius=2)
    text(screen, font_tiny, "CLI", CYAN_C, x1 - 7, wy + 9, "midtop")

    pygame.draw.rect(screen, PANEL, (x2, wy - 7, 14, 14), border_radius=2)
    pygame.draw.rect(screen, ORANGE_C, (x2, wy - 7, 14, 14), 1, border_radius=2)
    text(screen, font_tiny, "SRV", ORANGE_C, x2 + 7, wy + 9, "midtop")

    # Phase-Label
    text(screen, font_small, phase_lbl, phase_col, cx_mid, wy + 9, "midtop")

    # Combo-Anzeige rechts
    if game.hs_combo > 0:
        text(screen, font_tiny, f"COMBO x{game.hs_combo}", GOLD,
             x2 + 22, wy - strip_h // 2 + 2, "topleft")
    # Perfect-Tracker links
    if game.hs_perfects > 0:
        text(screen, font_tiny, "★" * game.hs_perfects, GOLD,
             x1 - 22, wy - strip_h // 2 + 2, "topright")

    # Fluganzeige (Schweif + Paket)
    pos = game._hs_packet_pos(now)
    if pos is not None:
        px, py = pos
        # Schweif
        trail_len = 36
        trail_dir = -1 if game.hs_state == "synack" else 1
        for i in range(6):
            tx = px - trail_dir * (i + 1) * (trail_len // 6)
            alpha = max(0, 120 - i * 22)
            ts = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(ts, (*phase_col, alpha), (5, 5), 4)
            screen.blit(ts, (tx - 5, py - 5))
        # Pulsierender Halo
        pulse = 0.5 + 0.5 * math.sin(now / 90.0)
        halo_r = int(HS_PACKET_HIT + 4 * pulse)
        halo = pygame.Surface((halo_r * 2 + 4, halo_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*phase_col, int(70 + 60 * pulse)),
                           (halo_r + 2, halo_r + 2), halo_r)
        screen.blit(halo, (px - halo_r - 2, py - halo_r - 2))
        # Paket
        pygame.draw.circle(screen, phase_col, (px, py), HS_PACKET_DRAW)
        pygame.draw.circle(screen, WHITE, (px, py), HS_PACKET_DRAW, 2)
        # Kleines Label im Paket
        text(screen, font_tiny,
             "S" if game.hs_state == "syn" else ("A" if game.hs_state == "ack" else "S/A"),
             WHITE, px, py - 6, "midtop")

def _bg_dot_grid(w, h, spacing, col):
    # Farbe quantisieren – Cache bleibt klein
    qc = (_qcol(col[:3], 8), col[3] if len(col) > 3 else 255)
    key = ("dotgrid", w, h, spacing, qc)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(spacing, w, spacing):
        for y in range(spacing, h, spacing):
            s.set_at((x, y), col)
    return _cache_put(key, s)

def _bg_line_grid(w, h):
    """24px Liniengrid + 8px feines Sub-Grid (Design-Tokens panelEdge)."""
    key = ("linegrid", w, h)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    # Feines 8px-Subgrid (#13192a) sehr dezent
    fine = (19, 25, 42, 90)
    for x in range(8, w, 8):
        pygame.draw.line(s, fine, (x, 0), (x, h), 1)
    for y in range(8, h, 8):
        pygame.draw.line(s, fine, (0, y), (w, y), 1)
    # Hauptes 24px-Grid (#1a2238)
    main = (26, 34, 56, 160)
    for x in range(24, w, 24):
        pygame.draw.line(s, main, (x, 0), (x, h), 1)
    for y in range(24, h, 24):
        pygame.draw.line(s, main, (0, y), (w, y), 1)
    return _cache_put(key, s)

def _bg_scanlines(w, h):
    """Horizontale Scanlines wie auf einem CRT — 6% Opacity."""
    key = ("scanlines", w, h)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 3):
        pygame.draw.line(s, (255, 255, 255, 14), (0, y), (w, y), 1)
    return _cache_put(key, s)

def _bg_horizon_glow(w, h):
    """Radialer weicher Glow unten Mitte — Magenta auf Cyan auf Hintergrund."""
    key = ("horizon", w, h)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, int(h * 0.85)
    steps = 22
    max_r = int(max(w, h) * 0.7)
    for i in range(steps, 0, -1):
        t = i / steps
        # Magenta nahe Zentrum, Cyan außen, transparent ganz außen
        if t < 0.35:
            tt = t / 0.35
            col = (255, 43, 214, int(40 * (1 - tt)))
        elif t < 0.7:
            tt = (t - 0.35) / 0.35
            col = (0, 229, 255, int(24 * (1 - tt)))
        else:
            continue
        r = int(max_r * t)
        pygame.draw.circle(s, col, (cx, cy), r)
    return _cache_put(key, s)

def _bg_vignette(w, h):
    key = ("vignette", w, h)
    if key in _SURF_CACHE: return _SURF_CACHE[key]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 28
    for i in range(steps):
        a = int(110 * (i / steps) ** 2.2)
        pygame.draw.rect(s, (0, 0, 0, a),
                         (i, i, w - i*2, h - i*2), 1)
    return _cache_put(key, s)

def draw_background(game: Game):
    # Flat-Base aus Design-bg statt Gradient (Cyberpunk wirkt mit ruhigem Hintergrund)
    screen.fill(BG)

    # Horizon-Glow (Magenta→Cyan)
    screen.blit(_bg_horizon_glow(W, H), (0, 0))

    # 24px Liniengrid + 8px Sub-Grid (gecacht)
    screen.blit(_bg_line_grid(W, H), (0, 0))

    # Animiertes Scan-Light bei mehr Researches
    res_count = len(game.research_done)
    if res_count >= 4:
        t = (pygame.time.get_ticks() / 14000.0) % 1.0
        scan_x = int(-200 + t * (W + 400))
        scan = pygame.Surface((220, H), pygame.SRCALPHA)
        for i in range(220):
            a = int(10 * math.sin(math.pi * i / 220))
            pygame.draw.line(scan, (*BORDER_A, a), (i, 0), (i, H))
        screen.blit(scan, (scan_x, 0))

    # CRT-Scanlines (sehr leicht)
    screen.blit(_bg_scanlines(W, H), (0, 0))

    # Vignette
    screen.blit(_bg_vignette(W, H), (0, 0))

    # Trennlinie zwischen den Panels — dünn, mit Cyan-Glow
    sep = pygame.Surface((16, H), pygame.SRCALPHA)
    for i in range(8):
        a = int(28 * (1 - i/8) ** 1.3)
        pygame.draw.line(sep, (*BORDER_A, a), (8 - i, 0), (8 - i, H))
        pygame.draw.line(sep, (*BORDER_A, a), (8 + i, 0), (8 + i, H))
    pygame.draw.line(sep, (*BORDER_A, 200), (8, 0), (8, H), 1)
    screen.blit(sep, (LEFT_W - 8, 0))


def _draw_corner_brackets(surf, rect, col, length=14, thickness=2):
    """4 L-Eckklammern wie im Design-Asset, in den Ecken eines Rect."""
    r = pygame.Rect(rect)
    for sx, sy, ax, ay in [(0,0,1,1), (r.w,0,-1,1), (r.w,r.h,-1,-1), (0,r.h,1,-1)]:
        x = r.x + sx
        y = r.y + sy
        pygame.draw.line(surf, col, (x, y), (x + ax*length, y), thickness)
        pygame.draw.line(surf, col, (x, y), (x, y + ay*length), thickness)

def _draw_outlined_text(surf, font, txt, x, y, stroke_col, anchor="midtop"):
    """Outline-Schrift wie das CLICKER im Design-Asset (Stroke-Outline statt Fill)."""
    base = font.render(str(txt), True, stroke_col)
    rect = base.get_rect(**{anchor: (x, y)})
    # Hintergrund-Glow
    g = base.copy()
    g.set_alpha(60)
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
        surf.blit(g, (rect.x + dx, rect.y + dy))
    # Hohle Outline: Stroke + interner Hintergrund-Cut
    surf.blit(base, rect)
    # "Cut-out" Effekt: dunkle innere Schicht
    inner = font.render(str(txt), True, BG)
    rect_i = inner.get_rect(**{anchor: (x, y)})
    # 2px shrink des Inner durch Skalierung
    iw, ih = inner.get_size()
    if iw > 4 and ih > 4:
        try:
            sm = pygame.transform.smoothscale(inner, (iw - 4, ih - 4))
            sm_rect = sm.get_rect(center=rect.center)
            surf.blit(sm, sm_rect)
        except Exception:
            pass
    return rect

def draw_left(game: Game, net: NetViz):
    # Header-Panel mit dünnem Rand + L-Eckklammern (Cyberpunk-HUD-Stil)
    header_rect = pygame.Rect(10, 6, LEFT_W - 20, 178)
    draw_rect_border(screen, BORDER, header_rect, fill=PANEL, radius=10,
                     shadow=False, highlight=False)
    _draw_corner_brackets(screen, header_rect, BORDER_A, length=14, thickness=2)

    # HUD-Caption oben links + rechts
    text(screen, font_tiny, "▌ NET.STATUS // ONLINE", BORDER_A, 22, 12)
    text(screen, font_tiny, f"AS{64512 + game.prestige}", DIM,
         LEFT_W - 22, 12, "topright")

    # Titel: PACKET (solid) + CLICKER (Stroke) + Magenta-Underscore
    title_y = 32
    packet_surf  = font_big.render("PACKET",  True, WHITE)
    clicker_surf = font_big.render("CLICKER", True, BORDER_A)
    underscore_surf = font_big.render("_",     True, ACCENT_2)
    total_w = packet_surf.get_width() + 8 + clicker_surf.get_width() + underscore_surf.get_width()
    start_x = LEFT_W//2 - total_w//2
    screen.blit(packet_surf, (start_x, title_y))
    cx_pos = start_x + packet_surf.get_width() + 8
    g = clicker_surf.copy(); g.set_alpha(70)
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        screen.blit(g, (cx_pos + dx, title_y + dy))
    screen.blit(clicker_surf, (cx_pos, title_y))
    screen.blit(underscore_surf, (cx_pos + clicker_surf.get_width(), title_y))

    # Tagline
    text(screen, font_tiny, "ROUTE · BUFFER · ASCEND", DIM,
         LEFT_W//2, title_y + 42, "midtop")

    # Pakete-Hauptanzeige mit Glow
    val_str = fmt(int(game.packets)) + " PKT"
    text_glow(screen, font_big, val_str, WHITE,
              LEFT_W // 2, 96, "midtop", glow_col=BORDER_A, intensity=1)
    pps_col = GREEN_C if (game.event is None or not game.event.get("negative")) else RED_C
    text(screen, font_small, f"+{fmt(game.pps)}/s   +{fmt(game.click_power)}/CLK",
         pps_col, LEFT_W//2, 134, "midtop")

    # RFC-Rate
    if game.rfc_unlocked:
        rfc_str = f"RFC {game.rfc_points:.1f}  +{game.rfc_rate:.2f}/s"
        text(screen, font_tiny, rfc_str, RFC_COL, LEFT_W//2, 158, "midtop")

    # ── Klick-Button (Iso-Hex-Cube nach Design-Asset) ───────────────
    cx, cy = LEFT_W//2, 335
    R_BASE, pulse = 108, game.click_pulse
    t = pygame.time.get_ticks() / 1000.0

    mx_p, my_p = pygame.mouse.get_pos()
    hover = math.hypot(mx_p - cx, my_p - cy) <= R_BASE + 6
    mouse_pressed = pygame.mouse.get_pressed()[0]

    press_amt = max(pulse, 1.0 if (hover and mouse_pressed) else 0.0)
    R = int(R_BASE - 5 * press_amt + (3 if hover else 0))

    # ── Shockwaves (expandierende Ringe vom Mittelpunkt) ────────────
    if game.click_shockwaves:
        max_r = R + 4 + 90
        sw_size = max_r * 2 + 8
        sw_buf = pygame.Surface((sw_size, sw_size), pygame.SRCALPHA)
        center = sw_size // 2
        for sw in game.click_shockwaves:
            p = sw["age"] / sw["ttl"]
            if p >= 1.0: continue
            ring_r = int(R + 4 + 90 * p)
            thick  = max(1, int(7 * (1 - p) ** 1.3))
            alpha  = int(200 * (1 - p) ** 1.5)
            pygame.draw.circle(sw_buf, (*sw["col"], alpha),
                               (center, center), ring_r, thick)
        screen.blit(sw_buf, (cx - center, cy - center))

    # ── Äußeres Soft-Glow (Cyan pulsierend, dezent) ─────────────────
    breathe = 0.5 + 0.5 * math.sin(t * 1.2)
    hover_boost = 1.0 if hover else 0.6
    base_intensity = int((50 + 70 * pulse + 18 * breathe) * hover_boost)
    g_surf = glow_surf(R + 48, BORDER_A,
                       intensity=base_intensity, layers=14)
    screen.blit(g_surf, (cx - g_surf.get_width()//2, cy - g_surf.get_height()//2))

    # ── Network-Viz hinter dem Kreis ────────────────────────────────
    net.draw(screen)

    # ── Drei Scan-Ringe (outer dim, mid+inner dashed cyan) ──────────
    pygame.draw.circle(screen, _shade(PANEL_HL, 1.0), (cx, cy), R + 4, 1)
    # Mid dashed
    mid_r = R - 2
    for i in range(40):
        if (i % 6) >= 3: continue
        a = (i / 40) * math.tau + t * 0.2
        x = cx + math.cos(a) * mid_r
        y = cy + math.sin(a) * mid_r
        pygame.draw.circle(screen, (*BORDER_A, 80), (int(x), int(y)), 1)
    # Inner dashed (kürzer)
    inner_r = R - 24
    for i in range(28):
        if (i % 4) >= 2: continue
        a = (i / 28) * math.tau - t * 0.3
        x = cx + math.cos(a) * inner_r
        y = cy + math.sin(a) * inner_r
        pygame.draw.circle(screen, (*BORDER_A, 130), (int(x), int(y)), 1)

    # ── Tick-Marks (36, jeder 9. major) ─────────────────────────────
    tick_outer = R - 5
    for i in range(36):
        ang = (i / 36) * math.tau - math.pi/2
        major = (i % 9 == 0)
        ti = tick_outer - (16 if major else 9)
        col = BORDER_A if major else INK_MUTE
        x1 = cx + math.cos(ang) * tick_outer
        y1 = cy + math.sin(ang) * tick_outer
        x2 = cx + math.cos(ang) * ti
        y2 = cy + math.sin(ang) * ti
        pygame.draw.line(screen, col, (x1, y1), (x2, y2), 2 if major else 1)

    # ── L-Eckklammern (Magenta) an den 4 Diagonalen ─────────────────
    br = R - 12       # Bracket-Position
    bl = 14           # Bracket-Schenkellänge
    for sx, sy in [(-1,-1), (1,-1), (1,1), (-1,1)]:
        bx, by = cx + sx * br, cy + sy * br
        pygame.draw.line(screen, ACCENT_2, (bx, by), (bx + sx * bl, by), 2)
        pygame.draw.line(screen, ACCENT_2, (bx, by), (bx, by + sy * bl), 2)

    # ── Eingehende Datenlinien (6 Stück, vom Iso-Cube nach außen) ───
    # Ein geteiltes Alpha-Surface für alle Linien (statt 6×große Allocs).
    cube_r = int(R * 0.42)
    far_r  = int(R * 0.78)
    lines_buf = pygame.Surface((R * 2 + 4, R * 2 + 4), pygame.SRCALPHA)
    for i in range(6):
        ang = (i / 6) * math.tau + t * 0.3
        x1 = cx + math.cos(ang) * cube_r
        y1 = cy + math.sin(ang) * cube_r
        x2 = cx + math.cos(ang) * far_r
        y2 = cy + math.sin(ang) * far_r
        flick = 0.5 + 0.5 * math.sin(t * 3 + i * 1.3)
        line_col = (*BORDER_A, int(80 + 100 * flick))
        pygame.draw.line(lines_buf, line_col,
                         (int(x1 - cx + R), int(y1 - cy + R)),
                         (int(x2 - cx + R), int(y2 - cy + R)), 2)
        pygame.draw.circle(lines_buf, (*BORDER_A, 255),
                           (int(x2 - cx + R), int(y2 - cy + R)), 2)
    screen.blit(lines_buf, (cx - R, cy - R))

    # ── Isometrischer Würfel (Top + Left + Right Face) ──────────────
    # Skalierung relativ zu R: cube_h_top = 0.42*R, cube_w = 0.6*R
    s = R * 0.42       # halbhöhe top vertex
    w = R * 0.6        # halbbreite mittlere kante
    bot_h = R * 0.4    # bottom vertex
    # Punkte: top, right-top-edge, center, left-top-edge, bot
    p_top   = (cx, cy - int(s))
    p_rt    = (cx + int(w), cy - int(s * 0.5))
    p_c     = (cx, cy - 2)
    p_lt    = (cx - int(w), cy - int(s * 0.5))
    p_rb    = (cx + int(w), cy + int(s * 0.5))
    p_lb    = (cx - int(w), cy + int(s * 0.5))
    p_bot   = (cx, cy + int(bot_h))

    # Top-Face
    top_face = [p_top, p_rt, p_c, p_lt]
    pygame.draw.polygon(screen, _shade(PANEL, 0.85), top_face)
    pygame.draw.polygon(screen, BORDER_A, top_face, 2)
    # Right-Face
    right_face = [p_rt, p_c, p_bot, p_rb]
    pygame.draw.polygon(screen, _shade(PANEL, 0.55), right_face)
    pygame.draw.polygon(screen, BORDER_A, right_face, 2)
    # Left-Face
    left_face = [p_lt, p_c, p_bot, p_lb]
    pygame.draw.polygon(screen, _shade(PANEL, 0.4), left_face)
    pygame.draw.polygon(screen, BORDER_A, left_face, 2)
    # Center-Seam (vertikaler Highlight)
    pygame.draw.line(screen, _mix(BORDER_A, WHITE, 0.4), p_c, p_bot, 1)

    # ── Circuit-Traces auf der Top-Face ─────────────────────────────
    # Zwei kleine Pfade mit Knotenpunkten, einer cyan, einer acid
    tf_cx, tf_cy = cx, cy - int(s * 0.55)
    pygame.draw.line(screen, BORDER_A,
                     (tf_cx - 20, tf_cy - 4), (tf_cx - 10, tf_cy - 4), 1)
    pygame.draw.line(screen, BORDER_A,
                     (tf_cx - 10, tf_cy - 4), (tf_cx - 10, tf_cy + 4), 1)
    pygame.draw.line(screen, BORDER_A,
                     (tf_cx - 10, tf_cy + 4), (tf_cx + 4, tf_cy + 4), 1)
    pygame.draw.circle(screen, BORDER_A, (tf_cx - 10, tf_cy - 4), 2)
    pygame.draw.circle(screen, BORDER_A, (tf_cx + 4, tf_cy + 4), 2)
    pygame.draw.line(screen, GREEN_C,
                     (tf_cx + 12, tf_cy - 8), (tf_cx + 12, tf_cy - 2), 1)
    pygame.draw.line(screen, GREEN_C,
                     (tf_cx + 12, tf_cy - 2), (tf_cx + 22, tf_cy - 2), 1)
    pygame.draw.circle(screen, GREEN_C, (tf_cx + 12, tf_cy - 2), 2)

    # ── Datenbits auf den Seitenflächen (3px Streifen) ──────────────
    # Linke Face
    lf_x = cx - int(w * 0.7)
    for row, (off, length, col) in enumerate([
        (0,  10, BORDER_A),
        (8,  18, _shade(BORDER_A, 0.6)),
        (16, 12, GREEN_C),
        (24, 18, BORDER_A),
        (32, 16, ACCENT_2),
    ]):
        pygame.draw.rect(screen, col, (lf_x, cy - 6 + row * 8, length, 3))
    # Rechte Face
    rf_x = cx + 6
    for row, (length, col) in enumerate([
        (28, _shade(BORDER_A, 0.6)),
        (16, BORDER_A),
        (22, _shade(GREEN_C, 0.85)),
        (14, BORDER_A),
        (26, _shade(BORDER_A, 0.6)),
    ]):
        pygame.draw.rect(screen, col, (rf_x, cy - 6 + row * 8, length, 3))

    # ── Top-Vertex weißer Glow ──────────────────────────────────────
    vg = glow_surf(8, (255, 255, 255), intensity=200, layers=6)
    screen.blit(vg, (p_top[0] - vg.get_width()//2, p_top[1] - vg.get_height()//2))
    pygame.draw.circle(screen, WHITE, p_top, 3)

    # ── Readout-Labels (Mono, ▌ CLICK / RTT) ────────────────────────
    text(screen, font_tiny, "▌ CLICK", BORDER_A,
         cx - R + 4, cy - R + 4)
    text(screen, font_tiny, "0x1F · TX", BORDER_A,
         cx - R + 4, cy + R - 18)
    rtt = max(2, int(8 - 4 * (game.click_pulse)))
    text(screen, font_tiny, f"RTT {rtt}ms", DIM,
         cx + R - 4, cy + R - 18, "topright")

    # Cursor → Hand bei Hover
    want = "hand" if hover else "arrow"
    if getattr(game, "_cursor_state", None) != want:
        try:
            pygame.mouse.set_cursor(
                pygame.SYSTEM_CURSOR_HAND if want == "hand" else pygame.SYSTEM_CURSOR_ARROW)
        except (pygame.error, AttributeError):
            pass
        game._cursor_state = want

    # Tier-Indikator als kleines Hex-Badge rechts unten am Klick-Asset
    tier = get_highest_tier_index(game)
    badge_cx, badge_cy = cx + R - 18, cy + R - 18
    pts = [(badge_cx + math.cos(a*math.tau/6 + math.pi/2)*12,
            badge_cy + math.sin(a*math.tau/6 + math.pi/2)*12) for a in range(6)]
    pygame.draw.polygon(screen, BG, pts)
    pygame.draw.polygon(screen, BORDER_A, pts, 1)
    text(screen, font_tiny, f"T{tier}", BORDER_A, badge_cx, badge_cy, "center")

    # Klick-Buff (x2 nach 3x PERFECT): Gold-Ring + Countdown
    buff_left = game.click_buff_remaining
    if buff_left > 0:
        now2 = pygame.time.get_ticks()
        bpulse = 0.5 + 0.5 * math.sin(now2 / 90.0)
        ring_w = int(5 + 3 * bpulse)
        bcol   = tuple(int(c * (0.6 + 0.4 * bpulse)) for c in GOLD)
        pygame.draw.circle(screen, bcol, (cx, cy), R + ring_w + 4, ring_w)
        text(screen, font_small,
             f"x{HS_PERFECT_BUFF_MULT:.0f} KLICK · {buff_left/1000:.1f}s",
             GOLD, cx, cy + R_BASE + 6, "midtop")
    else:
        # Pill-Badge unter dem Klick-Kreis – pulsiert sanft
        lbl_pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        lbl_col = _mix(BORDER_A, WHITE, 0.4 + 0.5 * lbl_pulse) if hover \
                  else _mix(DIM, BORDER_A, lbl_pulse)
        pill_w, pill_h = 116, 28
        pill_rect = pygame.Rect(cx - pill_w//2, cy + R_BASE + 4, pill_w, pill_h)
        if hover:
            draw_glow_border(screen, BORDER_A, pill_rect, radius=12, intensity=70)
        draw_rect_border(screen, BORDER_A if hover else BORDER, pill_rect,
                         fill=PANEL_HL if hover else PANEL, radius=12)
        text(screen, font_small, "KLICK", lbl_col,
             pill_rect.centerx, pill_rect.centery, "center")

    # ── TCP-Handshake-Overlay ────────────────────────────────────────
    draw_handshake(game)

    # ── Statistiken ──────────────────────────────────────────────────
    sy = 476
    draw_rect_border(screen, BORDER, (10, sy, LEFT_W-20, 96), fill=PANEL)
    text(screen, font_med,   "STATISTIKEN", DIM, 22, sy+6)
    text(screen, font_small, f"Alle Zeit:  {fmt(game.total_packets)} Pakete", WHITE,    22, sy+34)
    text(screen, font_small, f"Pakete/s:   {fmt(game.pps)}",                  WHITE,    22, sy+54)
    text(screen, font_small, f"Prestige:   {game.prestige}x  (x{game.prestige_mult:.0f})",
         GOLD, 22, sy+74)

    # ── Aktives Event ─────────────────────────────────────────────────
    ey = 578
    if game.event:
        now  = pygame.time.get_ticks()
        left = max(0, game.event_until - now)
        dur  = game.event.get("dur", 10) * 1000
        ratio = left / dur if dur > 0 else 0
        ecol  = game.event["col"]
        pulse2 = 0.5 + 0.5*math.sin(now/200)
        bc = tuple(int(c*(0.7+0.3*pulse2)) for c in ecol)
        draw_rect_border(screen, bc, (10, ey, LEFT_W-20, 64), fill=PANEL)
        text(screen, font_small, game.event["name"], ecol,  22, ey+6)
        text(screen, font_tiny,  game.event["desc"], WHITE, 22, ey+30)
        bw = LEFT_W - 44
        pygame.draw.rect(screen, BORDER, (22, ey+50, bw, 8), border_radius=4)
        pygame.draw.rect(screen, ecol,   (22, ey+50, int(bw*ratio), 8), border_radius=4)
    else:
        draw_rect_border(screen, BORDER, (10, ey, LEFT_W-20, 32), fill=PANEL)
        text(screen, font_small, "Kein aktives Event.", DIM, LEFT_W//2, ey+8, "midtop")

    # ── Prestige-Button (unten links in der Ecke) ─────────────────────
    PB_W, PB_H = 216, 70
    px = 10
    py = H - PB_H - 10
    can  = game.total_packets >= 1_000_000_000
    pcol = GOLD if can else DIM
    if can:
        pt = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 280.0)
        draw_glow_border(screen, GOLD, (px, py, PB_W, PB_H),
                         radius=10, intensity=int(60 + 70 * pt))
    draw_rect_border(screen, pcol, (px, py, PB_W, PB_H),
                     fill=(50, 38, 14) if can else PANEL, radius=10)
    # L-Eckklammern für Cyberpunk-Akzent
    _draw_corner_brackets(screen, pygame.Rect(px, py, PB_W, PB_H),
                          GOLD if can else BORDER, length=12, thickness=2)
    if can:
        bonus_str = f"  x{game.fx['prestige_bonus']*2:.1f}"
        text_glow(screen, font_med, "NEUES AS", pcol, px+PB_W//2, py+8, "midtop",
                  glow_col=GOLD, intensity=1)
        text(screen, font_small, f"1B Pakete{bonus_str}", pcol,
             px+PB_W//2, py+38, "midtop")
    else:
        text(screen, font_med, "PRESTIGE", pcol, px+PB_W//2, py+6, "midtop")
        text(screen, font_small, f"{fmt(game.total_packets)} / 1.00B",
             DIM, px+PB_W//2, py+34, "midtop")
        # Mini-Progress-Bar
        ratio = min(1.0, game.total_packets / 1_000_000_000)
        bar_y = py + PB_H - 10
        pygame.draw.rect(screen, BORDER, (px+12, bar_y, PB_W-24, 4), border_radius=2)
        if ratio > 0:
            pygame.draw.rect(screen, GOLD, (px+12, bar_y,
                                            int((PB_W-24)*ratio), 4), border_radius=2)
    if game.confirm_prestige:
        draw_rect_border(screen, RED_C, (px, py-54, PB_W, 50),
                         fill=(40,10,10), radius=8)
        text(screen, font_small, "Wirklich resetten?", RED_C,
             px+PB_W//2, py-50, "midtop")
        text(screen, font_tiny, "Nochmal klicken.", WHITE,
             px+PB_W//2, py-26, "midtop")

    asn = 64512 + game.prestige
    text(screen, font_tiny, f"AS{asn}  |  IPv6  |  BGP",
         DIM, LEFT_W-12, H-12, "bottomright")


TAB_RECTS = {
    "upgrades": pygame.Rect(LEFT_W+6,   2, 240, 40),
    "research": pygame.Rect(LEFT_W+252, 2, 260, 40),
}


def draw_tabs(game: Game):
    for tid, rect in TAB_RECTS.items():
        active = (game.tab == tid)
        locked = (tid == "research" and not game.rfc_unlocked)
        col    = BORDER if locked else (BORDER_A if active else BORDER)
        fill   = PANEL if locked else (PANEL_HL if active else PANEL)
        if active and not locked:
            draw_glow_border(screen, BORDER_A, rect, radius=8, intensity=80)
        draw_rect_border(screen, col, rect, fill=fill, radius=8)
        if active and not locked:
            # Akzent-Strich unter aktivem Tab
            pygame.draw.line(screen, BORDER_A,
                             (rect.x + 12, rect.bottom - 4),
                             (rect.right - 12, rect.bottom - 4), 2)
        if tid == "upgrades":
            label, tcol = "UPGRADES", WHITE if active else DIM
        elif locked:
            label, tcol = "FORSCHUNG (gesperrt)", DIM
        else:
            label, tcol = f"FORSCHUNG ({game.rfc_points:.0f} RFC)", WHITE if active else DIM
        text(screen, font_med, label, tcol, rect.centerx, rect.centery, "center")


def draw_shop(game: Game):
    ITEM_H, SHOP_TOP = 92, 48
    SHOP_X = LEFT_W + 8
    SHOP_W = W - LEFT_W - 16

    clip = pygame.Rect(LEFT_W, SHOP_TOP, W-LEFT_W, H-SHOP_TOP)
    screen.set_clip(clip)

    mxp, myp = pygame.mouse.get_pos()
    for i, upg in enumerate(UPGRADES):
        uid   = upg["id"]
        cnt   = game.owned.get(uid, 0)
        price = game.upgrade_price(uid)
        can   = game.packets >= price
        iy    = SHOP_TOP + i * ITEM_H - game.shop_scroll
        if iy + ITEM_H < SHOP_TOP or iy > H: continue

        card_rect = pygame.Rect(SHOP_X, iy+2, SHOP_W, ITEM_H-4)
        hover = card_rect.collidepoint(mxp, myp) and clip.collidepoint(mxp, myp)

        # Glow für hover/kaufbar
        if can:
            draw_glow_border(screen, upg["col"], card_rect, radius=8,
                             intensity=70 if hover else 38)
        draw_rect_border(screen, upg["col"] if can else BORDER, card_rect,
                         fill=PANEL_HL if (can or hover) else PANEL, radius=8)

        # Akzent-Streifen links (Tier-Color)
        stripe = pygame.Surface((4, ITEM_H-12), pygame.SRCALPHA)
        pygame.draw.rect(stripe, (*upg["col"], 220 if can else 100), stripe.get_rect(),
                         border_radius=2)
        screen.blit(stripe, (SHOP_X + 4, iy + 8))

        # Badge mit Gradient-Hintergrund
        bw = 64
        badge_rect = pygame.Rect(SHOP_X + 12, iy + 6, bw, ITEM_H - 16)
        badge_fill = _shade(upg["col"], 0.22) if can else _shade(upg["col"], 0.12)
        draw_rect_border(screen, upg["col"] if can else BORDER, badge_rect,
                         fill=badge_fill, radius=8, shadow=False)
        text(screen, font_med, upg["abbr"], upg["col"] if can else DIM,
             badge_rect.centerx, badge_rect.y + 4, "midtop")
        text(screen, font_tiny, f"x{cnt}", WHITE if cnt else DIM,
             badge_rect.centerx, badge_rect.y + 32, "midtop")
        pps_c = upg["pps"]*cnt * game.prestige_mult * (game.fx["cdn_mult"] if upg.get("cdn") else 1)
        pps_c *= game.fx["pps_mult"] * game.fx["all_mult"]
        text(screen, font_tiny, f"+{fmt(pps_c)}/s",
             upg["col"] if cnt else DIM,
             badge_rect.centerx, badge_rect.y + 54, "midtop")

        tx = SHOP_X + bw + 24
        text(screen, font_med,   upg["name"], WHITE if can else DIM,  tx, iy+8)
        text(screen, font_tiny,  upg["desc"], DIM,                    tx, iy+38)
        price_col = GREEN_C if can else DIM
        text(screen, font_small, fmt(price)+" Pakete", price_col,     tx, iy+60)

        btn_w = 110
        btn_x = SHOP_X + SHOP_W - btn_w - 10
        btn_rect = pygame.Rect(btn_x, iy + 24, btn_w, 44)
        btn_hover = btn_rect.collidepoint(mxp, myp) and clip.collidepoint(mxp, myp)
        if game.needs_challenge(uid):
            cd = game.challenge_cd_left(uid)
            available = game.is_challenge_available(uid)
            if not available:
                bcol = BORDER
                bg   = PANEL
                lbl  = "🔒 LOCKED"
                dim  = pygame.Surface((card_rect.w, card_rect.h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 100))
                screen.blit(dim, card_rect.topleft)
            elif cd > 0:
                bcol = BORDER
                bg   = PANEL
                lbl  = f"WAIT {cd/1000:.0f}s"
            else:
                bcol = GOLD
                bg   = (60, 44, 10)
                lbl  = "CHALLENGE"
                if btn_hover:
                    draw_glow_border(screen, GOLD, btn_rect, radius=8, intensity=80)
            draw_rect_border(screen, bcol, btn_rect, fill=bg, radius=8)
            text(screen, font_small, lbl, bcol, btn_rect.centerx, btn_rect.centery, "center")
        else:
            bcol  = BORDER_A if can else BORDER
            if can and btn_hover:
                draw_glow_border(screen, BORDER_A, btn_rect, radius=8, intensity=90)
            draw_rect_border(screen, bcol, btn_rect,
                             fill=(14, 56, 44) if can else PANEL, radius=8)
            lbl_col = WHITE if (can and btn_hover) else bcol
            text(screen, font_small, "KAUFEN" if can else "n/a",
                 lbl_col, btn_rect.centerx, btn_rect.centery, "center")

    screen.set_clip(None)

    total_h = len(UPGRADES) * ITEM_H + 150
    if total_h > H - SHOP_TOP:
        sb_h = max(30, int((H-SHOP_TOP)/total_h*(H-SHOP_TOP)))
        sb_y = SHOP_TOP + int(game.shop_scroll/(total_h-(H-SHOP_TOP))*(H-SHOP_TOP-sb_h))
        pygame.draw.rect(screen, BORDER,   (W-6, SHOP_TOP, 4, H-SHOP_TOP))
        pygame.draw.rect(screen, BORDER_A, (W-6, sb_y, 4, sb_h), border_radius=2)

    for f in game.floats:      f.draw(screen)
    for p in game.net_packets: p.draw(screen)


# ── Forschungs-Tab ────────────────────────────────────────────────────
# Layout: 3 Spalten × 4 Zeilen, Knoten mit Verbindungslinien

NODE_W, NODE_H = 240, 78
NODE_GAP_X, NODE_GAP_Y = 18, 18
TREE_TOP = 85   # relativ zu Oberkante des rechten Panels
TREE_LEFT = LEFT_W + 8

def _node_rect(pos) -> pygame.Rect:
    col, row = pos
    panel_w = W - LEFT_W
    total_tree_w = 3*NODE_W + 2*NODE_GAP_X
    start_x = LEFT_W + (panel_w - total_tree_w)//2
    x = start_x + col*(NODE_W + NODE_GAP_X)
    y = TREE_TOP + row*(NODE_H + NODE_GAP_Y)
    return pygame.Rect(x, y, NODE_W, NODE_H)


def draw_research(game: Game):
    RES_TOP = 42

    # RFC-Anzeige
    rfc_str = f"RFC-Punkte: {game.rfc_points:.1f}  (+{game.rfc_rate:.2f}/s)"
    text(screen, font_med, rfc_str, RFC_COL, LEFT_W + (W-LEFT_W)//2, RES_TOP+2, "midtop")

    clip = pygame.Rect(LEFT_W, RES_TOP+26, W-LEFT_W, H-RES_TOP-26)
    screen.set_clip(clip)

    # Verbindungslinien zuerst (unter den Nodes)
    id_to_rect = {r["id"]: _node_rect(r["pos"]) for r in RESEARCH}
    for r in RESEARCH:
        rect = id_to_rect[r["id"]]
        done = r["id"] in game.research_done
        for prereq in r["prereqs"]:
            pr = id_to_rect[prereq]
            p_done = prereq in game.research_done
            col = BORDER_A if (done and p_done) else (BORDER if p_done else DIM)
            sx = pr.centerx; sy = pr.bottom
            ex = rect.centerx; ey = rect.top
            mx = (sx+ex)//2;   my = (sy+ey)//2
            pygame.draw.line(screen, col, (sx, sy), (mx, my), 2)
            pygame.draw.line(screen, col, (mx, my), (ex, ey), 2)

    # Nodes
    for r in RESEARCH:
        rect  = _node_rect(r["pos"])
        done  = r["id"] in game.research_done
        avail = game.can_research(r["id"])
        prmet = game.prereqs_met(r["id"])
        rcol  = r["col"]

        if done:
            fill = tuple(max(0, int(c*0.25)) for c in rcol)
            border = rcol
        elif avail:
            fill = PANEL_HL
            border = rcol
        elif prmet:
            fill = PANEL
            border = BORDER
        else:
            fill = PANEL
            border = (30, 40, 65)

        draw_rect_border(screen, border, rect, fill=fill, radius=8)

        # Name
        name_col = WHITE if (done or avail) else DIM
        text(screen, font_small, r["name"], name_col, rect.x+8, rect.y+6)

        # Effekt-Beschreibung
        desc_col = rcol if done else (DIM if not prmet else WHITE)
        text(screen, font_tiny, r["desc"], desc_col, rect.x+8, rect.y+26)

        # Kosten / Status
        if done:
            text(screen, font_tiny, "[ ERFORSCHT ]", rcol, rect.x+8, rect.y+48)
        elif avail:
            text(screen, font_tiny, f"Kosten: {r['cost']} RFC  [ KLICKEN ]", GOLD, rect.x+8, rect.y+48)
        elif prmet:
            text(screen, font_tiny, f"Kosten: {r['cost']} RFC  (zu wenig RFC)", DIM, rect.x+8, rect.y+48)
        else:
            reqs = ", ".join(r["prereqs"])
            text(screen, font_tiny, f"Benoetigt: {reqs}", (50,60,90), rect.x+8, rect.y+48)

        # Tier-Label (kleine Ecke)
        tier = r["pos"][1] + 1
        text(screen, font_tiny, f"T{tier}", (50,70,110), rect.right-22, rect.y+4)

    screen.set_clip(None)

    for f in game.floats:      f.draw(screen)
    for p in game.net_packets: p.draw(screen)


# ── Klick-Handler ─────────────────────────────────────────────────────

def shop_click(game: Game, mx, my):
    ITEM_H, SHOP_TOP = 92, 48
    SHOP_X = LEFT_W + 8
    SHOP_W = W - LEFT_W - 16
    for i, upg in enumerate(UPGRADES):
        iy = SHOP_TOP + i*ITEM_H - game.shop_scroll
        if iy+ITEM_H < SHOP_TOP or iy > H: continue
        btn_w = 110
        btn_x = SHOP_X + SHOP_W - btn_w - 10
        if btn_x <= mx <= btn_x+btn_w and iy+24 <= my <= iy+68:
            uid = upg["id"]
            if game.needs_challenge(uid):
                if not game.is_challenge_available(uid):
                    play_sfx('error')
                elif game.challenge_cd_left(uid) > 0:
                    play_sfx('error')
                else:
                    game.start_minigame(uid)
            else:
                if not game.buy_upgrade(uid):
                    play_sfx('error')


def research_click(game: Game, mx, my):
    for r in RESEARCH:
        rect = _node_rect(r["pos"])
        if rect.collidepoint(mx, my):
            if not game.do_research(r["id"]):
                play_sfx('error')
            return


def prestige_click(game: Game, mx, my) -> bool:
    PB_W, PB_H = 216, 70
    px = 10
    py = H - PB_H - 10
    if px <= mx <= px + PB_W and py <= my <= py + PB_H:
        if game.total_packets >= 1_000_000_000:
            if game.confirm_prestige:
                game.do_prestige()
            else:
                game.confirm_prestige = True
        return True
    return False


# ── Minigame-Overlay (Frame Forwarder) ────────────────────────────────

def _ff_panel_rect():
    px = W // 2 - MG_PANEL_W // 2
    py = H // 2 - MG_PANEL_H // 2
    return px, py

def _ff_arena_rect():
    px, py = _ff_panel_rect()
    return px + 30, py + 108, MG_PANEL_W - 60, MG_FF_ARENA_H

def _ff_columns():
    """Liefert Liste (col_index, x_left, x_right, x_center) — drei Spalten = drei Ports."""
    ax, _, aw, _ = _ff_arena_rect()
    col_w = aw / 3
    return [(i, ax + i * col_w, ax + (i + 1) * col_w,
             ax + (i + 0.5) * col_w) for i in range(3)]

def _catmull_rom(points, n_per_segment=MG_CP_SEG_PTS):
    """Glatte Kurve durch beliebig viele Wegpunkte (uniform Catmull-Rom)."""
    if len(points) < 2:
        return list(points)
    # Endpunkte gespiegelt anhängen, damit Kurve start/end exakt trifft
    p_start = (2*points[0][0] - points[1][0], 2*points[0][1] - points[1][1])
    p_end   = (2*points[-1][0] - points[-2][0], 2*points[-1][1] - points[-2][1])
    pts = [p_start] + list(points) + [p_end]
    result = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i], pts[i+1], pts[i+2], pts[i+3]
        for k in range(n_per_segment):
            t  = k / n_per_segment
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2*p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2*p1[1]) +
                (-p0[1] + p2[1]) * t +
                (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
            )
            result.append((x, y))
    result.append(points[-1])
    return result


def _cp_pc_pos(i):
    px, py = _ff_panel_rect()
    return (px + 95, py + MG_CP_TOP_OFFSET + i * MG_CP_ROW_GAP)

def _cp_port_pos(i):
    px, py = _ff_panel_rect()
    return (px + 505, py + MG_CP_TOP_OFFSET + i * MG_CP_ROW_GAP)

def _cp_slot_pos(i):
    px, py = _ff_panel_rect()
    return (px + 300, py + MG_CP_TOP_OFFSET + i * MG_CP_ROW_GAP)

def _cp_anchor_pos(i):
    x, y = _cp_pc_pos(i)
    return (x + 36, y)

def _cp_socket_pos(i):
    x, y = _cp_port_pos(i)
    return (x - 22, y)


# ── Route-Table Racer Helpers ─────────────────────────────────────────

_RT_ROUTES = None

def _pi_base_packet():
    """Generiert ein 'neutrales' Paket auf einem Port, der keine Standard-Regel matcht."""
    proto = random.choice(["TCP", "TCP", "TCP", "UDP"])
    p = {
        "proto":    proto,
        "src_ip":   f"{random.choice([192,172,203,17,8,84])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "src_port": random.randint(1024, 65535),
        "dst_ip":   f"{random.choice([10,192,172,8,4,1])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        # Ports die NICHT in einem Standard-Rule sind:
        "dst_port": random.choice([8080, 4444, 5060, 161, 1900, 25, 110, 143, 5432, 6379, 587]),
        "flags":    random.choice(["SYN", "ACK", "FIN"]),
    }
    if proto == "UDP":
        p["flags"] = None
    return p

def _pi_apply_rule(p, rule_id):
    """Mutiert p so dass es die genannte Regel matcht."""
    if rule_id == "telnet":
        p["proto"] = "TCP"; p["dst_port"] = 23; p["flags"] = "SYN"
    elif rule_id == "rdp":
        p["proto"] = "TCP"; p["dst_port"] = 3389
    elif rule_id == "icmp":
        p["proto"] = "ICMP"; p["src_port"] = None; p["dst_port"] = None; p["flags"] = None
    elif rule_id == "privsrc":
        p["src_ip"] = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    elif rule_id == "web":
        p["proto"] = "TCP"; p["dst_port"] = random.choice([80, 443])
    elif rule_id == "dns":
        p["dst_port"] = 53; p["proto"] = random.choice(["UDP", "TCP"])
        if p["proto"] == "UDP": p["flags"] = None
    elif rule_id == "nmap":
        p["proto"] = "TCP"; p["flags"] = "SYN+FIN"

def _pi_first_match(p, rules):
    """Liefert (index, rule) oder (-1, None) für default-deny."""
    for i, r in enumerate(rules):
        if r["match"](p):
            return i, r
    return -1, None

def _pi_make_packet(rules, score=0):
    """Generiert ein Paket dessen Verdict eindeutig durch first-match-wins bestimmt ist.
       Verteilt ~50/50 zwischen ALLOW und DROP."""
    want = "allow" if random.random() < 0.5 else "drop"
    candidates = [r for r in rules if r["verdict"] == want]
    if not candidates:
        # Wenn keine passenden Rules: erzwinge anderes Verdict
        want = "drop"
        candidates = [r for r in rules if r["verdict"] == "drop"]
    for _ in range(20):
        p = _pi_base_packet()
        if candidates:
            rule = random.choice(candidates)
            _pi_apply_rule(p, rule["id"])
        idx, matched = _pi_first_match(p, rules)
        actual = matched["verdict"] if matched else "drop"
        # default-deny zählt als drop
        if actual == want:
            p["expected"]     = actual
            p["matched_rule"] = idx
            return p
    # Fallback
    p = _pi_base_packet()
    idx, matched = _pi_first_match(p, rules)
    p["expected"]     = matched["verdict"] if matched else "drop"
    p["matched_rule"] = idx
    return p

def _pi_build_rules():
    """Wählt 3 Regeln so, dass mindestens 1 ALLOW und 1 BLOCK dabei ist."""
    allow = [r for r in PI_RULES_POOL if r["verdict"] == "allow"]
    block = [r for r in PI_RULES_POOL if r["verdict"] == "drop"]
    picked = [random.choice(allow), random.choice(block)]
    remaining = [r for r in PI_RULES_POOL if r not in picked]
    picked.append(random.choice(remaining))
    random.shuffle(picked)
    return picked

def _rt_routes():
    global _RT_ROUTES
    if _RT_ROUTES is None:
        _RT_ROUTES = [
            {"label": "10.0.0.0/8",     "prefix": (10,),       "col": CYAN_C},
            {"label": "192.168.0.0/16", "prefix": (192, 168),  "col": GREEN_C},
            {"label": "0.0.0.0/0",      "prefix": (),           "col": ORANGE_C},
        ]
    return _RT_ROUTES

def _rt_match_route(ip_str):
    parts = tuple(int(x) for x in ip_str.split('.'))
    routes = _rt_routes()
    for i, r in enumerate(routes[:-1]):
        if parts[:len(r["prefix"])] == r["prefix"]:
            return i
    return len(routes) - 1

def _rt_random_ip():
    r = random.random()
    if r < 0.34:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    elif r < 0.67:
        return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"
    else:
        first = random.choice([172, 8, 1, 203, 185, 216, 100, 45])
        return f"{first}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def _rt_route_rects(px, py):
    btn_y = py + MG_PANEL_H - 140
    btn_h = 62
    usable_w = MG_PANEL_W - 60
    btn_w = (usable_w - 20) // 3
    return [pygame.Rect(px + 30 + i * (btn_w + 10), btn_y, btn_w, btn_h)
            for i in range(3)]


def _ff_drop_zones():
    """Passive Drop-Slots unter der Arena – spaltenausgerichtet."""
    _, py = _ff_panel_rect()
    btn_y = py + MG_PANEL_H - 100
    btn_h = 50
    zones = []
    for (_, xl, xr, _), port in zip(_ff_columns(), MG_FF_PORTS):
        zones.append((port, pygame.Rect(int(xl) + 10, btn_y,
                                        int(xr - xl) - 20, btn_h)))
    return zones


MG_TUTORIAL_TEXT = {
    "cable_patch": {
        "title": "KABEL VERBINDEN",
        "lines": [
            "Verbinde jeden Stecker auf der linken Seite",
            "mit dem passenden Anschluss auf der rechten Seite.",
            "",
            "Klicke einen Stecker an und ziehe ihn",
            "zur richtigen Buchse — Farben geben Hinweise.",
            "",
            "Verbinde alle Paare bevor die Zeit abläuft!",
        ],
    },
    "frame_forwarder": {
        "title": "FRAME FORWARDER",
        "lines": [
            "Ein Frame fällt von oben in die Arena.",
            "Bewege ihn mit  ← →  (Pfeiltasten oder A/D)",
            "in die Spalte des richtigen Ziel-Ports.",
            "",
            "Der Ziel-Port steht auf dem Frame.",
            "Fehler und Zeitablauf kosten ein Leben.",
            "",
            "Erreiche das Ziel-Score bevor alle Leben weg sind!",
        ],
    },
    "route_table": {
        "title": "ROUTE TABLE",
        "lines": [
            "Ein Paket mit einer Ziel-IP-Adresse erscheint.",
            "Klicke schnell die passende Route",
            "aus der Routing-Tabelle.",
            "",
            "Jede Route deckt einen IP-Adressbereich ab.",
            "Falsche Wahl oder Zeitablauf kostet ein Leben.",
            "",
            "Erreiche das Ziel-Score bevor alle Leben weg sind!",
        ],
    },
    "packet_inspector": {
        "title": "PACKET INSPECTOR",
        "lines": [
            "Ein Paket mit Protokoll, Port und Flags erscheint.",
            "Prüfe es anhand der angezeigten Firewall-Regeln",
            "und entscheide: ALLOW oder DROP.",
            "",
            "Stimmt das Paket mit einer Regel überein,",
            "gilt deren Verdict. Sonst gilt ALLOW.",
            "",
            "Falsche Entscheidung oder Zeitablauf kostet ein Leben!",
        ],
    },
}

def _mg_tutorial_ok_rect():
    cx, cy = W // 2, H // 2
    bw, bh = 200, 46
    return pygame.Rect(cx - bw // 2, cy + 148, bw, bh)

def draw_mg_tutorial(game: Game):
    mg = game.minigame
    if not mg or not mg.get("tutorial"): return
    tdata = MG_TUTORIAL_TEXT.get(mg["type"])
    if not tdata: return

    tw, th = 560, 360
    tx = W // 2 - tw // 2
    ty = H // 2 - th // 2

    draw_rect_border(screen, BORDER_A, (tx, ty, tw, th), fill=(10, 14, 22), radius=12)
    _draw_corner_brackets(screen, pygame.Rect(tx, ty, tw, th), BORDER_A, length=16, thickness=2)

    text(screen, font_big, tdata["title"], BORDER_A, W // 2, ty + 18, "midtop")
    pygame.draw.line(screen, PANEL_HL, (tx + 24, ty + 54), (tx + tw - 24, ty + 54), 1)

    ly = ty + 68
    for line in tdata["lines"]:
        if line:
            text(screen, font_small, line, WHITE, W // 2, ly, "midtop")
        ly += 22

    mx, my = pygame.mouse.get_pos()
    ok_r = _mg_tutorial_ok_rect()
    hov = ok_r.collidepoint(mx, my)
    draw_rect_border(screen, BORDER_A, ok_r, fill=PANEL_HL if hov else PANEL, radius=8)
    text(screen, font_big, "LOS GEHT'S  ▶", WHITE, ok_r.centerx, ok_r.y + 9, "midtop")


def draw_minigame(game: Game):
    mg = game.minigame
    if mg is None: return

    # Dim-Overlay (gemeinsam fuer alle Minigame-Typen)
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    if mg.get("tutorial"):
        draw_mg_tutorial(game)
        return

    px, py = _ff_panel_rect()
    draw_rect_border(screen, GOLD, (px, py, MG_PANEL_W, MG_PANEL_H),
                     fill=(15, 20, 28), radius=12)

    if mg["type"] == "cable_patch":
        _draw_cable_patch(game, mg, px, py)
        return
    if mg["type"] == "route_table":
        _draw_route_table(game, mg, px, py)
        return
    if mg["type"] == "packet_inspector":
        _draw_packet_inspector(game, mg, px, py)
        return
    if mg["type"] != "frame_forwarder": return

    # Titel
    text(screen, font_xl, "FRAME FORWARDER", GOLD,
         px + MG_PANEL_W // 2, py + 12, "midtop")
    text(screen, font_small,
         "Switch-Challenge — leite jedes Frame an den passenden Port",
         DIM, px + MG_PANEL_W // 2, py + 58, "midtop")

    # Score + Lives
    text(screen, font_med, f"SCORE  {mg['score']} / {MG_FF_GOAL}",
         WHITE, px + 30, py + 78)
    lives_txt = "LIVES " + ("● " * mg['lives']) + ("· " * (MG_FF_LIVES - mg['lives']))
    text(screen, font_med, lives_txt.strip(), RED_C,
         px + MG_PANEL_W - 30, py + 78, "topright")

    # Arena
    ax, ay, aw, ah = _ff_arena_rect()
    pygame.draw.rect(screen, PANEL, (ax, ay, aw, ah), border_radius=6)

    colors = _ff_colors()
    cols = _ff_columns()
    # Spalten-Tönung + Trenner
    for (i, xl, xr, xc), port in zip(cols, MG_FF_PORTS):
        col_c = colors[port]
        tint = pygame.Surface((int(xr - xl) - 2, ah - 2), pygame.SRCALPHA)
        tint.fill((*col_c, 22))
        screen.blit(tint, (int(xl) + 1, ay + 1))
        text(screen, font_tiny, f"→ {port}", col_c, int(xc), ay + 4, "midtop")
    for i in (1, 2):
        x = int(cols[i][1])
        for yy in range(ay + 6, ay + ah - 6, 10):
            pygame.draw.line(screen, BORDER, (x, yy), (x, yy + 5), 1)
    pygame.draw.rect(screen, BORDER, (ax, ay, aw, ah), 2, border_radius=6)

    # Fallendes Frame – in seiner aktuellen Spalte
    if mg["frame"] is not None and mg["result"] is None:
        f = mg["frame"]
        fw, fh = 80, MG_FF_FRAME_H
        col_center = cols[f["col"]][3]
        fx = int(col_center - fw // 2)
        fy = ay + int(f["y"])
        col = colors[f["port"]]
        # Schweif
        for k in range(4):
            ts = pygame.Surface((fw, 8), pygame.SRCALPHA)
            ts.fill((*col, max(0, 90 - k * 22)))
            screen.blit(ts, (fx, fy - 6 - k * 6))
        pygame.draw.rect(screen, col, (fx, fy, fw, fh), border_radius=6)
        pygame.draw.rect(screen, WHITE, (fx, fy, fw, fh), 2, border_radius=6)
        text(screen, font_big, f["port"], WHITE,
             fx + fw // 2, fy + 8, "midtop")
        text(screen, font_tiny, "FRAME", WHITE,
             fx + fw // 2, fy + fh - 14, "midtop")

    # Drop-Slots (passiv, nur Anzeige wo welcher Port landet)
    for port, r in _ff_drop_zones():
        col = colors[port]
        # Hervorheben, falls aktuelles Frame in dieser Spalte landen wuerde
        is_target = (mg["frame"] is not None and
                     MG_FF_PORTS[mg["frame"]["col"]] == port)
        bg = PANEL_HL if is_target else PANEL
        draw_rect_border(screen, col, r, fill=bg, radius=8)
        text(screen, font_xl, port, col, r.centerx, r.y + 6, "midtop")
        text(screen, font_tiny, "DROP", DIM, r.centerx, r.bottom - 14, "midtop")

    # Footer / Result
    if mg["result"] == "won":
        text(screen, font_big, "CONNECTION ESTABLISHED",
             GREEN_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    elif mg["result"] == "lost":
        text(screen, font_big, "PACKET LOSS — RETRY",
             RED_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    else:
        text(screen, font_small,
             "A / D  oder  ← / →  bewegen",
             WHITE, px + MG_PANEL_W // 2, py + MG_PANEL_H - 40, "midtop")
        text(screen, font_tiny,
             "ESC abbrechen  ·  Niederlage = 15s Sperre + 25% Paket-Verlust",
             DIM, px + MG_PANEL_W // 2, py + MG_PANEL_H - 22, "midtop")


def _draw_cable_patch(game: Game, mg, px, py):
    # Titel
    text(screen, font_xl, "CABLE PATCH", GOLD,
         px + MG_PANEL_W // 2, py + 12, "midtop")
    text(screen, font_small,
         "Hub-Challenge — verfolge jedes Kabel und stecke es in den passenden Port",
         DIM, px + MG_PANEL_W // 2, py + 58, "midtop")

    # Score / Lives
    placed = sum(1 for c in mg["cables"] if c["placed_port"] is not None)
    text(screen, font_med, f"VERBUNDEN  {placed} / 3",
         WHITE, px + 30, py + 78)
    lives_txt = "LIVES " + ("● " * mg['lives']) + ("· " * (MG_CP_LIVES - mg['lives']))
    text(screen, font_med, lives_txt.strip(), RED_C,
         px + MG_PANEL_W - 30, py + 78, "topright")

    # Zeit-Balken
    now = pygame.time.get_ticks()
    remaining = max(0, MG_CP_TIME_MS - (now - mg["start_time"]))
    ratio = remaining / MG_CP_TIME_MS
    bar_x, bar_y, bar_w, bar_h = px + 30, py + 105, MG_PANEL_W - 60, 6
    pygame.draw.rect(screen, BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    if ratio > 0.5:    bc = GREEN_C
    elif ratio > 0.25: bc = ORANGE_C
    else:              bc = RED_C
    if ratio <= 0.25:
        pulse = 0.6 + 0.4 * math.sin(now / 90.0)
        bc = tuple(int(c_ * (0.6 + 0.4 * pulse)) for c_ in bc)
    pygame.draw.rect(screen, bc, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=3)
    text(screen, font_tiny, f"{remaining/1000:.1f}s", bc,
         bar_x + bar_w, bar_y - 13, "topright")

    mx, my = pygame.mouse.get_pos()
    drag_idx = mg["dragging_idx"]

    # PCs (links)
    for i in range(3):
        cx, cy = _cp_pc_pos(i)
        rect = pygame.Rect(cx - 36, cy - 28, 72, 56)
        draw_rect_border(screen, CYAN_C, rect, fill=PANEL_HL, radius=6)
        text(screen, font_med, f"PC{i+1}", WHITE, cx, cy - 24, "midtop")
        sc = pygame.Rect(cx - 22, cy - 2, 44, 20)
        pygame.draw.rect(screen, (5, 8, 14), sc, border_radius=2)
        pygame.draw.rect(screen, BORDER_A, sc, 1, border_radius=2)
        # Kabel-Austrittspunkt
        ax, ay = _cp_anchor_pos(i)
        pygame.draw.circle(screen, BORDER_A, (ax, ay), 4)

    # Ports (rechts) – Hover/Snap-Highlight wenn aktuelles Kabel hierhin gezogen wird
    for i in range(3):
        cx, cy = _cp_port_pos(i)
        rect = pygame.Rect(cx - 36, cy - 28, 72, 56)
        is_snap = (drag_idx is not None and
                   math.hypot(mx - cx, my - cy) <= MG_CP_SNAP_R)
        border_col = WHITE if is_snap else ORANGE_C
        fill_col   = (50, 35, 10) if is_snap else PANEL_HL
        draw_rect_border(screen, border_col, rect, fill=fill_col, radius=6)
        text(screen, font_med, f"P{i+1}", WHITE, cx, cy - 24, "midtop")
        sx, sy = _cp_socket_pos(i)
        pygame.draw.circle(screen, (5, 8, 14), (sx, sy), 9)
        pygame.draw.circle(screen, BORDER, (sx, sy), 9, 1)

    # Kabel (Bezier) – gedraggtes zuoberst
    order = [i for i in range(3) if i != drag_idx]
    if drag_idx is not None:
        order.append(drag_idx)
    for i in order:
        c = mg["cables"][i]
        anchor = _cp_anchor_pos(i)
        end    = c["end_pos"]
        path_pts = [anchor] + list(c["waypoints"]) + [end]
        pts = _catmull_rom(path_pts)
        thick = 6 if i == drag_idx else 5
        pygame.draw.lines(screen, c["color"], False, pts, thick)

    # Plugs (lose Enden, nur fuer noch nicht plazierte Kabel)
    for i, c in enumerate(mg["cables"]):
        if c["placed_port"] is not None: continue
        ex, ey = c["end_pos"]
        hover = (i == drag_idx or
                 math.hypot(mx - ex, my - ey) <= MG_CP_PICK_R)
        if hover:
            halo = pygame.Surface((42, 42), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*c["color"], 90), (21, 21), 19)
            screen.blit(halo, (int(ex) - 21, int(ey) - 21))
        pygame.draw.circle(screen, c["color"], (int(ex), int(ey)), MG_CP_PLUG_R)
        pygame.draw.circle(screen, WHITE, (int(ex), int(ey)), MG_CP_PLUG_R, 2)

    # Footer
    if mg["result"] == "won":
        text(screen, font_big, "ALLE PATCHES VERBUNDEN!",
             GREEN_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    elif mg["result"] == "lost":
        text(screen, font_big, "MISWIRED — RETRY",
             RED_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    else:
        text(screen, font_small,
             "Plug greifen · ziehen · in passende Buchse ablegen",
             WHITE, px + MG_PANEL_W // 2, py + MG_PANEL_H - 40, "midtop")
        text(screen, font_tiny,
             "ESC abbrechen  ·  Niederlage = 15s Sperre + 25% Paket-Verlust",
             DIM, px + MG_PANEL_W // 2, py + MG_PANEL_H - 22, "midtop")


def _draw_route_table(game: Game, mg, px, py):
    now = pygame.time.get_ticks()
    routes = _rt_routes()

    text(screen, font_xl, "ROUTE-TABLE RACER", GOLD,
         px + MG_PANEL_W // 2, py + 12, "midtop")
    text(screen, font_small,
         "Router-Challenge — wähle die longest-prefix-match Route",
         DIM, px + MG_PANEL_W // 2, py + 58, "midtop")

    text(screen, font_med, f"SCORE  {mg['score']} / {MG_RT_GOAL}",
         WHITE, px + 30, py + 78)
    lives_txt = "LIVES " + ("● " * mg['lives']) + ("· " * (MG_RT_LIVES - mg['lives']))
    text(screen, font_med, lives_txt.strip(), RED_C,
         px + MG_PANEL_W - 30, py + 78, "topright")

    # IP-Paket-Anzeige
    box_x  = px + 80
    box_y  = py + 110
    box_w  = MG_PANEL_W - 160
    box_h  = 82
    fb = mg.get("feedback")

    if mg["packet_ip"] is not None:
        draw_rect_border(screen, BORDER_A, (box_x, box_y, box_w, box_h),
                         fill=PANEL_HL, radius=10)
        text(screen, font_small, "DESTINATION IP", DIM,
             px + MG_PANEL_W // 2, box_y + 8, "midtop")
        text(screen, font_xl, mg["packet_ip"], WHITE,
             px + MG_PANEL_W // 2, box_y + 30, "midtop")
    elif fb is not None:
        fb_col = GREEN_C if fb["type"] == "correct" else RED_C
        fb_msg = {"correct": "CORRECT!", "wrong": "WRONG!", "timeout": "TIMEOUT!"}[fb["type"]]
        draw_rect_border(screen, fb_col, (box_x, box_y, box_w, box_h),
                         fill=PANEL_HL, radius=10)
        text(screen, font_xl, fb_msg, fb_col,
             px + MG_PANEL_W // 2, box_y + 24, "midtop")
    else:
        draw_rect_border(screen, BORDER, (box_x, box_y, box_w, box_h),
                         fill=PANEL, radius=10)
        text(screen, font_big, "next packet...", DIM,
             px + MG_PANEL_W // 2, box_y + 28, "midtop")

    # Timer-Balken
    bar_x, bar_y = box_x, box_y + box_h + 8
    bar_w, bar_h = box_w, 7
    pygame.draw.rect(screen, BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    if mg["packet_ip"] is not None:
        elapsed = now - mg["timer_start"]
        ratio   = max(0.0, 1.0 - elapsed / mg["timer_ms"])
        if ratio > 0.5:    bc = GREEN_C
        elif ratio > 0.25: bc = ORANGE_C
        else:              bc = RED_C
        if ratio <= 0.25:
            pulse = 0.6 + 0.4 * math.sin(now / 80.0)
            bc = tuple(int(c_ * (0.6 + 0.4 * pulse)) for c_ in bc)
        pygame.draw.rect(screen, bc, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=3)
        secs_left = max(0.0, (mg["timer_ms"] - elapsed) / 1000.0)
        text(screen, font_tiny, f"{secs_left:.1f}s", bc,
             bar_x + bar_w, bar_y - 14, "topright")

    # Route-Buttons
    rects  = _rt_route_rects(px, py)
    mx_, my_ = pygame.mouse.get_pos()

    text(screen, font_tiny, "▼  ROUTING TABLE  ▼", DIM,
         px + MG_PANEL_W // 2, rects[0].y - 20, "midtop")

    for i, (r, route) in enumerate(zip(rects, routes)):
        col = route["col"]
        is_hover = r.collidepoint(mx_, my_) and mg["packet_ip"] is not None
        fill       = PANEL
        border_col = col
        if fb is not None:
            if i == fb.get("correct") and fb["type"] != "correct":
                border_col = GREEN_C
                fill = (0, 40, 20)
            elif i == fb.get("clicked") and fb["type"] == "wrong":
                border_col = RED_C
                fill = (40, 0, 0)
            elif fb["type"] == "timeout":
                border_col = RED_C
        elif is_hover:
            fill       = PANEL_HL
            border_col = WHITE
        draw_rect_border(screen, border_col, r, fill=fill, radius=8)
        text(screen, font_tiny, f"[{i+1}]", DIM, r.x + 8, r.y + 6)
        text(screen, font_big, route["label"],
             col if not is_hover else WHITE,
             r.centerx, r.y + 18, "midtop")

    # Footer
    if mg["result"] == "won":
        text(screen, font_big, "ROUTE ESTABLISHED!",
             GREEN_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    elif mg["result"] == "lost":
        text(screen, font_big, "ROUTING LOOP — RETRY",
             RED_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 36, "midtop")
    else:
        text(screen, font_small, "Klicken  oder  1 / 2 / 3  drücken",
             WHITE, px + MG_PANEL_W // 2, py + MG_PANEL_H - 40, "midtop")
        text(screen, font_tiny,
             "ESC abbrechen  ·  Niederlage = 15s Sperre + 25% Paket-Verlust",
             DIM, px + MG_PANEL_W // 2, py + MG_PANEL_H - 22, "midtop")


def _pi_button_rects(px, py):
    bw, bh = 260, 56
    allow = pygame.Rect(px + 40,                  py + 380, bw, bh)
    drop  = pygame.Rect(px + MG_PANEL_W - 40 - bw, py + 380, bw, bh)
    return allow, drop

def _draw_packet_inspector(game: Game, mg, px, py):
    now = pygame.time.get_ticks()
    fb  = mg.get("feedback")

    # Flash-Tint hinter dem Panel bei Feedback
    if fb is not None and fb["type"] in ("correct", "wrong", "timeout"):
        col = GREEN_C if fb["type"] == "correct" else RED_C
        fade = max(0.0, 1.0 - (now - fb["at"]) / MG_PI_FLASH_MS)
        if fade > 0:
            tint = pygame.Surface((MG_PANEL_W - 4, MG_PANEL_H - 4), pygame.SRCALPHA)
            tint.fill((*col, int(35 * fade)))
            screen.blit(tint, (px + 2, py + 2))

    # Header
    text(screen, font_xl, "PACKET INSPECTOR", GOLD,
         px + MG_PANEL_W // 2, py + 14, "midtop")
    text(screen, font_small,
         "Firewall-Challenge — wende die ACL auf jedes Paket an",
         DIM, px + MG_PANEL_W // 2, py + 72, "midtop")

    # Score + Lives
    text(screen, font_med, f"SCORE  {mg['score']} / {MG_PI_GOAL}",
         WHITE, px + 30, py + 104)
    lives_txt = "LIVES " + ("● " * mg['lives']) + ("· " * (MG_PI_LIVES - mg['lives']))
    text(screen, font_med, lives_txt.strip(), RED_C,
         px + MG_PANEL_W - 30, py + 104, "topright")

    # ── ACL-Box ─────────────────────────────────────────────────────
    acl_rect = pygame.Rect(px + 30, py + 140, MG_PANEL_W - 60, 132)
    draw_rect_border(screen, BORDER_A, acl_rect, fill=PANEL, radius=8)
    text(screen, font_tiny, "ACL  ·  first-match-wins", BORDER_A,
         acl_rect.x + 10, acl_rect.y + 6)
    matched_idx = mg["packet"]["matched_rule"] if (mg["packet"] is not None) else -2
    # Bei Feedback die match-info aus fb nehmen damit User sieht warum
    if fb is not None and "matched_rule" in fb:
        matched_idx = fb["matched_rule"]
    for i, rule in enumerate(mg["rules"]):
        row_y = acl_rect.y + 32 + i * 26
        is_match = (matched_idx == i and fb is not None)
        rule_col = (GREEN_C if rule["verdict"] == "allow" else RED_C)
        if is_match:
            hl = pygame.Surface((acl_rect.w - 16, 24), pygame.SRCALPHA)
            hl.fill((*rule_col, 60))
            screen.blit(hl, (acl_rect.x + 8, row_y - 2))
        text(screen, font_small, f"{i+1}.", DIM, acl_rect.x + 14, row_y)
        text(screen, font_small, rule["text"], rule_col, acl_rect.x + 40, row_y)
    # Default-Zeile
    default_y = acl_rect.y + 32 + 3 * 26
    is_default = (matched_idx == -1 and fb is not None)
    if is_default:
        hl = pygame.Surface((acl_rect.w - 16, 22), pygame.SRCALPHA)
        hl.fill((*RED_C, 60))
        screen.blit(hl, (acl_rect.x + 8, default_y - 2))
    text(screen, font_tiny, "*.  default:  DENY",
         DIM if not is_default else RED_C, acl_rect.x + 14, default_y + 2)

    # ── Paket-Karte ─────────────────────────────────────────────────
    pkt_rect = pygame.Rect(px + 80, py + 288, MG_PANEL_W - 160, 80)
    pkt = mg["packet"]
    if pkt is not None and fb is None:
        # Border-Color leicht pulsierend
        pulse = 0.5 + 0.5 * math.sin(now / 200.0)
        bcol = _mix(BORDER_A, WHITE, 0.3 * pulse)
        draw_glow_border(screen, BORDER_A, pkt_rect, radius=10, intensity=50)
        draw_rect_border(screen, bcol, pkt_rect, fill=(18, 28, 46), radius=10)
        # Proto + Flags rechts
        proto_col = {"TCP": CYAN_C, "UDP": BLUE_C, "ICMP": ORANGE_C}.get(pkt["proto"], WHITE)
        text(screen, font_big, pkt["proto"], proto_col,
             pkt_rect.x + 18, pkt_rect.y + 8)
        if pkt.get("flags"):
            flag_col = RED_C if pkt["flags"] == "SYN+FIN" else GOLD
            text(screen, font_med, f"[{pkt['flags']}]", flag_col,
                 pkt_rect.right - 18, pkt_rect.y + 12, "topright")
        # Adressen
        src = f"{pkt['src_ip']}" + (f":{pkt['src_port']}" if pkt['src_port'] else "")
        dst = f"{pkt['dst_ip']}" + (f":{pkt['dst_port']}" if pkt['dst_port'] else "")
        text(screen, font_med, src, WHITE, pkt_rect.x + 18, pkt_rect.y + 42)
        text(screen, font_med, "→", DIM,
             pkt_rect.x + 18, pkt_rect.y + 62)
        text(screen, font_med, dst, WHITE, pkt_rect.x + 42, pkt_rect.y + 62)
    elif fb is not None:
        # Zeige das gerade entschiedene Paket als Ergebnis
        col = GREEN_C if fb["type"] == "correct" else RED_C
        draw_rect_border(screen, col, pkt_rect, fill=PANEL, radius=10)
        if fb["type"] == "correct":
            msg = f"✓  KORREKT  ·  {fb['verdict'].upper()}"
        elif fb["type"] == "timeout":
            msg = f"⌛  TIMEOUT  ·  expected {fb['expected'].upper()}"
        else:
            msg = f"✗  FALSCH  ·  expected {fb['expected'].upper()}"
        text(screen, font_big, msg, col,
             pkt_rect.centerx, pkt_rect.centery - 14, "center")
        # Welche Regel hat gegriffen
        if fb.get("matched_rule", -2) >= 0:
            why = "matched rule " + str(fb["matched_rule"] + 1)
        elif fb.get("matched_rule") == -1:
            why = "no match → default DENY"
        else:
            why = ""
        if why:
            text(screen, font_small, why, DIM,
                 pkt_rect.centerx, pkt_rect.centery + 18, "center")

    # ── Action-Buttons + Timer (nicht im Result-Modus) ──────────────
    if mg["result"] is None:
        allow_rect, drop_rect = _pi_button_rects(px, py)
        mxp, myp = pygame.mouse.get_pos()
        hov_a = allow_rect.collidepoint(mxp, myp) and pkt is not None and fb is None
        hov_d = drop_rect.collidepoint(mxp, myp) and pkt is not None and fb is None
        if hov_a: draw_glow_border(screen, GREEN_C, allow_rect, radius=10, intensity=90)
        if hov_d: draw_glow_border(screen, RED_C,   drop_rect,  radius=10, intensity=90)
        draw_rect_border(screen, GREEN_C, allow_rect,
                         fill=(14, 50, 28) if hov_a else (10, 30, 18), radius=10)
        draw_rect_border(screen, RED_C, drop_rect,
                         fill=(60, 18, 22) if hov_d else (35, 10, 14), radius=10)
        text(screen, font_big, "ALLOW",  WHITE if hov_a else GREEN_C,
             allow_rect.centerx, allow_rect.centery, "center")
        text(screen, font_tiny, "[A]", DIM,
             allow_rect.right - 10, allow_rect.bottom - 4, "bottomright")
        text(screen, font_big, "DROP",  WHITE if hov_d else RED_C,
             drop_rect.centerx, drop_rect.centery, "center")
        text(screen, font_tiny, "[D]", DIM,
             drop_rect.right - 10, drop_rect.bottom - 4, "bottomright")

        # Timer-Bar
        bar_x, bar_y, bar_w, bar_h = px + 30, py + 446, MG_PANEL_W - 60, 6
        pygame.draw.rect(screen, BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        if pkt is not None and fb is None:
            window = mg.get("window_ms", mg["time_per_pkt"])
            left   = max(0, mg["deadline"] - now)
            ratio  = min(1.0, left / max(1, window))
            bar_col = GREEN_C if ratio > 0.5 else (ORANGE_C if ratio > 0.25 else RED_C)
            pygame.draw.rect(screen, bar_col,
                             (bar_x, bar_y, int(bar_w * ratio), bar_h),
                             border_radius=3)

    # ── Footer / Result ─────────────────────────────────────────────
    if mg["result"] == "won":
        text(screen, font_big, "FIREWALL ARMED — UNLOCKED",
             GREEN_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 60, "midtop")
    elif mg["result"] == "lost":
        text(screen, font_big, "BREACH DETECTED — RETRY",
             RED_C, px + MG_PANEL_W // 2, py + MG_PANEL_H - 60, "midtop")
    else:
        text(screen, font_tiny,
             "ESC abbrechen  ·  Niederlage = 15s Sperre + 25% Paket-Verlust",
             DIM, px + MG_PANEL_W // 2, py + MG_PANEL_H - 20, "midtop")


def minigame_click(game: Game, mx, my) -> bool:
    mg = game.minigame
    if mg is None: return False
    if mg.get("tutorial"):
        if _mg_tutorial_ok_rect().collidepoint(mx, my):
            mg["tutorial"] = False
            if mg["type"] == "route_table":
                mg["next_spawn"] = pygame.time.get_ticks() + 600
        return True
    if mg["result"] is not None: return True
    if mg["type"] == "cable_patch":
        game.cp_pickup((mx, my))
    elif mg["type"] == "route_table":
        px, py = _ff_panel_rect()
        for i, r in enumerate(_rt_route_rects(px, py)):
            if r.collidepoint(mx, my):
                game.rt_click(i)
                break
    elif mg["type"] == "packet_inspector":
        px, py = _ff_panel_rect()
        allow_r, drop_r = _pi_button_rects(px, py)
        if allow_r.collidepoint(mx, my):
            game.pi_decide("allow")
        elif drop_r.collidepoint(mx, my):
            game.pi_decide("drop")
    # frame_forwarder: Bewegung erfolgt nur per Tastatur
    return True


def minigame_motion(game: Game, pos):
    mg = game.minigame
    if mg is None: return
    if mg["type"] == "cable_patch":
        game.cp_drag(pos)


def minigame_release(game: Game, pos):
    mg = game.minigame
    if mg is None: return
    if mg["type"] == "cable_patch":
        game.cp_release(pos)


# ── Einführungs-Popup ────────────────────────────────────────────────

INTRO_W = 660
INTRO_H = 430

def _intro_rects():
    px = W // 2 - INTRO_W // 2
    py = H // 2 - INTRO_H // 2
    bw, bh = 190, 44
    btn_next = pygame.Rect(px + INTRO_W - bw - 22, py + INTRO_H - bh - 18, bw, bh)
    btn_back = pygame.Rect(px + 22, py + INTRO_H - bh - 18, bw, bh)
    return px, py, btn_next, btn_back


def draw_intro(game: Game):
    if not game.show_intro: return
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    px, py, btn_next, btn_back = _intro_rects()
    draw_rect_border(screen, BORDER_A, (px, py, INTRO_W, INTRO_H),
                     fill=(15, 20, 28), radius=12)

    mx, my = pygame.mouse.get_pos()

    if game.intro_page == 0:
        text(screen, font_xl, "WILLKOMMEN BEI",
             BORDER_A, px + INTRO_W // 2, py + 14, "midtop")
        text(screen, font_xl, "PACKET CLICKER",
             BORDER_A, px + INTRO_W // 2, py + 66, "midtop")
        text(screen, font_small,
             "Bau dein Autonomes System vom Hub bis zum globalen ASN auf.",
             DIM, px + INTRO_W // 2, py + 118, "midtop")

        lines = [
            (WHITE,  "Klicke auf den Kreis links, um Datenpakete zu generieren."),
            (WHITE,  "Pakete sind deine Währung — gib sie für Netzwerk-Equipment aus."),
            (None,   ""),
            (WHITE,  "Upgrades (Hub, Switch, Router …) erzeugen automatisch Pakete/s,"),
            (WHITE,  "auch während du nicht klickst."),
            (None,   ""),
            (CYAN_C, "Tipp: Die ersten Upgrades werden per Mini-Spiel-Challenge"),
            (CYAN_C, "freigeschaltet. Danach kannst du sie beliebig oft kaufen."),
            (None,   ""),
            (GOLD,   "Tipp: Später erscheint ein Forschungs-Tab für permanente Boni"),
            (GOLD,   "(wird nach dem ersten Firewall-Kauf freigeschaltet)."),
        ]
        ty = py + 136
        for col, line in lines:
            text(screen, font_small, line, col or DIM,
                 px + INTRO_W // 2, ty, "midtop")
            ty += 21
    else:
        text(screen, font_xl, "SPIELMECHANIKEN",
             BORDER_A, px + INTRO_W // 2, py + 14, "midtop")

        sections = [
            (CYAN_C,   "TCP-HANDSHAKE",
             ["Ein Paket fliegt über die Leitung oben — klicke es im richtigen Moment",
              "für Bonus-Pakete! Mehrfach treffen baut einen Combo-Multiplikator auf."]),
            (ORANGE_C, "NETZWERK-EVENTS",
             ["Zufällige Ereignisse (DDoS, BGP-Hijack, Peering-Deal …) tauchen auf",
              "und verändern deine Pakete/s vorübergehend — positiv oder negativ."]),
            (GOLD,     "PRESTIGE",
             ["Ab 1 Milliarde Gesamtpaketen kannst du alles resetten und einen",
              "dauerhaften Multiplikator für alle zukünftigen Runden kassieren."]),
        ]
        ty = py + 60
        for hcol, header, desc_lines in sections:
            text(screen, font_med, header, hcol, px + 36, ty)
            ty += 22
            for dline in desc_lines:
                text(screen, font_small, dline, WHITE, px + 36, ty)
                ty += 20
            ty += 12

    # Seiten-Punkte
    dots = "● ○" if game.intro_page == 0 else "○ ●"
    text(screen, font_small, dots, DIM, px + INTRO_W // 2, py + INTRO_H - 22, "midtop")

    # Weiter / LOS GEHT'S
    lbl_next = "WEITER  →" if game.intro_page == 0 else "LOS GEHT'S!"
    hov_next = btn_next.collidepoint(mx, my)
    draw_rect_border(screen, BORDER_A, btn_next,
                     fill=PANEL_HL if hov_next else PANEL, radius=8)
    text(screen, font_big, lbl_next, WHITE,
         btn_next.centerx, btn_next.y + 10, "midtop")

    # Zurück (nur Seite 2)
    if game.intro_page > 0:
        hov_back = btn_back.collidepoint(mx, my)
        draw_rect_border(screen, BORDER, btn_back,
                         fill=PANEL_HL if hov_back else PANEL, radius=8)
        text(screen, font_big, "←  ZURÜCK", DIM,
             btn_back.centerx, btn_back.y + 10, "midtop")


def intro_click(game: Game, mx, my) -> bool:
    if not game.show_intro: return False
    _, _, btn_next, btn_back = _intro_rects()
    if btn_next.collidepoint(mx, my):
        if game.intro_page == 0:
            game.intro_page = 1
        else:
            game.show_intro = False
            game.save()
        play_sfx('click')
    elif btn_back.collidepoint(mx, my) and game.intro_page > 0:
        game.intro_page -= 1
        play_sfx('click')
    return True


# ── RFC-Intro-Popup ───────────────────────────────────────────────────

RFC_INTRO_W = 600
RFC_INTRO_H = 380

def _rfc_intro_rects():
    px = W // 2 - RFC_INTRO_W // 2
    py = H // 2 - RFC_INTRO_H // 2
    bw, bh = 220, 50
    bx = px + RFC_INTRO_W // 2 - bw // 2
    by = py + RFC_INTRO_H - bh - 24
    return px, py, pygame.Rect(bx, by, bw, bh)


def draw_rfc_intro(game: Game):
    if not game.show_rfc_intro: return
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    px, py, btn = _rfc_intro_rects()
    draw_rect_border(screen, RFC_COL, (px, py, RFC_INTRO_W, RFC_INTRO_H),
                     fill=(15, 20, 28), radius=12)

    text(screen, font_xl, "RFC-FORSCHUNG FREIGESCHALTET",
         RFC_COL, px + RFC_INTRO_W // 2, py + 18, "midtop")
    text(screen, font_small,
         "Deine erste Firewall macht es ernst — Zeit fuer echte Standards.",
         DIM, px + RFC_INTRO_W // 2, py + 64, "midtop")

    lines = [
        "RFC-Punkte sammeln sich nun automatisch (Anzeige oben links).",
        "Die Rate steigt mit jedem unterschiedlichen Upgrade, das du besitzt,",
        "und mit jeder bereits abgeschlossenen Forschung.",
        "",
        "Im Tab FORSCHUNG (oben rechts) gibst du RFC-Punkte aus, um",
        "permanente Boni freizuschalten: mehr Pakete/s, staerkere Klicks,",
        "kuerzere negative Events und mehr.",
        "",
        "Forschungen ueberleben Prestige — RFC ist deine Langzeit-Strategie.",
    ]
    ty = py + 92
    for line in lines:
        col = WHITE if line else DIM
        text(screen, font_small, line, col,
             px + RFC_INTRO_W // 2, ty, "midtop")
        ty += 22

    mx, my = pygame.mouse.get_pos()
    hov = btn.collidepoint(mx, my)
    draw_rect_border(screen, RFC_COL, btn,
                     fill=PANEL_HL if hov else PANEL, radius=8)
    text(screen, font_big, "VERSTANDEN", WHITE,
         btn.centerx, btn.y + 11, "midtop")


def rfc_intro_click(game: Game, mx, my) -> bool:
    if not game.show_rfc_intro: return False
    _, _, btn = _rfc_intro_rects()
    if btn.collidepoint(mx, my):
        game.show_rfc_intro = False
        play_sfx('click')
        game.save()
    return True  # alle Klicks ausserhalb auch konsumieren


# ── Main Menu ─────────────────────────────────────────────────────────

def draw_main_menu(game: Game):
    mx, my = pygame.mouse.get_pos()

    # Vignette über dem Menü-Hintergrund
    screen.blit(_bg_vignette(W, H), (0, 0))

    # Hero-Titel mit großem Glow
    title_y = H//2 - 150
    # Doppelt-gerendert für stärkeren Glow
    text_glow(screen, font_xl, "PACKET CLICKER", BORDER_A,
              W//2, title_y, "midtop", glow_col=BORDER_A, intensity=3)
    text_glow(screen, font_xl, "PACKET CLICKER", WHITE,
              W//2, title_y, "midtop", glow_col=BORDER_A, intensity=1)

    # Akzent-Linie unter dem Titel
    line_w = 380
    line_y = title_y + 68
    line_surf = pygame.Surface((line_w, 4), pygame.SRCALPHA)
    for x in range(line_w):
        t = abs(x - line_w/2) / (line_w/2)
        a = int(220 * (1 - t**2))
        col = _mix(BORDER_A, ACCENT_2, x / line_w)
        line_surf.set_at((x, 1), (*col, a))
        line_surf.set_at((x, 2), (*col, a))
    screen.blit(line_surf, (W//2 - line_w//2, line_y))

    text(screen, font_small, "Manage your Autonomous System",
         DIM, W//2, line_y + 18, "midtop")

    bw, bh = 240, 50
    bx = W//2 - bw//2

    def hero_btn(rect, accent, label, hover):
        if hover:
            draw_glow_border(screen, accent, rect, radius=12, intensity=110)
        draw_rect_border(screen, accent if not hover else WHITE, rect,
                         fill=PANEL_HL if hover else PANEL, radius=12)
        text(screen, font_big, label, WHITE, rect.centerx, rect.centery, "center")

    # Start
    start_rect = pygame.Rect(bx, H//2, bw, bh)
    hero_btn(start_rect, GREEN_C, "START GAME", start_rect.collidepoint(mx, my))

    # Settings
    set_rect = pygame.Rect(bx, H//2 + 70, bw, bh)
    hero_btn(set_rect, BLUE_C, "SETTINGS", set_rect.collidepoint(mx, my))

    # Exit
    exit_rect = pygame.Rect(bx, H//2 + 140, bw, bh)
    hero_btn(exit_rect, RED_C, "EXIT", exit_rect.collidepoint(mx, my))
    
    # Audio Toggles
    icon_s = 40
    music_rect = pygame.Rect(W//2 - icon_s - 10, H - 80, icon_s, icon_s)
    hov_mus = music_rect.collidepoint(mx, my)
    mr = music_rect.inflate(6, 6) if hov_mus else music_rect
    draw_rect_border(screen, WHITE if hov_mus else (BORDER_A if not game.music_muted else RED_C), mr, fill=PANEL_HL if hov_mus else PANEL, radius=8)
    text(screen, font_med, "MUS", DIM if game.music_muted else WHITE, mr.centerx, mr.centery, "center")
    
    sfx_rect   = pygame.Rect(W//2 + 10, H - 80, icon_s, icon_s)
    hov_sfx = sfx_rect.collidepoint(mx, my)
    sfr = sfx_rect.inflate(6, 6) if hov_sfx else sfx_rect
    draw_rect_border(screen, WHITE if hov_sfx else (BORDER_A if not game.sfx_muted else RED_C), sfr, fill=PANEL_HL if hov_sfx else PANEL, radius=8)
    text(screen, font_med, "SFX", DIM if game.sfx_muted else WHITE, sfr.centerx, sfr.centery, "center")

def menu_click(game: Game, mx, my) -> bool:
    bw, bh = 240, 50
    bx = W//2 - bw//2
    
    start_rect = pygame.Rect(bx, H//2, bw, bh)
    if start_rect.collidepoint(mx, my):
        game.state = "playing"
        # Handshake-Cooldown neu setzen, sonst feuert er nach Pause sofort
        game.hs_state = None
        game.hs_next  = pygame.time.get_ticks() + 30_000
        play_sfx("click")
        return True

    set_rect = pygame.Rect(bx, H//2 + 70, bw, bh)
    if set_rect.collidepoint(mx, my):
        game.state = "settings"
        play_sfx("click")
        return True
        
    exit_rect = pygame.Rect(bx, H//2 + 140, bw, bh)
    if exit_rect.collidepoint(mx, my):
        game.state = "exit_confirm"
        play_sfx("click")
        return True
        
    icon_s = 40
    music_rect = pygame.Rect(W//2 - icon_s - 10, H - 80, icon_s, icon_s)
    if music_rect.collidepoint(mx, my):
        game.music_muted = not game.music_muted
        set_bgm_muted(game.music_muted)
        game.save()
        play_sfx("click")
        return True
        
    sfx_rect   = pygame.Rect(W//2 + 10, H - 80, icon_s, icon_s)
    if sfx_rect.collidepoint(mx, my):
        game.sfx_muted = not game.sfx_muted
        game.save()
        play_sfx("click")
        return True

    return False

# ── Settings Menu ──────────────────────────────────────────────────────

def draw_settings_menu(game: Game):
    mx, my = pygame.mouse.get_pos()
    
    text(screen, font_xl, "SETTINGS", BORDER_A, W//2, H//2 - 180, "midtop")
    
    bw, bh = 300, 40
    bx = W//2 - bw//2
    
    # Fullscreen
    fs_rect = pygame.Rect(bx, H//2 - 80, bw, bh)
    draw_rect_border(screen, PANEL_HL, fs_rect, fill=PANEL, radius=8)
    text(screen, font_med, "Fullscreen", DIM, fs_rect.x + 15, fs_rect.centery, "midleft")
    fs_val = "ON" if game.fullscreen else "OFF"
    fs_col = GREEN_C if game.fullscreen else RED_C
    text(screen, font_med, fs_val, fs_col, fs_rect.right - 15, fs_rect.centery, "midright")
    
    # Resolution
    res_rect = pygame.Rect(bx, H//2 - 20, bw, bh)
    draw_rect_border(screen, PANEL_HL, res_rect, fill=PANEL, radius=8)
    text(screen, font_med, "Resolution", DIM, res_rect.x + 15, res_rect.centery, "midleft")
    res_str = f"{RESOLUTIONS[game.res_idx][0]}x{RESOLUTIONS[game.res_idx][1]}"
    text(screen, font_med, res_str, WHITE, res_rect.right - 15, res_rect.centery, "midright")
    
    # FPS Limit
    fps_rect = pygame.Rect(bx, H//2 + 40, bw, bh)
    draw_rect_border(screen, PANEL_HL, fps_rect, fill=PANEL, radius=8)
    text(screen, font_med, "FPS Limit", DIM, fps_rect.x + 15, fps_rect.centery, "midleft")
    fps_val = FPS_LIMITS[game.fps_idx]
    fps_str = str(fps_val) if fps_val > 0 else "Uncapped"
    text(screen, font_med, fps_str, WHITE, fps_rect.right - 15, fps_rect.centery, "midright")
    
    # Back
    back_rect = pygame.Rect(bx, H//2 + 120, bw, 50)
    hov_back = back_rect.collidepoint(mx, my)
    br = back_rect.inflate(10, 10) if hov_back else back_rect
    draw_rect_border(screen, WHITE if hov_back else DIM, br, fill=PANEL_HL if hov_back else PANEL, radius=8)
    text(screen, font_big, "BACK", WHITE, br.centerx, br.centery, "center")
    
def settings_click(game: Game, mx, my) -> bool:
    bw, bh = 300, 40
    bx = W//2 - bw//2
    
    fs_rect = pygame.Rect(bx, H//2 - 80, bw, bh)
    if fs_rect.collidepoint(mx, my):
        game.fullscreen = not game.fullscreen
        apply_display_settings(game)
        game.save()
        play_sfx("click")
        return True
        
    res_rect = pygame.Rect(bx, H//2 - 20, bw, bh)
    if res_rect.collidepoint(mx, my):
        game.res_idx = (game.res_idx + 1) % len(RESOLUTIONS)
        apply_display_settings(game)
        game.save()
        play_sfx("click")
        return True
        
    fps_rect = pygame.Rect(bx, H//2 + 40, bw, bh)
    if fps_rect.collidepoint(mx, my):
        game.fps_idx = (game.fps_idx + 1) % len(FPS_LIMITS)
        apply_display_settings(game)
        game.save()
        play_sfx("click")
        return True
        
    back_rect = pygame.Rect(bx, H//2 + 120, bw, 50)
    if back_rect.collidepoint(mx, my):
        game.state = "menu"
        play_sfx("click")
        return True
        
    return False

# ── Exit Confirm ──────────────────────────────────────────────────────

def draw_exit_confirm(game: Game):
    mx, my = pygame.mouse.get_pos()
    dw, dh = 400, 200
    dx = W//2 - dw//2
    dy = H//2 - dh//2
    
    # Dunkler Hintergrund-Overlay (optional, falls gewünscht)
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    draw_rect_border(screen, RED_C, (dx, dy, dw, dh), fill=(15, 10, 15), radius=12)
    text(screen, font_xl, "Wirklich beenden?", RED_C, dx+dw//2, dy+30, "midtop")
    text(screen, font_small, "Fortschritt wird automatisch gespeichert.", DIM, dx+dw//2, dy+75, "midtop")
    
    bw, bh = 140, 50
    
    # YES Button
    yes_rect = pygame.Rect(dx + 40, dy + 120, bw, bh)
    hov_yes = yes_rect.collidepoint(mx, my)
    yr = yes_rect.inflate(8, 8) if hov_yes else yes_rect
    draw_rect_border(screen, WHITE if hov_yes else RED_C, yr, fill=(60,10,10) if hov_yes else PANEL, radius=8)
    text(screen, font_big, "JA", WHITE, yr.centerx, yr.centery, "center")
    
    # NO Button
    no_rect = pygame.Rect(dx + dw - bw - 40, dy + 120, bw, bh)
    hov_no = no_rect.collidepoint(mx, my)
    nr = no_rect.inflate(8, 8) if hov_no else no_rect
    draw_rect_border(screen, WHITE if hov_no else GREEN_C, nr, fill=PANEL_HL if hov_no else PANEL, radius=8)
    text(screen, font_big, "NEIN", WHITE, nr.centerx, nr.centery, "center")

def exit_confirm_click(game: Game, mx, my) -> bool:
    dw, dh = 400, 200
    dx = W//2 - dw//2
    dy = H//2 - dh//2
    bw, bh = 140, 50
    
    yes_rect = pygame.Rect(dx + 40, dy + 120, bw, bh)
    if yes_rect.collidepoint(mx, my):
        game.save()
        pygame.quit()
        sys.exit()
        
    no_rect = pygame.Rect(dx + dw - bw - 40, dy + 120, bw, bh)
    if no_rect.collidepoint(mx, my):
        game.state = "menu"
        play_sfx("click")
        return True
        
    return False

# ── Debug Menü ────────────────────────────────────────────────────────

def draw_debug_menu(game: Game):
    if not game.show_debug: return
    dw, dh = 300, 50 + len(EVENTS) * 40 + 150
    dx = W//2 - dw//2
    dy = H//2 - dh//2
    draw_rect_border(screen, RED_C, (dx, dy, dw, dh), fill=(10,10,15), radius=10)
    text(screen, font_big, "DEBUG MENU (Events)", RED_C, dx+dw//2, dy+10, "midtop")

    for i, ev in enumerate(EVENTS):
        btn_y = dy + 50 + i * 40
        btn_rect = pygame.Rect(dx+20, btn_y, dw-40, 30)
        draw_rect_border(screen, ev["col"], btn_rect, fill=PANEL_HL, radius=5)
        text(screen, font_med, ev["name"], WHITE, btn_rect.centerx, btn_rect.centery, "center")

    hs_y = dy + 50 + len(EVENTS) * 40 + 10
    hs_rect = pygame.Rect(dx+20, hs_y, dw-40, 30)
    draw_rect_border(screen, CYAN_C, hs_rect, fill=PANEL_HL, radius=5)
    hs_label = "TCP-Handshake (laeuft)" if game.hs_state else "TCP-Handshake triggern"
    text(screen, font_med, hs_label, WHITE, hs_rect.centerx, hs_rect.centery, "center")

    give_y = dy + 50 + len(EVENTS) * 40 + 50
    give_rect = pygame.Rect(dx+20, give_y, dw-40, 30)
    draw_rect_border(screen, GOLD, give_rect, fill=PANEL_HL, radius=5)
    text(screen, font_med, "+1 Mrd. Pakete", WHITE, give_rect.centerx, give_rect.centery, "center")

    reset_y = dy + 50 + len(EVENTS) * 40 + 90
    reset_rect = pygame.Rect(dx+20, reset_y, dw-40, 30)
    draw_rect_border(screen, RED_C, reset_rect, fill=(60,10,10), radius=5)
    text(screen, font_med, "HARD RESET (Wipe Save)", WHITE, reset_rect.centerx, reset_rect.centery, "center")

    text(screen, font_small, "Druecke F12 zum Schliessen", DIM, dx+dw//2, dy+dh-25, "midtop")

def debug_click(game: Game, mx, my) -> bool:
    if not game.show_debug: return False
    dw, dh = 300, 50 + len(EVENTS) * 40 + 150
    dx = W//2 - dw//2
    dy = H//2 - dh//2

    if dx <= mx <= dx+dw and dy <= my <= dy+dh:
        for i, ev in enumerate(EVENTS):
            btn_y = dy + 50 + i * 40
            btn_rect = pygame.Rect(dx+20, btn_y, dw-40, 30)
            if btn_rect.collidepoint(mx, my):
                game.event = dict(ev)
                dur = ev["dur"]
                if ev.get("negative") and dur > 0:
                    dur = max(1, int(dur * game.fx["neg_dur"]))
                    play_sfx('event_neg')
                else:
                    play_sfx('event_pos')
                game.event_until = pygame.time.get_ticks() + dur * 1000
                game.show_debug = False
                return True

        hs_y = dy + 50 + len(EVENTS) * 40 + 10
        hs_rect = pygame.Rect(dx+20, hs_y, dw-40, 30)
        if hs_rect.collidepoint(mx, my):
            now = pygame.time.get_ticks()
            game.hs_perfects = 0
            game._hs_start_phase("syn", now)
            game.hs_next  = now + HS_TRAVEL_MS  # blockt Auto-Spawn waehrend laeuft
            play_sfx('event_pos')
            game.show_debug = False
            return True

        give_y = dy + 50 + len(EVENTS) * 40 + 50
        give_rect = pygame.Rect(dx+20, give_y, dw-40, 30)
        if give_rect.collidepoint(mx, my):
            amt = 1_000_000_000.0
            game.packets       += amt
            game.total_packets += amt
            game.floats.append(FloatingText(LEFT_W//2, 200, "+1.00B Pakete", GOLD))
            play_sfx('prestige')
            game.show_debug = False
            return True

        reset_y = dy + 50 + len(EVENTS) * 40 + 90
        reset_rect = pygame.Rect(dx+20, reset_y, dw-40, 30)
        if reset_rect.collidepoint(mx, my):
            now = pygame.time.get_ticks()
            game.packets = 0.0
            game.total_packets = 0.0
            game.owned = {}
            game.prestige = 0
            game.prestige_mult = 1.0
            game.rfc_points = 0.0
            game.research_done = set()
            game.event = None
            game.next_event = now + 45_000
            game.unlocked = set()
            game.minigame = None
            game.challenge_cooldown = {}
            game.rfc_unlocked = False
            game.show_rfc_intro = False
            game.show_intro = True
            game.intro_page = 0
            game.tab = "upgrades"
            game.hs_state = None
            game.hs_combo = 0
            game.hs_perfects = 0
            game.hs_started = 0
            game.hs_next = now + 60_000
            game.click_buff_until = 0
            game.confirm_prestige = False
            game.state = "menu"
            game._invalidate_fx()
            game.save()
            play_sfx('error')
            game.show_debug = False
            return True

        return True # Intercept click in menu but not on button
    return False
# ── Hauptschleife ─────────────────────────────────────────────────────

def play_intro_video(path):
    if not _CV2_AVAILABLE or not os.path.exists(path):
        return False
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    start_bgm()
    clock_intro = pygame.time.Clock()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        skip = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                pygame.quit()
                sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                skip = True
        if skip:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]
        surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        scaled = pygame.transform.scale(surf, (W, H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock_intro.tick(fps)
    cap.release()
    return True

def main():
    intro_played = play_intro_video(_asset("abcdef_abcdef_abcdef_abcdefmp_.mp4"))
    game     = Game()
    net      = NetViz(LEFT_W//2, 335, 90)
    menu_bg  = MenuBackground()
    max_scroll_shop = max(0, len(UPGRADES)*74 + 150 - (H-42))
    if not intro_played:
        start_bgm()

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == MUSIC_END:
                _start_bgm_loop()

            if event.type == pygame.QUIT:
                game.state = "exit_confirm"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12 and game.state == "playing":
                    game.show_debug = not game.show_debug
                if event.key == pygame.K_ESCAPE:
                    if game.state == "playing":
                        if game.show_intro:
                            game.show_intro = False
                            game.save()
                        elif game.show_rfc_intro:
                            game.show_rfc_intro = False
                            game.save()
                        elif game.minigame is not None:
                            game.abort_minigame()
                        else:
                            game.state = "menu"
                    elif game.state == "settings":
                        game.state = "menu"
                    elif game.state == "exit_confirm":
                        game.state = "menu"
                    else:
                        game.state = "exit_confirm"
                if event.key == pygame.K_SPACE and game.state == "playing":
                    if game.minigame is None:
                        mx, my = pygame.mouse.get_pos()
                        if mx < LEFT_W:
                            game.click(mx, my)

                if game.state == "playing" and game.minigame is not None:
                    mg_type = game.minigame.get("type")
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        if mg_type == "packet_inspector":
                            game.pi_decide("allow")
                        else:
                            game.mg_move(-1)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        if mg_type == "packet_inspector":
                            game.pi_decide("drop")
                        else:
                            game.mg_move(+1)
                    elif event.key == pygame.K_1:
                        game.rt_click(0)
                    elif event.key == pygame.K_2:
                        game.rt_click(1)
                    elif event.key == pygame.K_3:
                        game.rt_click(2)

            if event.type == pygame.MOUSEWHEEL and game.state == "playing":
                if game.tab == "upgrades":
                    game.shop_scroll = min(max_scroll_shop, max(0, game.shop_scroll - event.y * 40))

            if event.type == pygame.MOUSEMOTION and game.state == "playing":
                if game.minigame is not None:
                    minigame_motion(game, event.pos)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if game.state == "playing" and game.minigame is not None:
                    minigame_release(game, event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    if game.state == "exit_confirm":
                        exit_confirm_click(game, mx, my)
                        continue
                    elif game.state == "menu":
                        menu_click(game, mx, my)
                        continue
                    elif game.state == "settings":
                        settings_click(game, mx, my)
                        continue

                    if debug_click(game, mx, my):
                        continue

                    # Einführungs-Popup blockt alle anderen Klicks
                    if intro_click(game, mx, my):
                        continue

                    # RFC-Intro-Popup blockt alle anderen Klicks
                    if rfc_intro_click(game, mx, my):
                        continue

                    # Aktives Minigame fängt alle Klicks ab
                    if game.minigame is not None:
                        minigame_click(game, mx, my)
                        continue

                    hit_ddos = False
                    for p in game.ddos_packets:
                        if math.hypot(mx - p.x, my - p.y) < p.radius + 5:
                            game.ddos_packets.remove(p)
                            game.event_until -= 1500  # Reduziere Event-Dauer um 1.5s
                            game.floats.append(FloatingText(mx, my, "Filtered!", GREEN_C))
                            play_sfx('click')
                            hit_ddos = True
                            break

                    if hit_ddos:
                        continue

                    # TCP-Handshake: Hit-Test auf fliegendes Paket
                    if game.try_hs_click(mx, my):
                        continue

                    # Tab-Wechsel
                    for tid, rect in TAB_RECTS.items():
                        if rect.collidepoint(mx, my):
                            if tid == "research" and not game.rfc_unlocked:
                                play_sfx('error')
                            else:
                                game.tab = tid
                                game.confirm_prestige = False
                            break
                    else:
                        if mx < LEFT_W:
                            if prestige_click(game, mx, my):
                                pass  # prestige_click handles confirmation logic internally
                            else:
                                game.confirm_prestige = False
                                cx, cy = LEFT_W//2, 335
                                if math.hypot(mx-cx, my-cy) < 112:
                                    game.click(mx, my)
                        else:
                            game.confirm_prestige = False
                            if game.tab == "upgrades":
                                shop_click(game, mx, my)
                            else:
                                research_click(game, mx, my)

                if event.button == 4 and game.state == "playing":
                    if game.tab == "upgrades":
                        game.shop_scroll = max(0, game.shop_scroll - 40)
                if event.button == 5 and game.state == "playing":
                    if game.tab == "upgrades":
                        game.shop_scroll = min(max_scroll_shop, game.shop_scroll + 40)

        if game.state == "playing":
            game.update(dt)
            net.update(dt)

            draw_background(game)
            draw_left(game, net)
            draw_tabs(game)

            if game.tab == "upgrades":
                draw_shop(game)
            else:
                draw_research(game)

            for p in game.ddos_packets:
                p.draw(screen)

            if game.minigame is not None:
                draw_minigame(game)

            draw_rfc_intro(game)
            draw_intro(game)

            draw_debug_menu(game)
        else:
            menu_bg.update(dt)
            menu_bg.draw(screen)
            if game.state in ("menu", "exit_confirm"):
                draw_main_menu(game)
                if game.state == "exit_confirm":
                    draw_exit_confirm(game)
            elif game.state == "settings":
                draw_settings_menu(game)

        pygame.display.flip()

if __name__ == "__main__":
    main()
