import streamlit as st
import json
import math
import re
import random
import os
from pathlib import Path
try:
    from anthropic import Anthropic as _Anthropic
    _ai_key = os.environ.get("ANTHROPIC_API_KEY")
    _ai_client = _Anthropic(api_key=_ai_key) if _ai_key else None
except Exception:
    _ai_client = None
    _ai_key = None

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ryndor: Character Maker",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data
def load_races():
    with open(DATA_DIR / "races.json") as f:
        return json.load(f)["races"]

@st.cache_data
def load_classes():
    with open(DATA_DIR / "classes.json") as f:
        classes = json.load(f)["classes"]
    try:
        with open(DATA_DIR / "srd_subclasses.json") as f:
            srd = json.load(f)
        for cls in classes:
            srd_subs = srd.get(cls["id"], [])
            if srd_subs:
                cls["subclasses"] = cls["subclasses"] + srd_subs
    except FileNotFoundError:
        pass
    return classes

@st.cache_data
def load_backgrounds():
    with open(DATA_DIR / "backgrounds.json") as f:
        ryndor = json.load(f)["backgrounds"]
    for b in ryndor:
        b.setdefault("source", "Ryndor")
    try:
        with open(DATA_DIR / "srd_backgrounds.json") as f:
            srd = json.load(f)["backgrounds"]
    except FileNotFoundError:
        srd = []
    return ryndor + srd

@st.cache_data
def load_class_mechanics():
    with open(DATA_DIR / "class_mechanics.json") as f:
        return json.load(f)

@st.cache_data
def load_class_features():
    with open(DATA_DIR / "class_features.json") as f:
        return json.load(f)

@st.cache_data
def load_srd_items():
    with open(DATA_DIR / "srd_items.json") as f:
        return json.load(f)

@st.cache_data
def load_srd_spells():
    try:
        with open(DATA_DIR / "srd_spells.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@st.cache_data
def load_srd_feats():
    try:
        with open(DATA_DIR / "srd_feats.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

RACES = load_races()
CLASSES = load_classes()
BACKGROUNDS = load_backgrounds()
CLASS_MECHANICS = load_class_mechanics()
CLASS_FEATURES = load_class_features()
SRD_ITEMS = load_srd_items()
SRD_SPELLS = load_srd_spells()
SRD_FEATS  = load_srd_feats()

# ASI level schedules (levels at which a class gains Ability Score Improvement)
ASI_LEVELS = {
    "fighter": [4, 6, 8, 12, 14, 16, 19],
    "rogue":   [4, 8, 10, 12, 16, 19],
}
DEFAULT_ASI_LEVELS = [4, 8, 12, 16, 19]

# ── Spell slot tables (SRD constants) ─────────────────────────────────────────
# Index = level-1. Each inner list: [1st,2nd,3rd,4th,5th,6th,7th,8th,9th] slots.
FULL_CASTER_SLOTS = [
    [2,0,0,0,0,0,0,0,0],[3,0,0,0,0,0,0,0,0],[4,2,0,0,0,0,0,0,0],[4,3,0,0,0,0,0,0,0],
    [4,3,2,0,0,0,0,0,0],[4,3,3,0,0,0,0,0,0],[4,3,3,1,0,0,0,0,0],[4,3,3,2,0,0,0,0,0],
    [4,3,3,3,1,0,0,0,0],[4,3,3,3,2,0,0,0,0],[4,3,3,3,2,1,0,0,0],[4,3,3,3,2,1,0,0,0],
    [4,3,3,3,2,1,1,0,0],[4,3,3,3,2,1,1,0,0],[4,3,3,3,2,1,1,1,0],[4,3,3,3,2,1,1,1,0],
    [4,3,3,3,2,1,1,1,1],[4,3,3,3,3,1,1,1,1],[4,3,3,3,3,2,1,1,1],[4,3,3,3,3,2,2,1,1],
]
HALF_CASTER_SLOTS = [
    [0,0,0,0,0],[2,0,0,0,0],[3,0,0,0,0],[3,0,0,0,0],[4,2,0,0,0],
    [4,2,0,0,0],[4,3,0,0,0],[4,3,0,0,0],[4,3,2,0,0],[4,3,2,0,0],
    [4,3,3,0,0],[4,3,3,0,0],[4,3,3,1,0],[4,3,3,1,0],[4,3,3,2,0],
    [4,3,3,2,0],[4,3,3,3,1],[4,3,3,3,1],[4,3,3,3,2],[4,3,3,3,2],
]
# Warlock: [slot_count, slot_level]
PACT_SLOTS = [
    [1,1],[2,1],[2,2],[2,2],[2,3],[2,3],[2,4],[2,4],
    [2,5],[2,5],[3,5],[3,5],[3,5],[3,5],[3,5],[3,5],
    [4,5],[4,5],[4,5],[4,5],
]
ALL_SKILLS = [
    ("Acrobatics",    "DEX"), ("Animal Handling", "WIS"), ("Arcana",       "INT"),
    ("Athletics",     "STR"), ("Deception",       "CHA"), ("History",      "INT"),
    ("Insight",       "WIS"), ("Intimidation",    "CHA"), ("Investigation","INT"),
    ("Medicine",      "WIS"), ("Nature",          "INT"), ("Perception",   "WIS"),
    ("Performance",   "CHA"), ("Persuasion",      "CHA"), ("Religion",     "INT"),
    ("Sleight of Hand","DEX"),("Stealth",         "DEX"), ("Survival",     "WIS"),
]

# ── Languages ─────────────────────────────────────────────────────────────────
RYNDOR_LANGUAGES = ["Auran", "Drakarim", "Inglishmek", "Leoporin", "Sylvan"]
SRD_LANGUAGES = [
    "Common", "Dwarvish", "Elvish", "Giant", "Gnomish", "Goblin", "Halfling", "Orc",
    "Abyssal", "Celestial", "Deep Speech", "Draconic", "Infernal", "Primordial", "Undercommon",
]
ALL_LANGUAGES = sorted(set(RYNDOR_LANGUAGES + SRD_LANGUAGES))

# ── Optimal stat priority per class ───────────────────────────────────────────
# Order: highest priority stat first. Standard Array [15,14,13,12,10,8] assigned in this order.
CLASS_STAT_PRIORITY = {
    "barbarian": ["STR", "CON", "DEX", "WIS", "CHA", "INT"],
    "bard":      ["CHA", "DEX", "CON", "WIS", "INT", "STR"],
    "cleric":    ["WIS", "CON", "STR", "CHA", "INT", "DEX"],
    "druid":     ["WIS", "CON", "INT", "DEX", "CHA", "STR"],
    "fighter":   ["STR", "CON", "DEX", "WIS", "INT", "CHA"],
    "monk":      ["DEX", "WIS", "CON", "STR", "INT", "CHA"],
    "paladin":   ["STR", "CHA", "CON", "WIS", "DEX", "INT"],
    "ranger":    ["DEX", "WIS", "CON", "STR", "INT", "CHA"],
    "rogue":     ["DEX", "CON", "INT", "WIS", "CHA", "STR"],
    "sorcerer":  ["CHA", "CON", "DEX", "WIS", "INT", "STR"],
    "warlock":   ["CHA", "CON", "DEX", "WIS", "INT", "STR"],
    "wizard":    ["INT", "CON", "DEX", "WIS", "CHA", "STR"],
    "artificer": ["INT", "CON", "DEX", "WIS", "CHA", "STR"],
    "sevrinn":   ["CON", "DEX", "WIS", "STR", "INT", "CHA"],
}
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────
STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=IM+Fell+English:ital@0;1&display=swap');

/* ── Root Theme — The Weirding ── */
:root {
    --void:       #040010;
    --deep:       #080118;
    --rift:       #120630;
    --weird:      #7c3aed;
    --weird-glow: #a78bfa;
    --weird-dim:  rgba(124,58,237,0.12);
    --elem:       #22d3ee;
    --elem-glow:  #67e8f9;
    --ember:      #f59e0b;
    --ember-glow: #fcd34d;
    --rune:       #10b981;
    --soul:       #f472b6;
    --text:       #e2d9f3;
    --text-dim:   #a99cbf;
    --text-mute:  #4e3d6e;
    --shadow:     rgba(4,0,16,0.7);
}

/* ── Global resets ── */
html, body, [class*="css"] {
    font-family: 'Crimson Text', Georgia, serif;
    background-color: var(--void) !important;
    color: var(--text) !important;
}
.stApp {
    background:
        radial-gradient(ellipse 70% 50% at 10% 5%,  rgba(124,58,237,0.14) 0%, transparent 65%),
        radial-gradient(ellipse 50% 40% at 90% 85%, rgba(34,211,238,0.09) 0%, transparent 65%),
        radial-gradient(ellipse 80% 80% at 50% 50%, #04000f 0%, #020008 100%) !important;
    min-height: 100vh;
}
.block-container { padding-top: 1rem !important; max-width: 1100px; }

/* ── Headings ── */
h1, h2, h3, h4, .cinzel { font-family: 'Cinzel', serif !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: var(--weird); border-radius: 3px; }

/* ── Step progress bar ── */
.step-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 1rem auto 2rem;
    max-width: 800px;
}
.step-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    cursor: default;
}
.step-circle {
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 2px solid var(--text-mute);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Cinzel', serif;
    font-size: 13px;
    font-weight: 700;
    color: var(--text-mute);
    background: var(--void);
    transition: all .35s;
}
.step-circle.active {
    border-color: var(--weird);
    color: var(--weird-glow);
    background: rgba(124,58,237,0.15);
    box-shadow: 0 0 16px rgba(124,58,237,0.6), 0 0 32px rgba(124,58,237,0.2), inset 0 0 12px rgba(124,58,237,0.1);
}
.step-circle.done {
    border-color: var(--elem);
    color: var(--elem-glow);
    background: rgba(34,211,238,0.08);
    box-shadow: 0 0 8px rgba(34,211,238,0.25);
}
.step-label {
    font-family: 'Cinzel', serif;
    font-size: 8px;
    letter-spacing: 0.1em;
    color: var(--text-mute);
    text-align: center;
    text-transform: uppercase;
    opacity: 0.9;
}
.step-label.active { color: var(--weird-glow); opacity: 1; }
.step-label.done   { color: var(--elem);        opacity: 0.85; }
.step-connector {
    width: 48px; height: 2px;
    background: var(--text-mute);
    opacity: 0.25;
    margin-bottom: 20px;
}
.step-connector.done {
    background: linear-gradient(90deg, var(--elem), var(--weird));
    opacity: 0.55;
}

/* ── Page title ── */
.page-title {
    text-align: center;
    padding: 1.5rem 0 0.5rem;
}
.page-title h1 {
    font-family: 'Cinzel', serif !important;
    font-size: 2.6rem;
    font-weight: 900;
    background: linear-gradient(135deg, var(--ember-glow) 0%, var(--weird-glow) 50%, var(--elem-glow) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 18px rgba(124,58,237,0.55));
    letter-spacing: 0.1em;
    margin: 0;
}
.page-title p {
    font-family: 'IM Fell English', 'Crimson Text', serif;
    font-style: italic;
    color: var(--text-dim);
    font-size: 1.05rem;
    margin: 0.3rem 0 0;
    letter-spacing: 0.04em;
}

/* ── Card ── */
.card {
    background: linear-gradient(145deg, rgba(124,58,237,0.07) 0%, rgba(8,1,24,0.97) 45%, rgba(34,211,238,0.04) 100%);
    border: 1px solid rgba(124,58,237,0.28);
    border-radius: 6px;
    padding: 1.5rem;
    margin: 0.5rem 0;
    box-shadow: 0 4px 30px var(--shadow), 0 0 0 0.5px rgba(124,58,237,0.08), inset 0 0 50px rgba(0,0,0,0.45);
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--weird), var(--elem), transparent);
    opacity: 0.65;
}

/* ── Selection card (clickable) ── */
.sel-card {
    background: linear-gradient(145deg, rgba(124,58,237,0.06) 0%, rgba(8,1,24,0.95) 100%);
    border: 1px solid rgba(124,58,237,0.22);
    border-radius: 5px;
    padding: 1rem 1.2rem;
    margin: 0.4rem 0;
    cursor: pointer;
    transition: all .25s;
    position: relative;
}
.sel-card:hover {
    border-color: rgba(124,58,237,0.55);
    background: linear-gradient(145deg, rgba(124,58,237,0.12) 0%, rgba(34,211,238,0.04) 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 22px rgba(124,58,237,0.18), 0 0 0 0.5px rgba(124,58,237,0.3);
}
.sel-card.selected {
    border-color: var(--weird);
    background: linear-gradient(145deg, rgba(124,58,237,0.16) 0%, rgba(8,1,24,0.95) 100%);
    box-shadow: 0 0 0 1px var(--weird), 0 4px 28px rgba(124,58,237,0.28), inset 0 0 30px rgba(124,58,237,0.06);
}
.sel-card h3 {
    font-family: 'Cinzel', serif;
    color: var(--weird-glow);
    font-size: 1.05rem;
    margin: 0 0 0.3rem;
}
.sel-card p {
    font-family: 'Crimson Text', serif;
    color: var(--text-dim);
    font-size: 0.95rem;
    margin: 0;
    line-height: 1.4;
}
.sel-card .icon { font-size: 1.8rem; margin-bottom: 0.3rem; }

/* ── Trait block ── */
.trait-block {
    background: rgba(124,58,237,0.05);
    border-left: 2px solid var(--weird);
    border-radius: 0 4px 4px 0;
    padding: 0.6rem 1rem;
    margin: 0.4rem 0;
}
.trait-block .name {
    font-family: 'Cinzel', serif;
    color: var(--weird-glow);
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 0.2rem;
}
.trait-block .desc {
    font-family: 'Crimson Text', serif;
    color: var(--text-dim);
    font-size: 0.95rem;
    line-height: 1.5;
}

/* ── Ability score box ── */
.stat-box {
    background: linear-gradient(180deg, rgba(124,58,237,0.12) 0%, rgba(4,0,16,0.95) 100%);
    border: 1px solid rgba(124,58,237,0.45);
    border-radius: 5px;
    text-align: center;
    padding: 0.8rem 0.4rem;
    box-shadow: 0 0 12px rgba(124,58,237,0.12), inset 0 0 20px rgba(0,0,0,0.35);
}
.stat-box .stat-name {
    font-family: 'Cinzel', serif;
    font-size: 0.62rem;
    font-weight: 700;
    color: var(--elem);
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.stat-box .stat-val {
    font-family: 'Cinzel', serif;
    font-size: 2.2rem;
    font-weight: 900;
    color: var(--text);
    line-height: 1.1;
    text-shadow: 0 0 12px rgba(167,139,250,0.55);
}
.stat-box .stat-mod {
    font-family: 'Cinzel', serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--weird-glow);
    background: rgba(124,58,237,0.22);
    border-radius: 50%;
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    margin: 0.3rem auto 0;
    box-shadow: 0 0 8px rgba(124,58,237,0.3);
}

/* ── Section headers ── */
.section-header {
    font-family: 'Cinzel', serif;
    color: var(--weird-glow);
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(124,58,237,0.3);
    padding-bottom: 0.4rem;
    margin: 1.2rem 0 0.8rem;
}

/* ── Info badge ── */
.badge {
    display: inline-block;
    background: rgba(124,58,237,0.12);
    border: 1px solid rgba(124,58,237,0.35);
    border-radius: 2px;
    padding: 2px 8px;
    font-family: 'Cinzel', serif;
    font-size: 0.72rem;
    color: var(--weird-glow);
    letter-spacing: 0.05em;
    margin: 2px;
}
.badge.teal {
    background: rgba(34,211,238,0.1);
    border-color: rgba(34,211,238,0.35);
    color: var(--elem-glow);
}
.badge.crimson {
    background: rgba(245,158,11,0.1);
    border-color: rgba(245,158,11,0.3);
    color: var(--ember-glow);
}

/* ── Character sheet ── */
.sheet-header {
    background: linear-gradient(180deg, rgba(124,58,237,0.18) 0%, rgba(4,0,16,0.98) 100%);
    border: 1px solid rgba(124,58,237,0.5);
    border-radius: 6px 6px 0 0;
    padding: 2rem;
    text-align: center;
    position: relative;
    box-shadow: 0 0 60px rgba(124,58,237,0.12), inset 0 0 40px rgba(0,0,0,0.4);
}
.sheet-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--weird), var(--elem), var(--ember), transparent);
    opacity: 0.8;
}
.sheet-header .char-name {
    font-family: 'Cinzel', serif;
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, var(--ember-glow) 0%, var(--weird-glow) 50%, var(--elem-glow) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 18px rgba(124,58,237,0.55));
    letter-spacing: 0.1em;
}
.sheet-header .char-sub {
    font-family: 'Crimson Text', serif;
    font-style: italic;
    color: var(--text-dim);
    font-size: 1.2rem;
    margin-top: 0.3rem;
}
.sheet-divider {
    border: none;
    border-top: 1px solid rgba(124,58,237,0.2);
    margin: 1rem 0;
}
.sheet-section {
    background: linear-gradient(160deg, rgba(124,58,237,0.06) 0%, rgba(4,0,16,0.97) 100%);
    border: 1px solid rgba(124,58,237,0.18);
    border-radius: 4px;
    padding: 1.2rem 1.5rem;
    margin: 0.6rem 0;
}
.sheet-section-title {
    font-family: 'Cinzel', serif;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--weird-glow);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    border-bottom: 1px solid rgba(124,58,237,0.2);
    padding-bottom: 0.4rem;
}
.feat-row {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    margin: 0.4rem 0;
}
.feat-row .fname {
    font-family: 'Cinzel', serif;
    color: var(--elem-glow);
    font-size: 0.9rem;
    font-weight: 600;
    min-width: 180px;
}
.feat-row .fdesc {
    font-family: 'Crimson Text', serif;
    color: var(--text-dim);
    font-size: 0.95rem;
    line-height: 1.5;
    flex: 1;
    opacity: 0.9;
}

/* ── Navigation buttons ── */
.stButton > button {
    font-family: 'Cinzel', serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    border-radius: 3px !important;
    transition: all .25s !important;
    border-color: rgba(124,58,237,0.4) !important;
    color: var(--text-dim) !important;
    background: rgba(124,58,237,0.08) !important;
}
.stButton > button:hover {
    border-color: var(--weird) !important;
    background: rgba(124,58,237,0.18) !important;
    color: var(--weird-glow) !important;
    box-shadow: 0 0 14px rgba(124,58,237,0.25) !important;
}
div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(124,58,237,0.35), rgba(34,211,238,0.12)) !important;
    border: 1px solid var(--weird) !important;
    color: var(--weird-glow) !important;
    box-shadow: 0 0 16px rgba(124,58,237,0.2) !important;
}
div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, rgba(124,58,237,0.5), rgba(34,211,238,0.2)) !important;
    box-shadow: 0 0 24px rgba(124,58,237,0.35) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: rgba(8,1,24,0.9) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: var(--text) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 1rem !important;
}
.stTextInput label, .stSelectbox label, .stNumberInput label {
    font-family: 'Cinzel', serif !important;
    font-size: 0.78rem !important;
    color: var(--weird-glow) !important;
    letter-spacing: 0.08em !important;
}
.stRadio > div { gap: 0.5rem !important; }

/* ── Expander ── */
details {
    background: rgba(8,1,24,0.8) !important;
    border: 1px solid rgba(124,58,237,0.2) !important;
    border-radius: 3px !important;
}
summary {
    font-family: 'Cinzel', serif !important;
    color: var(--weird-glow) !important;
    font-size: 0.88rem !important;
    padding: 0.5rem !important;
}

/* ── Alert ── */
.ryndor-alert {
    background: rgba(245,158,11,0.1);
    border: 1px solid rgba(245,158,11,0.35);
    border-radius: 3px;
    padding: 0.8rem 1rem;
    font-family: 'Crimson Text', serif;
    color: var(--ember-glow);
    font-size: 0.95rem;
    margin: 0.5rem 0;
}

