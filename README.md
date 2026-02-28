# 🐉 Ryndor: Character Maker

> An aesthetic D&D 5e character sheet builder for **Ryndor: The Weirded Lands** — a homebrew sourcebook set in a dark, elemental fantasy world.

[**→ Launch the App**](https://ryndor-character-maker-git-164613525255.us-west1.run.app/) &nbsp;·&nbsp; [**→ Project Site**](https://kicak5h.github.io/ryndor-character-maker)

---

## Features

- **6-step guided builder** — walk through race, class, background, ability scores, and more
- **Ryndor-exclusive content** — custom races, classes (including the Sev'rinn), subclasses, and backgrounds drawn from the sourcebook
- **AI character generation** — one click rolls a full character and uses Claude AI to generate a fitting name, personality, ideals, bonds, and flaws
- **Printable character sheet** — export to PDF directly from the browser
- **Point Buy, Standard Array, or Manual** ability score entry
- **Full combat stats** — AC, initiative, hit points, attacks, spell slots, saving throws, and skill modifiers all computed automatically
- **Dark fantasy aesthetic** — Cinzel + Crimson Text typography, deep void colour palette

---

## Races

| Icon | Race | Icon | Race |
|------|------|------|------|
| 🦅 | Aviari | 🧑 | Human |
| 🦌 | Cervar | 🧝 | Elf |
| 🐉 | Drakarim | 😈 | Tiefling |
| 🦇 | Khuzud | ⛏️ | Dwarf |
| 🐇 | Leoporin | 🌌 | Nebernorian |

## Classes

All 12 PHB classes plus the Ryndor-original **Sev'rinn** — an elemental attunement class with 9 subclasses (Tideborn, Skycaller, Lithomage, Greenheart, Chronomancer, Voidstrider, Emberclad, Eidolon, Luminor).

## Backgrounds

9 Ryndor-exclusive backgrounds: Sev'rinn Initiate · Ban Mynydd Miner · Skywatcher of Holmea · Ghost Whisperer of Dollow Canyon · Kigan Uldar Champion · Utfordring Diver · Weirding Refugee · Hurstwold Warden · Surreymouth Trader

---

## Running Locally

**Requirements:** Docker + Docker Compose

```bash
git clone https://github.com/kicak5h/ryndor-character-maker.git
cd ryndor-character-maker

# Add your Anthropic API key (optional — enables AI name/trait generation)
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env

docker compose up --build
```

Then open [http://localhost:8501](http://localhost:8501).

---

## Stack

| Layer | Technology |
|-------|-----------|
| App | Python · Streamlit |
| AI | Claude (Anthropic API) via `anthropic` SDK |
| PDF export | fpdf2 |
| Containerisation | Docker · Docker Compose |
| Hosting | Google Cloud Run |
| Fonts | Cinzel · Crimson Text (Google Fonts) |

---

## Project Structure

```
ryndor-character-maker/
├── app/
│   ├── app.py            # Main Streamlit application (~1000 lines)
│   └── data/             # JSON data files (races, classes, backgrounds, items, spells)
├── docs/                 # GitHub Pages landing site
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## AI Character Generation

Clicking **🎲 Roll Random Character** on Step 1:

1. Randomly selects race, class, subclass, background, and alignment
2. Assigns a shuffled Standard Array across all six ability scores
3. Picks class skills, equipment, fighting styles, languages, etc.
4. Calls **Claude Haiku** to generate a contextual name, personality, ideals, bonds, and flaws
5. Jumps straight to the completed character sheet

The `ANTHROPIC_API_KEY` environment variable must be set for AI generation. Without it the roll still works — name and traits are simply left blank for manual entry.
