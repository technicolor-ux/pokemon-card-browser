#!/usr/bin/env python3
"""
Generate TCGPlayer search URLs for all Pokémon TCG cards and sets.

Outputs:
  ~/pokemon_card_data/tcgplayer_urls.json   — card-level lookup (keyed by card ID)
  ~/pokemon_card_data/tcgplayer_sets.json   — set-level index
  bookmarks.html                            — Chrome-importable bookmarks file

Usage:
  python3 generate_tcgplayer_urls.py
"""

import json
import os
import time
from urllib.parse import quote_plus

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(HOME, "pokemon_card_data")
CARDS_FILE = os.path.join(DATA_DIR, "cards.json")
SETS_FILE = os.path.join(DATA_DIR, "sets.json")
OUT_CARD_URLS = os.path.join(DATA_DIR, "tcgplayer_urls.json")
OUT_SET_URLS = os.path.join(DATA_DIR, "tcgplayer_sets.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_BOOKMARKS = os.path.join(SCRIPT_DIR, "bookmarks.html")

# ── Era mapping (matches card browser ERAS constant) ──────────────────────────
ERAS = {
    "Scarlet & Violet":       ["sv1","sv2","sv3","sv3pt5","sv4","sv4pt5","sv5","sv6","sv6pt5","sv7","sv8","sv8pt5","sv9","sv10","zsv10pt5","svp","sve"],
    "Sword & Shield":         ["swsh1","swsh2","swsh3","swsh35","swsh4","swsh45","swsh5","swsh6","swsh7","swsh8","swsh9","swsh10","swsh11","swsh12","swsh12pt5","swsblastapro"],
    "Sun & Moon":             ["sm1","sm2","sm3","sm35","sm4","sm5","sm6","sm7","sm75","sm8","sm9","sm10","sm11","sm115","sm12","sm_black_star_promos"],
    "XY":                     ["xy1","xy2","xy3","xy4","xy5","xy6","xy7","xy8","xy9","xy10","xy11","xy12","g1","dc1","me1","me2","me2pt5","mep"],
    "Black & White":          ["bw1","bw2","bw3","bw4","bw5","bw6","bw7","bw8","bw9","bw10","bw11","dv1"],
    "HeartGold SoulSilver":   ["hgss1","hgss2","hgss3","hgss4","col1"],
    "Diamond & Pearl":        ["dp1","dp2","dp3","dp4","dp5","dp6","dp7","pl1","pl2","pl3","pl4"],
    "EX Series":              ["ex1","ex2","ex3","ex4","ex5","ex6","ex7","ex8","ex9","ex10","ex11","ex12","ex13","ex14","ex15","ex16","tk1a","tk1b","tk2a","tk2b"],
    "e-Card":                 ["ecard1","ecard2","ecard3"],
    "Neo":                    ["neo1","neo2","neo3","neo4"],
    "Gym":                    ["gym1","gym2"],
    "Base Set Era":           ["base1","base2","base3","base5","base6","basep"],
    "Celebrations":           ["cel25","cel25c"],
    "Promos & Special":       ["np","bp","pop1","pop2","pop3","pop4","pop5","pop6","pop7","pop8","pop9","det1","pgo","mcd23","mcd24"],
}

SET_NAMES = {
    "base1":"Base Set","base2":"Jungle","base3":"Fossil","base5":"Team Rocket","base6":"Legendary Collection","basep":"Wizards Black Star Promos",
    "bp":"Best of Game","bw1":"Black & White","bw2":"Emerging Powers","bw3":"Noble Victories","bw4":"Next Destinies","bw5":"Dark Explorers",
    "bw6":"Dragons Exalted","bw7":"Boundaries Crossed","bw8":"Plasma Storm","bw9":"Plasma Freeze","bw10":"Plasma Blast","bw11":"Legendary Treasures",
    "cel25":"Celebrations","cel25c":"Celebrations: Classic","col1":"Call of Legends","dc1":"Double Crisis","det1":"Detective Pikachu",
    "dp1":"Diamond & Pearl","dp2":"Mysterious Treasures","dp3":"Secret Wonders","dp4":"Great Encounters","dp5":"Majestic Dawn",
    "dp6":"Legends Awakened","dp7":"Stormfront","dv1":"Dragon Vault","ecard1":"Expedition Base Set","ecard2":"Aquapolis","ecard3":"Skyridge",
    "ex1":"Ruby & Sapphire","ex2":"Sandstorm","ex3":"Dragon","ex4":"Team Magma vs Team Aqua","ex5":"Hidden Legends","ex6":"FireRed & LeafGreen",
    "ex7":"Team Rocket Returns","ex8":"Deoxys","ex9":"Emerald","ex10":"Unseen Forces","ex11":"Delta Species","ex12":"Legend Maker",
    "ex13":"Holon Phantoms","ex14":"Crystal Guardians","ex15":"Dragon Frontiers","ex16":"Power Keepers","g1":"Generations",
    "gym1":"Gym Heroes","gym2":"Gym Challenge","hgss1":"HeartGold & SoulSilver","hgss2":"HS Unleashed","hgss3":"HS Undaunted","hgss4":"HS Triumphant",
    "mcd23":"McDonald's 2023","mcd24":"McDonald's 2024","me1":"Mega Evolution","me2":"Phantasmal Flames","me2pt5":"Ascended Heroes","mep":"Mega Evolution Promos",
    "neo1":"Neo Genesis","neo2":"Neo Discovery","neo3":"Neo Revelation","neo4":"Neo Destiny","np":"Nintendo Black Star Promos","pgo":"Pokémon GO",
    "pl1":"Platinum","pl2":"Rising Rivals","pl3":"Supreme Victors","pl4":"Arceus",
    "pop1":"POP Series 1","pop2":"POP Series 2","pop3":"POP Series 3","pop4":"POP Series 4","pop5":"POP Series 5",
    "pop6":"POP Series 6","pop7":"POP Series 7","pop8":"POP Series 8","pop9":"POP Series 9",
    "rsv10pt5":"White Flare","sm1":"Sun & Moon","sm2":"Guardians Rising","sm3":"Burning Shadows","sm35":"Shining Legends",
    "sm4":"Crimson Invasion","sm5":"Ultra Prism","sm6":"Forbidden Light","sm7":"Celestial Storm","sm75":"Dragon Majesty",
    "sm8":"Lost Thunder","sm9":"Team Up","sm10":"Unbroken Bonds","sm11":"Unified Minds","sm115":"Hidden Fates","sm12":"Cosmic Eclipse",
    "sv1":"Scarlet & Violet","sv2":"Paldea Evolved","sv3":"Obsidian Flames","sv3pt5":"151","sv4":"Paradox Rift","sv4pt5":"Paldean Fates",
    "sv5":"Temporal Forces","sv6":"Twilight Masquerade","sv6pt5":"Shrouded Fable","sv7":"Stellar Crown","sv8":"Surging Sparks",
    "sv8pt5":"Prismatic Evolutions","sv9":"Journey Together","sv10":"Destined Rivals","sve":"SV Energies","svp":"SV Black Star Promos",
    "swsh1":"Sword & Shield","swsh2":"Rebel Clash","swsh3":"Darkness Ablaze","swsh35":"Champion's Path","swsh4":"Vivid Voltage",
    "swsh45":"Shining Fates","swsh5":"Battle Styles","swsh6":"Chilling Reign","swsh7":"Evolving Skies","swsh8":"Fusion Strike",
    "swsh9":"Brilliant Stars","swsh10":"Astral Radiance","swsh11":"Lost Origin","swsh12":"Silver Tempest","swsh12pt5":"Crown Zenith",
    "tk1a":"EX Trainer Kit Latias","tk1b":"EX Trainer Kit Latios","tk2a":"EX Trainer Kit 2 Plusle","tk2b":"EX Trainer Kit 2 Minun",
    "xy1":"XY","xy2":"Flashfire","xy3":"Furious Fists","xy4":"Phantom Forces","xy5":"Primal Clash","xy6":"Roaring Skies",
    "xy7":"Ancient Origins","xy8":"BREAKthrough","xy9":"BREAKpoint","xy10":"Fates Collide","xy11":"Steam Siege","xy12":"Evolutions",
    "zsv10pt5":"Black Bolt",
}

BASE_SEARCH = "https://www.tcgplayer.com/search/pokemon/product"


def card_url(card_name: str, set_name: str) -> str:
    params = f"productLineName=pokemon&q={quote_plus(card_name)}&setName={quote_plus(set_name)}"
    return f"{BASE_SEARCH}?{params}"


def set_url(set_name: str) -> str:
    params = f"productLineName=pokemon&setName={quote_plus(set_name)}&view=grid"
    return f"{BASE_SEARCH}?{params}"


def set_era(set_id: str) -> str:
    for era, ids in ERAS.items():
        if set_id in ids:
            return era
    return "Other"


def build_bookmark_timestamp() -> int:
    # Chrome uses microseconds since 1601-01-01 for bookmark dates
    # Approximate: use a fixed recent date
    return 13370000000000000


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    print("Loading card data...")
    with open(CARDS_FILE) as f:
        cards = json.load(f)
    print(f"  {len(cards):,} cards loaded")

    # ── Build set → cards index ────────────────────────────────────────────────
    sets_index: dict[str, list] = {}
    for card in cards:
        sid = card.get("set_id", "")
        sets_index.setdefault(sid, []).append(card)

    # ── Generate card URL lookup ───────────────────────────────────────────────
    print("Generating card URLs...")
    card_urls: dict = {}
    for card in cards:
        cid = card["id"]
        cname = card.get("name", "")
        sid = card.get("set_id", "")
        sname = card.get("set_name") or SET_NAMES.get(sid, sid)
        cnum = card.get("number", "")
        card_urls[cid] = {
            "card_name": cname,
            "card_number": cnum,
            "set_id": sid,
            "set_name": sname,
            "era": set_era(sid),
            "tcgplayer_card_url": card_url(cname, sname),
            "tcgplayer_set_url": set_url(sname),
        }

    with open(OUT_CARD_URLS, "w") as f:
        json.dump(card_urls, f, separators=(",", ":"))
    print(f"  Wrote {OUT_CARD_URLS} ({os.path.getsize(OUT_CARD_URLS) // 1024} KB)")

    # ── Generate set URL index ─────────────────────────────────────────────────
    print("Generating set URLs...")
    set_urls_list = []
    seen_sets: set = set()
    for era_name, era_set_ids in ERAS.items():
        for sid in era_set_ids:
            if sid in seen_sets:
                continue
            seen_sets.add(sid)
            sname = SET_NAMES.get(sid, sid)
            set_urls_list.append({
                "set_id": sid,
                "set_name": sname,
                "era": era_name,
                "card_count": len(sets_index.get(sid, [])),
                "tcgplayer_url": set_url(sname),
            })
    # Add any sets not in ERAS (catch-all)
    for sid in sets_index:
        if sid not in seen_sets:
            sname = SET_NAMES.get(sid, sid)
            set_urls_list.append({
                "set_id": sid,
                "set_name": sname,
                "era": "Other",
                "card_count": len(sets_index[sid]),
                "tcgplayer_url": set_url(sname),
            })

    with open(OUT_SET_URLS, "w") as f:
        json.dump(set_urls_list, f, indent=2)
    print(f"  Wrote {OUT_SET_URLS} ({len(set_urls_list)} sets)")

    # ── Generate Chrome bookmarks HTML ────────────────────────────────────────
    print("Generating bookmarks.html...")
    ts = build_bookmark_timestamp()

    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<!-- This is an automatically generated file.',
        '     It will be read and overwritten.',
        '     DO NOT EDIT! -->',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks</H1>',
        '<DL><p>',
        f'    <DT><H3 ADD_DATE="{ts}" LAST_MODIFIED="{ts}">Future Sight \u2014 TCGPlayer</H3>',
        '    <DL><p>',
    ]

    for era_name, era_set_ids in ERAS.items():
        lines.append(f'        <DT><H3 ADD_DATE="{ts}" LAST_MODIFIED="{ts}">{escape_html(era_name)}</H3>')
        lines.append('        <DL><p>')
        for sid in era_set_ids:
            sname = SET_NAMES.get(sid, sid)
            surl = set_url(sname)
            set_card_count = len(sets_index.get(sid, []))
            # Set-level bookmark (folder containing all cards)
            lines.append(f'            <DT><H3 ADD_DATE="{ts}" LAST_MODIFIED="{ts}">{escape_html(sname)} ({set_card_count} cards)</H3>')
            lines.append('            <DL><p>')
            # Set price guide link first
            lines.append(f'                <DT><A HREF="{escape_html(surl)}" ADD_DATE="{ts}">Browse {escape_html(sname)} on TCGPlayer</A>')
            # Individual card bookmarks
            set_cards = sorted(sets_index.get(sid, []), key=lambda c: c.get("number", ""))
            for card in set_cards:
                cname = card.get("name", "")
                cnum = card.get("number", "")
                curl = card_url(cname, sname)
                label = f"{cname} #{cnum}" if cnum else cname
                lines.append(f'                <DT><A HREF="{escape_html(curl)}" ADD_DATE="{ts}">{escape_html(label)}</A>')
            lines.append('            </DL><p>')
        lines.append('        </DL><p>')

    lines.append('    </DL><p>')
    lines.append('</DL><p>')

    with open(OUT_BOOKMARKS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    size_kb = os.path.getsize(OUT_BOOKMARKS) // 1024
    print(f"  Wrote {OUT_BOOKMARKS} ({size_kb} KB)")

    print("\nDone.")
    print(f"  Card URL lookup : {OUT_CARD_URLS}")
    print(f"  Set URL index   : {OUT_SET_URLS}")
    print(f"  Chrome bookmarks: {OUT_BOOKMARKS}")
    print("\nTo use bookmarks:")
    print("  Chrome → chrome://bookmarks → ⋮ menu → Import bookmarks → select bookmarks.html")


if __name__ == "__main__":
    main()