/* ── Weirding surge table ── */
.surge-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Crimson Text', serif;
}
.surge-table th {
    font-family: 'Cinzel', serif;
    font-size: 0.75rem;
    color: var(--weird-glow);
    letter-spacing: 0.08em;
    text-align: left;
    border-bottom: 1px solid rgba(124,58,237,0.3);
    padding: 0.4rem 0.6rem;
}
.surge-table td {
    padding: 0.4rem 0.6rem;
    color: var(--text-dim);
    font-size: 0.95rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.surge-table td:first-child {
    font-family: 'Cinzel', serif;
    color: var(--elem-glow);
    font-weight: 700;
    width: 40px;
}

/* ── Text area ── */
.stTextArea > div > div > textarea {
    background: rgba(8,1,24,0.9) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: var(--text) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: var(--weird) !important;
    box-shadow: 0 0 8px rgba(124,58,237,0.25) !important;
}
.stTextArea label {
    font-family: 'Cinzel', serif !important;
    font-size: 0.78rem !important;
    color: var(--weird-glow) !important;
    letter-spacing: 0.08em !important;
}

/* ── Number input: nuclear override ── */
input[type="number"],
input[type="number"]:focus,
input[type="number"]:hover {
    background-color: rgba(8,1,24,0.9) !important;
    background: rgba(8,1,24,0.9) !important;
    color: var(--text) !important;
    border-color: rgba(124,58,237,0.3) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 1rem !important;
}
/* All Base Web input wrappers */
[data-baseweb="input"],
[data-baseweb="input"] > div,
[data-baseweb="input"] > div > div {
    background-color: rgba(8,1,24,0.9) !important;
    background: rgba(8,1,24,0.9) !important;
    border-color: rgba(124,58,237,0.3) !important;
}
[data-baseweb="input"] input {
    background-color: transparent !important;
    background: transparent !important;
    color: var(--text) !important;
    font-family: 'Crimson Text', serif !important;
}
/* Number input container at every nesting level */
.stNumberInput > div > div,
.stNumberInput > div > div > div,
[data-testid="stNumberInput"] > div,
[data-testid="stNumberInput"] > div > div,
[data-testid="stNumberInput"] > div > div > div {
    background-color: rgba(8,1,24,0.9) !important;
    background: rgba(8,1,24,0.9) !important;
    border-color: rgba(124,58,237,0.3) !important;
}
.stNumberInput button {
    background: rgba(124,58,237,0.1) !important;
    border-color: rgba(124,58,237,0.3) !important;
    color: var(--weird-glow) !important;
}
.stNumberInput button:hover {
    background: rgba(124,58,237,0.25) !important;
    color: var(--elem-glow) !important;
}

/* ── Selectbox dropdown ── */
.stSelectbox > div > div {
    background: rgba(8,1,24,0.9) !important;
}
[data-baseweb="select"] * { background: rgba(8,1,24,0.95) !important; color: var(--text) !important; }
[data-baseweb="popover"] { background: rgba(8,1,24,0.98) !important; border: 1px solid rgba(124,58,237,0.4) !important; }
[data-baseweb="menu"] { background: rgba(8,1,24,0.98) !important; }
[role="option"] { color: var(--text-dim) !important; }
[role="option"]:hover, [aria-selected="true"] { background: rgba(124,58,237,0.18) !important; color: var(--weird-glow) !important; }

/* ── Multiselect ── */
.stMultiSelect > div > div {
    background: rgba(8,1,24,0.9) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: var(--text) !important;
}
.stMultiSelect label {
    font-family: 'Cinzel', serif !important;
    font-size: 0.78rem !important;
    color: var(--weird-glow) !important;
    letter-spacing: 0.08em !important;
}
[data-baseweb="tag"] {
    background: rgba(124,58,237,0.22) !important;
    border: 1px solid rgba(124,58,237,0.45) !important;
    color: var(--weird-glow) !important;
}
[data-baseweb="tag"] span { color: var(--weird-glow) !important; }

/* ── Checkbox ── */
.stCheckbox label {
    color: var(--text-dim) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 1rem !important;
}
.stCheckbox label:hover { color: var(--text) !important; }
.stCheckbox > label > div[data-testid="stMarkdownContainer"] p { color: var(--text-dim) !important; }

/* ── Radio ── */
.stRadio label { color: var(--text-dim) !important; font-family: 'Crimson Text', serif !important; }
.stRadio label:hover { color: var(--text) !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: var(--text-dim) !important; }

/* ── Streamlit header & toolbar ── */
header[data-testid="stHeader"] {
    background: rgba(4,0,16,0.96) !important;
    border-bottom: 1px solid rgba(124,58,237,0.18) !important;
    backdrop-filter: blur(8px) !important;
}
header[data-testid="stHeader"] button,
[data-testid="stToolbar"] button,
[data-testid="stToolbarActions"] button,
button[data-testid="baseButton-header"],
button[data-testid="baseButton-headerNoPadding"] {
    color: var(--text-mute) !important;
    background: transparent !important;
    border: none !important;
}
header[data-testid="stHeader"] button:hover,
[data-testid="stToolbar"] button:hover,
button[data-testid="baseButton-header"]:hover,
button[data-testid="baseButton-headerNoPadding"]:hover {
    color: var(--weird-glow) !important;
    background: rgba(124,58,237,0.12) !important;
}
/* Hide the three-dot (⋮) menu */
[data-testid="stMainMenu"] { display: none !important; }

/* Dropdown menu from toolbar */
[data-testid="stMainMenu"] ul,
[data-testid="stMainMenu"] li,
ul[data-testid="stMainMenuList"] {
    background: rgba(8,1,24,0.98) !important;
    color: var(--text-dim) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
}
[data-testid="stMainMenu"] li:hover,
ul[data-testid="stMainMenuList"] li:hover {
    background: rgba(124,58,237,0.15) !important;
    color: var(--weird-glow) !important;
}
[data-testid="stMainMenu"] span,
ul[data-testid="stMainMenuList"] span {
    color: var(--text-dim) !important;
}

/* ── All input focus rings ── */
input:focus, textarea:focus, [data-baseweb="select"]:focus-within {
    border-color: var(--weird) !important;
    box-shadow: 0 0 0 1px rgba(124,58,237,0.4) !important;
    outline: none !important;
}

/* ── Streamlit error/info/warning boxes ── */
[data-testid="stAlert"] {
    background: rgba(245,158,11,0.08) !important;
    border: 1px solid rgba(245,158,11,0.3) !important;
    color: var(--ember-glow) !important;
}
[data-testid="stAlert"][kind="error"] {
    background: rgba(239,68,68,0.1) !important;
    border-color: rgba(239,68,68,0.35) !important;
    color: #fca5a5 !important;
}

/* ── Print styles ── */
@media print {
    /* Light parchment base */
    html, body, .stApp, [class*="css"] {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        background: #f5f0e8 !important;
        color: #1a1020 !important;
    }
    .no-print { display: none !important; }

    /* Force ALL text to dark — covers CSS-class-set and inline-style colors.
       -webkit-text-fill-color overrides the gradient-clip trick on .char-name. */
    * {
        color: #1a1020 !important;
        -webkit-text-fill-color: #1a1020 !important;
    }

    /* Reset dark-background elements so dark text is readable */
    .card {
        background: transparent !important;
        border-color: rgba(124,58,237,0.25) !important;
        box-shadow: none !important;
    }
    .stat-box {
        background: #ede8f5 !important;
        border-color: rgba(124,58,237,0.45) !important;
        box-shadow: none !important;
    }
    .stat-box .stat-mod {
        background: rgba(124,58,237,0.15) !important;
        box-shadow: none !important;
    }
    .sheet-header {
        background: rgba(124,58,237,0.06) !important;
        box-shadow: none !important;
    }
    .sheet-section {
        background: #ffffff !important;
        border-color: rgba(124,58,237,0.35) !important;
        box-shadow: none !important;
    }
    .trait-block {
        background: rgba(124,58,237,0.05) !important;
    }

    /* Re-apply accent colours (visible on light bg) */
    .char-name {
        -webkit-text-fill-color: #4c1d95 !important;
        background: none !important;
        -webkit-background-clip: unset !important;
        background-clip: unset !important;
        filter: none !important;
    }
    .fname, .trait-block .name { color: #0e7490 !important; -webkit-text-fill-color: #0e7490 !important; }
    .sheet-section-title, .section-header { color: #4c1d95 !important; -webkit-text-fill-color: #4c1d95 !important; }
    .fdesc, .trait-block .desc, .char-sub { color: #3a2d50 !important; -webkit-text-fill-color: #3a2d50 !important; }
}
</style>
"""
st.markdown(STYLES, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
defaults = {
    "step": 1,
    "char_name": "",
    "player_name": "",
    "char_level": 1,
    "race_id": None,
    "class_id": None,
    "subclass_id": None,
    "background_id": None,
    "alignment": "",
    "stats": {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8},
    "stat_method": "Standard Array",
    "chosen_skills": [],
    "equip_choices": {},   # {choice_id: option_index}
    "class_options": {},   # {choice_key: selected_id or [selected_ids]}
    "expertise_skills": [],
    "chosen_languages": [],
    "draconic_ancestry": "",
    "damage_resistances": [],
    "notes": "",
    "personality": "",
    "ideals": "",
    "bonds": "",
    "flaws": "",
    "inv_weapons": [],
    "equipped_main": None,
    "equipped_offhand": None,
    "has_dual_wielder": False,
    "inv_gear": [],
    "chosen_cantrips": [],
    "chosen_spells": [],
    "asi_choices": {},
    "combat_tactics": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# RANDOM CHARACTER GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_random_character():
    race = random.choice(RACES)
    cls  = random.choice(CLASSES)
    sub  = random.choice(cls["subclasses"]) if cls.get("subclasses") else None
    bg   = random.choice(BACKGROUNDS)
    alignments = [
        "Lawful Good", "Neutral Good", "Chaotic Good",
        "Lawful Neutral", "True Neutral", "Chaotic Neutral",
        "Lawful Evil", "Neutral Evil", "Chaotic Evil",
    ]
    st.session_state.race_id       = race["id"]
    st.session_state.class_id      = cls["id"]
    st.session_state.subclass_id   = sub["id"] if sub else None
    st.session_state.background_id = bg["id"]
    st.session_state.alignment     = random.choice(alignments)
    st.session_state.char_level    = 1

    # Stats: shuffle Standard Array using class priority order
    array = [15, 14, 13, 12, 10, 8]
    random.shuffle(array)
    st.session_state.stats       = dict(zip(["STR", "DEX", "CON", "INT", "WIS", "CHA"], array))
    st.session_state.stat_method = "Standard Array"

    # Skills: random sample from class options, excluding auto-granted skills
    mech = CLASS_MECHANICS.get(cls["id"], {})
    sc   = mech.get("skill_choices", {})
    opts = sc.get("options", [])
    pick = sc.get("count", 2)
    auto = set(bg.get("skill_proficiencies", [])) | set(race.get("bonus_skills", []))
    eligible = [s for s in opts if s not in auto]
    st.session_state.chosen_skills = random.sample(eligible, min(pick, len(eligible)))

    # Equipment: random option index for each choice group
    equip = {
        ch["id"]: random.randrange(len(ch["options"]))
        for ch in mech.get("equipment_choices", [])
        if ch.get("options")
    }
    st.session_state.equip_choices = equip

    # Class options (Fighting Style, Pact Boon, etc.)
    class_opts = {}
    for ch in CLASS_FEATURES.get(cls["id"], {}).get("choices", []):
        o = ch.get("options", [])
        if o:
            class_opts[ch["key"]] = (
                [random.choice(o)["id"]] if ch.get("multi") else random.choice(o)["id"]
            )
    st.session_state.class_options = class_opts

    # Languages: fill "of your choice" slots
    race_langs = [l for l in race.get("languages", []) if "of your choice" not in l.lower()]
    bg_langs   = [l for l in bg.get("languages", [])   if "of your choice" not in l.lower()]
    auto_langs = list(dict.fromkeys(race_langs + bg_langs))
    slots = sum(
        1 for l in race.get("languages", []) + bg.get("languages", [])
        if "of your choice" in l.lower()
    )
    pool = [l for l in ALL_LANGUAGES if l not in auto_langs]
    st.session_state.chosen_languages = random.sample(pool, min(slots, len(pool)))

    # Drakarim ancestry
    if race["id"] == "drakarim":
        anc = race.get("draconic_ancestry_table", [])
        if anc:
            st.session_state.draconic_ancestry = random.choice(anc)["dragon"]

    # Equip first weapon found in the chosen equipment items
    inv_names = []
    for ch in mech.get("equipment_choices", []):
        idx = equip.get(ch["id"], 0)
        if idx < len(ch.get("options", [])):
            inv_names.extend(ch["options"][idx].get("items", []))
    inv_names.extend(mech.get("equipment_fixed", []))
    equipped = next(
        (w["id"] for name in inv_names
         for w in SRD_ITEMS["weapons"] if w["name"].lower() == name.lower()), None
    )
    st.session_state.equipped_main    = equipped
    st.session_state.equipped_offhand = None
    st.session_state.inv_weapons      = [equipped] if equipped else []

    # Clear fields left for AI or user to fill
    for k in ["char_name", "player_name", "notes", "personality", "ideals", "bonds", "flaws",
              "chosen_cantrips", "chosen_spells", "asi_choices", "combat_tactics",
              "expertise_skills", "damage_resistances", "inv_gear", "has_dual_wielder"]:
        st.session_state[k] = defaults[k]


def _ai_enrich_character():
    """Call Claude to generate a name and personality details for the rolled character."""
    if not _ai_client:
        if not _ai_key:
            print("[AI] ANTHROPIC_API_KEY not set — skipping AI enrichment.", flush=True)
        return
    race   = next((r for r in RACES       if r["id"] == st.session_state.race_id),       None)
    cls    = next((c for c in CLASSES      if c["id"] == st.session_state.class_id),      None)
    bg     = next((b for b in BACKGROUNDS  if b["id"] == st.session_state.background_id), None)
    sub    = next(
        (s for s in (cls.get("subclasses", []) if cls else [])
         if s["id"] == st.session_state.subclass_id), None
    )
    if not (race and cls and bg):
        return

    race_name  = race["name"]
    class_name = cls["name"]
    sub_name   = sub["name"] if sub else ""
    bg_name    = bg["name"]
    alignment  = st.session_state.alignment

    prompt = f"""You are a creative D&D character writer for the world of Ryndor: The Weirded Lands.

Generate a character profile for:
- Race: {race_name}
- Class: {class_name}{f" ({sub_name})" if sub_name else ""}
- Background: {bg_name}
- Alignment: {alignment}

Return ONLY valid JSON (no markdown, no commentary) with exactly these keys:
{{
  "name": "a fitting fantasy name for this race and character",
  "personality": "1–2 sentences describing their demeanor and quirks",
  "ideals": "one core belief or principle that drives them",
  "bonds": "one person, place, or duty they are loyal to",
  "flaws": "one weakness, vice, or fear that holds them back"
}}"""

    try:
        resp = _ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.strip())
        data = json.loads(raw)
        for key in ("name", "personality", "ideals", "bonds", "flaws"):
            if key in data and isinstance(data[key], str):
                st.session_state["char_name" if key == "name" else key] = data[key]
        print(f"[AI] Character enriched: {data.get('name', '?')}", flush=True)
    except Exception as e:
        print(f"[AI] ERROR: {e}\nRaw response: {raw if 'raw' in dir() else 'N/A'}", flush=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_race(id_):
    return next((r for r in RACES if r["id"] == id_), None)

def get_class(id_):
    return next((c for c in CLASSES if c["id"] == id_), None)

def get_background(id_):
    return next((b for b in BACKGROUNDS if b["id"] == id_), None)

def get_subclass(cls, sub_id):
    if not cls or not sub_id:
        return None
    return next((s for s in cls.get("subclasses", []) if s["id"] == sub_id), None)

def modifier(score):
    mod = math.floor((score - 10) / 2)
    return f"+{mod}" if mod >= 0 else str(mod)

def modifier_int(score):
    return math.floor((score - 10) / 2)

def proficiency_bonus(level):
    return 2 + math.floor((level - 1) / 4)

def effective_stat(stat_key, race):
    base = st.session_state.stats[stat_key]
    asi = race.get("ability_scores", {}) if race else {}
    name_map = {"STR": "Strength", "DEX": "Dexterity", "CON": "Constitution",
                "INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma"}
    bonus = asi.get(name_map[stat_key], 0) if isinstance(asi.get(name_map[stat_key], 0), int) else 0
    return base + bonus + get_asi_stat_bonus(stat_key)

STAT_KEY_MAP = {"DEX":"DEX","STR":"STR","CON":"CON","INT":"INT","WIS":"WIS","CHA":"CHA"}
ABILITY_SHORT = {"DEX":"Dex","STR":"Str","CON":"Con","INT":"Int","WIS":"Wis","CHA":"Cha"}

def skill_modifier(skill_name, ability_key, race, prof_bonus, proficient_skills, half_prof=0):
    score = effective_stat(ability_key, race)
    mod = modifier_int(score)
    if skill_name in proficient_skills:
        mod += prof_bonus
    elif half_prof:
        mod += half_prof
    return mod

def has_jack_of_all_trades():
    return st.session_state.get("class_id") == "bard" and st.session_state.get("char_level", 1) >= 2

def get_all_proficient_skills(race, bg, chosen_skills):
    """Return full set of proficient skill names from race + background + chosen class skills."""
    proficient = set(chosen_skills)
    if race:
        proficient.update(race.get("bonus_skills", []))
    if bg:
        proficient.update(bg.get("skill_proficiencies", []))
    return proficient

def get_mech(class_id):
    return CLASS_MECHANICS.get(class_id, {})

def compute_ac(class_id, race, equip_choices):
    """Compute base AC from chosen equipment. Returns (ac_value, note_string)."""
    mech = get_mech(class_id)
    dex_mod = modifier_int(effective_stat("DEX", race))
    con_mod = modifier_int(effective_stat("CON", race))
    wis_mod = modifier_int(effective_stat("WIS", race))
    shield_bonus = 0
    armor_ac = None
    armor_type = None

    # Check equipment choices for armor
    for choice in mech.get("equipment_choices", []):
        cid = choice["id"]
        idx = equip_choices.get(cid, 0)
        if idx < len(choice["options"]):
            opt = choice["options"][idx]
            if opt.get("ac_base") is not None:
                armor_ac = opt["ac_base"]
                armor_type = opt["ac_type"]
            if opt.get("shield"):
                shield_bonus = 2

    # If no armor chosen from choices, check default_ac
    if armor_ac is None and "default_ac" in mech:
        armor_ac = mech["default_ac"]["ac_base"]
        armor_type = mech["default_ac"]["ac_type"]

    # Special unarmored calculations
    special = mech.get("special_ac")
    if armor_ac is None:
        if special == "barbarian":
            return 10 + dex_mod + con_mod + shield_bonus, f"Unarmored Defense (10+DEX+CON)"
        elif special == "monk":
            return 10 + dex_mod + wis_mod, "Unarmored Defense (10+DEX+WIS)"
        else:
            return 10 + dex_mod + shield_bonus, "Unarmored"

    if armor_type == "fixed":
        return armor_ac + shield_bonus, "Heavy armor"
    elif armor_type == "medium":
        return armor_ac + min(dex_mod, 2) + shield_bonus, "Medium armor"
    else:  # light or unarmored
        return armor_ac + dex_mod + shield_bonus, "Light armor"

def get_spell_slots(slot_type, level):
    """Return list of (slot_level_str, count) for display, filtering zeros."""
    idx = min(level - 1, 19)
    if slot_type == "full":
        slots = FULL_CASTER_SLOTS[idx]
        return [(f"{i+1}{'st' if i==0 else 'nd' if i==1 else 'rd' if i==2 else 'th'}", n)
                for i, n in enumerate(slots) if n > 0]
    elif slot_type == "half":
        slots = HALF_CASTER_SLOTS[idx]
        return [(f"{i+1}{'st' if i==0 else 'nd' if i==1 else 'rd' if i==2 else 'th'}", n)
                for i, n in enumerate(slots) if n > 0]
    elif slot_type == "pact":
        count, slvl = PACT_SLOTS[idx]
        suffix = "st" if slvl==1 else "nd" if slvl==2 else "rd" if slvl==3 else "th"
        return [(f"{slvl}{suffix} (Pact)", count)]
    return []

def get_spells_known_or_prepared(sc, level, race):
    """Return (int_or_formula_str, label) for display."""
    if sc is None:
        return None, None
    idx = min(level - 1, 19)
    spells_known = sc.get("spells_known")
    formula = sc.get("prepare_formula")
    ability = sc.get("ability", "")
    key_map = {"Wisdom":"WIS","Intelligence":"INT","Charisma":"CHA",
               "Strength":"STR","Dexterity":"DEX","Constitution":"CON"}
    if spells_known is not None:
        count = spells_known[idx]
        return count, "Spells Known"
    elif formula:
        race_ = get_race(st.session_state.race_id)
        akey = key_map.get(ability, "WIS")
        mod = modifier_int(effective_stat(akey, race_))
        if "half_level" in formula:
            val = max(1, mod + math.floor(level / 2))
        else:
            val = max(1, mod + level)
        return val, "Max Prepared"
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# FEAT / ASI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_feat(feat_id):
    return next((f for f in SRD_FEATS if f["id"] == feat_id), None)

def get_asi_stat_bonus(stat_key):
    """Sum all ASI and feat stat bonuses for a given stat key."""
    total = 0
    for choice in st.session_state.get("asi_choices", {}).values():
        t = choice.get("type")
        if t == "asi_2" and choice.get("stat1") == stat_key:
            total += 2
        elif t == "asi_1_1":
            if choice.get("stat1") == stat_key:
                total += 1
            if choice.get("stat2") == stat_key:
                total += 1
        elif t == "feat":
            feat = get_feat(choice.get("feat_id", ""))
            if feat and feat.get("stat_bonus"):
                total += feat["stat_bonus"].get(stat_key, 0)
    return total

def get_class_asi_levels(class_id, level):
    """Return list of ASI levels unlocked at or below given character level."""
    schedule = ASI_LEVELS.get(class_id, DEFAULT_ASI_LEVELS)
    return [lvl for lvl in schedule if lvl <= level]

def get_spells_for_class(class_id, spell_level_str):
    """Return spell list for a class at a given level string ('cantrips','1'..'9')."""
    lookup_id = class_id
    if class_id in ("fighter", "rogue"):
        lookup_id = "wizard"
    if class_id == "artificer":
        lookup_id = "wizard"
    return SRD_SPELLS.get(spell_level_str, {}).get(lookup_id, [])

def lookup_spell_detail(name):
    """Find a spell dict by name in SRD_SPELLS. Returns (spell_dict, level_key) or (None, None)."""
    for level_key, classes in SRD_SPELLS.items():
        for class_spells in classes.values():
            for spell in class_spells:
                if spell.get("name") == name:
                    return spell, level_key
    return None, None

def _spell_level_label(level_key):
    """Return a display label for a spell level key like 'cantrips', '1', '2' etc."""
    if level_key == "cantrips":
        return "Cantrip"
    suffix = {"1":"st","2":"nd","3":"rd"}.get(level_key, "th")
    return f"{level_key}{suffix} Level"

def _build_slot_dict(sc_data, level):
    """Return ({spell_level_int: slot_count}, is_pact) from spellcasting data."""
    if not sc_data:
        return {}, False
    slot_type = sc_data.get("slot_type")
    idx = min(level - 1, 19)
    if slot_type == "full":
        raw = FULL_CASTER_SLOTS[idx]
        return {i + 1: n for i, n in enumerate(raw) if n > 0}, False
    elif slot_type == "half":
        raw = HALF_CASTER_SLOTS[idx]
        return {i + 1: n for i, n in enumerate(raw) if n > 0}, False
    elif slot_type == "pact":
        count, slvl = PACT_SLOTS[idx]
        return {slvl: count}, True
    return {}, False

def _spell_cast_label(level_key, slot_dict, is_pact):
    """Return a human-readable slot count string for a spell level, e.g. '4 slots / long rest'."""
    if level_key == "cantrips":
        return "At will"
    try:
        lvl_num = int(level_key)
    except (ValueError, TypeError):
        return ""
    count = slot_dict.get(lvl_num, 0)
    if not count:
        return ""
    rest = "short rest" if is_pact else "long rest"
    slot_word = "slot" if count == 1 else "slots"
    return f"{count} {slot_word} / {rest}"

# ── Combat action helpers ────────────────────────────────────────────────────
_DMG_RE  = re.compile(r'(\d+d\d+(?:[+\-]\d+)?)\s+(\w+)\s+damage', re.IGNORECASE)
_SAVE_RE = re.compile(
    r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+saving\s+throw',
    re.IGNORECASE,
)
_ATCK_RE = re.compile(r'(ranged|melee)\s+spell\s+attack', re.IGNORECASE)
_SAVE_ABBR = {
    "strength": "STR", "dexterity": "DEX", "constitution": "CON",
    "intelligence": "INT", "wisdom": "WIS", "charisma": "CHA",
}

def _parse_spell_combat(spell_dict):
    """Return (dice, dmg_type, atk_type, save_key) if the spell deals damage, else None.

    atk_type values:
      'attack'       — uses a spell attack roll
      'save'         — targets make a saving throw
      'weapon_bonus' — buff that adds damage to weapon attacks (e.g. Divine Favor)
      'auto'         — deals damage without a roll (e.g. Magic Missile)
    """
    desc = spell_dict.get("description", "")
    m = _DMG_RE.search(desc)
    if not m:
        return None
    dice     = m.group(1).strip()
    dmg_type = m.group(2).capitalize()
    if _ATCK_RE.search(desc):
        return dice, dmg_type, "attack", None
    sm = _SAVE_RE.search(desc)
    if sm:
        return dice, dmg_type, "save", _SAVE_ABBR[sm.group(1).lower()]
    if "weapon attack" in desc.lower() or "on a hit" in desc.lower():
        return dice, dmg_type, "weapon_bonus", None
    return dice, dmg_type, "auto", None

def _race_combat_actions(race, con_mod, prof, level):
    """Return a list of action dicts for race-granted combat abilities."""
    actions = []
    if not race:
        return actions
    if race["id"] == "drakarim":
        anc_name = st.session_state.get("draconic_ancestry", "")
        anc = next((x for x in race.get("draconic_ancestry_table", []) if x["dragon"] == anc_name), None)
        if anc:
            dc = 8 + prof + con_mod
            actions.append({
                "name": f"Breath Weapon ({anc['dragon']})",
                "category": "Racial",
                "hit": None,
                "save": f"DC {dc} {anc['save']}",
                "damage": f"2d6 {anc['damage_type'].lower()}",
                "note": f"{anc['breath']} · Half on save · Recharges short/long rest",
            })
    if race["id"] == "tiefling" and level >= 3:
        cha_mod = modifier_int(effective_stat("CHA", race))
        hb_dc   = 8 + prof + cha_mod
        # Cast at 2nd level → 3d10
        actions.append({
            "name": "Hellish Rebuke",
            "category": "Racial",
            "hit": None,
            "save": f"DC {hb_dc} DEX",
            "damage": "3d10 fire",
            "note": "Reaction (when damaged) · Half on save · 1× / long rest",
        })
    return actions

def _class_combat_actions(class_id, level, race, prof):
    """Return a list of action dicts for class-level damage features."""
    actions = []
    if class_id == "barbarian":
        rage_bonus = 2 if level < 9 else (3 if level < 16 else 4)
        actions.append({
            "name": "Rage",
            "category": "Feature",
            "hit": None,
            "save": None,
            "damage": f"+{rage_bonus} to STR melee damage",
            "note": "While raging · Resistance to B/P/S · Recharges long rest",
        })
    elif class_id == "paladin":
        actions.append({
            "name": "Divine Smite",
            "category": "Feature",
            "hit": None,
            "save": None,
            "damage": "2d8+ radiant",
            "note": "On a hit: expend spell slot · +1d8/slot lvl above 1st · Max 5d8 · +1d8 vs undead/fiends",
        })
    elif class_id == "rogue":
        sneak_dice = math.ceil(level / 2)
        actions.append({
            "name": "Sneak Attack",
            "category": "Feature",
            "hit": None,
            "save": None,
            "damage": f"{sneak_dice}d6",
            "note": "1× per turn · Requires advantage or ally adjacent to target",
        })
    return actions

def has_dual_wielder_feat():
    """Return True if the Dual Wielder feat is active (via ASI choices or legacy checkbox)."""
    for choice in st.session_state.get("asi_choices", {}).values():
        if choice.get("type") == "feat" and choice.get("feat_id") == "dual_wielder":
            return True
    return st.session_state.get("has_dual_wielder", False)

# ─────────────────────────────────────────────────────────────────────────────
# SRD ITEM HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_weapon(id_):
    return next((w for w in SRD_ITEMS["weapons"] if w["id"] == id_), None)

def is_weapon_proficient(weapon, cls):
    """Return True if cls has proficiency with the given weapon."""
    if not cls or not weapon:
        return False
    profs = cls.get("weapons", [])
    cat = weapon.get("category", "")
    name = weapon.get("name", "").lower()
    for p in profs:
        p_lower = p.lower()
        if p_lower in ("simple weapons", "all simple weapons") and cat.startswith("Simple"):
            return True
        if p_lower in ("martial weapons", "all martial weapons") and cat.startswith("Martial"):
            return True
        # Specific named proficiency (e.g. "Daggers", "Longswords")
        if name in p_lower or name.rstrip("s") in p_lower or p_lower.rstrip("s") in name:
            return True
    return False

def calc_weapon_attack(weapon, race, cls, level, for_offhand=False):
    """Return dict with attack, damage, versatile_damage, proficient, stat, notes."""
    if not weapon:
        return {}
    prof = proficiency_bonus(level)
    str_mod = modifier_int(effective_stat("STR", race))
    dex_mod = modifier_int(effective_stat("DEX", race))
    props = weapon.get("properties", [])
    cat = weapon.get("category", "")

    # Determine stat
    if "finesse" in props:
        if str_mod >= dex_mod:
            stat_key = "STR"
            stat_mod = str_mod
        else:
            stat_key = "DEX"
            stat_mod = dex_mod
    elif cat.endswith("Ranged"):
        stat_key = "DEX"
        stat_mod = dex_mod
    else:
        stat_key = "STR"
        stat_mod = str_mod

    proficient = is_weapon_proficient(weapon, cls)
    prof_bonus_applied = prof if proficient else 0

    atk_total = stat_mod + prof_bonus_applied
    atk_str = f"+{atk_total}" if atk_total >= 0 else str(atk_total)

    # Damage mod: off-hand bonus action attack gets no ability modifier per RAW
    if for_offhand:
        dmg_mod = 0
        dmg_note = "(no ability mod — off-hand)"
    else:
        dmg_mod = stat_mod
        dmg_note = ""

    base_dmg = weapon.get("damage", "1d4")
    if base_dmg == "—":
        dmg_str = "—"
    elif dmg_mod > 0:
        dmg_str = f"{base_dmg}+{dmg_mod} {weapon['damage_type']}"
    elif dmg_mod < 0:
        dmg_str = f"{base_dmg}{dmg_mod} {weapon['damage_type']}"
    else:
        dmg_str = f"{base_dmg} {weapon['damage_type']}"

    # Versatile
    versatile_dmg = None
    if "versatile" in props and weapon.get("versatile_damage") and not for_offhand:
        vd = weapon["versatile_damage"]
        if dmg_mod > 0:
            versatile_dmg = f"{vd}+{dmg_mod} {weapon['damage_type']}"
        elif dmg_mod < 0:
            versatile_dmg = f"{vd}{dmg_mod} {weapon['damage_type']}"
        else:
            versatile_dmg = f"{vd} {weapon['damage_type']}"

    notes = []
    if not proficient:
        notes.append("⚠ Not proficient")
    if dmg_note:
        notes.append(dmg_note)

    return {
        "attack": atk_str,
        "damage": dmg_str,
        "versatile_damage": versatile_dmg,
        "proficient": proficient,
        "stat": stat_key,
        "notes": notes,
    }

def check_dual_wield(main_wep, off_wep, has_dual_wielder_feat):
    """Return (ok: bool, reason: str). Empty reason means valid."""
    if not main_wep or not off_wep:
        return True, ""
    main_props = main_wep.get("properties", [])
    off_props  = off_wep.get("properties", [])
    if "two-handed" in main_props:
        return False, f"{main_wep['name']} requires two hands — cannot hold an off-hand weapon"
    if "two-handed" in off_props:
        return False, f"{off_wep['name']} requires two hands — cannot be used as off-hand"
    if not has_dual_wielder_feat:
        if "light" not in main_props:
            return False, f"{main_wep['name']} is not Light — requires Dual Wielder feat"
        if "light" not in off_props:
            return False, f"{off_wep['name']} is not Light — requires Dual Wielder feat"
    return True, ""

def get_current_armor_info(class_id, equip_choices):
    """Return (armor_type, has_shield) from equipment choices.
    armor_type: 'none', 'light', 'medium', 'fixed'
    """
    mech = get_mech(class_id)
    armor_type = "none"
    has_shield = False

    for choice in mech.get("equipment_choices", []):
        cid = choice["id"]
        idx = equip_choices.get(cid, 0)
        if idx < len(choice["options"]):
            opt = choice["options"][idx]
            if opt.get("ac_base") is not None:
                armor_type = opt.get("ac_type", "light")
            if opt.get("shield"):
                has_shield = True

    if armor_type == "none" and "default_ac" in mech:
        armor_type = mech["default_ac"].get("ac_type", "light")

    return armor_type, has_shield

def get_armor_restrictions(class_id, armor_type, has_shield):
    """Return list of (feature_name, reason) tuples for disabled features."""
    cls = get_class(class_id)
    if not cls:
        return []
    restrictions = []
    wearing_armor = armor_type != "none"
    armor_profs = [p.lower() for p in cls.get("armor", [])]

    has_light_prof   = any("light" in p or "all" in p for p in armor_profs)
    has_medium_prof  = any("medium" in p or "all" in p for p in armor_profs)
    has_heavy_prof   = any("heavy" in p or "all armor" in p for p in armor_profs)
    has_shield_prof  = any("shield" in p for p in armor_profs)

    if class_id == "monk":
        if wearing_armor or has_shield:
            what = []
            if wearing_armor:
                what.append("wearing armor")
            if has_shield:
                what.append("using a shield")
            reason = " and ".join(what)
            for feat in ("Martial Arts", "Unarmored Defense", "Unarmored Movement"):
                restrictions.append((feat, reason))

    elif class_id == "barbarian":
        if wearing_armor:
            restrictions.append(("Unarmored Defense", "wearing armor"))

    else:
        # Spellcasting restriction for classes with no or limited armor proficiency
        if wearing_armor:
            if armor_type == "fixed" and not has_heavy_prof:
                restrictions.append(("Spellcasting", "wearing heavy armor without proficiency — disadvantage on STR/DEX checks, spellcasting may fail"))
            elif armor_type == "medium" and not has_medium_prof:
                restrictions.append(("Spellcasting", "wearing medium armor without proficiency — disadvantage on STR/DEX checks, spellcasting may fail"))
            elif armor_type == "light" and not has_light_prof:
                restrictions.append(("Spellcasting", "wearing light armor without proficiency — disadvantage on STR/DEX checks, spellcasting may fail"))

    return restrictions

# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def _pdf_safe(text):
    """Replace Unicode characters unsupported by Helvetica with ASCII equivalents."""
    if not text:
        return ""
    return (str(text)
        .replace("\u2014", "--")   # em dash
        .replace("\u2013", "-")    # en dash
        .replace("\u2019", "'")    # right single quote
        .replace("\u2018", "'")    # left single quote
        .replace("\u201c", '"')    # left double quote
        .replace("\u201d", '"')    # right double quote
        .replace("\u2026", "...")  # ellipsis
        .replace("\u25cf", "*")    # bullet ●
        .replace("\u25cb", "o")    # circle ○
        .replace("\u2605", "*")    # star ★
        .replace("\u00bd", "1/2")  # half ½
        .replace("\u2019", "'")    # apostrophe variant
        .replace("\u00b7", "·")    # middle dot (latin-1 OK, keep)
        .replace("\u2022", "-")    # bullet •
        .replace("\u2260", "!=")   # not equal
        .replace("\u2192", "->")   # arrow →
        .replace("\u2190", "<-")   # arrow ←
        .encode("latin-1", errors="replace").decode("latin-1")
    )

def build_print_html():
    """Generate a standalone, print-ready HTML character sheet with its own light-theme CSS."""
    import math as _m
    ss    = st.session_state
    STAT_KEYS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    STAT_FULL = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

    race  = get_race(ss.get("race_id"))
    cls   = get_class(ss.get("class_id"))
    sub   = get_subclass(cls, ss.get("subclass_id")) if cls else None
    bg    = get_background(ss.get("background_id"))
    mech  = get_mech(ss.get("class_id") or "")
    level = ss.get("char_level", 1)
    prof  = proficiency_bonus(level)
    name  = (ss.get("char_name") or "Unnamed").strip()

    def eff(k):  return effective_stat(k, race)
    def modn(k): return modifier_int(eff(k))
    def mods(k): return modifier(eff(k))

    con_mod     = modn("CON")
    hit_die_num = int(cls["hit_die"][1:]) if cls else 8
    hp          = hit_die_num + con_mod + (level - 1) * (_m.floor(hit_die_num / 2) + 1 + con_mod)
    ac_val, ac_note = compute_ac(ss.get("class_id") or "", race, ss.get("equip_choices", {}))
    all_prof_sk  = get_all_proficient_skills(race, bg, ss.get("chosen_skills", []))
    joat_half    = _m.floor(prof / 2) if has_jack_of_all_trades() else 0
    expertise_set = set(ss.get("expertise_skills", []))
    perc_mod     = skill_modifier("Perception", "WIS", race, prof, all_prof_sk, half_prof=joat_half)
    speed        = race["speed"].get("walk", 30) if race else 30

    # ── Skill-to-ability map ──────────────────────────────────────────────────
    ABILITY_SKILLS = {
        "STR": ["Athletics"],
        "DEX": ["Acrobatics", "Sleight of Hand", "Stealth"],
        "CON": [],
        "INT": ["Arcana", "History", "Investigation", "Nature", "Religion"],
        "WIS": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
        "CHA": ["Deception", "Intimidation", "Performance", "Persuasion"],
    }
    SKILL_ABILITY = {}
    for ab, skills in ABILITY_SKILLS.items():
        for s in skills:
            SKILL_ABILITY[s] = ab

    # ── CSS ───────────────────────────────────────────────────────────────────
    CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
@page { margin:1.4cm 1.2cm; size:letter; }
body {
    font-family: 'Crimson Text', Georgia, serif;
    background: #f9f7f4;
    color: #1a1020;
    font-size: 9.5pt;
    line-height: 1.4;
    padding: 0.8rem;
    max-width: 960px;
    margin: 0 auto;
}
@media print { body { padding:0; background:#fff; } }
.print-btn {
    font-family: 'Cinzel', serif;
    background: #4c1d95; color: #fff;
    border: none; border-radius: 4px;
    padding: 0.5rem 1.3rem; cursor: pointer;
    font-size: 0.85rem; margin-bottom: 0.9rem;
    display: inline-block;
}
@media print { .print-btn { display:none !important; } }

/* ── Top header: 2 columns ── */
.top-header {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
    margin-bottom: 0.6rem;
}
.box {
    background: #fff;
    border: 1px solid rgba(100,50,200,0.25);
    border-radius: 4px;
    padding: 0.55rem 0.7rem;
}
.char-name {
    font-family: 'Cinzel', serif;
    font-size: 1.7rem; font-weight: 900;
    color: #3b0d8a; letter-spacing: 0.04em;
    line-height: 1.1;
}
.field-row {
    display: flex; align-items: baseline;
    border-bottom: 1px solid rgba(100,50,200,0.15);
    padding: 0.18rem 0; gap: 0.4rem;
    font-size: 0.85rem; color: #1a1020;
}
.field-row:last-child { border-bottom: none; }
.field-lbl {
    font-family: 'Cinzel', serif;
    font-size: 0.52rem; font-weight: 700;
    color: #3b0d8a; letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap; min-width: 80px;
}
.field-val { flex: 1; color: #1a1020; }
.field-blank {
    flex: 1;
    border-bottom: 1px solid #aaa;
    min-height: 0.9rem;
}

/* ── Main 3-column grid ── */
.main-grid {
    display: grid;
    grid-template-columns: 190px 200px 1fr;
    gap: 0.55rem;
    align-items: stretch;
}

/* ── Left col: ability + skill groups ── */
.ab-group {
    display: flex; gap: 0.3rem;
    align-items: flex-start;
    margin-bottom: 0.28rem;
}
.ab-box {
    width: 50px; min-width: 50px;
    background: #ede8f5;
    border: 1px solid rgba(100,50,200,0.4);
    border-radius: 4px; text-align: center;
    padding: 0.3rem 0.15rem;
}
.ab-key  { font-family:'Cinzel',serif; font-size:0.5rem; font-weight:700;
           color:#0e6a80; letter-spacing:0.08em; text-transform:uppercase; }
.ab-score{ font-family:'Cinzel',serif; font-size:1.35rem; font-weight:900;
           color:#1a1020; line-height:1.05; }
.ab-mod  { font-family:'Cinzel',serif; font-size:0.72rem; font-weight:700;
           color:#3b0d8a; }
.ab-skills { flex:1; padding-top:0.1rem; }
.sk-row {
    display: flex; justify-content: space-between;
    font-size: 0.75rem; padding: 0.08rem 0.2rem;
    border-bottom: 1px solid rgba(100,50,200,0.08);
    color: #1a1020;
}
.sk-row.prof { color:#3b0d8a; font-weight:600; }
.sk-row.exp  { color:#0e6a80; font-weight:700; }
.sk-mod { font-family:'Cinzel',serif; font-weight:700; font-size:0.73rem; }
.no-skills { font-size:0.7rem; color:#9a8aaa; font-style:italic; padding:0.2rem 0.2rem; }

/* ── Middle col: combat grid ── */
.cs-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.32rem;
    margin-bottom: 0.35rem;
}
.cs-item {
    background: #ede8f5;
    border: 1px solid rgba(100,50,200,0.32);
    border-radius: 4px;
    text-align: center;
    padding: 0.28rem 0.15rem 0.22rem;
}
.cs-item.blank {
    background: #fff;
}
.cs-item.full { grid-column: 1 / -1; }
.cs-lbl {
    font-family:'Cinzel',serif; font-size:0.46rem; font-weight:700;
    color:#0e6a80; letter-spacing:0.08em; text-transform:uppercase;
    display:block; margin-bottom:0.12rem;
}
.cs-val {
    font-family:'Cinzel',serif; font-size:1.05rem; font-weight:900;
    color:#1a1020; line-height:1;
    display:block;
}
.cs-line {
    border-bottom: 1px solid #999;
    display: block; height: 1.1rem; margin: 0 0.3rem;
}
.death-boxes { display:flex; gap:0.25rem; justify-content:center; flex-wrap:wrap; margin-top:0.1rem; }
.dbox { width:11px; height:11px; border:1px solid #7c5c9a; border-radius:50%; display:inline-block; }
.sec-title {
    font-family:'Cinzel',serif; font-size:0.6rem; font-weight:700;
    color:#3b0d8a; letter-spacing:0.14em; text-transform:uppercase;
    border-bottom:1px solid rgba(100,50,200,0.18);
    padding-bottom:0.22rem; margin-bottom:0.45rem;
}
table { width:100%; border-collapse:collapse; font-size:0.78rem; }
th { font-family:'Cinzel',serif; font-size:0.55rem; color:#3b0d8a;
     text-align:left; padding:0.1rem 0.25rem;
     border-bottom:1px solid rgba(100,50,200,0.2); }
td { padding:0.12rem 0.25rem; border-bottom:1px solid rgba(100,50,200,0.06); color:#1a1020;
     word-break:break-word; overflow-wrap:break-word; }
td.an { font-family:'Cinzel',serif; font-weight:700; font-size:0.7rem; }
td.ar { color:#3b0d8a; font-weight:600; }
td.ad { color:#5a4a7a; font-size:0.7rem; }
.atk-table { table-layout:fixed; }
.atk-table col.c-name { width:36%; }
.atk-table col.c-roll { width:22%; }
.atk-table col.c-dmg  { width:24%; }
.atk-table col.c-type { width:18%; }

/* ── Right col: features ── */
.feat-row { margin:0.45rem 0; }
.fname { font-family:'Cinzel',serif; color:#0e6a80;
         font-size:0.75rem; font-weight:600;
         display:block; margin-bottom:0.07rem; }
.fdesc { font-size:0.82rem; color:#2a1f40; line-height:1.4; }

/* ── Spell detail entries ── */
.spell-entry { margin:0.35rem 0; border-bottom:1px solid rgba(100,50,200,0.1); padding-bottom:0.28rem; }
.spell-entry:last-child { border-bottom:none; }
.sp-meta { font-size:0.68rem; color:#5a4a7a; display:block; margin-bottom:0.1rem; }

/* ── Page 2+ sections ── */
.page-break { page-break-before:always; padding-top:0.5rem; }
.sec-box {
    background:#fff; border:1px solid rgba(100,50,200,0.22);
    border-radius:4px; padding:0.65rem 0.8rem; margin:0.4rem 0;
    page-break-inside:avoid;
}
.lbl {
    font-family:'Cinzel',serif; font-size:0.55rem; font-weight:700;
    color:#3b0d8a; letter-spacing:0.1em; text-transform:uppercase;
    display:block; margin-bottom:0.1rem;
}
ul { padding-left:1rem; }
li { margin:0.1rem 0; font-size:0.84rem; color:#1a1020; }
"""

    # ── Left column: abilities + skills ──────────────────────────────────────
    left_col = '<div class="box" style="flex:1">'
    for key, full in zip(STAT_KEYS, STAT_FULL):
        e = eff(key); m = mods(key)
        left_col += f'<div class="ab-group">'
        left_col += (f'<div class="ab-box">'
                     f'<div class="ab-key">{key}</div>'
                     f'<div class="ab-score">{e}</div>'
                     f'<div class="ab-mod">{m}</div>'
                     f'</div>')
        left_col += '<div class="ab-skills">'
        skill_list = ABILITY_SKILLS.get(key, [])
        if skill_list:
            for sname in skill_list:
                is_exp = sname in expertise_set
                eff_pr = prof * 2 if is_exp else prof
                mv     = skill_modifier(sname, key, race, eff_pr, all_prof_sk, half_prof=joat_half)
                sign   = f"+{mv}" if mv >= 0 else str(mv)
                dot    = "★" if is_exp else ("●" if sname in all_prof_sk else "○")
                cls_s  = "exp" if is_exp else ("prof" if sname in all_prof_sk else "")
                left_col += (f'<div class="sk-row {cls_s}">'
                             f'<span>{dot} {sname}</span>'
                             f'<span class="sk-mod">{sign}</span></div>')
        else:
            left_col += '<div class="no-skills">—</div>'
        left_col += '</div></div>'
    left_col += '</div>'

    # ── Middle column: combat stats + attacks ─────────────────────────────────
    class_saves = cls["saves"] if cls else []

    def save_sign(full, key):
        total = modn(key) + (prof if full in class_saves else 0)
        return f"+{total}" if total >= 0 else str(total)

    saving_throws = " / ".join(
        f'<b>{full[:3]}</b> {save_sign(full, key)}{"★" if full in class_saves else ""}'
        for full, key in zip(STAT_FULL, STAT_KEYS)
    )

    def cs_item(label, val=None, blank=False, full=False):
        cls_str = "cs-item" + (" blank" if blank else "") + (" full" if full else "")
        inner = f'<span class="cs-line"></span>' if blank else f'<span class="cs-val">{val}</span>'
        return f'<div class="{cls_str}"><span class="cs-lbl">{label}</span>{inner}</div>'

    dboxes = '<div class="death-boxes">' + ''.join('<span class="dbox"></span>' * 3) + '</div>'

    combat_box = (
        f'<div class="box" style="margin-bottom:0.45rem">'
        f'<div class="sec-title">Combat</div>'
        f'<div class="cs-grid">'
        + cs_item("Armor Class", ac_val)
        + cs_item("Initiative", mods("DEX"))
        + cs_item("Speed", f"{speed} ft")
        + cs_item("Hit Point Maximum", str(max(hp, 1)))
        + cs_item("Hit Dice", f"{level}{cls['hit_die'] if cls else 'd8'}")
        + cs_item("Passive Perception", str(10 + perc_mod))
        + f'<div class="cs-item full"><span class="cs-lbl">Death Saves</span>'
        + f'<span style="font-size:0.6rem;color:#5a4a7a">Successes</span> {dboxes}'
        + f'<span style="font-size:0.6rem;color:#5a4a7a">Failures</span> {dboxes}</div>'
        + '</div></div>'
    )

    # Attacks table
    all_actions = []
    main_wep = get_weapon(ss.get("equipped_main"))
    off_wep  = get_weapon(ss.get("equipped_offhand"))
    if main_wep:
        ms = calc_weapon_attack(main_wep, race, cls, level)
        vd = f" + {ms['versatile_damage']} (2h)" if ms.get("versatile_damage") else ""
        all_actions.append({"name": main_wep["name"],
                            "roll": ms["attack"], "dmg": ms["damage"] + vd,
                            "note": "Proficient" if ms["proficient"] else "—"})
    if off_wep:
        ms2 = calc_weapon_attack(off_wep, race, cls, level, for_offhand=True)
        all_actions.append({"name": off_wep["name"] + " (off-hand)",
                            "roll": ms2["attack"], "dmg": ms2["damage"], "note": "Off-hand"})
    for a in _race_combat_actions(race, con_mod, prof, level):
        all_actions.append({"name": a["name"],
                            "roll": a.get("hit") or (f'DC {a.get("save") or ""}' if a.get("save") else "—"),
                            "dmg": a.get("damage","—"), "note": a.get("category","")})
    for a in _class_combat_actions(ss.get("class_id") or "", level, race, prof):
        all_actions.append({"name": a["name"],
                            "roll": a.get("hit") or (f'DC {a.get("save") or ""}' if a.get("save") else "—"),
                            "dmg": a.get("damage","—"), "note": a.get("category","")})

    sc_data = mech.get("spellcasting")
    if sc_data:
        sc_key_map = {"Wisdom":"WIS","Intelligence":"INT","Charisma":"CHA"}
        sc_key = sc_key_map.get(sc_data.get("ability","Wisdom"), "WIS")
        sc_mod = modn(sc_key)
        sp_atk = f"+{prof+sc_mod}" if (prof+sc_mod) >= 0 else str(prof+sc_mod)
        sp_dc  = 8 + prof + sc_mod
        for cname in ss.get("chosen_cantrips", []):
            csd, _ = lookup_spell_detail(cname)
            if csd:
                cp = _parse_spell_combat(csd)
                if cp:
                    cdice, cdtype, catk, csave = cp
                    roll = sp_atk if catk=="attack" else (f"DC {sp_dc} {csave}" if catk=="save" else "—")
                    all_actions.append({"name": cname, "roll": roll,
                                        "dmg": f"{cdice} {cdtype.lower()}", "note": "Cantrip"})
        for sname_sp in ss.get("chosen_spells", []):
            spd, slk = lookup_spell_detail(sname_sp)
            if spd:
                sp2 = _parse_spell_combat(spd)
                if sp2:
                    sdice, sdtype, satk, ssave = sp2
                    roll = sp_atk if satk=="attack" else (f"DC {sp_dc} {ssave}" if satk=="save" else "—")
                    all_actions.append({"name": sname_sp, "roll": roll,
                                        "dmg": f"{sdice} {sdtype.lower()}", "note": slk or "Spell"})

    atk_mid = ('<div class="box"><div class="sec-title">Attacks &amp; Damaging Actions</div>'
               + ('<table class="atk-table">'
                  '<colgroup>'
                  '<col class="c-name"><col class="c-roll"><col class="c-dmg"><col class="c-type">'
                  '</colgroup>'
                  '<tr><th>Name</th><th>ATK / Save</th><th>Damage</th><th>Type</th></tr>'
                  + "".join(
                      f'<tr><td class="an">{a["name"]}</td>'
                      f'<td class="ar">{a["roll"]}</td>'
                      f'<td>{a["dmg"]}</td>'
                      f'<td class="ad">{a["note"]}</td></tr>'
                      for a in all_actions)
                  + '</table>' if all_actions
                  else '<p style="font-size:0.78rem;color:#9a8aaa;font-style:italic">No attacks configured.</p>')
               + '</div>')

    # ── Middle bottom: spellcasting (if any) else languages + equipment ────────
    _mid_has_spell = False
    _mid_has_lang  = False
    _mid_has_equip = False

    def _spell_block_html(sname, force_label=""):
        spd, slk = lookup_spell_detail(sname)
        lvl_str = force_label or (_spell_level_label(slk) if slk else "")
        badge = (f'<span style="font-family:Cinzel,serif;font-size:0.46rem;color:#0e6a80;'
                 f'margin-left:0.35rem;font-weight:400;text-transform:uppercase;'
                 f'letter-spacing:0.06em">{lvl_str}</span>')
        if not spd:
            return f'<div class="spell-entry"><span class="fname">{sname}{badge}</span></div>'
        parts = []
        if spd.get("casting_time"): parts.append(f"Cast: {spd['casting_time']}")
        if spd.get("range"):        parts.append(f"Range: {spd['range']}")
        if spd.get("components"):   parts.append(f"Comp: {spd['components']}")
        if spd.get("duration"):     parts.append(f"Dur: {spd['duration']}")
        meta = " &nbsp;·&nbsp; ".join(parts)
        desc = spd.get("description", "")
        return (f'<div class="spell-entry">'
                f'<span class="fname">{sname}{badge}</span>'
                + (f'<span class="sp-meta">{meta}</span>' if meta else "")
                + (f'<span class="fdesc">{desc}</span>' if desc else "")
                + '</div>')

    if sc_data and (ss.get("chosen_cantrips") or ss.get("chosen_spells")):
        _mid_has_spell = True
        sc_ab   = sc_data.get("ability", "Wisdom")
        sc_key2 = {"Wisdom":"WIS","Intelligence":"INT","Charisma":"CHA"}.get(sc_ab, "WIS")
        sc_mod2 = modn(sc_key2)
        sp_dc2  = 8 + prof + sc_mod2
        sp_atk2 = f"+{prof+sc_mod2}" if (prof+sc_mod2) >= 0 else str(prof+sc_mod2)
        sp_html_mid = (f'<p style="font-size:0.8rem;margin-bottom:0.4rem">'
                       f'<b>Ability:</b> {sc_ab} &nbsp;·&nbsp; '
                       f'<b>DC:</b> {sp_dc2} &nbsp;·&nbsp; '
                       f'<b>Atk:</b> {sp_atk2}</p>')
        cantrips_mid = ss.get("chosen_cantrips", [])
        spells_mid   = ss.get("chosen_spells", [])
        total_known  = len(cantrips_mid) + len(spells_mid)
        sp_html_mid += (f'<p style="font-size:0.78rem;color:#5a4a7a;margin-bottom:0.35rem">'
                        f'<b>Spells Known:</b> {total_known}</p>')
        if cantrips_mid:
            sp_html_mid += ('<p style="font-family:Cinzel,serif;font-size:0.55rem;color:#3b0d8a;'
                            'letter-spacing:0.1em;margin:0.3rem 0 0.12rem">CANTRIPS</p>'
                            + "".join(
                                f'<div style="font-size:0.82rem;padding:0.07rem 0;'
                                f'border-bottom:1px solid rgba(100,50,200,0.08);color:#1a1020">{s}</div>'
                                for s in cantrips_mid))
        if spells_mid:
            sp_html_mid += ('<p style="font-family:Cinzel,serif;font-size:0.55rem;color:#3b0d8a;'
                            'letter-spacing:0.1em;margin:0.4rem 0 0.12rem">SPELLS KNOWN</p>'
                            + "".join(
                                f'<div style="font-size:0.82rem;padding:0.07rem 0;'
                                f'border-bottom:1px solid rgba(100,50,200,0.08);color:#1a1020">{s}</div>'
                                for s in spells_mid))
        mid_bottom = (f'<div class="box" style="flex:1">'
                      f'<div class="sec-title">Spellcasting</div>{sp_html_mid}</div>')
    else:
        _mid_has_lang  = True
        _mid_has_equip = True
        # Languages & Proficiencies
        _all_langs = list(dict.fromkeys(
            (race.get("languages", []) if race else []) +
            (bg.get("languages", []) if bg else []) +
            ss.get("chosen_languages", [])
        ))
        _prof_html = ""
        if _all_langs:
            _prof_html += f'<span class="lbl">Languages</span>{", ".join(_all_langs)}<br>'
        if bg and bg.get("tool_proficiencies"):
            _prof_html += f'<span class="lbl" style="margin-top:0.35rem">Tools</span>{", ".join(bg["tool_proficiencies"])}<br>'
        if cls:
            _aw = cls.get("armor", []) + cls.get("weapons", [])
            if _aw:
                _prof_html += f'<span class="lbl" style="margin-top:0.35rem">Armor &amp; Weapons</span>{", ".join(_aw)}'
        # Equipment
        _eq_fixed   = mech.get("equipment_fixed", [])
        _eq_choices = mech.get("equipment_choices", [])
        _eq_items   = list(_eq_fixed)
        for _ch in _eq_choices:
            _idx = ss.get("equip_choices", {}).get(_ch["id"], 0)
            if _idx < len(_ch["options"]):
                _eq_items.extend(_ch["options"][_idx]["items"])
        if bg:   _eq_items.append(bg.get("equipment", ""))
        if main_wep: _eq_items.append(f"{main_wep['name']} (main hand)")
        if off_wep:  _eq_items.append(f"{off_wep['name']} (off-hand)")
        _eq_html = "<ul>" + "".join(f"<li>{i}</li>" for i in _eq_items if i) + "</ul>"
        _combined = ""
        if _prof_html:
            _combined += f'<div style="margin-bottom:0.5rem"><div class="sec-title">Languages &amp; Proficiencies</div>{_prof_html}</div>'
        _combined += f'<div class="sec-title">Equipment &amp; Inventory</div>{_eq_html}'
        mid_bottom = f'<div class="box" style="flex:1">{_combined}</div>'

    # ── Right column: Features & Traits ───────────────────────────────────────
    def feat_item(fname, fdesc):
        return (f'<div class="feat-row">'
                f'<span class="fname">{fname}</span>'
                f'<span class="fdesc">{fdesc}</span>'
                f'</div>')

    right_col = '<div class="box" style="flex:1"><div class="sec-title">Features &amp; Traits</div>'

    if race:
        right_col += f'<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#0e6a80;letter-spacing:0.1em;text-transform:uppercase;margin:0.3rem 0 0.15rem">{race["name"]} Traits</p>'
        for t in race.get("traits", []):
            right_col += feat_item(t["name"], t["description"])

    if cls:
        cf_data = CLASS_FEATURES.get(cls["id"], {})
        feats   = [f for f in cf_data.get("features", []) if f["level"] <= level]
        if feats:
            right_col += f'<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#0e6a80;letter-spacing:0.1em;text-transform:uppercase;margin:0.5rem 0 0.15rem">{cls["name"]} Features</p>'
            for feat in feats:
                right_col += feat_item(f'{feat["name"]} (L{feat["level"]})', feat["description"])
        if sub:
            sub_feats = [f for f in sub.get("features", []) if f["level"] <= level]
            if sub_feats:
                right_col += f'<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#0e6a80;letter-spacing:0.1em;text-transform:uppercase;margin:0.5rem 0 0.15rem">{sub["name"]}</p>'
                for feat in sub_feats:
                    right_col += feat_item(f'{feat["name"]} (L{feat["level"]})', feat["description"])

    if bg:
        bf = bg.get("feature", {})
        if bf:
            right_col += f'<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#0e6a80;letter-spacing:0.1em;text-transform:uppercase;margin:0.5rem 0 0.15rem">Background: {bg["name"]}</p>'
            right_col += feat_item(bf.get("name","Feature"), bf.get("description",""))

    right_col += '</div>'

    # ── Page 1: assemble ──────────────────────────────────────────────────────
    _race_name  = race["name"] if race else "—"
    _cls_name   = cls["name"] if cls else "—"
    _cls_sub    = f" — {sub['name']}" if sub else ""
    char_subtitle = f"{_race_name} · Level {level} {_cls_name}{_cls_sub}"

    top_header = f"""
<div class="top-header">
  <div class="box">
    <div class="char-name">{name}</div>
    <div style="font-family:Cinzel,serif;font-size:0.68rem;color:#3b0d8a;letter-spacing:0.03em;margin:0.18rem 0 0">{char_subtitle}</div>
  </div>
  <div class="box">
    <div class="field-row"><span class="field-lbl">Player Name</span><span class="field-blank"></span></div>
    <div class="field-row"><span class="field-lbl">Background</span><span class="field-val">{bg["name"] if bg else "—"}</span></div>
    <div class="field-row"><span class="field-lbl">Alignment</span><span class="field-val">{ss.get("alignment") or "—"}</span></div>
    <div class="field-row"><span class="field-lbl">Experience Points</span><span class="field-blank"></span></div>
  </div>
</div>"""

    main_grid = f"""
<div class="main-grid">
  <div style="display:flex;flex-direction:column;gap:0.55rem">{combat_box}{left_col}</div>
  <div style="display:flex;flex-direction:column;gap:0.55rem">{atk_mid}{mid_bottom}</div>
  <div style="display:flex;flex-direction:column">{right_col}</div>
</div>"""

    # ── Page 2+: spells, tactics, details, equipment ──────────────────────────
    def sec_box(title, body):
        return f'<div class="sec-box"><div class="sec-title">{title}</div>{body}</div>'

    page2_parts = []

    # ── Sev'rinn class content ────────────────────────────────────────────────
    if cls and cls["id"] == "sevrinn" and sub:
        sv_mech = cls.get("mechanics", {})

        # Resources header
        lvl_data = None
        for row in sv_mech.get("level_table", []):
            if row["min_level"] <= level <= row["max_level"]:
                lvl_data = row; break
        sv_res_html = ""
        if lvl_data:
            sv_res_html += (f'<p style="font-size:0.85rem;margin-bottom:0.4rem">'
                            f'<b>Charges:</b> {lvl_data["charges"]} &nbsp;·&nbsp; '
                            f'<b>Techniques Known:</b> {lvl_data["techniques"]}</p>')
        ws = sv_mech.get("weirding_surge", "")
        if ws:
            sv_res_html += feat_item("Weirding Surge", ws)
        es = sv_mech.get("elemental_shift", {})
        if es:
            es_text = (f"Activation: {es.get('activation','')} "
                       f"Lock Mode: {es.get('lock_mode','')} "
                       f"Shifted Discount: {es.get('shift_discount','')} "
                       f"Re-entry: {es.get('reentry','')}")
            sv_res_html += feat_item("Elemental Shift (Bonus Action, 1 Charge)", es_text)
        for cf in sv_mech.get("class_features", []):
            if cf["level"] <= level:
                sv_res_html += feat_item(f'{cf["name"]} (Level {cf["level"]})', cf["description"])
        if sv_res_html:
            page2_parts.append(sec_box("Sev&#x2019;rinn — Elemental Resources", sv_res_html))

        # Weirding Surge Table
        surge_table = sv_mech.get("weirding_surge_table", [])
        if surge_table:
            surge_html = ('<table><tr><th style="width:2rem">d6</th><th>Effect</th></tr>'
                          + "".join(f'<tr><td class="an">{i}</td><td>{effect}</td></tr>'
                                    for i, effect in enumerate(surge_table, 1))
                          + '</table>')
            page2_parts.append(sec_box("Weirding Surge Table (roll d6 on every Charge spend)", surge_html))

        # Shift Table
        shift_table = sub.get("shift_table", [])
        if shift_table:
            form_name = sub["features"][0]["name"] if sub.get("features") else "Elemental Form"
            form_desc = sub["features"][0].get("description", "") if sub.get("features") else ""
            shift_html = (f'<p class="fdesc" style="margin-bottom:0.4rem">{form_desc}</p>'
                          '<table><tr><th>Roll</th><th>Form</th><th>Effect</th></tr>'
                          + "".join(f'<tr><td class="an">{s["roll"]}</td>'
                                    f'<td class="ar">{s["name"]}</td>'
                                    f'<td class="ad">{s["effect"]}</td></tr>'
                                    for s in shift_table)
                          + '</table>')
            page2_parts.append(sec_box(f"{form_name} — Shift Table (Bonus Action, 1 Charge)", shift_html))

        # Combat Techniques
        techs = [t for t in sub.get("techniques", []) if t["level"] <= level]
        if techs:
            tech_html = ""
            for tech in techs:
                usage     = tech.get("usage", "")
                tech_lvl  = tech["level"]
                if usage == "Elemental Shift use":
                    cost_str = "[Shift use]"
                elif any(x in usage for x in ["/Short Rest", "/Long Rest", "/7 days", "proficiency bonus"]):
                    cost_str = f"[{usage}]"
                elif tech_lvl <= 3:
                    cost_str = "[1 Charge]"
                elif tech_lvl <= 10:
                    cost_str = "[2C / 1C Shifted]"
                else:
                    cost_str = "[3C / 2C Shifted]"
                tech_html += feat_item(
                    f'[Lv.{tech_lvl}] {tech["name"]} '
                    f'<span style="font-weight:400;color:#5a4a7a;font-size:0.68rem">{cost_str}</span>',
                    tech.get("description", "")
                )
            page2_parts.append(sec_box("Combat Techniques", tech_html))

    # Spellcasting — full descriptions + slots always go to page 2
    if sc_data and (ss.get("chosen_cantrips") or ss.get("chosen_spells")):
        sc_ab   = sc_data.get("ability", "Wisdom")
        sc_key2 = {"Wisdom":"WIS","Intelligence":"INT","Charisma":"CHA"}.get(sc_ab, "WIS")
        sc_mod2 = modn(sc_key2)
        sp_dc2  = 8 + prof + sc_mod2
        sp_atk2 = f"+{prof+sc_mod2}" if (prof+sc_mod2) >= 0 else str(prof+sc_mod2)
        sp_html = (f'<p style="font-size:0.8rem;margin-bottom:0.5rem">'
                   f'<b>Spellcasting Ability:</b> {sc_ab} &nbsp;·&nbsp; '
                   f'<b>Spell Save DC:</b> {sp_dc2} &nbsp;·&nbsp; '
                   f'<b>Spell Attack Bonus:</b> {sp_atk2}</p>')
        # Spell slots table
        slots, is_pact = _build_slot_dict(sc_data, level)
        if slots:
            slot_label = "PACT MAGIC SLOTS" if is_pact else "SPELL SLOTS PER LEVEL"
            sp_html += (f'<p style="font-family:Cinzel,serif;font-size:0.55rem;color:#3b0d8a;'
                        f'letter-spacing:0.1em;margin:0 0 0.2rem">{slot_label}</p>'
                        '<table style="width:auto;margin-bottom:0.6rem"><tr style="background:#ede8f5">')
            for slvl in sorted(slots.keys()):
                suffix = {"1": "st", "2": "nd", "3": "rd"}.get(str(slvl), "th")
                sp_html += f'<th style="text-align:center;padding:0.15rem 0.45rem;font-family:Cinzel,serif;font-size:0.52rem">{slvl}{suffix}</th>'
            sp_html += '</tr><tr>'
            for slvl in sorted(slots.keys()):
                sp_html += f'<td style="text-align:center;padding:0.15rem 0.45rem;font-size:0.85rem;font-weight:700">{slots[slvl]}</td>'
            sp_html += '</tr></table>'
        # Full spell descriptions
        cantrips = ss.get("chosen_cantrips", [])
        spells   = ss.get("chosen_spells", [])
        if cantrips:
            sp_html += ('<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#3b0d8a;'
                        'letter-spacing:0.1em;margin:0.3rem 0 0.2rem">CANTRIPS</p>')
            for cn in cantrips:
                sp_html += _spell_block_html(cn, "Cantrip")
        if spells:
            sp_html += ('<p style="font-family:Cinzel,serif;font-size:0.58rem;color:#3b0d8a;'
                        'letter-spacing:0.1em;margin:0.5rem 0 0.2rem">SPELLS</p>')
            for sn in spells:
                sp_html += _spell_block_html(sn)
        page2_parts.append(sec_box("Spellcasting", sp_html))

    # Combat Tactics
    _ct = ss.get("combat_tactics", {})
    if _ct:
        ct_html = ""
        if _ct.get("role"):
            ct_html += f'<p style="font-style:italic;color:#5a4a7a;margin-bottom:0.4rem;font-size:0.85rem">{_ct["role"]}</p>'
        for tac in _ct.get("tactics", []):
            ct_html += (f'<div class="feat-row">'
                        f'<span class="fname">{tac["phase"]}</span>'
                        f'<span class="fdesc">{tac["text"]}</span></div>')
        page2_parts.append(sec_box("Combat Tactics", ct_html))

    # Character Details
    details_html = ""
    for label, val in [("Personality Traits", ss.get("personality","")),
                       ("Ideals",             ss.get("ideals","")),
                       ("Bonds",              ss.get("bonds","")),
                       ("Flaws",              ss.get("flaws","")),
                       ("Additional Notes",   ss.get("notes",""))]:
        if val:
            details_html += f'<div style="margin:0.35rem 0"><span class="lbl">{label}</span>{val}</div>'
    if details_html:
        page2_parts.append(sec_box("Character Details", details_html))

    # Equipment & Inventory (only on page 2 if not already shown in mid col)
    if not _mid_has_equip:
        eq_fixed   = mech.get("equipment_fixed", [])
        eq_choices = mech.get("equipment_choices", [])
        eq_items   = list(eq_fixed)
        for choice in eq_choices:
            idx = ss.get("equip_choices", {}).get(choice["id"], 0)
            if idx < len(choice["options"]):
                eq_items.extend(choice["options"][idx]["items"])
        if bg:
            eq_items.append(bg.get("equipment", ""))
        if main_wep: eq_items.append(f"{main_wep['name']} (main hand)")
        if off_wep:  eq_items.append(f"{off_wep['name']} (off-hand)")
        eq_html = "<ul>" + "".join(f"<li>{i}</li>" for i in eq_items if i) + "</ul>"
        page2_parts.append(sec_box("Equipment &amp; Inventory", eq_html))

    # Languages & Proficiencies (only on page 2 if not already shown in mid col)
    if not _mid_has_lang:
        all_langs = list(dict.fromkeys(
            (race.get("languages", []) if race else []) +
            (bg.get("languages", []) if bg else []) +
            ss.get("chosen_languages", [])
        ))
        prof_html = ""
        if all_langs:
            prof_html += f'<span class="lbl">Languages</span>{", ".join(all_langs)}<br style="margin-bottom:0.2rem">'
        if bg and bg.get("tool_proficiencies"):
            prof_html += f'<span class="lbl" style="margin-top:0.35rem">Tools</span>{", ".join(bg["tool_proficiencies"])}<br>'
        if cls:
            aw = cls.get("armor", []) + cls.get("weapons", [])
            if aw:
                prof_html += f'<span class="lbl" style="margin-top:0.35rem">Armor &amp; Weapons</span>{", ".join(aw)}'
        if prof_html:
            page2_parts.append(sec_box("Languages &amp; Proficiencies", prof_html))

    page2_html = ""
    if page2_parts:
        page2_html = f'<div class="page-break">{"".join(page2_parts)}</div>'

    fonts = ("https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900"
             "&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{name} — Character Sheet</title>
  <link href="{fonts}" rel="stylesheet">
  <style>{CSS}</style>
</head>
<body>
  <button class="print-btn" onclick="window.print()">&#x1F5A8; Print / Save as PDF</button>
  {top_header}
  {main_grid}
  {page2_html}
</body>
</html>"""


def generate_character_pdf():
    """Generate a formatted PDF character sheet. Returns bytes."""
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    race   = get_race(st.session_state.race_id)
    cls    = get_class(st.session_state.class_id)
    sub    = get_subclass(cls, st.session_state.subclass_id)
    bg     = get_background(st.session_state.background_id)
    level  = st.session_state.char_level
    prof   = proficiency_bonus(level)
    STAT_KEYS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    STAT_FULL = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

    # ── Colour palette ──
    C_HDR_FILL = (30, 30, 30)      # section header background (near-black)
    C_HDR_TEXT = (255, 255, 255)   # section header text (white on dark)
    C_SUB      = (80, 80, 80)      # italic sub-labels (dark grey)
    C_STAT     = (50, 50, 50)      # stat values / key-value pairs
    C_BODY     = (30, 30, 30)      # body text / list items

    def _sec(title):
        """Render a styled section header bar."""
        pdf.set_fill_color(*C_HDR_FILL)
        pdf.set_text_color(*C_HDR_TEXT)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, _pdf_safe(title), ln=True, fill=True)
        pdf.ln(1)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Header ──
    char_name = st.session_state.char_name or "Unnamed Character"
    race_name = race["name"] if race else "Unknown Race"
    cls_name  = cls["name"]  if cls  else "Unknown Class"
    sub_name  = sub["name"]  if sub  else ""
    bg_name   = bg["name"]   if bg   else "Unknown Background"
    alignment = st.session_state.alignment or ""

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 11, _pdf_safe(char_name), ln=True, align="C")
    pdf.set_text_color(*C_SUB)
    pdf.set_font("Helvetica", "I", 10)
    sub_part = f" ({_pdf_safe(sub_name)})" if sub_name else ""
    pdf.cell(0, 6, _pdf_safe(f"{race_name}  *  {cls_name}{sub_part} Lv.{level}  *  {bg_name}  *  {alignment}"), ln=True, align="C")
    pdf.ln(4)

    # ── Ability Scores ──
    _sec("ABILITY SCORES")
    col_w = (pdf.w - 30) / 6
    pdf.set_text_color(*C_SUB)
    pdf.set_font("Helvetica", "B", 8)
    for full in STAT_FULL:
        pdf.cell(col_w, 5, full[:3].upper(), border=0, align="C")
    pdf.ln(5)
    pdf.set_text_color(*C_HDR_TEXT)
    pdf.set_font("Helvetica", "B", 11)
    for key in STAT_KEYS:
        eff = effective_stat(key, race)
        mod = modifier(eff)
        pdf.cell(col_w, 6, f"{eff} ({mod})", border=0, align="C")
    pdf.ln(8)

    # ── Combat Stats ──
    con_mod = modifier_int(effective_stat("CON", race))
    hit_die_num = int(cls["hit_die"][1:]) if cls else 8
    hp = hit_die_num + con_mod + (level - 1) * (math.floor(hit_die_num / 2) + 1 + con_mod)
    ac_val, ac_note = compute_ac(st.session_state.class_id or "", race, st.session_state.equip_choices)
    all_prof_skills = get_all_proficient_skills(race, bg, st.session_state.chosen_skills)
    joat_half_pdf = math.floor(prof / 2) if has_jack_of_all_trades() else 0
    perc_mod = skill_modifier("Perception", "WIS", race, prof, all_prof_skills, half_prof=joat_half_pdf)
    speed = str(race["speed"].get("walk", 30) if race else 30)
    init_mod = modifier(effective_stat("DEX", race))

    _sec("COMBAT")
    # ── 6-stat grid ──
    third_w = (pdf.w - 30) / 3
    combat_items = [
        ("Max HP",            str(max(hp, 1))),
        ("Armor Class",       str(ac_val)),
        ("Initiative",        init_mod),
        ("Speed",             f"{speed} ft"),
        ("Proficiency Bonus", f"+{prof}"),
        ("Passive Perception", str(10 + perc_mod)),
    ]
    for i, (label, value) in enumerate(combat_items):
        if i > 0 and i % 3 == 0:
            pdf.ln(5)
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(third_w * 0.55, 5, _pdf_safe(label + ":"))
        pdf.set_text_color(*C_HDR_TEXT)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(third_w * 0.45, 5, _pdf_safe(value))
    pdf.ln(7)

    # ── AC formula + Hit Die sub-line ──
    pdf.set_text_color(*C_SUB)
    pdf.set_font("Helvetica", "I", 8)
    hit_die_str = cls["hit_die"] if cls else "d8"
    pdf.cell(0, 4.5, _pdf_safe(f"AC: {ac_note}  |  Hit Die: {hit_die_str}"), ln=True)
    pdf.ln(1)

    # ── Damage Resistances ──
    _dmg_res_pdf = list(st.session_state.get("damage_resistances", []))
    if race and race["id"] == "drakarim":
        _anc_res_p = st.session_state.get("draconic_ancestry", "")
        _anc_r_p = next((x for x in race.get("draconic_ancestry_table", []) if x["dragon"] == _anc_res_p), None)
        if _anc_r_p and _anc_r_p["damage_type"] not in _dmg_res_pdf:
            _dmg_res_pdf.append(_anc_r_p["damage_type"])
    if _dmg_res_pdf:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 4.5, _pdf_safe("Damage Resistances: " + ", ".join(_dmg_res_pdf)), ln=True)
        pdf.ln(1)

    # ── Attacks & Actions ──
    _pdf_acts = []
    _pm = get_weapon(st.session_state.get("equipped_main"))
    _po = get_weapon(st.session_state.get("equipped_offhand"))
    if _pm:
        _ms2 = calc_weapon_attack(_pm, race, cls, level)
        _vd2 = f" / Versatile: {_ms2['versatile_damage']}" if _ms2.get("versatile_damage") else ""
        _pdf_acts.append({"name": _pm["name"], "category": "Weapon",
                          "hit": f"{_ms2['attack']} to hit", "save": None,
                          "damage": _ms2["damage"] + _vd2,
                          "note": "Prof" if _ms2["proficient"] else "Not prof"})
    if _po:
        _os2 = calc_weapon_attack(_po, race, cls, level, for_offhand=True)
        _pdf_acts.append({"name": _po["name"] + " (off-hand)", "category": "Weapon",
                          "hit": f"{_os2['attack']} to hit", "save": None,
                          "damage": _os2["damage"],
                          "note": "Prof" if _os2["proficient"] else "Not prof"})
    _pdf_acts.extend(_race_combat_actions(race, con_mod, prof, level))
    _mech_p = get_mech(st.session_state.class_id or "")
    _sc_p   = _mech_p.get("spellcasting")
    if _sc_p and st.session_state.class_id != "sevrinn":
        _sck_p  = {"Wisdom": "WIS", "Intelligence": "INT", "Charisma": "CHA"}.get(_sc_p["ability"], "WIS")
        _scm_p  = modifier_int(effective_stat(_sck_p, race))
        _ab_p   = prof + _scm_p
        _dc_p   = 8 + _ab_p
        _as_p   = f"+{_ab_p}" if _ab_p >= 0 else str(_ab_p)
        for _cn2 in st.session_state.get("chosen_cantrips", []):
            _csd3, _ = lookup_spell_detail(_cn2)
            if _csd3:
                _cp3 = _parse_spell_combat(_csd3)
                if _cp3:
                    _cd3, _ct3, _ca3, _cs3 = _cp3
                    _ch3 = "half" in _csd3.get("description", "").lower()
                    if _ca3 == "attack":
                        _pdf_acts.append({"name": _cn2, "category": "Cantrip", "hit": f"{_as_p} to hit", "save": None, "damage": f"{_cd3} {_ct3.lower()}", "note": "At will"})
                    elif _ca3 == "save":
                        _pdf_acts.append({"name": _cn2, "category": "Cantrip", "hit": None, "save": f"DC {_dc_p} {_cs3}", "damage": f"{_cd3} {_ct3.lower()}", "note": "At will" + (" / half on save" if _ch3 else "")})
                    else:
                        _pdf_acts.append({"name": _cn2, "category": "Cantrip", "hit": None, "save": None, "damage": f"{_cd3} {_ct3.lower()}", "note": "At will"})
        for _sn2 in st.session_state.get("chosen_spells", []):
            _ssd3, _slk3 = lookup_spell_detail(_sn2)
            if _ssd3:
                _sp3 = _parse_spell_combat(_ssd3)
                if _sp3:
                    _sd3, _st3, _sa3, _ss3 = _sp3
                    _slv3 = _spell_level_label(_slk3) if _slk3 else "Spell"
                    _sh3 = "half" in _ssd3.get("description", "").lower()
                    if _sa3 == "attack":
                        _pdf_acts.append({"name": _sn2, "category": _slv3, "hit": f"{_as_p} to hit", "save": None, "damage": f"{_sd3} {_st3.lower()}", "note": None})
                    elif _sa3 == "save":
                        _pdf_acts.append({"name": _sn2, "category": _slv3, "hit": None, "save": f"DC {_dc_p} {_ss3}", "damage": f"{_sd3} {_st3.lower()}", "note": "Half on save" if _sh3 else None})
                    elif _sa3 == "weapon_bonus":
                        _pdf_acts.append({"name": _sn2, "category": _slv3, "hit": None, "save": None, "damage": f"+{_sd3} {_st3.lower()} per hit", "note": "Bonus to weapon attacks / Conc."})
                    else:
                        _pdf_acts.append({"name": _sn2, "category": _slv3, "hit": None, "save": None, "damage": f"{_sd3} {_st3.lower()}", "note": "Auto-hit"})
    _pdf_acts.extend(_class_combat_actions(st.session_state.class_id or "", level, race, prof))
    if _pdf_acts:
        pdf.ln(1)
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "BI", 8)
        pdf.cell(0, 5, "ATTACKS & ACTIONS", ln=True)
        pdf.ln(0.5)
        _aw = pdf.w - 30
        _wn, _wc, _wr, _wd, _wo = _aw*0.26, _aw*0.13, _aw*0.20, _aw*0.20, _aw*0.21
        _x0 = pdf.l_margin
        for _act in _pdf_acts:
            _roll_str = _act.get("hit") or ((_act.get("save", "") + " save") if _act.get("save") else "")
            _y0 = pdf.get_y()
            _max_y = _y0 + 4.5  # minimum row height

            pdf.set_xy(_x0, _y0)
            pdf.set_text_color(*C_HDR_TEXT); pdf.set_font("Helvetica", "B", 8)
            pdf.multi_cell(_wn, 4.5, _pdf_safe(_act["name"]))
            _max_y = max(_max_y, pdf.get_y())

            pdf.set_xy(_x0 + _wn, _y0)
            pdf.set_text_color(*C_SUB); pdf.set_font("Helvetica", "I", 7.5)
            pdf.multi_cell(_wc, 4.5, _pdf_safe(f"[{_act['category']}]"))
            _max_y = max(_max_y, pdf.get_y())

            pdf.set_xy(_x0 + _wn + _wc, _y0)
            pdf.set_text_color(*C_STAT); pdf.set_font("Helvetica", "", 8)
            pdf.multi_cell(_wr, 4.5, _pdf_safe(_roll_str))
            _max_y = max(_max_y, pdf.get_y())

            pdf.set_xy(_x0 + _wn + _wc + _wr, _y0)
            pdf.set_text_color(*C_HDR_TEXT); pdf.set_font("Helvetica", "B", 8)
            pdf.multi_cell(_wd, 4.5, _pdf_safe(_act.get("damage", "")))
            _max_y = max(_max_y, pdf.get_y())

            pdf.set_xy(_x0 + _wn + _wc + _wr + _wd, _y0)
            pdf.set_text_color(*C_SUB); pdf.set_font("Helvetica", "I", 7)
            pdf.multi_cell(_wo, 4.5, _pdf_safe(_act.get("note") or ""))
            _max_y = max(_max_y, pdf.get_y())

            pdf.set_xy(_x0, _max_y)
        pdf.ln(2)

    # ── Saving Throws ──
    class_saves = cls["saves"] if cls else []
    _sec("SAVING THROWS")
    half_w = (pdf.w - 30) / 2
    save_pairs = list(zip(STAT_FULL, STAT_KEYS))
    for i, (full, key) in enumerate(save_pairs):
        eff = effective_stat(key, race)
        base_mod = modifier_int(eff)
        save_val = base_mod + (prof if key in class_saves else 0)
        sign = f"+{save_val}" if save_val >= 0 else str(save_val)
        is_prof = key in class_saves
        dot = "*" if is_prof else "o"
        pdf.set_text_color(*C_HDR_TEXT if is_prof else C_STAT)
        pdf.set_font("Helvetica", "B" if is_prof else "", 9)
        pdf.cell(half_w * 0.12, 5, dot)
        pdf.set_text_color(*C_STAT)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(half_w * 0.55, 5, _pdf_safe(full))
        pdf.set_text_color(*C_HDR_TEXT if is_prof else C_STAT)
        pdf.set_font("Helvetica", "B" if is_prof else "", 9)
        pdf.cell(half_w * 0.33, 5, sign)
        if i % 2 == 1:
            pdf.ln(5)
    if len(save_pairs) % 2 != 0:
        pdf.ln(5)
    pdf.ln(5)

    # ── Skills ──
    sheet_expertise = set(st.session_state.get("expertise_skills", []))
    _sec("SKILLS")
    skill_col_w = (pdf.w - 30) / 3
    for i, (sname, akey) in enumerate(ALL_SKILLS):
        is_exp   = sname in sheet_expertise
        eff_prof = prof * 2 if is_exp else prof
        mod_val  = skill_modifier(sname, akey, race, eff_prof, all_prof_skills, half_prof=joat_half_pdf)
        sign     = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
        is_joat  = joat_half_pdf and sname not in all_prof_skills and not is_exp
        is_prof  = sname in all_prof_skills
        dot      = "**" if is_exp else ("*" if is_prof else "o")
        joat_note = f" (+{joat_half_pdf})" if is_joat else ""
        # dot
        pdf.set_text_color(*(C_HDR_TEXT if (is_prof or is_exp) else C_SUB))
        pdf.set_font("Helvetica", "B" if (is_prof or is_exp) else "", 8)
        pdf.cell(skill_col_w * 0.10, 4.5, dot)
        # name
        pdf.set_text_color(*(C_HDR_TEXT if (is_prof or is_exp) else C_STAT))
        pdf.set_font("Helvetica", "B" if is_exp else ("" if not is_prof else ""), 8)
        pdf.cell(skill_col_w * 0.65, 4.5, _pdf_safe(sname + joat_note))
        # value
        pdf.set_text_color(*C_HDR_TEXT)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(skill_col_w * 0.25, 4.5, sign)
        if i % 3 == 2:
            pdf.ln(4.5)
    if len(ALL_SKILLS) % 3 != 0:
        pdf.ln(4.5)
    pdf.ln(4)

    # ── Features (class + subclass + background) ──
    cls_feats_data = CLASS_FEATURES.get(st.session_state.class_id or "", {})
    cls_feats = [f for f in cls_feats_data.get("features", []) if f.get("level", 1) <= level]
    sub_feats = [f for f in sub.get("features", []) if f.get("level", 1) <= level] if sub else []
    bg_feat_data = bg.get("feature", {}) if bg else {}

    has_features = cls_feats or sub_feats or bg_feat_data
    if has_features:
        _sec("FEATURES")

    if cls_feats:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, _pdf_safe(cls_name), ln=True)
        for feat_item in cls_feats:
            fi_name = feat_item["name"]
            if feat_item.get("level") == 3 and fi_name == "Elemental Shift" and sub:
                sub_form = next((f for f in sub.get("features", []) if f["level"] == 3), None)
                if sub_form:
                    fi_name = sub_form["name"]
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 4.5, _pdf_safe(f"[Lv.{feat_item['level']}] {fi_name}"), ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 3.5, _pdf_safe(feat_item.get("description", "")))
            pdf.ln(0.5)
        pdf.ln(2)

    if sub_feats:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, _pdf_safe(sub_name), ln=True)
        for feat_item in sub_feats:
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 4.5, _pdf_safe(f"[Lv.{feat_item['level']}] {feat_item['name']}"), ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 3.5, _pdf_safe(feat_item.get("description", "")))
            pdf.ln(0.5)
        pdf.ln(2)

    if bg and bg_feat_data:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, _pdf_safe(bg_name), ln=True)
        pdf.set_text_color(*C_HDR_TEXT)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 4.5, _pdf_safe(bg_feat_data.get("name", "")), ln=True)
        pdf.set_text_color(*C_BODY)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(0, 3.5, _pdf_safe(bg_feat_data.get("description", "")))
        pdf.ln(3)

    # ── Sev'rinn Elemental Sections ──
    if cls and cls["id"] == "sevrinn" and sub:
        sv_mech = cls.get("mechanics", {})

        # Find level row
        lvl_data = None
        for row in sv_mech.get("level_table", []):
            if row["min_level"] <= level <= row["max_level"]:
                lvl_data = row
                break

        # ─ Elemental Resources ─
        _sec("ELEMENTAL RESOURCES")
        if lvl_data:
            pdf.set_text_color(*C_STAT)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, _pdf_safe(
                f"Charges: {lvl_data['charges']}  |  Techniques Known: {lvl_data['techniques']}"
            ), ln=True)
            pdf.ln(1)

        pdf.set_text_color(*C_HDR_TEXT)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 4.5, "Weirding Surge:", ln=True)
        pdf.set_text_color(*C_BODY)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(0, 3.5, _pdf_safe(sv_mech.get("weirding_surge", "")))
        pdf.ln(1)

        es = sv_mech.get("elemental_shift", {})
        if es:
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 4.5, "Elemental Shift (Bonus Action, 1 Charge):", ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 3.5, _pdf_safe(
                f"Activation: {es.get('activation', '')}\n"
                f"Lock Mode: {es.get('lock_mode', '')}\n"
                f"Roll Mode: {es.get('roll_mode', '')}\n"
                f"Shifted Discount: {es.get('shift_discount', '')}\n"
                f"Re-entry: {es.get('reentry', '')}"
            ))
            pdf.ln(1)

        for cf in sv_mech.get("class_features", []):
            if cf["level"] <= level:
                pdf.set_text_color(*C_HDR_TEXT)
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 4.5, _pdf_safe(f"{cf['name']} (Level {cf['level']}):"), ln=True)
                pdf.set_text_color(*C_BODY)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(0, 3.5, _pdf_safe(cf["description"]))
                pdf.ln(0.5)
        pdf.ln(2)

        # ─ Elemental Form / Shift Table ─
        shift_table = sub.get("shift_table", [])
        if shift_table:
            form_name = sub["features"][0]["name"] if sub.get("features") else "Elemental Form"
            _sec(f"{form_name.upper()} — SHIFT TABLE (Bonus Action, 1 Charge)")
            form_feat = sub["features"][0] if sub.get("features") else None
            if form_feat:
                pdf.set_text_color(*C_BODY)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(0, 3.5, _pdf_safe(form_feat["description"]))
                pdf.ln(2)
            _x0_sh = pdf.l_margin
            _aw_sh = pdf.w - 30
            _rw, _nw, _ew = _aw_sh * 0.08, _aw_sh * 0.28, _aw_sh * 0.64
            for shift in shift_table:
                _y0 = pdf.get_y()
                _max_y = _y0 + 4.5
                pdf.set_xy(_x0_sh, _y0)
                pdf.set_text_color(*C_STAT)
                pdf.set_font("Helvetica", "B", 8)
                pdf.multi_cell(_rw, 4.5, _pdf_safe(f"({shift['roll']})"))
                _max_y = max(_max_y, pdf.get_y())
                pdf.set_xy(_x0_sh + _rw, _y0)
                pdf.set_text_color(*C_HDR_TEXT)
                pdf.set_font("Helvetica", "B", 8)
                pdf.multi_cell(_nw, 4.5, _pdf_safe(shift["name"]))
                _max_y = max(_max_y, pdf.get_y())
                pdf.set_xy(_x0_sh + _rw + _nw, _y0)
                pdf.set_text_color(*C_BODY)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(_ew, 4.5, _pdf_safe(shift["effect"]))
                _max_y = max(_max_y, pdf.get_y())
                pdf.set_xy(_x0_sh, _max_y)
            pdf.ln(2)

        # ─ Weirding Surge Table ─
        surge_table = sv_mech.get("weirding_surge_table", [])
        if surge_table:
            _sec("WEIRDING SURGE TABLE (roll d6 on every Charge spend)")
            _x0_sg = pdf.l_margin
            _aw_sg = pdf.w - 30
            _nw_sg = _aw_sg * 0.08
            for i, effect in enumerate(surge_table, 1):
                _y0 = pdf.get_y()
                _max_y = _y0 + 4.5
                pdf.set_xy(_x0_sg, _y0)
                pdf.set_text_color(*C_STAT)
                pdf.set_font("Helvetica", "B", 9)
                pdf.multi_cell(_nw_sg, 4.5, str(i))
                _max_y = max(_max_y, pdf.get_y())
                pdf.set_xy(_x0_sg + _nw_sg, _y0)
                pdf.set_text_color(*C_BODY)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(0, 4.5, _pdf_safe(effect))
                _max_y = max(_max_y, pdf.get_y())
                pdf.set_xy(_x0_sg, _max_y)
            pdf.ln(2)

        # ─ Combat Techniques (new page) ─
        techs = [t for t in sub.get("techniques", []) if t["level"] <= level]
        if techs:
            pdf.add_page()
            _sec("COMBAT TECHNIQUES")
            for tech in techs:
                usage = tech.get("usage", "")
                tech_level = tech["level"]
                if usage == "Elemental Shift use":
                    cost_str = "[Shift use]"
                elif any(x in usage for x in ["/Short Rest", "/Long Rest", "/7 days", "proficiency bonus"]):
                    cost_str = f"[{usage}]"
                elif tech_level <= 3:
                    cost_str = "[1C]"
                elif tech_level <= 10:
                    cost_str = "[2C / 1C Shifted]"
                else:
                    cost_str = "[3C / 2C Shifted]"
                pdf.set_text_color(*C_HDR_TEXT)
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 4.5, _pdf_safe(f"[Lv.{tech_level}] {tech['name']}  {cost_str}"), ln=True)
                pdf.set_text_color(*C_BODY)
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(0, 3.5, _pdf_safe(tech.get("description", "")))
                pdf.ln(0.5)
            pdf.ln(2)

    # ── Racial Traits ──
    pdf_race_traits = race.get("traits", []) if race else []
    if pdf_race_traits:
        _pdf_anc = None
        if race and race["id"] == "drakarim":
            _chosen_anc_pdf = st.session_state.get("draconic_ancestry", "")
            _pdf_anc = next((x for x in race.get("draconic_ancestry_table", []) if x["dragon"] == _chosen_anc_pdf), None)
        _sec("RACIAL TRAITS")
        for trait in pdf_race_traits:
            t_name = trait["name"]
            t_desc = trait["description"]
            if _pdf_anc:
                if t_name == "Draconic Ancestry":
                    t_desc = (f"{_pdf_anc['dragon']} Dragon ({_pdf_anc['damage_type']}). "
                              f"Breath weapon: {_pdf_anc['breath']}, {_pdf_anc['save']} save.")
                elif t_name == "Draconic Resistance":
                    t_desc = f"Resistance to {_pdf_anc['damage_type'].lower()} damage."
                elif t_name == "Breath Weapon":
                    t_desc = (f"{_pdf_anc['breath']} ({_pdf_anc['save']} save, DC = 8 + proficiency bonus + CON modifier). "
                              f"2d6 {_pdf_anc['damage_type'].lower()} damage on a failed save, half on success. "
                              f"Recharges on a short or long rest.")
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 4.5, _pdf_safe(t_name), ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 3.5, _pdf_safe(t_desc))
            pdf.ln(0.5)
        pdf.ln(2)

    # ── Character Details (after Features) ──
    details = [
        ("Personality Traits", st.session_state.get("personality", "")),
        ("Ideals",             st.session_state.get("ideals", "")),
        ("Bonds",              st.session_state.get("bonds", "")),
        ("Flaws",              st.session_state.get("flaws", "")),
        ("Notes",              st.session_state.get("notes", "")),
    ]
    if any(v for _, v in details):
        _sec("CHARACTER DETAILS")
        for label, val in details:
            if not val:
                continue
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, _pdf_safe(label), ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 4.5, _pdf_safe(val))
            pdf.ln(1)
        pdf.ln(2)

    # ── Combat Tactics ──
    ct_pdf = st.session_state.get("combat_tactics", {})
    if ct_pdf:
        _sec("COMBAT TACTICS")
        if ct_pdf.get("role"):
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(0, 3.8, _pdf_safe(ct_pdf["role"]))
            pdf.ln(2)
        for _tac in ct_pdf.get("tactics", []):
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(0, 4.5, _pdf_safe(_tac.get("phase", "")), ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(0, 3.5, _pdf_safe(_tac.get("text", "")))
            pdf.ln(0.5)
        pdf.ln(2)

    # ── Spellcasting ──
    mech_pdf = get_mech(st.session_state.class_id or "")
    sc_data = mech_pdf.get("spellcasting")
    chosen_c = st.session_state.get("chosen_cantrips", [])
    chosen_s = st.session_state.get("chosen_spells", [])
    if sc_data and st.session_state.class_id != "sevrinn":
        sc_ability = sc_data["ability"]
        sc_key_map = {"Wisdom": "WIS", "Intelligence": "INT", "Charisma": "CHA"}
        sc_key  = sc_key_map.get(sc_ability, "WIS")
        sc_mod  = modifier_int(effective_stat(sc_key, race))
        spell_dc  = 8 + prof + sc_mod
        spell_atk = f"+{prof + sc_mod}" if (prof + sc_mod) >= 0 else str(prof + sc_mod)
        cantrips  = sc_data.get("cantrips_known")
        cantrips_val = str(cantrips[min(level - 1, 19)]) if cantrips else "--"
        slots = get_spell_slots(sc_data.get("slot_type"), level)

        _sec(f"SPELLCASTING ({sc_ability.upper()})")
        sc_stats = [
            ("Spell Save DC", str(spell_dc)),
            ("Spell Attack", spell_atk),
            ("Cantrips Known", cantrips_val),
        ]
        for label, val in sc_stats:
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(third_w * 0.65, 5, _pdf_safe(label + ":"))
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(third_w * 0.35, 5, _pdf_safe(val))
        pdf.ln(6)
        if slots:
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 4.5, "Spell Slots:", ln=True)
            pdf.set_text_color(*C_STAT)
            pdf.set_font("Helvetica", "", 9)
            slot_str = "  |  ".join(f"{lvl}: {cnt}" for lvl, cnt in slots)
            pdf.cell(0, 4.5, _pdf_safe(slot_str), ln=True)
        if chosen_c:
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, "Cantrips:", ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 4.5, _pdf_safe(", ".join(chosen_c)), ln=True)
        if chosen_s:
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, "Known / Prepared Spells:", ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 4.5, _pdf_safe(", ".join(chosen_s)), ln=True)
        pdf.ln(3)

    # ── Equipment & Armor/Weapons ──
    mech_eq = mech_pdf
    eq_fixed   = mech_eq.get("equipment_fixed", [])
    eq_choices = mech_eq.get("equipment_choices", [])
    eq_items   = list(eq_fixed)
    for choice in eq_choices:
        cid = choice["id"]
        idx = st.session_state.equip_choices.get(cid, 0)
        if idx < len(choice["options"]):
            eq_items.extend(choice["options"][idx]["items"])
    if bg:
        eq_items.append(bg.get("equipment", ""))
    main_wep_pdf = get_weapon(st.session_state.get("equipped_main"))
    off_wep_pdf  = get_weapon(st.session_state.get("equipped_offhand"))
    if main_wep_pdf:
        eq_items.append(f"{main_wep_pdf['name']} (main hand)")
    if off_wep_pdf:
        eq_items.append(f"{off_wep_pdf['name']} (off-hand)")
    armor_weapons = (cls.get("armor", []) + cls.get("weapons", [])) if cls else []

    _sec("EQUIPMENT & ARMOR / WEAPONS")
    if armor_weapons:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 4.5, "Proficiencies:", ln=True)
        pdf.set_text_color(*C_BODY)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 4.5, _pdf_safe(", ".join(armor_weapons)), ln=True)
        pdf.ln(1)
    if eq_items:
        pdf.set_text_color(*C_SUB)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 4.5, "Carried:", ln=True)
        pdf.set_text_color(*C_BODY)
        pdf.set_font("Helvetica", "", 9)
        for item in eq_items:
            if item:
                pdf.cell(0, 4.5, _pdf_safe(f"- {item}"), ln=True)

    # ── Languages ──
    race_langs = [l for l in (race.get("languages", []) if race else [])
                  if "of your choice" not in l.lower()]
    chosen_langs = [l for l in st.session_state.get("chosen_languages", [])
                    if "of your choice" not in l.lower()]
    all_langs = list(dict.fromkeys(race_langs + chosen_langs))
    tool_profs = bg.get("tool_proficiencies", []) if bg else []
    if all_langs or tool_profs:
        pdf.ln(2)
        _sec("LANGUAGES & TOOLS")
        if all_langs:
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 4.5, "Languages:", ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 4.5, _pdf_safe(", ".join(all_langs)), ln=True)
        if tool_profs:
            pdf.ln(1)
            pdf.set_text_color(*C_SUB)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 4.5, "Tool Proficiencies:", ln=True)
            pdf.set_text_color(*C_BODY)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 4.5, _pdf_safe(", ".join(tool_profs)), ln=True)

    # ── Spell Details (last page) ──
    all_pdf_spells = chosen_c + chosen_s
    if all_pdf_spells:
        _slot_dict_pdf, _is_pact_pdf = _build_slot_dict(sc_data, level)
        _spells_by_lk_pdf = {}
        for sn in chosen_s:
            _, lk = lookup_spell_detail(sn)
            if lk:
                _spells_by_lk_pdf.setdefault(lk, []).append(sn)
        _sorted_lks_pdf = sorted(_spells_by_lk_pdf.keys(), key=lambda x: int(x) if x.isdigit() else 0)

        pdf.add_page()
        _sec("SPELL DETAILS")
        pdf.ln(1)

        def _pdf_spell_entry(spell_name, lk):
            sp, _ = lookup_spell_detail(spell_name)
            if not sp:
                return
            school = sp.get("school", "")
            meta = f"{_spell_level_label(lk)}{' -- ' + school if school else ''}"
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.cell(0, 6, _pdf_safe(spell_name), ln=True)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*C_SUB)
            pdf.cell(0, 4.5, _pdf_safe(meta), ln=True)
            stat_parts = []
            if sp.get("casting_time"): stat_parts.append(f"Casting Time: {sp['casting_time']}")
            if sp.get("range"):        stat_parts.append(f"Range: {sp['range']}")
            if sp.get("components"):   stat_parts.append(f"Components: {sp['components']}")
            if sp.get("duration"):     stat_parts.append(f"Duration: {sp['duration']}")
            if stat_parts:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*C_STAT)
                pdf.cell(0, 4.5, _pdf_safe("  |  ".join(stat_parts)), ln=True)
            if sp.get("description"):
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*C_BODY)
                pdf.multi_cell(0, 4.5, _pdf_safe(sp["description"]))
            pdf.ln(2.5)

        def _pdf_level_subheader(lk):
            cast_lbl = _spell_cast_label(lk, _slot_dict_pdf, _is_pact_pdf)
            lv_text = "CANTRIPS" if lk == "cantrips" else _spell_level_label(lk).upper()
            header = f"{lv_text}  --  {cast_lbl}" if cast_lbl else lv_text
            pdf.set_fill_color(30, 18, 44)
            pdf.set_text_color(*C_HDR_TEXT)
            pdf.set_font("Helvetica", "BI", 8)
            pdf.cell(0, 6, _pdf_safe(header), ln=True, fill=True)
            pdf.ln(1)

        if chosen_c:
            _pdf_level_subheader("cantrips")
            for sn in chosen_c:
                _pdf_spell_entry(sn, "cantrips")
        for lk in _sorted_lks_pdf:
            _pdf_level_subheader(lk)
            for sn in _spells_by_lk_pdf[lk]:
                _pdf_spell_entry(sn, lk)

    return bytes(pdf.output())

# ─────────────────────────────────────────────────────────────────────────────
# STEP BAR
# ─────────────────────────────────────────────────────────────────────────────
STEPS = ["Basics", "Race", "Class", "Features", "Background", "Stats", "Skills", "Gear & Inventory", "Feats", "Sheet"]

def render_step_bar():
    current = st.session_state.step
    html = '<div class="step-bar">'
    for i, label in enumerate(STEPS, 1):
        if i == current:
            css = "active"
        elif i < current:
            css = "done"
        else:
            css = ""
        html += f'<div class="step-node"><div class="step-circle {css}">{i}</div><div class="step-label {css}">{label}</div></div>'
        if i < len(STEPS):
            conn_css = "done" if i < current else ""
            html += f'<div class="step-connector {conn_css}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-title">
  <h1>🐉 Ryndor: The Weirded Lands</h1>
  <p>Choose Your Fate — Character Sheet Builder</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CHARACTER IMPORT HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _apply_character_upload(uploaded_file):
    """Load a character JSON into session state. Returns True on success."""
    if uploaded_file is None:
        return False
    # Guard against re-processing the same file on every rerun
    if st.session_state.get("_loaded_file") == uploaded_file.name:
        return False
    try:
        saved = json.load(uploaded_file)
        for k, v in defaults.items():
            if k == "step":
                continue
            st.session_state[k] = saved.get(k, v)
        st.session_state.step = 10
        st.session_state["_loaded_file"] = uploaded_file.name
        return True
    except Exception as e:
        st.error(f"Could not load file: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Load Character
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📂 Load Character")
    sidebar_upload = st.file_uploader("Upload a saved character (.json)", type="json", label_visibility="collapsed")
    if _apply_character_upload(sidebar_upload):
        st.rerun()

render_step_bar()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — BASICS
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.step == 1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📂 Import Character</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif; color:#a99cbf; font-style:italic; margin-bottom:1rem;">Already have a saved character? Upload it here to pick up where you left off.</p>', unsafe_allow_html=True)
    step1_upload = st.file_uploader("Upload character JSON", type="json", label_visibility="collapsed", key="step1_upload")
    if _apply_character_upload(step1_upload):
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">⚔️ Character Basics</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family: Crimson Text, serif; color: #a99cbf; font-style: italic; margin-bottom:1.5rem;">In a world as vast and diverse as Ryndor, every face tells a story and every soul carries the essence of something greater. What story will yours tell?</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.session_state.char_name = st.text_input("Character Name", st.session_state.char_name, placeholder="e.g. Isera Wyrgleam")
    with col2:
        st.session_state.player_name = st.text_input("Player Name", st.session_state.player_name, placeholder="Your name")
    with col3:
        st.session_state.char_level = st.number_input("Level", min_value=1, max_value=20, value=st.session_state.char_level)

    alignments = [
        "Lawful Good", "Neutral Good", "Chaotic Good",
        "Lawful Neutral", "True Neutral", "Chaotic Neutral",
        "Lawful Evil", "Neutral Evil", "Chaotic Evil"
    ]
    st.session_state.alignment = st.selectbox(
        "Alignment",
        alignments,
        index=alignments.index(st.session_state.alignment) if st.session_state.alignment in alignments else 4
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🎲 Roll Random Character", use_container_width=True,
                 help="Randomly pick race, class, background, stats and jump to the sheet."):
        generate_random_character()
        with st.spinner("✨ Weaving your fate…"):
            _ai_enrich_character()
        st.session_state.step = 10
        st.rerun()

    _, right = st.columns([6, 1])
    with right:
        if st.button("Next →", type="primary", use_container_width=True):
            if not st.session_state.char_name.strip():
                st.error("Please enter a character name.")
            else:
                st.session_state.step = 2
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — RACE
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 2:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🌍 Choose Your Race</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-family: Crimson Text, serif; color: #a99cbf; font-style: italic; margin-bottom:1rem;">The people of Ryndor are as varied as the lands they tread.</p>', unsafe_allow_html=True)

        for race in RACES:
            selected = st.session_state.race_id == race["id"]
            sel_cls = "selected" if selected else ""
            st.markdown(
                f'<div class="sel-card {sel_cls}" id="race-{race["id"]}">'
                f'<div class="icon">{race["icon"]}</div>'
                f'<h3>{race["name"]}</h3>'
                f'<p>{race["description"][:110]}…</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Select {race['name']}", key=f"race_{race['id']}", use_container_width=True):
                st.session_state.race_id = race["id"]
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        race = get_race(st.session_state.race_id)
        if race:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; font-size:3rem; margin-bottom:0.5rem">{race["icon"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<h2 style="font-family:Cinzel,serif; color:#a78bfa; text-align:center; font-size:1.6rem; margin:0 0 0.3rem">{race["name"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:Crimson Text,serif; font-style:italic; color:#9d8dbf; text-align:center; margin:0 0 1rem">{race.get("flavor","")}</p>', unsafe_allow_html=True)

            # ASI
            asi = race.get("ability_scores", {})
            if isinstance(asi, dict):
                note = asi.get("note", "")
                badges = " ".join([
                    f'<span class="badge">+{v} {k}</span>'
                    for k, v in asi.items() if k != "note" and isinstance(v, int)
                ])
                if note:
                    badges += f' <span class="badge crimson">{note}</span>'
                st.markdown(f'<div style="margin:0.5rem 0">{badges}</div>', unsafe_allow_html=True)

            # Speed
            spd = race.get("speed", {})
            speed_parts = []
            if spd.get("walk"):
                speed_parts.append(f'<span class="badge">🚶 {spd["walk"]} ft</span>')
            if spd.get("fly"):
                speed_parts.append(f'<span class="badge teal">🦅 {spd["fly"]} ft fly</span>')
            if spd.get("note"):
                speed_parts.append(f'<span class="badge crimson" style="font-size:0.65rem">{spd["note"]}</span>')
            st.markdown(f'<div style="margin:0.3rem 0">{"".join(speed_parts)}</div>', unsafe_allow_html=True)

            # Languages
            langs = " ".join([f'<span class="badge teal">🗣 {l}</span>' for l in race.get("languages", [])])
            st.markdown(f'<div style="margin:0.3rem 0">{langs}</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-header" style="margin-top:1rem">Racial Traits</div>', unsafe_allow_html=True)
            for trait in race.get("traits", []):
                st.markdown(
                    f'<div class="trait-block"><div class="name">{trait["name"]}</div>'
                    f'<div class="desc">{trait["description"]}</div></div>',
                    unsafe_allow_html=True
                )

            # Draconic Ancestry picker (Drakarim only)
            if race["id"] == "drakarim":
                anc_table = race.get("draconic_ancestry_table", [])
                if anc_table:
                    st.markdown('<div class="section-header" style="margin-top:1rem">🐉 Draconic Ancestry</div>', unsafe_allow_html=True)
                    anc_by_dragon = {a["dragon"]: a for a in anc_table}
                    anc_names = [a["dragon"] for a in anc_table]
                    current_anc = st.session_state.get("draconic_ancestry", "")
                    anc_idx = anc_names.index(current_anc) if current_anc in anc_names else 0
                    chosen_anc = st.selectbox(
                        "Choose your dragon type",
                        options=anc_names,
                        index=anc_idx,
                        format_func=lambda d: f"{d} Dragon  —  {anc_by_dragon[d]['damage_type']}",
                        key="da_select",
                    )
                    if chosen_anc != st.session_state.get("draconic_ancestry", ""):
                        st.session_state.draconic_ancestry = chosen_anc
                        st.rerun()
                    a = anc_by_dragon[chosen_anc]
                    st.markdown(
                        f'<div class="trait-block">'
                        f'<div class="name">Breath Weapon — {a["damage_type"]}</div>'
                        f'<div class="desc">{a["breath"]} ({a["save"]} save, DC = 8 + proficiency bonus + CON modifier). '
                        f'2d6 {a["damage_type"].lower()} damage on a failed save, half on success. '
                        f'Recharges on a short or long rest.</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f'<div class="trait-block">'
                        f'<div class="name">Damage Resistance</div>'
                        f'<div class="desc">Resistance to {a["damage_type"].lower()} damage.</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # Age/Size/Alignment
            st.markdown(f'<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.88rem; margin-top:0.8rem"><b style="color:#a78bfa">Age:</b> {race.get("age","")} &nbsp;|&nbsp; <b style="color:#a78bfa">Size:</b> {race.get("size","")} &nbsp;|&nbsp; <b style="color:#a78bfa">Alignment:</b> {race.get("alignment","")}</p>', unsafe_allow_html=True)

            # Suggested classes
            sc = ", ".join(race.get("suggested_classes", []))
            st.markdown(f'<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.88rem"><b style="color:#a78bfa">Suggested Classes:</b> {sc}</p>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic; text-align:center; padding:2rem">← Select a race to see its details</p></div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True):
            if not st.session_state.race_id:
                st.error("Please select a race.")
            else:
                st.session_state.step = 3
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — CLASS
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 3:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">⚔️ Choose Your Class</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-family: Crimson Text, serif; color: #a99cbf; font-style: italic; margin-bottom:1rem;">Every adventurous road in Ryndor has its calling.</p>', unsafe_allow_html=True)

        for cls in CLASSES:
            selected = st.session_state.class_id == cls["id"]
            sel_cls_css = "selected" if selected else ""
            subs = cls.get("subclasses", [])
            sub_names = " · ".join(s["name"] for s in subs)
            st.markdown(
                f'<div class="sel-card {sel_cls_css}">'
                f'<div style="display:flex; align-items:center; gap:0.7rem">'
                f'<span style="font-size:1.5rem">{cls["icon"]}</span>'
                f'<div><h3 style="margin:0">{cls["name"]}</h3>'
                f'<p style="margin:0; font-size:0.82rem; color:#4e3d6e">{sub_names}</p></div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Select {cls['name']}", key=f"cls_{cls['id']}", use_container_width=True):
                if st.session_state.class_id != cls["id"]:
                    st.session_state.class_id = cls["id"]
                    st.session_state.subclass_id = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        cls = get_class(st.session_state.class_id)
        if cls:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; font-size:2.5rem; margin-bottom:0.3rem">{cls["icon"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<h2 style="font-family:Cinzel,serif; color:#a78bfa; text-align:center; margin:0 0 0.5rem">{cls["name"]}</h2>', unsafe_allow_html=True)

            # Core stats
            hit = f'<span class="badge">❤️ Hit Die: {cls["hit_die"]}</span>'
            primary = f'<span class="badge teal">✨ {cls["primary_ability"]}</span>'
            saves = " ".join([f'<span class="badge crimson">🛡 {s}</span>' for s in cls["saves"]])
            st.markdown(f'<div style="text-align:center; margin-bottom:0.5rem">{hit} {primary} {saves}</div>', unsafe_allow_html=True)

            st.markdown(f'<p style="font-family:Crimson Text,serif; font-style:italic; color:#9d8dbf; margin:0.5rem 0">{cls["flavor"]}</p>', unsafe_allow_html=True)

            # Skills
            st.markdown(f'<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.88rem"><b style="color:#a78bfa">Skills:</b> {cls["skills"]}</p>', unsafe_allow_html=True)

            # Special note for Sev'rinn
            if cls["id"] == "sevrinn":
                st.markdown(f'<div class="ryndor-alert">⚠️ {cls["special_note"]}</div>', unsafe_allow_html=True)
                # Elemental Charges info block
                level = st.session_state.char_level
                sv_mech = cls.get("mechanics", {})
                lvl_data = None
                for row in sv_mech.get("level_table", []):
                    if row["min_level"] <= level <= row["max_level"]:
                        lvl_data = row
                        break
                if not lvl_data:
                    # fallback: use the highest row at or below level
                    for row in sv_mech.get("level_table", []):
                        if row["min_level"] <= level:
                            lvl_data = row
                if lvl_data:
                    st.markdown(
                        f'<div style="background:rgba(167,139,250,0.08);border:1px solid rgba(167,139,250,0.25);'
                        f'border-radius:6px;padding:0.75rem 1rem;margin:0.6rem 0;font-family:Crimson Text,serif">'
                        f'<div style="font-family:Cinzel,serif;color:#a78bfa;font-size:0.8rem;letter-spacing:0.1em;margin-bottom:0.4rem">⚡ ELEMENTAL CHARGES</div>'
                        f'<p style="margin:0.15rem 0;color:#c4b5fd;font-size:0.95rem">At level {level} you have <b>{lvl_data["charges"]}</b> charges (restored on short or long rest).</p>'
                        f'<p style="margin:0.15rem 0;color:#a99cbf;font-size:0.9rem"><b style="color:#c4b5fd">Weirding Surge:</b> Roll d6 when spending charges; the result on the Surge Table always occurs.</p>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                # Resonant Flow (level 9+)
                if level >= 9:
                    rf = next((f for f in sv_mech.get("class_features", []) if f["level"] == 9), None)
                    if rf:
                        st.markdown(
                            f'<div style="background:rgba(34,211,238,0.07);border-left:3px solid #22d3ee;border-radius:0 4px 4px 0;padding:0.5rem 0.8rem;margin:0.3rem 0;font-family:Crimson Text,serif">'
                            f'<span style="font-family:Cinzel,serif;color:#67e8f9;font-size:0.8rem">{rf["name"]} (Level 9):</span> '
                            f'<span style="color:#a99cbf;font-size:0.9rem">{rf["description"]}</span></div>',
                            unsafe_allow_html=True
                        )
                # Elemental Avatar (level 17+)
                if level >= 17:
                    ea = next((f for f in sv_mech.get("class_features", []) if f["level"] == 17), None)
                    if ea:
                        st.markdown(
                            f'<div style="background:rgba(251,191,36,0.07);border-left:3px solid #fbbf24;border-radius:0 4px 4px 0;padding:0.5rem 0.8rem;margin:0.3rem 0;font-family:Crimson Text,serif">'
                            f'<span style="font-family:Cinzel,serif;color:#fcd34d;font-size:0.8rem">{ea["name"]} (Level 17):</span> '
                            f'<span style="color:#a99cbf;font-size:0.9rem">{ea["description"]}</span></div>',
                            unsafe_allow_html=True
                        )

            # Subclass selection
            st.markdown('<div class="section-header">Choose Your Path</div>', unsafe_allow_html=True)
            subs = cls.get("subclasses", [])
            for sub in subs:
                selected = st.session_state.subclass_id == sub["id"]
                sel_css = "selected" if selected else ""
                st.markdown(
                    f'<div class="sel-card {sel_css}">'
                    f'<h3 style="margin:0 0 0.3rem">{sub["name"]}</h3>'
                    f'<p style="margin:0">{sub["description"]}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button(f"Choose {sub['name']}", key=f"sub_{sub['id']}", use_container_width=True):
                    st.session_state.subclass_id = sub["id"]
                    st.rerun()

            # Feature preview for selected subclass
            sub = get_subclass(cls, st.session_state.subclass_id)
            if sub:
                level = st.session_state.char_level
                st.markdown(f'<div class="section-header" style="margin-top:1rem">{sub["name"]} Features</div>', unsafe_allow_html=True)

                # Patron list for Warlock
                if "patrons" in sub:
                    st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.85rem; margin-bottom:0.3rem">Available Rift Patrons:</p>', unsafe_allow_html=True)
                    for patron in sub["patrons"]:
                        st.markdown(
                            f'<div class="trait-block"><div class="name">{patron["name"]}</div>'
                            f'<div class="desc">{patron["description"]}</div></div>',
                            unsafe_allow_html=True
                        )

                # Oath spells or domain spells
                for spell_key in ["domain_spells", "oath_spells", "circle_spells"]:
                    if spell_key in sub:
                        with st.expander(f"📜 {sub['name']} Spells"):
                            for lvl, spells in sub[spell_key].items():
                                spell_list = ", ".join(spells)
                                st.markdown(f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin:0.2rem 0"><b style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.8rem">{lvl}:</b> {spell_list}</p>', unsafe_allow_html=True)

                # Features up to current level
                features = sub.get("features", [])
                available = [f for f in features if f["level"] <= level]
                future = [f for f in features if f["level"] > level]

                if available:
                    for feat in available:
                        st.markdown(
                            f'<div class="trait-block">'
                            f'<div class="name">{feat["name"]} <span style="color:#4e3d6e; font-size:0.78rem">(Level {feat["level"]})</span></div>'
                            f'<div class="desc">{feat["description"]}</div></div>',
                            unsafe_allow_html=True
                        )
                if future:
                    st.markdown(f'<p style="font-family:Cinzel,serif; color:#4e3d6e; font-size:0.78rem; margin-top:0.5rem">+{len(future)} more features at higher levels</p>', unsafe_allow_html=True)

                # Sev'rinn special: show shift table and techniques
                if cls["id"] == "sevrinn" and "shift_table" in sub:
                    form_name = sub["features"][0]["name"] if sub.get("features") else "Elemental Form"
                    with st.expander(f"🌀 {form_name} — Shift Table"):
                        # Lock vs Roll explanation
                        st.markdown(
                            '<div style="font-family:Crimson Text,serif;color:#a99cbf;font-size:0.88rem;'
                            'background:rgba(167,139,250,0.07);border-radius:4px;padding:0.5rem 0.8rem;margin-bottom:0.6rem">'
                            '<b style="font-family:Cinzel,serif;color:#a78bfa;font-size:0.82rem">Activate (bonus action, 1 Charge):</b><br>'
                            '• <b style="color:#c4b5fd">Lock</b> — Choose one effect; it lasts the full duration.<br>'
                            '• <b style="color:#c4b5fd">Roll</b> — Roll d6; freely re-roll at start of each turn.<br>'
                            '<b style="color:#67e8f9">While Shifted:</b> all techniques cost 1 fewer Charge (min 1).<br>'
                            'End freely on your turn; re-activate anytime for 1 Charge.'
                            '</div>',
                            unsafe_allow_html=True
                        )
                        st.markdown('<table class="surge-table"><tr><th>d6</th><th>Effect</th><th>Description</th></tr>', unsafe_allow_html=True)
                        for entry in sub["shift_table"]:
                            st.markdown(f'<tr><td>{entry["roll"]}</td><td style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.85rem">{entry["name"]}</td><td>{entry["effect"]}</td></tr>', unsafe_allow_html=True)
                        st.markdown('</table>', unsafe_allow_html=True)

                    techs = sub.get("techniques", [])
                    avail_techs = [t for t in techs if t["level"] <= level]
                    if avail_techs:
                        with st.expander(f"⚗️ Combat Techniques ({len(avail_techs)} available)"):
                            for tech in avail_techs:
                                # Determine charge cost badge
                                usage = tech.get("usage", "")
                                tech_level = tech["level"]
                                if usage in ("Elemental Shift use",):
                                    cost_badge = '[Shift use]'
                                    badge_color = '#a78bfa'
                                elif usage.startswith("Costs 1 Elemental Charge") or tech_level <= 3:
                                    cost_badge = '[1 Charge]'
                                    badge_color = '#4ade80'
                                elif tech_level <= 10:
                                    cost_badge = '[2C / 1C Shifted]'
                                    badge_color = '#fbbf24'
                                else:
                                    cost_badge = '[3C / 2C Shifted]'
                                    badge_color = '#f87171'
                                # If usage is a rest-based resource, show that instead
                                if any(x in usage for x in ['/Short Rest', '/Long Rest', '/7 days', 'proficiency bonus']):
                                    cost_badge = f'[{usage}]'
                                    badge_color = '#94a3b8'
                                st.markdown(
                                    f'<div class="trait-block">'
                                    f'<div class="name">{tech["name"]} '
                                    f'<span style="color:#4e3d6e; font-size:0.78rem">(Lv {tech["level"]})</span> '
                                    f'<span style="color:{badge_color}; font-size:0.75rem; font-family:Cinzel,serif">{cost_badge}</span>'
                                    f'</div>'
                                    f'<div class="desc">{tech["description"]}</div></div>',
                                    unsafe_allow_html=True
                                )

                    # Level table
                    if "mechanics" in cls:
                        with st.expander("📊 Sev'rinn Level Table"):
                            st.markdown('<table class="surge-table"><tr><th>Level</th><th>Charges</th><th>Techniques</th></tr>', unsafe_allow_html=True)
                            for row in cls["mechanics"]["level_table"]:
                                hl = "color:#a78bfa; font-weight:bold" if row["min_level"] <= level <= row["max_level"] else ""
                                st.markdown(f'<tr><td style="{hl}">{row["range"]}</td><td>{row["charges"]}</td><td>{row["techniques"]}</td></tr>', unsafe_allow_html=True)
                            st.markdown('</table>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic; text-align:center; padding:2rem">← Select a class to see its details</p></div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True):
            if not st.session_state.class_id:
                st.error("Please select a class.")
            elif not st.session_state.subclass_id:
                st.error("Please select a subclass.")
            else:
                st.session_state.step = 4
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — CLASS FEATURES & CHOICES
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 4:
    cls   = get_class(st.session_state.class_id)
    level = st.session_state.char_level

    cf_data  = CLASS_FEATURES.get(st.session_state.class_id or "", {})
    features = cf_data.get("features", [])
    choices  = cf_data.get("choices", [])

    # Filter to current level
    avail_feats   = [f for f in features if f["level"] <= level]
    avail_choices = [c for c in choices  if c["level"] <= level]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header">✨ Features</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0 0 0.6rem">{cls["name"] if cls else "Class"}</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="font-family:Crimson Text,serif; color:#a99cbf; font-style:italic; margin-bottom:1rem">'
        'Review your class features and make any required choices for your level.</p>',
        unsafe_allow_html=True
    )

    # ── Interactive choices ──
    if avail_choices:
        st.markdown('<div class="section-header" style="margin-top:0">Required Choices</div>', unsafe_allow_html=True)
        class_opts = dict(st.session_state.class_options)

        for choice in avail_choices:
            key       = choice["key"]
            pick      = choice["pick"]
            ctype     = choice["type"]
            options   = choice.get("options", [])
            level_req = choice["level"]

            st.markdown(
                f'<div style="margin:1.2rem 0 0.4rem">'
                f'<span style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.95rem; font-weight:700">'
                f'{choice["name"]}</span>'
                f'<span style="font-family:Cinzel,serif; color:#4e3d6e; font-size:0.75rem; margin-left:0.5rem">'
                f'(Level {level_req})</span></div>'
                f'<p style="font-family:Crimson Text,serif; color:#9d8dbf; font-size:0.92rem; margin:0 0 0.6rem">'
                f'{choice["description"]}</p>',
                unsafe_allow_html=True
            )

            current_val = class_opts.get(key)

            if ctype == "single_choice":
                opt_labels = [o["name"] for o in options]
                opt_descs  = {o["name"]: o["description"] for o in options}
                opt_ids    = {o["name"]: o["id"] for o in options}
                try:
                    cur_idx = next(
                        (i for i, o in enumerate(options) if o["id"] == current_val), 0
                    )
                except Exception:
                    cur_idx = 0
                sel = st.radio(
                    choice["name"],
                    opt_labels,
                    index=cur_idx,
                    key=f"cf_{key}",
                    label_visibility="collapsed"
                )
                class_opts[key] = opt_ids[sel]
                st.markdown(
                    f'<p style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.88rem; '
                    f'font-style:italic; margin:0.2rem 0 0; padding-left:0.5rem">'
                    f'{opt_descs[sel]}</p>',
                    unsafe_allow_html=True
                )

            elif ctype == "multi_choice":
                selected_ids = current_val if isinstance(current_val, list) else []
                new_selected = list(selected_ids)
                for opt in options:
                    is_checked = opt["id"] in new_selected
                    at_limit   = len(new_selected) >= pick and not is_checked
                    label_text = opt["name"] + (f" — *{opt['description']}*" if not at_limit else f" — {opt['description']}")
                    if at_limit and not is_checked:
                        label_text = opt["name"] + " *(limit reached)*"
                    checked = st.checkbox(
                        f"**{opt['name']}** — {opt['description']}",
                        value=is_checked,
                        disabled=at_limit,
                        key=f"cf_{key}_{opt['id']}"
                    )
                    if checked and opt["id"] not in new_selected:
                        new_selected.append(opt["id"])
                    elif not checked and opt["id"] in new_selected:
                        new_selected.remove(opt["id"])
                class_opts[key] = new_selected[:pick]
                st.markdown(
                    f'<p style="font-family:Cinzel,serif; color:#{"a78bfa" if len(new_selected)==pick else "e04040"}; '
                    f'font-size:0.78rem; margin-top:0.3rem">'
                    f'Selected: {len(new_selected)}/{pick}</p>',
                    unsafe_allow_html=True
                )

        st.session_state.class_options = class_opts

    elif not avail_feats:
        st.markdown(
            '<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic">'
            'No class features or choices available yet — check back as you level up!</p>',
            unsafe_allow_html=True
        )

    # ── Automatic features ──
    if avail_feats:
        st.markdown(
            f'<div class="section-header" style="margin-top:1.2rem">'
            f'Features at Level {level}</div>',
            unsafe_allow_html=True
        )
        for feat in avail_feats:
            st.markdown(
                f'<div class="trait-block">'
                f'<div class="name">{feat["name"]} '
                f'<span style="color:#4e3d6e; font-size:0.75rem">(Level {feat["level"]})</span></div>'
                f'<div class="desc">{feat["description"]}</div></div>',
                unsafe_allow_html=True
            )

    # ── Subclass features ──
    sub_feat_step = get_subclass(cls, st.session_state.subclass_id)
    if sub_feat_step:
        avail_sub_feats = [f for f in sub_feat_step.get("features", []) if f["level"] <= level]
        if avail_sub_feats:
            st.markdown(
                f'<div class="section-header" style="margin-top:1.2rem">'
                f'{sub_feat_step["name"]} Features</div>',
                unsafe_allow_html=True
            )
            for feat in avail_sub_feats:
                st.markdown(
                    f'<div class="trait-block">'
                    f'<div class="name">{feat["name"]} '
                    f'<span style="color:#4e3d6e; font-size:0.75rem">(Level {feat["level"]})</span></div>'
                    f'<div class="desc">{feat["description"]}</div></div>',
                    unsafe_allow_html=True
                )

    # ── Background feature ──
    bg_feat_step = get_background(st.session_state.background_id)
    if bg_feat_step:
        bg_feat_data = bg_feat_step.get("feature", {})
        st.markdown(
            f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:1rem 0 0.4rem">'
            f'{bg_feat_step["icon"]} {bg_feat_step["name"]}</p>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="trait-block">'
            f'<div class="name">{bg_feat_data.get("name","")}</div>'
            f'<div class="desc">{bg_feat_data.get("description","")}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── SPELL SELECTION (spellcasting classes only) ──────────────────────────
    mech_feat_step = get_mech(st.session_state.class_id or "")
    sc_feat = mech_feat_step.get("spellcasting")
    race_feat_step = get_race(st.session_state.race_id)
    if sc_feat and st.session_state.class_id != "sevrinn":
        sc_ability = sc_feat["ability"]
        sc_key_map = {"Wisdom": "WIS", "Intelligence": "INT", "Charisma": "CHA"}
        sc_key = sc_key_map.get(sc_ability, "WIS")
        sc_mod = modifier_int(effective_stat(sc_key, race_feat_step))
        spell_dc_feat = 8 + proficiency_bonus(level) + sc_mod
        spell_atk_val = proficiency_bonus(level) + sc_mod
        spell_atk_feat = f"+{spell_atk_val}" if spell_atk_val >= 0 else str(spell_atk_val)

        st.markdown('<div class="card" style="margin-top:0.8rem">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-header">✨ Spell Selection — {sc_ability} · DC {spell_dc_feat} · Atk {spell_atk_feat}</div>',
            unsafe_allow_html=True
        )

        # Cantrips
        cantrips_list = sc_feat.get("cantrips_known")
        cantrip_limit = cantrips_list[min(level - 1, 19)] if cantrips_list else 0
        if cantrip_limit > 0:
            available_cantrips = get_spells_for_class(st.session_state.class_id, "cantrips")
            if available_cantrips:
                chosen_c = list(st.session_state.chosen_cantrips)
                # Filter valid
                valid_names = {s["name"] for s in available_cantrips}
                chosen_c = [n for n in chosen_c if n in valid_names]

                st.markdown(
                    f'<div style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.88rem; '
                    f'margin:0.8rem 0 0.4rem; font-weight:700; letter-spacing:0.06em">'
                    f'CANTRIPS — choose {cantrip_limit} '
                    f'<span style="color:{"#10b981" if len(chosen_c)==cantrip_limit else "#e04040"}; font-size:0.8rem">'
                    f'[{len(chosen_c)}/{cantrip_limit}]</span></div>',
                    unsafe_allow_html=True
                )
                cantrip_search = st.text_input("Search cantrips", key="cantrip_search_4", label_visibility="collapsed", placeholder="Search cantrips…")
                filtered_cantrips = [s for s in available_cantrips if not cantrip_search or cantrip_search.lower() in s["name"].lower()]
                if not filtered_cantrips and cantrip_search:
                    st.caption(f"No cantrips match \"{cantrip_search}\"")
                else:
                    c_cols = st.columns(3)
                    for i, spell in enumerate(filtered_cantrips):
                        is_checked = spell["name"] in chosen_c
                        at_limit = len(chosen_c) >= cantrip_limit and not is_checked
                        checked = c_cols[i % 3].checkbox(
                            f"{spell['name']} ({spell.get('school','')})",
                            value=is_checked,
                            disabled=at_limit,
                            key=f"cantrip4_{spell['name'].replace(' ','_').replace('/','_')}"
                        )
                        if checked and spell["name"] not in chosen_c:
                            chosen_c.append(spell["name"])
                        elif not checked and spell["name"] in chosen_c:
                            chosen_c.remove(spell["name"])
                st.session_state.chosen_cantrips = chosen_c[:cantrip_limit]

        # Leveled spells
        spells_val_feat, spells_label_feat = get_spells_known_or_prepared(sc_feat, level, race_feat_step)
        if spells_val_feat is not None:
            chosen_s = list(st.session_state.chosen_spells)
            # Filter valid across all levels
            all_spell_names = set()
            for sl in range(1, 10):
                for sp in get_spells_for_class(st.session_state.class_id, str(sl)):
                    all_spell_names.add(sp["name"])
            chosen_s = [n for n in chosen_s if n in all_spell_names]

            # Determine which spell levels are accessible
            slot_type = sc_feat.get("slot_type", "full")
            is_spells_known = sc_feat.get("spells_known") is not None
            spell_limit = spells_val_feat

            for sl in range(1, 10):
                level_spells = get_spells_for_class(st.session_state.class_id, str(sl))
                if not level_spells:
                    continue
                slots_at_level = get_spell_slots(slot_type, level)
                # For pact magic, all accessible if slot level >= spell level
                if slot_type == "pact":
                    pact_lvl = PACT_SLOTS[min(level - 1, 19)][1]
                    if sl > pact_lvl:
                        continue
                elif sl > len([x for x in (FULL_CASTER_SLOTS if slot_type == "full" else HALF_CASTER_SLOTS)[min(level - 1, 19)] if x > 0]):
                    continue

                suffix = "st" if sl == 1 else "nd" if sl == 2 else "rd" if sl == 3 else "th"
                at_level_count = sum(1 for n in chosen_s if n in {sp["name"] for sp in level_spells})
                total_chosen = len(chosen_s)

                st.markdown(
                    f'<div style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.85rem; '
                    f'margin:0.8rem 0 0.3rem; font-weight:700; letter-spacing:0.06em">'
                    f'{sl}{suffix}-LEVEL SPELLS '
                    f'<span style="color:{"#10b981" if total_chosen==spell_limit else "#e8c87a"}; font-size:0.78rem">'
                    f'[{total_chosen}/{spell_limit} total {spells_label_feat}]</span></div>',
                    unsafe_allow_html=True
                )
                spell_search = st.text_input(f"Search {sl}{suffix}-level spells", key=f"spell_search_4_{sl}", label_visibility="collapsed", placeholder=f"Search {sl}{suffix}-level spells…")
                filtered_spells = [s for s in level_spells if not spell_search or spell_search.lower() in s["name"].lower()]
                if not filtered_spells and spell_search:
                    st.caption(f"No {sl}{suffix}-level spells match \"{spell_search}\"")
                else:
                    s_cols = st.columns(3)
                    for i, spell in enumerate(filtered_spells):
                        is_checked = spell["name"] in chosen_s
                        at_limit = total_chosen >= spell_limit and not is_checked
                        checked = s_cols[i % 3].checkbox(
                            f"{spell['name']}",
                            value=is_checked,
                            disabled=at_limit,
                            key=f"spell4_{sl}_{spell['name'].replace(' ','_').replace('/','_')}"
                        )
                        if checked and spell["name"] not in chosen_s:
                            chosen_s.append(spell["name"])
                            total_chosen += 1
                        elif not checked and spell["name"] in chosen_s:
                            chosen_s.remove(spell["name"])
                            total_chosen -= 1
                st.session_state.chosen_spells = chosen_s

        st.markdown('</div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="feat_back"):
            st.session_state.step = 3
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True, key="feat_next"):
            # Validate all required choices are made
            all_ok = True
            for choice in avail_choices:
                val = st.session_state.class_options.get(choice["key"])
                if val is None:
                    all_ok = False
                elif isinstance(val, list) and len(val) < choice["pick"]:
                    all_ok = False
            if not all_ok:
                st.error("Please complete all required class choices before continuing.")
            else:
                st.session_state.step = 5
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — BACKGROUND
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 5:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">📜 Choose Your Background</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-family: Crimson Text, serif; color: #a99cbf; font-style: italic; margin-bottom:1rem;">Where did your story begin?</p>', unsafe_allow_html=True)

        ryndor_bgs = [bg for bg in BACKGROUNDS if bg.get("source", "Ryndor") == "Ryndor"]
        srd_bgs    = [bg for bg in BACKGROUNDS if bg.get("source") == "SRD"]

        if ryndor_bgs:
            st.markdown('<div style="font-family:Cinzel,serif; font-size:0.72rem; color:#4e3d6e; letter-spacing:0.1em; margin:0.6rem 0 0.3rem">── RYNDOR BACKGROUNDS ──</div>', unsafe_allow_html=True)
        for bg in ryndor_bgs:
            selected = st.session_state.background_id == bg["id"]
            sel_cls = "selected" if selected else ""
            st.markdown(
                f'<div class="sel-card {sel_cls}">'
                f'<div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.3rem">'
                f'<span style="font-size:1.4rem">{bg["icon"]}</span>'
                f'<h3 style="margin:0">{bg["name"]}</h3>'
                f'<span class="badge" style="font-size:0.65rem;padding:1px 5px">Ryndor</span></div>'
                f'<p style="margin:0">{bg["description"][:100]}…</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Select {bg['name']}", key=f"bg_{bg['id']}", use_container_width=True):
                st.session_state.background_id = bg["id"]
                st.rerun()

        if srd_bgs:
            st.markdown('<div style="font-family:Cinzel,serif; font-size:0.72rem; color:#4e3d6e; letter-spacing:0.1em; margin:1rem 0 0.3rem">── SRD BACKGROUNDS ──</div>', unsafe_allow_html=True)
        for bg in srd_bgs:
            selected = st.session_state.background_id == bg["id"]
            sel_cls = "selected" if selected else ""
            st.markdown(
                f'<div class="sel-card {sel_cls}">'
                f'<div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.3rem">'
                f'<span style="font-size:1.4rem">{bg["icon"]}</span>'
                f'<h3 style="margin:0">{bg["name"]}</h3>'
                f'<span class="badge teal" style="font-size:0.65rem;padding:1px 5px">SRD</span></div>'
                f'<p style="margin:0">{bg["description"][:100]}…</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Select {bg['name']}", key=f"bg_{bg['id']}", use_container_width=True):
                st.session_state.background_id = bg["id"]
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        bg = get_background(st.session_state.background_id)
        if bg:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; font-size:2.5rem; margin-bottom:0.3rem">{bg["icon"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<h2 style="font-family:Cinzel,serif; color:#a78bfa; text-align:center; margin:0 0 0.5rem">{bg["name"]}</h2>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:Crimson Text,serif; font-style:italic; color:#9d8dbf">{bg["description"]}</p>', unsafe_allow_html=True)

            # Skills
            st.markdown('<div class="section-header">Proficiencies</div>', unsafe_allow_html=True)
            skills = " ".join([f'<span class="badge">🎲 {s}</span>' for s in bg.get("skill_proficiencies", [])])
            tools = " ".join([f'<span class="badge teal">🔧 {t}</span>' for t in bg.get("tool_proficiencies", [])])
            langs = " ".join([f'<span class="badge">🗣 {l}</span>' for l in bg.get("languages", [])])
            st.markdown(f'<div style="margin-bottom:0.5rem">{skills} {tools} {langs}</div>', unsafe_allow_html=True)

            # Equipment
            st.markdown('<div class="section-header">Starting Equipment</div>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.95rem">{bg["equipment"]}</p>', unsafe_allow_html=True)

            # Feature
            feat = bg.get("feature", {})
            st.markdown('<div class="section-header">Background Feature</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="trait-block"><div class="name">{feat["name"]}</div>'
                f'<div class="desc">{feat["description"]}</div></div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic; text-align:center; padding:2rem">← Select a background to see its details</p></div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 4
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True):
            if not st.session_state.background_id:
                st.error("Please select a background.")
            else:
                st.session_state.step = 6
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — ABILITY SCORES
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 6:
    race = get_race(st.session_state.race_id)

    cls_stats = get_class(st.session_state.class_id)
    priority = CLASS_STAT_PRIORITY.get(st.session_state.class_id or "", [])
    STAT_KEYS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    STAT_FULL = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
    STAT_LONG = {"STR":"Strength","DEX":"Dexterity","CON":"Constitution",
                 "INT":"Intelligence","WIS":"Wisdom","CHA":"Charisma"}

    # ── Optimize button: assign Standard Array in class priority order ──
    if priority and cls_stats:
        # Show priority order as badge strip
        priority_html = " → ".join(
            f'<span class="badge" style="font-size:0.8rem;padding:3px 8px">'
            f'{"★ " if i == 0 else ""}{k}</span>'
            for i, k in enumerate(priority)
        )
        opt_col1, opt_col2 = st.columns([3, 1])
        with opt_col1:
            st.markdown(
                f'<div style="margin-bottom:0.6rem">'
                f'<span style="font-family:Cinzel,serif;color:#a78bfa;font-size:0.78rem;'
                f'letter-spacing:0.08em">OPTIMAL FOR {cls_stats["name"].upper()}: </span>'
                f'{priority_html}</div>',
                unsafe_allow_html=True
            )
        with opt_col2:
            if st.button(f"⚡ Auto-Arrange", use_container_width=True, help=f"Assign Standard Array values in optimal order for {cls_stats['name']}"):
                for stat_key, value in zip(priority, STANDARD_ARRAY):
                    st.session_state.stats[stat_key] = value
                st.rerun()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🎲 Ability Scores</div>', unsafe_allow_html=True)

    method = st.radio(
        "Score Method",
        ["Standard Array", "Point Buy", "Manual Entry"],
        index=["Standard Array", "Point Buy", "Manual Entry"].index(st.session_state.stat_method),
        horizontal=True
    )
    st.session_state.stat_method = method

    if method == "Standard Array":
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:0.8rem">'
            f'Assign these values to your abilities: <b>{" · ".join(str(x) for x in STANDARD_ARRAY)}</b>'
            f'{"  —  click ⚡ Auto-Arrange to apply the optimal order for your class." if priority else ""}</p>',
            unsafe_allow_html=True
        )
        cols = st.columns(6)
        for i, (col, key, full) in enumerate(zip(cols, STAT_KEYS, STAT_FULL)):
            with col:
                options = sorted(set(STANDARD_ARRAY), reverse=True)
                current = st.session_state.stats[key]
                if current not in options:
                    current = options[i % len(options)]
                # Highlight if this stat is the top priority
                label = full[:3]
                if priority and priority.index(key) == 0:
                    label = f"★ {full[:3]}"
                choice = st.selectbox(label, options, index=options.index(current), key=f"sa_{key}")
                st.session_state.stats[key] = choice

    elif method == "Point Buy":
        COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
        total_points = 27
        spent = sum(COSTS.get(v, 0) for v in st.session_state.stats.values())
        remaining = total_points - spent
        color = "#50c050" if remaining >= 0 else "#e04040"
        st.markdown(
            f'<p style="font-family:Cinzel,serif; color:{color}; margin-bottom:0.8rem">'
            f'Points Remaining: <b>{remaining}</b> / {total_points}'
            f'{"  —  click ⚡ Auto-Arrange for the optimal distribution for your class." if priority else ""}</p>',
            unsafe_allow_html=True
        )
        cols = st.columns(6)
        for col, key, full in zip(cols, STAT_KEYS, STAT_FULL):
            with col:
                label = full[:3]
                if priority and priority.index(key) == 0:
                    label = f"★ {full[:3]}"
                val = st.number_input(label, min_value=8, max_value=15, value=st.session_state.stats[key], key=f"pb_{key}")
                st.session_state.stats[key] = val

    else:  # Manual
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:0.8rem">'
            f'Enter your scores directly (rolled or custom).'
            f'{"  The ⚡ Auto-Arrange button can suggest an optimal distribution." if priority else ""}</p>',
            unsafe_allow_html=True
        )
        cols = st.columns(6)
        for col, key, full in zip(cols, STAT_KEYS, STAT_FULL):
            with col:
                label = full[:3]
                if priority and priority.index(key) == 0:
                    label = f"★ {full[:3]}"
                val = st.number_input(label, min_value=1, max_value=30, value=st.session_state.stats[key], key=f"man_{key}")
                st.session_state.stats[key] = val

    st.markdown('</div>', unsafe_allow_html=True)

    # Preview stats with racial bonuses
    st.markdown('<div class="section-header" style="color:#a78bfa; margin-top:1.5rem">📊 Final Ability Scores (with Racial Bonuses)</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    for col, key, full in zip(cols, STAT_KEYS, STAT_FULL):
        eff = effective_stat(key, race)
        mod = modifier(eff)
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-name">{full[:3].upper()}</div>'
            f'<div class="stat-val">{eff}</div>'
            f'<div class="stat-mod">{mod}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Derived stats
    level = st.session_state.char_level
    prof = proficiency_bonus(level)
    con_mod = modifier_int(effective_stat("CON", race))
    dex_mod = modifier_int(effective_stat("DEX", race))
    cls = get_class(st.session_state.class_id)
    hit_die_num = int(cls["hit_die"][1:]) if cls else 8
    hp = hit_die_num + con_mod + (level - 1) * (math.floor(hit_die_num / 2) + 1 + con_mod)

    st.markdown('<br>', unsafe_allow_html=True)
    dcol1, dcol2, dcol3, dcol4 = st.columns(4)
    for c, label, val in [
        (dcol1, "Proficiency Bonus", f"+{prof}"),
        (dcol2, "Initiative", f"{modifier(effective_stat('DEX', race))}"),
        (dcol3, "HP (Average)", str(max(hp, 1))),
        (dcol4, "Passive Perception", str(10 + modifier_int(effective_stat("WIS", race)) + prof)),
    ]:
        c.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-name" style="font-size:0.55rem">{label.upper()}</div>'
            f'<div class="stat-val" style="font-size:1.6rem">{val}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Character details
    st.markdown('<div class="card" style="margin-top:1.5rem">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🖊️ Character Details (Optional)</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.personality = st.text_area("Personality Traits", st.session_state.personality, height=80, placeholder="How does your character act?")
        st.session_state.ideals = st.text_area("Ideals", st.session_state.ideals, height=80, placeholder="What drives your character?")
    with col2:
        st.session_state.bonds = st.text_area("Bonds", st.session_state.bonds, height=80, placeholder="What connects your character to the world?")
        st.session_state.flaws = st.text_area("Flaws", st.session_state.flaws, height=80, placeholder="What are your character's weaknesses?")
    st.session_state.notes = st.text_area("Additional Notes", st.session_state.notes, height=68, placeholder="Any other notes about your character…")
    st.markdown('</div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 5
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state.step = 7
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — SKILL PROFICIENCIES
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 7:
    race  = get_race(st.session_state.race_id)
    cls   = get_class(st.session_state.class_id)
    bg    = get_background(st.session_state.background_id)
    mech  = get_mech(st.session_state.class_id or "")
    level = st.session_state.char_level
    prof  = proficiency_bonus(level)

    sc = mech.get("skill_choices", {})
    class_options = sc.get("options", [])
    pick_count    = sc.get("count", 2)

    bg_skills     = bg.get("skill_proficiencies", []) if bg else []
    race_skills   = race.get("bonus_skills", []) if race else []
    auto_skills   = set(bg_skills) | set(race_skills)

    # Eligible: class options not already granted for free
    eligible = [s for s in class_options if s not in auto_skills]

    # Restore or prune previous selection to valid choices
    prev = [s for s in st.session_state.chosen_skills if s in eligible]
    if prev != st.session_state.chosen_skills:
        st.session_state.chosen_skills = prev

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🎯 Choose Skill Proficiencies</div>', unsafe_allow_html=True)

    if has_jack_of_all_trades():
        joat_preview = math.floor(prof / 2)
        st.markdown(
            f'<span class="badge teal">⚡ Jack of All Trades: +{joat_preview} to untrained skills</span>',
            unsafe_allow_html=True
        )

    if bg_skills or race_skills:
        auto_badges = " ".join(
            [f'<span class="badge teal">✔ {s} (background)</span>' for s in bg_skills] +
            [f'<span class="badge">✔ {s} (race)</span>' for s in race_skills]
        )
        st.markdown(f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:0.6rem">Already proficient: {auto_badges}</p>', unsafe_allow_html=True)

    if eligible:
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:1rem">'
            f'Choose <b style="color:#a78bfa">{pick_count}</b> additional skills from your class list '
            f'({cls["name"] if cls else ""}):</p>',
            unsafe_allow_html=True
        )
        chosen = list(st.session_state.chosen_skills)
        for skill in eligible:
            is_checked = skill in chosen
            at_limit   = len(chosen) >= pick_count and not is_checked
            key        = f"skill_{skill}"
            label      = f"{skill}" + (" *(limit reached)*" if at_limit and not is_checked else "")
            if st.checkbox(label, value=is_checked, disabled=at_limit, key=key):
                if skill not in chosen:
                    chosen.append(skill)
            else:
                if skill in chosen:
                    chosen.remove(skill)
        st.session_state.chosen_skills = chosen[:pick_count]
    else:
        st.markdown('<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic">All class skill options are already covered by your race/background proficiencies.</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Expertise (Rogue L1, Bard L3+) ───────────────────────────────────────
    all_prof = get_all_proficient_skills(race, bg, st.session_state.chosen_skills)
    has_expertise = (
        st.session_state.class_id == "rogue" or
        (st.session_state.class_id == "bard" and level >= 3)
    )
    if has_expertise:
        expertise_pick = 2
        st.markdown('<div class="card" style="margin-top:1rem">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">🌟 Expertise</div>', unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:0.6rem">'
            f'Choose <b style="color:#a78bfa">{expertise_pick}</b> skills you are proficient in. '
            f'Your proficiency bonus is <b>doubled</b> for those skills.</p>',
            unsafe_allow_html=True
        )
        proficient_list = sorted(all_prof)
        chosen_exp = [s for s in st.session_state.expertise_skills if s in proficient_list]
        if chosen_exp != st.session_state.expertise_skills:
            st.session_state.expertise_skills = chosen_exp
        new_exp = list(chosen_exp)
        for skill in proficient_list:
            is_checked = skill in new_exp
            at_limit   = len(new_exp) >= expertise_pick and not is_checked
            if st.checkbox(
                skill + (" *(limit reached)*" if at_limit and not is_checked else ""),
                value=is_checked,
                disabled=at_limit,
                key=f"exp_{skill}"
            ):
                if skill not in new_exp:
                    new_exp.append(skill)
            else:
                if skill in new_exp:
                    new_exp.remove(skill)
        st.session_state.expertise_skills = new_exp[:expertise_pick]
        st.markdown(
            f'<p style="font-family:Cinzel,serif; color:#{"a78bfa" if len(new_exp)==expertise_pick else "e04040"}; '
            f'font-size:0.78rem; margin-top:0.3rem">Selected: {len(new_exp)}/{expertise_pick}</p>',
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Language Selection ────────────────────────────────────────────────────
    st.markdown('<div class="card" style="margin-top:1rem">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🗣 Languages</div>', unsafe_allow_html=True)

    # Auto languages from race and background
    race_langs = race.get("languages", []) if race else []
    bg_langs   = bg.get("languages", []) if bg else []
    auto_langs = list(dict.fromkeys(race_langs + bg_langs))  # preserve order, dedupe
    if auto_langs:
        badges = " ".join([f'<span class="badge teal">🗣 {l}</span>' for l in auto_langs])
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:0.6rem">'
            f'Known from race & background: {badges}</p>',
            unsafe_allow_html=True
        )

    # Additional languages (optional — for GM-approved extra languages)
    extra_options = [l for l in ALL_LANGUAGES if l not in auto_langs]
    st.markdown(
        '<p style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.9rem; margin-bottom:0.4rem">'
        'Additional languages (with GM approval — for backgrounds or feats that grant extras):</p>',
        unsafe_allow_html=True
    )
    chosen_langs = st.multiselect(
        "Additional Languages",
        extra_options,
        default=[l for l in st.session_state.chosen_languages if l in extra_options],
        key="lang_select",
        label_visibility="collapsed"
    )
    st.session_state.chosen_languages = chosen_langs
    st.markdown('</div>', unsafe_allow_html=True)

    # Preview: full skill list with modifiers
    st.markdown('<div class="section-header" style="color:#a78bfa; margin-top:1.5rem">📋 All Skills Preview</div>', unsafe_allow_html=True)
    expertise_set = set(st.session_state.expertise_skills)
    cols = st.columns(3)
    joat_half = math.floor(prof / 2) if has_jack_of_all_trades() else 0
    for i, (sname, akey) in enumerate(ALL_SKILLS):
        is_exp = sname in expertise_set
        eff_prof = prof * 2 if is_exp else prof
        mod_val = skill_modifier(sname, akey, race, eff_prof, all_prof, half_prof=joat_half)
        sign    = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
        is_joat_boosted = joat_half and sname not in all_prof and not is_exp
        dot   = "★" if is_exp else ("●" if sname in all_prof else "○")
        color = "#c4b5fd" if is_exp else ("#a78bfa" if sname in all_prof else "#5a4a7a")
        joat_tag = f' <span style="font-size:0.7rem;color:#5a6a6a">(+{joat_half})</span>' if is_joat_boosted else ""
        cols[i % 3].markdown(
            f'<div style="display:flex;justify-content:space-between;padding:0.2rem 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.04)">'
            f'<span style="font-family:Crimson Text,serif;color:{color}">'
            f'<span style="font-size:0.85rem">{dot}</span> {sname}{joat_tag} '
            f'<span style="font-size:0.75rem;opacity:0.6">({ABILITY_SHORT[akey]})</span></span>'
            f'<span style="font-family:Cinzel,serif;color:{color};font-weight:700">{sign}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 6
            st.rerun()
    with col3:
        if st.button("Next →", type="primary", use_container_width=True):
            if len(st.session_state.chosen_skills) < min(pick_count, len(eligible)):
                st.error(f"Please choose {pick_count} skill(s) from the list.")
            else:
                st.session_state.step = 8
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — STARTING EQUIPMENT
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 8:
    cls  = get_class(st.session_state.class_id)
    mech = get_mech(st.session_state.class_id or "")
    choices  = mech.get("equipment_choices", [])
    fixed    = mech.get("equipment_fixed", [])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-header">🎒 Starting Equipment — {cls["name"] if cls else ""}</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:1rem">Choose your starting gear. Your armor choice also determines your base Armor Class.</p>', unsafe_allow_html=True)

    equip = dict(st.session_state.equip_choices)
    for choice in choices:
        cid = choice["id"]
        options = [o["label"] for o in choice["options"]]
        current = equip.get(cid, 0)
        if current >= len(options):
            current = 0
        st.markdown(f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.85rem; margin:0.8rem 0 0.3rem; letter-spacing:0.06em">{choice["prompt"].upper()}</p>', unsafe_allow_html=True)
        sel = st.radio(
            choice["prompt"],
            options,
            index=current,
            key=f"equip_{cid}",
            label_visibility="collapsed"
        )
        equip[cid] = options.index(sel)
    st.session_state.equip_choices = equip

    if fixed:
        st.markdown('<div class="section-header" style="margin-top:1rem">Also included</div>', unsafe_allow_html=True)
        st.markdown(" ".join([f'<span class="badge">📦 {item}</span>' for item in fixed]), unsafe_allow_html=True)

    # AC preview
    race = get_race(st.session_state.race_id)
    if st.session_state.class_id:
        ac_val, ac_note = compute_ac(st.session_state.class_id, race, equip)
        st.markdown(
            f'<div style="margin-top:1.5rem; display:flex; align-items:center; gap:1rem">'
            f'<div class="stat-box" style="width:100px">'
            f'<div class="stat-name" style="font-size:0.6rem">ARMOR CLASS</div>'
            f'<div class="stat-val" style="font-size:2rem">{ac_val}</div>'
            f'</div>'
            f'<p style="font-family:Crimson Text,serif; color:#9d8dbf; font-style:italic">{ac_note}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Full item list preview
    all_items = list(fixed)
    for choice in choices:
        cid = choice["id"]
        idx = equip.get(cid, 0)
        if idx < len(choice["options"]):
            all_items.extend(choice["options"][idx]["items"])
    st.markdown('<div class="section-header" style="margin-top:1rem">Your Full Equipment List</div>', unsafe_allow_html=True)
    st.markdown(
        "<ul style='font-family:Crimson Text,serif; color:#a99cbf; columns:2; margin:0; padding-left:1.2rem'>" +
        "".join(f"<li>{item}</li>" for item in all_items) +
        "</ul>",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    level = st.session_state.char_level

    # ── Weapons & Loadout ──
    st.markdown('<div class="card" style="margin-top:0.8rem">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🗡 Weapons & Loadout</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:1rem">Browse SRD weapons, build your inventory, and equip your loadout.</p>', unsafe_allow_html=True)

    # ── Armor Restrictions Banner ──
    armor_type_inv, has_shield_inv = get_current_armor_info(
        st.session_state.class_id or "", st.session_state.equip_choices
    )
    restrictions = get_armor_restrictions(
        st.session_state.class_id or "", armor_type_inv, has_shield_inv
    )
    if restrictions:
        armor_label_map = {"none": "Unarmored", "light": "Light Armor", "medium": "Medium Armor", "fixed": "Heavy Armor"}
        armor_display = armor_label_map.get(armor_type_inv, armor_type_inv.title())
        shield_display = " · Shield" if has_shield_inv else ""
        lines = "".join(
            f'<div style="margin-top:0.3rem">⚔ <b style="font-family:Cinzel,serif;font-size:0.82rem;color:#fcd34d">'
            f'{feat}</b> — <span style="color:#f59e0b">DISABLED</span> ({reason})</div>'
            for feat, reason in restrictions
        )
        st.markdown(
            f'<div class="ryndor-alert" style="margin-bottom:1rem">'
            f'<b>⚠ ARMOR RESTRICTIONS</b> — Currently: {armor_display}{shield_display}'
            f'{lines}</div>',
            unsafe_allow_html=True
        )

    # ── Two-column layout ──
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown('<div class="section-header" style="font-size:0.85rem">🗡 WEAPON BROWSER</div>', unsafe_allow_html=True)

        all_weapons = SRD_ITEMS["weapons"]
        categories = ["All", "Simple Melee", "Simple Ranged", "Martial Melee", "Martial Ranged"]
        filter_cat = st.selectbox("Filter by category", categories, key="wep_filter_cat", label_visibility="collapsed")

        filtered = all_weapons if filter_cat == "All" else [w for w in all_weapons if w["category"] == filter_cat]

        for wep in filtered:
            props = wep.get("properties", [])
            prof_mark = "●" if is_weapon_proficient(wep, cls) else "○"
            prof_color = "#67e8f9" if is_weapon_proficient(wep, cls) else "#4e3d6e"
            props_str = ", ".join(p.title() for p in props) if props else "—"
            versatile_str = f" · Versatile: {wep['versatile_damage']}" if wep.get("versatile_damage") else ""
            rng_str = f" · Range: {wep['range']}" if wep.get("range") else ""
            already_in = wep["id"] in st.session_state.inv_weapons

            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<div style="padding:0.4rem 0; border-bottom:1px solid rgba(124,58,237,0.12)">'
                    f'<span style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.88rem">{wep["name"]}</span>'
                    f' <span style="font-family:Crimson Text,serif; color:#9d8dbf; font-size:0.82rem">— {wep["damage"]} {wep["damage_type"]}{versatile_str}</span><br>'
                    f'<span style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.78rem">'
                    f'{wep["category"]} · {props_str}{rng_str} · {wep["cost"]}</span>'
                    f' <span style="color:{prof_color}; font-size:0.8rem">{prof_mark}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with col_btn:
                if already_in:
                    if st.button("✓", key=f"wep_rm_{wep['id']}", help="Remove from inventory"):
                        new_list = [w for w in st.session_state.inv_weapons if w != wep["id"]]
                        st.session_state.inv_weapons = new_list
                        if st.session_state.equipped_main == wep["id"]:
                            st.session_state.equipped_main = None
                        if st.session_state.equipped_offhand == wep["id"]:
                            st.session_state.equipped_offhand = None
                        st.rerun()
                else:
                    if st.button("+", key=f"wep_add_{wep['id']}", help="Add to inventory"):
                        st.session_state.inv_weapons = st.session_state.inv_weapons + [wep["id"]]
                        st.rerun()

    with right_col:
        st.markdown('<div class="section-header" style="font-size:0.85rem">⚔ EQUIPPED WEAPONS</div>', unsafe_allow_html=True)

        inv_weapon_objs = [get_weapon(wid) for wid in st.session_state.inv_weapons if get_weapon(wid)]
        equip_options = ["— (none)"] + [w["name"] for w in inv_weapon_objs]
        equip_ids     = [None]        + [w["id"]   for w in inv_weapon_objs]

        # Main hand
        main_idx = equip_ids.index(st.session_state.equipped_main) if st.session_state.equipped_main in equip_ids else 0
        main_sel = st.selectbox("Main Hand", equip_options, index=main_idx, key="equip_main_sel")
        new_main_id = equip_ids[equip_options.index(main_sel)]
        if new_main_id != st.session_state.equipped_main:
            st.session_state.equipped_main = new_main_id
            st.rerun()

        main_wep = get_weapon(st.session_state.equipped_main)
        if main_wep:
            main_stats = calc_weapon_attack(main_wep, race, cls, level)
            prof_icon = "● Proficient" if main_stats["proficient"] else "○ Not proficient"
            prof_col  = "#67e8f9" if main_stats["proficient"] else "#f59e0b"
            vd_line = f'<br><span style="color:#9d8dbf;font-size:0.78rem">Versatile: {main_stats["versatile_damage"]}</span>' if main_stats.get("versatile_damage") else ""
            notes_html = "".join(f'<br><span style="color:#f59e0b;font-size:0.75rem">{n}</span>' for n in main_stats["notes"])
            st.markdown(
                f'<div style="background:rgba(124,58,237,0.08);border-radius:4px;padding:0.5rem 0.8rem;margin:0.2rem 0 0.8rem">'
                f'<span style="font-family:Cinzel,serif;color:#fcd34d;font-size:0.95rem">{main_stats["attack"]} to hit</span>'
                f' · <span style="font-family:Crimson Text,serif;color:#a99cbf">{main_stats["damage"]}</span>'
                f'{vd_line}{notes_html}'
                f'<br><span style="font-size:0.78rem;color:{prof_col}">{prof_icon} ({main_stats["stat"]})</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Off-hand
        off_idx = equip_ids.index(st.session_state.equipped_offhand) if st.session_state.equipped_offhand in equip_ids else 0
        off_sel = st.selectbox("Off-Hand", equip_options, index=off_idx, key="equip_off_sel")
        new_off_id = equip_ids[equip_options.index(off_sel)]
        if new_off_id != st.session_state.equipped_offhand:
            st.session_state.equipped_offhand = new_off_id
            st.rerun()

        off_wep = get_weapon(st.session_state.equipped_offhand)
        if off_wep:
            off_stats = calc_weapon_attack(off_wep, race, cls, level, for_offhand=True)
            prof_icon2 = "● Proficient" if off_stats["proficient"] else "○ Not proficient"
            prof_col2  = "#67e8f9" if off_stats["proficient"] else "#f59e0b"
            notes_html2 = "".join(f'<br><span style="color:#9d8dbf;font-size:0.75rem">{n}</span>' for n in off_stats["notes"])
            st.markdown(
                f'<div style="background:rgba(34,211,238,0.06);border-radius:4px;padding:0.5rem 0.8rem;margin:0.2rem 0 0.8rem">'
                f'<span style="font-family:Cinzel,serif;color:#fcd34d;font-size:0.95rem">{off_stats["attack"]} to hit</span>'
                f' · <span style="font-family:Crimson Text,serif;color:#a99cbf">{off_stats["damage"]}</span>'
                f'{notes_html2}'
                f'<br><span style="font-size:0.78rem;color:{prof_col2}">{prof_icon2} ({off_stats["stat"]})</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Dual wield check
        dw_ok, dw_reason = check_dual_wield(main_wep, off_wep, has_dual_wielder_feat())
        if main_wep and off_wep:
            if not dw_ok:
                st.markdown(
                    f'<div class="ryndor-alert" style="padding:0.4rem 0.7rem; font-size:0.82rem">'
                    f'⚠ Dual wield invalid: {dw_reason}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);'
                    'border-radius:3px;padding:0.3rem 0.7rem;font-size:0.8rem;color:#6ee7b7;margin:0.3rem 0">'
                    '✓ Dual wield valid — bonus action attack available</div>',
                    unsafe_allow_html=True
                )

        dw_from_feat = any(
            c.get("type") == "feat" and c.get("feat_id") == "dual_wielder"
            for c in st.session_state.get("asi_choices", {}).values()
        )
        if dw_from_feat:
            st.markdown(
                '<div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);'
                'border-radius:3px;padding:0.3rem 0.7rem;font-size:0.8rem;color:#6ee7b7;margin:0.3rem 0">'
                '✓ Dual Wielder feat active (via Feats step)</div>',
                unsafe_allow_html=True
            )
        else:
            st.session_state.has_dual_wielder = st.checkbox(
                "Dual Wielder feat (manual override)",
                value=st.session_state.has_dual_wielder,
                key="dw_feat_chk",
                help="Select the Dual Wielder feat in the Feats step, or enable here manually"
            )

        # My weapon inventory
        if st.session_state.inv_weapons:
            st.markdown('<div class="section-header" style="font-size:0.85rem;margin-top:1rem">MY WEAPON INVENTORY</div>', unsafe_allow_html=True)
            for wid in st.session_state.inv_weapons:
                w = get_weapon(wid)
                if w:
                    eq_mark = ""
                    if wid == st.session_state.equipped_main:
                        eq_mark = ' <span style="color:#fcd34d;font-size:0.72rem">[MAIN]</span>'
                    elif wid == st.session_state.equipped_offhand:
                        eq_mark = ' <span style="color:#67e8f9;font-size:0.72rem">[OFF]</span>'
                    st.markdown(
                        f'<div style="font-family:Crimson Text,serif;color:#a99cbf;padding:0.15rem 0;font-size:0.9rem">'
                        f'⚔ {w["name"]}{eq_mark}</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.markdown('<p style="font-family:Crimson Text,serif;color:#4e3d6e;font-style:italic;font-size:0.88rem">No weapons in inventory yet.</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Adventuring Gear ──
    st.markdown('<div class="card" style="margin-top:0.8rem">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🎒 ADVENTURING GEAR</div>', unsafe_allow_html=True)

    gear_list = SRD_ITEMS["adventuring_gear"]
    gear_cols = st.columns(3)
    current_gear = set(st.session_state.inv_gear)
    for i, item in enumerate(gear_list):
        checked = item["id"] in current_gear
        new_val = gear_cols[i % 3].checkbox(
            f'{item["name"]} ({item["cost"]})',
            value=checked,
            key=f"gear_{item['id']}"
        )
        if new_val and item["id"] not in current_gear:
            current_gear.add(item["id"])
        elif not new_val and item["id"] in current_gear:
            current_gear.discard(item["id"])
    st.session_state.inv_gear = list(current_gear)
    st.markdown('</div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 7
            st.rerun()
    with col3:
        if st.button("Feats →", type="primary", use_container_width=True):
            st.session_state.step = 9
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — FEATS & ABILITY SCORE IMPROVEMENTS
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 9:
    cls_asi  = get_class(st.session_state.class_id)
    level_asi = st.session_state.char_level
    class_id_asi = st.session_state.class_id or ""

    eligible_levels = get_class_asi_levels(class_id_asi, level_asi)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-header">⚡ Ability Improvements & Feats'
        f'{"  —  " + cls_asi["name"] if cls_asi else ""} Level {level_asi}</div>',
        unsafe_allow_html=True
    )

    if not eligible_levels:
        st.markdown(
            '<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-style:italic">'
            'No Ability Score Improvements available yet at your current level. '
            'The first ASI unlocks at level 4.</p>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<p style="font-family:Crimson Text,serif; color:#a99cbf; margin-bottom:1rem">'
            f'You have <b style="color:#a78bfa">{len(eligible_levels)}</b> Ability Score Improvement'
            f'{"s" if len(eligible_levels) != 1 else ""} available. '
            f'For each, choose +2 to one stat, +1 to two stats, or a feat.</p>',
            unsafe_allow_html=True
        )

    STAT_KEYS_ASI = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    asi_choices = dict(st.session_state.asi_choices)

    for asi_lvl in eligible_levels:
        key_str = f"L{asi_lvl}"
        current = asi_choices.get(key_str, {"type": "asi_2", "stat1": "STR"})

        st.markdown(
            f'<div style="border-top:1px solid rgba(124,58,237,0.25); margin:1rem 0 0.5rem; '
            f'padding-top:0.8rem; font-family:Cinzel,serif; color:#a78bfa; font-size:0.88rem; '
            f'font-weight:700; letter-spacing:0.08em">LEVEL {asi_lvl}</div>',
            unsafe_allow_html=True
        )

        asi_type = st.radio(
            f"Type at L{asi_lvl}",
            ["+2 to one ability score", "+1 to two ability scores", "Choose a Feat"],
            index={"asi_2": 0, "asi_1_1": 1, "feat": 2}.get(current.get("type","asi_2"), 0),
            key=f"asi_type_{key_str}",
            label_visibility="collapsed"
        )

        if asi_type == "+2 to one ability score":
            stat1 = st.selectbox(
                "Ability", STAT_KEYS_ASI,
                index=STAT_KEYS_ASI.index(current.get("stat1","STR")),
                key=f"asi_stat1_{key_str}"
            )
            asi_choices[key_str] = {"type": "asi_2", "stat1": stat1}

        elif asi_type == "+1 to two ability scores":
            col_a, col_b = st.columns(2)
            with col_a:
                stat1 = st.selectbox(
                    "First ability", STAT_KEYS_ASI,
                    index=STAT_KEYS_ASI.index(current.get("stat1","STR")),
                    key=f"asi_s1_{key_str}"
                )
            with col_b:
                stat2_opts = [s for s in STAT_KEYS_ASI if s != stat1]
                prev2 = current.get("stat2","DEX")
                if prev2 not in stat2_opts:
                    prev2 = stat2_opts[0]
                stat2 = st.selectbox(
                    "Second ability", stat2_opts,
                    index=stat2_opts.index(prev2),
                    key=f"asi_s2_{key_str}"
                )
            asi_choices[key_str] = {"type": "asi_1_1", "stat1": stat1, "stat2": stat2}

        else:  # Choose a Feat
            feat_search = st.text_input(
                f"Search feats (L{asi_lvl})", key=f"feat_search_{key_str}",
                label_visibility="collapsed", placeholder="Search feats…"
            )
            current_feat_id = current.get("feat_id") if current.get("type") == "feat" else None

            for feat_obj in SRD_FEATS:
                if feat_search and feat_search.lower() not in feat_obj["name"].lower():
                    continue
                is_selected = feat_obj["id"] == current_feat_id
                stat_str = ""
                if feat_obj.get("stat_bonus"):
                    for sk, sv in feat_obj["stat_bonus"].items():
                        stat_str += f" (+{sv} {sk})"
                prereq_str = f" · *Prereq: {feat_obj['prerequisite']}*" if feat_obj.get("prerequisite") else ""
                label = f"{'✓ ' if is_selected else ''}{feat_obj['name']}{stat_str}{prereq_str}"

                f_col1, f_col2 = st.columns([5, 1])
                with f_col1:
                    prereq_html = (
                        f'<br><span style="font-family:Crimson Text,serif;color:#4e3d6e;font-size:0.72rem">'
                        f'Prereq: {feat_obj["prerequisite"]}</span>'
                    ) if feat_obj.get("prerequisite") else ""
                    name_color = "#a78bfa" if is_selected else "#9d8dbf"
                    check_mark = "✓ " if is_selected else ""
                    st.markdown(
                        f'<div style="padding:0.25rem 0; border-bottom:1px solid rgba(124,58,237,0.1)">'
                        f'<span style="font-family:Cinzel,serif; color:{name_color}; font-size:0.88rem">'
                        f'{check_mark}{feat_obj["name"]}{stat_str}</span>'
                        f'<span style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.8rem"> — {feat_obj["description"][:80]}…</span>'
                        f'{prereq_html}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with f_col2:
                    if is_selected:
                        if st.button("✕", key=f"feat_rm_{key_str}_{feat_obj['id']}", help="Remove"):
                            asi_choices[key_str] = {"type": "feat", "feat_id": None}
                            st.rerun()
                    else:
                        if st.button("Pick", key=f"feat_pick_{key_str}_{feat_obj['id']}", help=f"Select {feat_obj['name']}"):
                            asi_choices[key_str] = {"type": "feat", "feat_id": feat_obj["id"]}
                            st.rerun()

            if current_feat_id:
                picked = get_feat(current_feat_id)
                if picked:
                    st.markdown(
                        f'<div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.35);'
                        f'border-radius:4px;padding:0.5rem 0.8rem;margin:0.5rem 0">'
                        f'<span style="font-family:Cinzel,serif;color:#a78bfa;font-size:0.9rem">✓ {picked["name"]}</span>'
                        f'{"".join(f" <span class=badge>+{sv} {sk}</span>" for sk,sv in (picked["stat_bonus"] or {}).items())}'
                        f'<br><span style="font-family:Crimson Text,serif;color:#9d8dbf;font-size:0.88rem">{picked["description"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                asi_choices[key_str] = {"type": "feat", "feat_id": None}

    st.session_state.asi_choices = asi_choices

    # Summary of stat bonuses
    if eligible_levels:
        bonus_parts = []
        for sk in STAT_KEYS_ASI:
            total_b = get_asi_stat_bonus(sk)
            if total_b != 0:
                sign_b = f"+{total_b}" if total_b > 0 else str(total_b)
                bonus_parts.append(f"<b style='color:#a78bfa'>{sk}</b> {sign_b}")
        if bonus_parts:
            st.markdown(
                f'<div style="margin-top:1.2rem; padding:0.6rem 1rem; background:rgba(124,58,237,0.06);'
                f'border:1px solid rgba(124,58,237,0.2); border-radius:4px; font-family:Crimson Text,serif; color:#a99cbf">'
                f'<span style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.78rem; margin-right:0.5rem">STAT BONUSES:</span>'
                f'{" &nbsp;·&nbsp; ".join(bonus_parts)}</div>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← Back", use_container_width=True, key="asi_back"):
            st.session_state.step = 8
            st.rerun()
    with col3:
        if st.button("View Sheet →", type="primary", use_container_width=True, key="asi_next"):
            st.session_state.step = 10
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 — CHARACTER SHEET
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.step == 10:
    race = get_race(st.session_state.race_id)
    cls = get_class(st.session_state.class_id)
    sub = get_subclass(cls, st.session_state.subclass_id)
    bg = get_background(st.session_state.background_id)
    level = st.session_state.char_level
    prof = proficiency_bonus(level)

    STAT_KEYS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
    STAT_FULL = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

    # ── Header ──
    race_name = race["name"] if race else "Unknown Race"
    cls_name = cls["name"] if cls else "Unknown Class"
    sub_name = sub["name"] if sub else ""
    bg_name = bg["name"] if bg else "Unknown Background"
    race_icon = race["icon"] if race else ""
    cls_icon = cls["icon"] if cls else ""

    st.markdown(
        f'<div class="sheet-header">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem">'
        f'<span style="font-family:Cinzel,serif; font-size:0.75rem; color:#9d8dbf; letter-spacing:0.1em">RYNDOR: THE WEIRDED LANDS</span>'
        f'<span style="font-family:Cinzel,serif; font-size:0.75rem; color:#9d8dbf">LEVEL {level}</span>'
        f'</div>'
        f'<div class="char-name">{st.session_state.char_name}</div>'
        f'<div class="char-sub">'
        f'{race_icon} {race_name} &nbsp;·&nbsp; {cls_icon} {cls_name}'
        f'{" (" + sub_name + ")" if sub_name else ""}'
        f' &nbsp;·&nbsp; 📜 {bg_name}'
        f'</div>'
        f'<div style="margin-top:0.5rem">'
        f'<span class="badge">{st.session_state.alignment}</span>'
        f'{"&nbsp;" + "<span class=badge>Player: " + st.session_state.player_name + "</span>" if st.session_state.player_name else ""}'
        f'<span class="badge">Proficiency Bonus: +{prof}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Ability Scores ──
    st.markdown('<div class="sheet-section" style="margin-top:0">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-section-title">Ability Scores</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    for col, key, full in zip(cols, STAT_KEYS, STAT_FULL):
        eff = effective_stat(key, race)
        mod = modifier(eff)
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-name">{full[:3]}</div>'
            f'<div class="stat-val">{eff}</div>'
            f'<div class="stat-mod">{mod}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    # ASI / Feat bonus summary row
    asi_sheet_choices = st.session_state.get("asi_choices", {})
    if asi_sheet_choices:
        bonus_sheet_parts = []
        for sk_s in STAT_KEYS:
            total_b = get_asi_stat_bonus(sk_s)
            if total_b != 0:
                sign_b = f"+{total_b}" if total_b > 0 else str(total_b)
                bonus_sheet_parts.append(f"<b style='color:#a78bfa'>{sk_s}</b> {sign_b}")
        feat_parts = []
        for lk, cv in asi_sheet_choices.items():
            if cv.get("type") == "feat" and cv.get("feat_id"):
                feat_sh = get_feat(cv["feat_id"])
                if feat_sh:
                    feat_parts.append(feat_sh["name"])
        if bonus_sheet_parts or feat_parts:
            row_html = '<p style="font-family:Crimson Text,serif; color:#5a4a7a; font-size:0.82rem; margin:0.4rem 0 0; font-style:italic">'
            row_html += '<b style="font-family:Cinzel,serif; color:#4e3d6e; font-size:0.72rem">ASI/FEAT BONUSES:</b> '
            if bonus_sheet_parts:
                row_html += " &nbsp;·&nbsp; ".join(bonus_sheet_parts)
            if feat_parts:
                if bonus_sheet_parts:
                    row_html += " &nbsp;·&nbsp; "
                row_html += "Feats: " + ", ".join(feat_parts)
            row_html += '</p>'
            st.markdown(row_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Derived Stats ──
    mech_sheet = get_mech(st.session_state.class_id or "")
    con_mod = modifier_int(effective_stat("CON", race))
    dex_mod = modifier_int(effective_stat("DEX", race))
    wis_mod = modifier_int(effective_stat("WIS", race))
    hit_die_num = int(cls["hit_die"][1:]) if cls else 8
    hp = hit_die_num + con_mod + (level - 1) * (math.floor(hit_die_num / 2) + 1 + con_mod)
    ac_val, ac_note = compute_ac(st.session_state.class_id or "", race, st.session_state.equip_choices)
    all_prof_skills = get_all_proficient_skills(race, bg, st.session_state.chosen_skills)

    # Passive Perception: 10 + Perception modifier
    joat_half_sheet = math.floor(prof / 2) if has_jack_of_all_trades() else 0
    perc_mod = skill_modifier("Perception", "WIS", race, prof, all_prof_skills, half_prof=joat_half_sheet)

    st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-section-title">Combat Statistics</div>', unsafe_allow_html=True)
    dcols = st.columns(5)
    stats_display = [
        ("Max HP", str(max(hp, 1))),
        ("Armor Class", f"{ac_val}"),
        ("Initiative", modifier(effective_stat("DEX", race))),
        ("Speed", str(race["speed"].get("walk", 30) if race else 30) + " ft"),
        ("Passive Perception", str(10 + perc_mod)),
    ]
    for col, (label, val) in zip(dcols, stats_display):
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-name" style="font-size:0.55rem">{label.upper()}</div>'
            f'<div class="stat-val" style="font-size:1.5rem">{val}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown(f'<p style="font-family:Crimson Text,serif; color:#4e3d6e; font-size:0.82rem; margin:0.3rem 0 0; font-style:italic">AC: {ac_note} · Hit Die: {cls["hit_die"] if cls else "d8"} · Proficiency Bonus: +{prof}</p>', unsafe_allow_html=True)
    dmg_res = list(st.session_state.get("damage_resistances", []))
    if race and race["id"] == "drakarim":
        _anc_res = st.session_state.get("draconic_ancestry", "")
        _anc_r = next((x for x in race.get("draconic_ancestry_table", []) if x["dragon"] == _anc_res), None)
        if _anc_r and _anc_r["damage_type"] not in dmg_res:
            dmg_res.append(_anc_r["damage_type"])
    if dmg_res:
        res_badges = " ".join(f'<span style="color:#67e8f9">⬡ {r}</span>' for r in dmg_res)
        st.markdown(f'<p style="font-family:Crimson Text,serif; color:#4e3d6e; font-size:0.82rem; margin:0.2rem 0 0; font-style:italic">Damage Resistances: {res_badges}</p>', unsafe_allow_html=True)

    # ── Attacks & Actions ──
    _all_actions = []

    # Weapons
    sheet_main_wep = get_weapon(st.session_state.get("equipped_main"))
    sheet_off_wep  = get_weapon(st.session_state.get("equipped_offhand"))
    if sheet_main_wep:
        ms = calc_weapon_attack(sheet_main_wep, race, cls, level)
        vd = f" · Versatile: {ms['versatile_damage']}" if ms.get("versatile_damage") else ""
        _all_actions.append({
            "name": sheet_main_wep["name"],
            "category": "Weapon",
            "hit": f"{ms['attack']} to hit",
            "save": None,
            "damage": ms["damage"] + vd,
            "note": "● Proficient" if ms["proficient"] else "○ Not proficient",
        })
    if sheet_off_wep:
        os_ = calc_weapon_attack(sheet_off_wep, race, cls, level, for_offhand=True)
        _all_actions.append({
            "name": sheet_off_wep["name"] + " (off-hand)",
            "category": "Weapon",
            "hit": f"{os_['attack']} to hit",
            "save": None,
            "damage": os_["damage"],
            "note": "● Proficient" if os_["proficient"] else "○ Not proficient",
        })

    # Racial abilities
    _all_actions.extend(_race_combat_actions(race, con_mod, prof, level))

    # Spellcasting — damaging cantrips and spells
    _mech_sh = get_mech(st.session_state.class_id or "")
    _sc_sh   = _mech_sh.get("spellcasting")
    if _sc_sh and st.session_state.class_id != "sevrinn":
        _sc_key2   = {"Wisdom": "WIS", "Intelligence": "INT", "Charisma": "CHA"}.get(_sc_sh["ability"], "WIS")
        _sc_mod2   = modifier_int(effective_stat(_sc_key2, race))
        _atk_bonus = prof + _sc_mod2
        _spell_dc2 = 8 + _atk_bonus
        _atk_str   = f"+{_atk_bonus}" if _atk_bonus >= 0 else str(_atk_bonus)
        for _cname in st.session_state.get("chosen_cantrips", []):
            _csd, _ = lookup_spell_detail(_cname)
            if _csd:
                _cp = _parse_spell_combat(_csd)
                if _cp:
                    _cdice, _cdtype, _catk, _csave = _cp
                    _chalf = "half" in _csd.get("description", "").lower()
                    if _catk == "attack":
                        _all_actions.append({"name": _cname, "category": "Cantrip", "hit": f"{_atk_str} to hit", "save": None, "damage": f"{_cdice} {_cdtype.lower()}", "note": "At will"})
                    elif _catk == "save":
                        _all_actions.append({"name": _cname, "category": "Cantrip", "hit": None, "save": f"DC {_spell_dc2} {_csave}", "damage": f"{_cdice} {_cdtype.lower()}", "note": "At will" + (" · half on save" if _chalf else "")})
                    else:
                        _all_actions.append({"name": _cname, "category": "Cantrip", "hit": None, "save": None, "damage": f"{_cdice} {_cdtype.lower()}", "note": "At will"})
        for _sname in st.session_state.get("chosen_spells", []):
            _ssd, _slk = lookup_spell_detail(_sname)
            if _ssd:
                _sp = _parse_spell_combat(_ssd)
                if _sp:
                    _sdice, _sdtype, _satk, _ssave = _sp
                    _slvl  = _spell_level_label(_slk) if _slk else "Spell"
                    _shalf = "half" in _ssd.get("description", "").lower()
                    if _satk == "attack":
                        _all_actions.append({"name": _sname, "category": _slvl, "hit": f"{_atk_str} to hit", "save": None, "damage": f"{_sdice} {_sdtype.lower()}", "note": None})
                    elif _satk == "save":
                        _all_actions.append({"name": _sname, "category": _slvl, "hit": None, "save": f"DC {_spell_dc2} {_ssave}", "damage": f"{_sdice} {_sdtype.lower()}", "note": "Half on save" if _shalf else None})
                    elif _satk == "weapon_bonus":
                        _all_actions.append({"name": _sname, "category": _slvl, "hit": None, "save": None, "damage": f"+{_sdice} {_sdtype.lower()} per hit", "note": "Bonus to weapon attacks · Concentration"})
                    else:
                        _all_actions.append({"name": _sname, "category": _slvl, "hit": None, "save": None, "damage": f"{_sdice} {_sdtype.lower()}", "note": "Auto-hit"})

    # Class damage features
    _all_actions.extend(_class_combat_actions(st.session_state.class_id or "", level, race, prof))

    # Render
    if _all_actions:
        _cat_colors = {
            "Weapon": "#a78bfa", "Cantrip": "#67e8f9",
            "Feature": "#fcd34d", "Racial": "#f59e0b",
        }
        st.markdown('<p style="font-family:Cinzel,serif;color:#a78bfa;font-size:0.72rem;letter-spacing:0.1em;margin:0.8rem 0 0.4rem">ATTACKS & ACTIONS</p>', unsafe_allow_html=True)
        for _act in _all_actions:
            _cc  = _cat_colors.get(_act["category"], "#c4b5fd")
            _cat = f'<span style="color:{_cc};font-size:0.7rem;font-family:Cinzel,serif">[{_act["category"]}]</span>'
            if _act.get("hit"):
                _roll = f'<span style="color:#fcd34d">{_act["hit"]}</span>'
            elif _act.get("save"):
                _roll = f'<span style="color:#fcd34d">{_act["save"]} save</span>'
            else:
                _roll = ""
            _sep  = " · " if _roll else ""
            _note = f' <span style="color:#67e8f9;font-size:0.75rem">· {_act["note"]}</span>' if _act.get("note") else ""
            st.markdown(
                f'<div style="font-family:Crimson Text,serif;color:#a99cbf;font-size:0.9rem;margin:0.2rem 0">'
                f'<b style="font-family:Cinzel,serif;color:#c4b5fd;font-size:0.8rem">{_act["name"]}</b> '
                f'{_cat} {_roll}{_sep}{_act["damage"]}{_note}'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── Armor restriction warnings on sheet ──
    sheet_armor_type, sheet_has_shield = get_current_armor_info(
        st.session_state.class_id or "", st.session_state.equip_choices
    )
    sheet_restrictions = get_armor_restrictions(
        st.session_state.class_id or "", sheet_armor_type, sheet_has_shield
    )
    if sheet_restrictions:
        lines_sh = "".join(
            f'<div>⚠ <b style="font-family:Cinzel,serif;font-size:0.78rem;color:#fcd34d">{feat}</b>'
            f' — <span style="color:#f59e0b">DISABLED</span> ({reason})</div>'
            for feat, reason in sheet_restrictions
        )
        st.markdown(
            f'<div class="ryndor-alert" style="margin-top:0.6rem;font-size:0.82rem">'
            f'<b>⚠ ARMOR RESTRICTIONS</b>{lines_sh}</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Saving Throws (prominent stat-box style) ──
    st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-section-title">Saving Throws</div>', unsafe_allow_html=True)
    class_saves = cls["saves"] if cls else []
    save_cols = st.columns(6)
    for (full, key), col in zip(
        [("Strength","STR"),("Dexterity","DEX"),("Constitution","CON"),
         ("Intelligence","INT"),("Wisdom","WIS"),("Charisma","CHA")],
        save_cols
    ):
        eff = effective_stat(key, race)
        mod_val = modifier_int(eff)
        is_prof = full in class_saves
        total = mod_val + (prof if is_prof else 0)
        sign = f"+{total}" if total >= 0 else str(total)
        border_color = "var(--weird)" if is_prof else "rgba(124,58,237,0.25)"
        label_color  = "#a78bfa"     if is_prof else "#5a4a7a"
        prof_label   = "★ PROF"      if is_prof else "SAVE"
        col.markdown(
            f'<div class="stat-box" style="border-color:{border_color}">'
            f'<div class="stat-name">{full[:3]}</div>'
            f'<div class="stat-val" style="font-size:1.8rem">{sign}</div>'
            f'<div style="font-family:Cinzel,serif;font-size:0.52rem;color:{label_color};margin-top:0.15rem">{prof_label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Proficiencies & Languages ──
    st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-section-title">Proficiencies & Languages</div>', unsafe_allow_html=True)
    prof_col1, prof_col2 = st.columns(2)
    with prof_col1:
        # Languages: race + bg + chosen
        race_langs_sheet = race.get("languages", []) if race else []
        bg_langs_sheet   = bg.get("languages", []) if bg else []
        extra_langs      = st.session_state.get("chosen_languages", [])
        all_sheet_langs  = list(dict.fromkeys(race_langs_sheet + bg_langs_sheet + extra_langs))
        if all_sheet_langs:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0 0 0.3rem">LANGUAGES</p>', unsafe_allow_html=True)
            for l in all_sheet_langs:
                st.markdown(f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.12rem 0">🗣 {l}</div>', unsafe_allow_html=True)
        if bg and bg.get("tool_proficiencies"):
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0.5rem 0 0.3rem">TOOLS</p>', unsafe_allow_html=True)
            for t in bg["tool_proficiencies"]:
                st.markdown(f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.12rem 0">🔧 {t} (+{prof})</div>', unsafe_allow_html=True)
    with prof_col2:
        if cls:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0 0 0.3rem">ARMOR & WEAPONS</p>', unsafe_allow_html=True)
            for item in cls.get("armor", []) + cls.get("weapons", []):
                st.markdown(f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.1rem 0; font-size:0.88rem">⚔ {item}</div>', unsafe_allow_html=True)
        # Class options summary (Fighting Style, Pact Boon, etc.)
        class_opts_display = st.session_state.get("class_options", {})
        cf_choices = CLASS_FEATURES.get(st.session_state.class_id or "", {}).get("choices", [])
        if class_opts_display and cf_choices:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0.5rem 0 0.3rem">CLASS CHOICES</p>', unsafe_allow_html=True)
            for choice in cf_choices:
                val = class_opts_display.get(choice["key"])
                if val:
                    if isinstance(val, list):
                        opts = choice.get("options", [])
                        names = [o["name"] for o in opts if o["id"] in val]
                        display = ", ".join(names)
                    else:
                        opts = choice.get("options", [])
                        display = next((o["name"] for o in opts if o["id"] == val), val)
                    st.markdown(
                        f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.12rem 0; font-size:0.88rem">'
                        f'<span style="font-family:Cinzel,serif; color:#c4b5fd; font-size:0.78rem">{choice["name"]}:</span> {display}</div>',
                        unsafe_allow_html=True
                    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Skills ──
    sheet_expertise = set(st.session_state.get("expertise_skills", []))
    st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
    title_suffix = ' <span style="font-family:Crimson Text,serif;font-size:0.75rem;color:#5a4a7a;font-weight:normal;font-style:italic">★ = Expertise (double prof)</span>' if sheet_expertise else ""
    st.markdown(f'<div class="sheet-section-title">Skills{title_suffix}</div>', unsafe_allow_html=True)
    skill_cols = st.columns(3)
    for i, (sname, akey) in enumerate(ALL_SKILLS):
        is_exp    = sname in sheet_expertise
        eff_prof  = prof * 2 if is_exp else prof
        mod_val   = skill_modifier(sname, akey, race, eff_prof, all_prof_skills, half_prof=joat_half_sheet)
        sign      = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
        is_joat_sh = joat_half_sheet and sname not in all_prof_skills and not is_exp
        dot   = "★" if is_exp else ("●" if sname in all_prof_skills else "○")
        color = "#c4b5fd" if is_exp else ("#a78bfa" if sname in all_prof_skills else "#5a4a7a")
        joat_tag_sh = f' <span style="font-size:0.68rem;color:#5a6a6a">(+{joat_half_sheet})</span>' if is_joat_sh else ""
        skill_cols[i % 3].markdown(
            f'<div style="display:flex;justify-content:space-between;padding:0.2rem 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.04)">'
            f'<span style="font-family:Crimson Text,serif;color:{color}">'
            f'<span style="font-size:0.85rem">{dot}</span> {sname}{joat_tag_sh} '
            f'<span style="font-size:0.72rem;opacity:0.55">({ABILITY_SHORT[akey]})</span></span>'
            f'<span style="font-family:Cinzel,serif;color:{color};font-weight:700;font-size:0.9rem">{sign}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Equipment ──
    mech_eq = get_mech(st.session_state.class_id or "")
    eq_fixed = mech_eq.get("equipment_fixed", [])
    eq_choices = mech_eq.get("equipment_choices", [])
    eq_items = list(eq_fixed)
    for choice in eq_choices:
        cid = choice["id"]
        idx = st.session_state.equip_choices.get(cid, 0)
        if idx < len(choice["options"]):
            eq_items.extend(choice["options"][idx]["items"])
    if bg:
        eq_items.append(bg.get("equipment", ""))
    # Append equipped weapons
    main_wep_obj = get_weapon(st.session_state.get("equipped_main"))
    off_wep_obj  = get_weapon(st.session_state.get("equipped_offhand"))
    if main_wep_obj:
        eq_items.append(f"{main_wep_obj['name']} (main hand)")
    if off_wep_obj:
        eq_items.append(f"{off_wep_obj['name']} (off-hand)")

    st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
    st.markdown('<div class="sheet-section-title">🎒 Equipment</div>', unsafe_allow_html=True)
    st.markdown(
        "<ul style='font-family:Crimson Text,serif; color:#a99cbf; columns:2; margin:0; padding-left:1.2rem; font-size:0.95rem'>" +
        "".join(f"<li>{item}</li>" for item in eq_items if item) +
        "</ul>",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Spellcasting (non-Sev'rinn only) ──
    sc_data = mech_sheet.get("spellcasting")
    if sc_data and st.session_state.class_id != "sevrinn":
        sc_ability = sc_data["ability"]
        sc_key_map = {"Wisdom":"WIS","Intelligence":"INT","Charisma":"CHA"}
        sc_key = sc_key_map.get(sc_ability, "WIS")
        sc_mod = modifier_int(effective_stat(sc_key, race))
        spell_dc = 8 + prof + sc_mod
        spell_atk = f"+{prof + sc_mod}" if (prof + sc_mod) >= 0 else str(prof + sc_mod)
        cantrips = sc_data.get("cantrips_known")
        cantrips_val = cantrips[min(level-1, 19)] if cantrips else "—"
        slots = get_spell_slots(sc_data.get("slot_type"), level)
        spells_val, spells_label = get_spells_known_or_prepared(sc_data, level, race)

        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown(f'<div class="sheet-section-title">✨ Spellcasting ({sc_ability})</div>', unsafe_allow_html=True)

        sp_cols = st.columns(4)
        sp_cols[0].markdown(f'<div class="stat-box"><div class="stat-name" style="font-size:0.55rem">SPELL SAVE DC</div><div class="stat-val" style="font-size:1.8rem">{spell_dc}</div></div>', unsafe_allow_html=True)
        sp_cols[1].markdown(f'<div class="stat-box"><div class="stat-name" style="font-size:0.55rem">SPELL ATTACK</div><div class="stat-val" style="font-size:1.8rem">{spell_atk}</div></div>', unsafe_allow_html=True)
        sp_cols[2].markdown(f'<div class="stat-box"><div class="stat-name" style="font-size:0.55rem">CANTRIPS KNOWN</div><div class="stat-val" style="font-size:1.8rem">{cantrips_val}</div></div>', unsafe_allow_html=True)
        if spells_val is not None:
            sp_cols[3].markdown(f'<div class="stat-box"><div class="stat-name" style="font-size:0.55rem">{(spells_label or "SPELLS").upper()}</div><div class="stat-val" style="font-size:1.8rem">{spells_val}</div></div>', unsafe_allow_html=True)

        if slots:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0.8rem 0 0.4rem; letter-spacing:0.1em">SPELL SLOTS</p>', unsafe_allow_html=True)
            slot_html = " ".join([
                f'<span class="badge" style="font-size:0.82rem; padding:4px 10px">{lvl}: {cnt} slot{"s" if cnt != 1 else ""}</span>'
                for lvl, cnt in slots
            ])
            st.markdown(slot_html, unsafe_allow_html=True)
            if sc_data.get("slot_type") == "pact":
                st.markdown('<p style="font-family:Crimson Text,serif; color:#4e3d6e; font-size:0.82rem; margin-top:0.3rem; font-style:italic">Pact Magic slots recover on a short rest.</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="font-family:Crimson Text,serif; color:#4e3d6e; font-size:0.82rem; margin-top:0.3rem; font-style:italic">Spell slots recover on a long rest.</p>', unsafe_allow_html=True)

        # Chosen cantrips and spells from Features step
        chosen_c_sheet = st.session_state.get("chosen_cantrips", [])
        chosen_s_sheet = st.session_state.get("chosen_spells", [])
        if chosen_c_sheet:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0.8rem 0 0.2rem; letter-spacing:0.1em">CANTRIPS</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.92rem">{", ".join(chosen_c_sheet)}</p>',
                unsafe_allow_html=True
            )
        if chosen_s_sheet:
            st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.75rem; margin:0.8rem 0 0.2rem; letter-spacing:0.1em">KNOWN/PREPARED SPELLS</p>', unsafe_allow_html=True)
            # Group by level for display
            by_level = {}
            for sl in range(1, 10):
                level_spell_names = {sp["name"] for sp in get_spells_for_class(st.session_state.class_id or "", str(sl))}
                at_level = [n for n in chosen_s_sheet if n in level_spell_names]
                if at_level:
                    suffix = "st" if sl==1 else "nd" if sl==2 else "rd" if sl==3 else "th"
                    by_level[f"{sl}{suffix} level"] = at_level
            for lvl_label, spell_names in by_level.items():
                st.markdown(
                    f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.15rem 0; font-size:0.9rem">'
                    f'<b style="font-family:Cinzel,serif; color:#c4b5fd; font-size:0.75rem">{lvl_label}:</b> {", ".join(spell_names)}</div>',
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Spell Details ──
    all_chosen_spells_sheet = (
        st.session_state.get("chosen_cantrips", []) +
        st.session_state.get("chosen_spells", [])
    )
    if sc_data and all_chosen_spells_sheet and st.session_state.class_id != "sevrinn":
        _slot_dict_sh, _is_pact_sh = _build_slot_dict(sc_data, level)
        _cantrips_grp = st.session_state.get("chosen_cantrips", [])
        _spells_by_lk_sh = {}
        for sn in st.session_state.get("chosen_spells", []):
            _, lk = lookup_spell_detail(sn)
            if lk:
                _spells_by_lk_sh.setdefault(lk, []).append(sn)
        _sorted_lks_sh = sorted(_spells_by_lk_sh.keys(), key=lambda x: int(x) if x.isdigit() else 0)

        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown('<div class="sheet-section-title">📜 Spell Details</div>', unsafe_allow_html=True)

        def _render_spell_html(spell_name, lk):
            sp, _ = lookup_spell_detail(spell_name)
            if not sp:
                return
            school = sp.get("school", "")
            meta = f"{_spell_level_label(lk)}{' — ' + school if school else ''}"
            stat_parts = []
            if sp.get("casting_time"): stat_parts.append(f"<b>Casting Time:</b> {sp['casting_time']}")
            if sp.get("range"):        stat_parts.append(f"<b>Range:</b> {sp['range']}")
            if sp.get("components"):   stat_parts.append(f"<b>Components:</b> {sp['components']}")
            if sp.get("duration"):     stat_parts.append(f"<b>Duration:</b> {sp['duration']}")
            st.markdown(
                f'<div style="margin:0.6rem 0 0.3rem; padding:0.6rem 0 0.4rem; border-top:1px solid rgba(167,139,250,0.1)">'
                f'<div style="font-family:Cinzel,serif; color:#c4b5fd; font-size:0.92rem; font-weight:600">{spell_name}</div>'
                f'<div style="font-family:Crimson Text,serif; color:#7c6d9a; font-size:0.78rem; font-style:italic; margin-bottom:0.3rem">{meta}</div>'
                f'<div style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.8rem; margin-bottom:0.3rem">{"  &nbsp;·&nbsp;  ".join(stat_parts)}</div>'
                f'<div style="font-family:Crimson Text,serif; color:#a99cbf; font-size:0.88rem; line-height:1.5">{sp.get("description","")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        def _level_subheader(lk):
            cast_lbl = _spell_cast_label(lk, _slot_dict_sh, _is_pact_sh)
            lv_text = "Cantrips" if lk == "cantrips" else _spell_level_label(lk)
            slot_part = f'<span style="color:#5a4a7a; font-weight:400"> — {cast_lbl}</span>' if cast_lbl else ""
            st.markdown(
                f'<div style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.78rem; '
                f'letter-spacing:0.08em; margin:1.2rem 0 0.2rem; padding-bottom:0.35rem; '
                f'border-bottom:2px solid rgba(167,139,250,0.2)">'
                f'{lv_text.upper()}{slot_part}</div>',
                unsafe_allow_html=True
            )

        if _cantrips_grp:
            _level_subheader("cantrips")
            for sn in _cantrips_grp:
                _render_spell_html(sn, "cantrips")
        for lk in _sorted_lks_sh:
            _level_subheader(lk)
            for sn in _spells_by_lk_sh[lk]:
                _render_spell_html(sn, lk)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Racial Traits ──
    if race:
        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown(f'<div class="sheet-section-title">{race["icon"]} Racial Traits — {race["name"]}</div>', unsafe_allow_html=True)
        _sheet_anc = None
        if race["id"] == "drakarim":
            _chosen_anc_s = st.session_state.get("draconic_ancestry", "")
            _sheet_anc = next((x for x in race.get("draconic_ancestry_table", []) if x["dragon"] == _chosen_anc_s), None)
        for trait in race.get("traits", []):
            _tname = trait["name"]
            _tdesc = trait["description"]
            if _sheet_anc:
                if _tname == "Draconic Ancestry":
                    _tdesc = (f"{_sheet_anc['dragon']} Dragon ({_sheet_anc['damage_type']}). "
                              f"Breath weapon: {_sheet_anc['breath']}, {_sheet_anc['save']} save.")
                elif _tname == "Draconic Resistance":
                    _tdesc = f"Resistance to {_sheet_anc['damage_type'].lower()} damage."
                elif _tname == "Breath Weapon":
                    _tdesc = (f"{_sheet_anc['breath']} ({_sheet_anc['save']} save, DC = 8 + proficiency bonus + CON modifier). "
                              f"2d6 {_sheet_anc['damage_type'].lower()} damage on a failed save, half on success. "
                              f"Recharges on a short or long rest.")
            st.markdown(
                f'<div class="feat-row">'
                f'<div class="fname">{_tname}</div>'
                f'<div class="fdesc">{_tdesc}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Class Features ──
    if cls:
        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown('<div class="sheet-section-title">✨ Features</div>', unsafe_allow_html=True)

        if cls["id"] == "sevrinn":
            # ── Sev'rinn: class-level features from CLASS_FEATURES ──
            sv_feats = CLASS_FEATURES.get("sevrinn", {}).get("features", [])
            avail_sv_feats = [f for f in sv_feats if f["level"] <= level]
            if avail_sv_feats:
                st.markdown(f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0 0 0.4rem">{cls["name"]}</p>', unsafe_allow_html=True)
                for feat in avail_sv_feats:
                    feat_name = feat["name"]
                    feat_desc = feat["description"]
                    if feat["level"] == 3 and feat_name == "Elemental Shift" and sub:
                        sub_form = next((f for f in sub.get("features", []) if f["level"] == 3), None)
                        if sub_form:
                            feat_name = sub_form["name"]
                    st.markdown(
                        f'<div class="feat-row">'
                        f'<div class="fname">{feat_name} <span style="color:#4e3d6e; font-size:0.75rem">(L{feat["level"]})</span></div>'
                        f'<div class="fdesc">{feat_desc}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # ── Level table (elemental resources) ──
            sv_mech = cls.get("mechanics", {})
            lvl_data = None
            for row in sv_mech.get("level_table", []):
                if row["min_level"] <= level <= row["max_level"]:
                    lvl_data = row
                    break
            if not lvl_data:
                for row in sv_mech.get("level_table", []):
                    if row["min_level"] <= level:
                        lvl_data = row
            if lvl_data:
                st.markdown(
                    f'<div style="display:flex; gap:1rem; margin:0.8rem 0">'
                    f'<span class="badge">⚡ Charges: {lvl_data["charges"]}</span>'
                    f'<span class="badge">📚 Techniques Known: {lvl_data["techniques"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # ── Combat Techniques (filtered by level) ──
            techs = [t for t in sub.get("techniques", []) if t["level"] <= level]
            if techs:
                st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">COMBAT TECHNIQUES</p>', unsafe_allow_html=True)
                for tech in techs:
                    usage = tech.get("usage", "")
                    tech_level = tech["level"]
                    if usage == "Elemental Shift use":
                        cost_badge = '[Shift use]'
                        badge_color = '#a78bfa'
                    elif usage.startswith("Costs 1 Elemental Charge") or tech_level <= 3:
                        cost_badge = '[1C]'
                        badge_color = '#4ade80'
                    elif tech_level <= 10:
                        cost_badge = '[2C / 1C Shifted]'
                        badge_color = '#fbbf24'
                    else:
                        cost_badge = '[3C / 2C Shifted]'
                        badge_color = '#f87171'
                    if any(x in usage for x in ['/Short Rest', '/Long Rest', '/7 days', 'proficiency bonus']):
                        cost_badge = f'[{usage}]'
                        badge_color = '#94a3b8'
                    st.markdown(
                        f'<div class="feat-row">'
                        f'<div class="fname">{tech["name"]} '
                        f'<span style="color:#4e3d6e; font-size:0.75rem">(L{tech["level"]})</span> '
                        f'<span style="color:{badge_color}; font-size:0.72rem; font-family:Cinzel,serif">{cost_badge}</span>'
                        f'</div>'
                        f'<div class="fdesc">{tech["description"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # ── Elemental Shift (available at level 3+) ──
            if level >= 3:
                shift_table = sub.get("shift_table", [])
                if shift_table:
                    sheet_form_name = sub["features"][0]["name"] if sub.get("features") else "Elemental Form"
                    st.markdown(f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">{sheet_form_name.upper()} (Bonus Action, 1 Charge)</p>', unsafe_allow_html=True)
                    for shift in shift_table:
                        st.markdown(
                            f'<div class="feat-row">'
                            f'<div class="fname" style="min-width:140px">'
                            f'<span style="color:#4e3d6e;font-size:0.8rem">({shift["roll"]})</span> {shift["name"]}</div>'
                            f'<div class="fdesc">{shift["effect"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

            # ── Weirding Surge Table ──
            surge_table = sv_mech.get("weirding_surge_table", [])
            if surge_table:
                st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">WEIRDING SURGE TABLE (roll d6)</p>', unsafe_allow_html=True)
                for i, effect in enumerate(surge_table, 1):
                    st.markdown(
                        f'<div style="font-family:Crimson Text,serif;color:#a99cbf;font-size:0.88rem;padding:0.15rem 0;'
                        f'border-bottom:1px solid rgba(255,255,255,0.04)">'
                        f'<span style="font-family:Cinzel,serif;color:#f472b6;font-size:0.8rem;margin-right:0.5rem">{i}</span>{effect}</div>',
                        unsafe_allow_html=True
                    )

        else:
            # Non-Sev'rinn: show class features from CLASS_FEATURES filtered by level
            cf_sheet = CLASS_FEATURES.get(st.session_state.class_id or "", {}).get("features", [])
            avail_cf = [f for f in cf_sheet if f["level"] <= level]
            if avail_cf:
                st.markdown(f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0 0 0.4rem">{cls["name"]}</p>', unsafe_allow_html=True)
                for feat in avail_cf:
                    st.markdown(
                        f'<div class="feat-row">'
                        f'<div class="fname">{feat["name"]} <span style="color:#4e3d6e; font-size:0.75rem">(L{feat["level"]})</span></div>'
                        f'<div class="fdesc">{feat["description"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # ASI choices summary
            asi_ch = st.session_state.get("asi_choices", {})
            if asi_ch:
                st.markdown('<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">ABILITY IMPROVEMENTS & FEATS</p>', unsafe_allow_html=True)
                for lk, cv in sorted(asi_ch.items()):
                    if not cv:
                        continue
                    t = cv.get("type")
                    if t == "asi_2" and cv.get("stat1"):
                        desc = f"+2 {cv['stat1']}"
                    elif t == "asi_1_1" and cv.get("stat1") and cv.get("stat2"):
                        desc = f"+1 {cv['stat1']}, +1 {cv['stat2']}"
                    elif t == "feat" and cv.get("feat_id"):
                        f_obj = get_feat(cv["feat_id"])
                        desc = f_obj["name"] if f_obj else cv["feat_id"]
                    else:
                        continue
                    lvl_num = lk.replace("L","")
                    st.markdown(
                        f'<div style="font-family:Crimson Text,serif; color:#a99cbf; padding:0.12rem 0; font-size:0.9rem">'
                        f'<span style="font-family:Cinzel,serif; color:#c4b5fd; font-size:0.72rem">Level {lvl_num}:</span> {desc}</div>',
                        unsafe_allow_html=True
                    )

            # Subclass features
            if sub:
                sub_available = [f for f in sub.get("features", []) if f["level"] <= level]
                if sub_available:
                    st.markdown(
                        f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">'
                        f'{sub["name"]}</p>',
                        unsafe_allow_html=True
                    )
                    for feat in sub_available:
                        st.markdown(
                            f'<div class="feat-row">'
                            f'<div class="fname">{feat["name"]} <span style="color:#4e3d6e; font-size:0.75rem">(L{feat["level"]})</span></div>'
                            f'<div class="fdesc">{feat["description"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

        if bg:
            bg_feat = bg.get("feature", {})
            st.markdown(
                f'<p style="font-family:Cinzel,serif; color:#a78bfa; font-size:0.72rem; letter-spacing:0.1em; margin:0.8rem 0 0.4rem">'
                f'{bg["icon"]} {bg["name"]}</p>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="feat-row">'
                f'<div class="fname">{bg_feat.get("name","")}</div>'
                f'<div class="fdesc">{bg_feat.get("description","")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Character Details ──
    if any([st.session_state.personality, st.session_state.ideals,
            st.session_state.bonds, st.session_state.flaws, st.session_state.notes]):
        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown('<div class="sheet-section-title">📖 Character Details</div>', unsafe_allow_html=True)
        details = [
            ("Personality", st.session_state.personality),
            ("Ideals", st.session_state.ideals),
            ("Bonds", st.session_state.bonds),
            ("Flaws", st.session_state.flaws),
            ("Notes", st.session_state.notes),
        ]
        for label, val in details:
            if val:
                st.markdown(
                    f'<div class="feat-row">'
                    f'<div class="fname">{label}</div>'
                    f'<div class="fdesc">{val}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Combat Tactics ──
    _ct = st.session_state.get("combat_tactics", {})
    if _ct:
        st.markdown('<div class="sheet-section">', unsafe_allow_html=True)
        st.markdown('<div class="sheet-section-title">⚔ Combat Tactics</div>', unsafe_allow_html=True)
        if _ct.get("role"):
            st.markdown(
                f'<p style="font-family:Crimson Text,serif;font-style:italic;color:#9d8dbf;margin:0 0 0.8rem">{_ct["role"]}</p>',
                unsafe_allow_html=True
            )
        for _tac in _ct.get("tactics", []):
            st.markdown(
                f'<div class="feat-row">'
                f'<div class="fname">{_tac["phase"]}</div>'
                f'<div class="fdesc">{_tac["text"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Actions ──
    st.markdown('<br>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Edit Feats", use_container_width=True):
            st.session_state.step = 9
            st.rerun()
    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    with col3:
        import base64 as _b64
        _html_sheet = build_print_html()
        _b64_str = _b64.b64encode(_html_sheet.encode("utf-8")).decode("ascii")
        st.components.v1.html(f"""
<html><head><style>
  body {{ margin:0; padding:0; background:transparent; }}
  button {{
    width:100%; height:42px;
    background: rgba(124,58,237,0.12);
    color: #a99cbf;
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Cinzel', Georgia, serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.05em;
    transition: background 0.2s, color 0.2s;
  }}
  button:hover {{
    background: rgba(124,58,237,0.25);
    color: #c4b5fd;
    border-color: rgba(124,58,237,0.7);
  }}
</style></head>
<body>
<script>
var _b64 = "{_b64_str}";
function openSheet() {{
  var bytes = Uint8Array.from(atob(_b64), function(c) {{ return c.charCodeAt(0); }});
  var html  = new TextDecoder("utf-8").decode(bytes);
  var blob  = new Blob([html], {{type: "text/html;charset=utf-8"}});
  var url   = URL.createObjectURL(blob);
  window.open(url, "_blank");
}}
</script>
<button onclick="openSheet()">&#x1F5A8; Save Character Sheet</button>
</body></html>""", height=46)

    # Save character JSON
    save_data = {k: st.session_state.get(k, v) for k, v in defaults.items() if k != "step"}
    save_json = json.dumps(save_data, indent=2)
    save_fname = f"{(st.session_state.char_name or 'character').lower().replace(' ', '_')}_character.json"
    st.download_button("💾 Download JSON", data=save_json, file_name=save_fname,
                       mime="application/json", use_container_width=True)
