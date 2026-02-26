#!/usr/bin/env python3
"""
Scrape card rarity data from scrydex.com for all Pokemon TCG expansions.
Updates the future_sight PostgreSQL database with rarity, image URLs, and set metadata.
Also exports JSON files to ~/pokemon_card_data/.
"""

import os
import re
import sys
import json
import time
import requests
import psycopg2
from pathlib import Path

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
BASE_URL = 'https://scrydex.com/pokemon/expansions'
IMAGE_URL_TEMPLATE = 'https://images.scrydex.com/pokemon/{card_id}/small'
DELAY = 1.0  # seconds between requests

# All expansions from scrydex (name, slug/code)
EXPANSIONS = [
    # Mega Evolution
    ("Ascended Heroes", "ascended-heroes/me2pt5"),
    ("Phantasmal Flames", "phantasmal-flames/me2"),
    ("Mega Evolution", "mega-evolution/me1"),
    ("Mega Evolution Black Star Promos", "mega-evolution-black-star-promos/mep"),
    # Scarlet & Violet
    ("White Flare", "white-flare/rsv10pt5"),
    ("Black Bolt", "black-bolt/zsv10pt5"),
    ("Destined Rivals", "destined-rivals/sv10"),
    ("Journey Together", "journey-together/sv9"),
    ("Prismatic Evolutions", "prismatic-evolutions/sv8pt5"),
    ("Surging Sparks", "surging-sparks/sv8"),
    ("Stellar Crown", "stellar-crown/sv7"),
    ("Shrouded Fable", "shrouded-fable/sv6pt5"),
    ("Twilight Masquerade", "twilight-masquerade/sv6"),
    ("Temporal Forces", "temporal-forces/sv5"),
    ("Paldean Fates", "paldean-fates/sv4pt5"),
    ("Paradox Rift", "paradox-rift/sv4"),
    ("151", "151/sv3pt5"),
    ("Obsidian Flames", "obsidian-flames/sv3"),
    ("Paldea Evolved", "paldea-evolved/sv2"),
    ("Scarlet & Violet", "scarlet-violet/sv1"),
    ("Scarlet & Violet Energies", "scarlet-violet-energies/sve"),
    ("Scarlet & Violet Black Star Promos", "scarlet-violet-black-star-promos/svp"),
    # Sword & Shield
    ("Crown Zenith Galarian Gallery", "crown-zenith-galarian-gallery/swsh12pt5gg"),
    ("Crown Zenith", "crown-zenith/swsh12pt5"),
    ("Silver Tempest Trainer Gallery", "silver-tempest-trainer-gallery/swsh12tg"),
    ("Silver Tempest", "silver-tempest/swsh12"),
    ("Lost Origin Trainer Gallery", "lost-origin-trainer-gallery/swsh11tg"),
    ("Lost Origin", "lost-origin/swsh11"),
    ("Pokemon GO", "pokmon-go/pgo"),
    ("Astral Radiance Trainer Gallery", "astral-radiance-trainer-gallery/swsh10tg"),
    ("Astral Radiance", "astral-radiance/swsh10"),
    ("Brilliant Stars Trainer Gallery", "brilliant-stars-trainer-gallery/swsh9tg"),
    ("Brilliant Stars", "brilliant-stars/swsh9"),
    ("Fusion Strike", "fusion-strike/swsh8"),
    ("Celebrations: Classic Collection", "celebrations-classic-collection/cel25c"),
    ("Celebrations", "celebrations/cel25"),
    ("Evolving Skies", "evolving-skies/swsh7"),
    ("Chilling Reign", "chilling-reign/swsh6"),
    ("Battle Styles", "battle-styles/swsh5"),
    ("Shining Fates Shiny Vault", "shining-fates-shiny-vault/swsh45sv"),
    ("Shining Fates", "shining-fates/swsh45"),
    ("Vivid Voltage", "vivid-voltage/swsh4"),
    ("Champion's Path", "champions-path/swsh35"),
    ("Darkness Ablaze", "darkness-ablaze/swsh3"),
    ("Rebel Clash", "rebel-clash/swsh2"),
    ("Sword & Shield", "sword-shield/swsh1"),
    ("SWSH Black Star Promos", "swsh-black-star-promos/swshp"),
    # Sun & Moon
    ("Cosmic Eclipse", "cosmic-eclipse/sm12"),
    ("Hidden Fates Shiny Vault", "hidden-fates-shiny-vault/sma"),
    ("Hidden Fates", "hidden-fates/sm115"),
    ("Unified Minds", "unified-minds/sm11"),
    ("Unbroken Bonds", "unbroken-bonds/sm10"),
    ("Detective Pikachu", "detective-pikachu/det1"),
    ("Team Up", "team-up/sm9"),
    ("Lost Thunder", "lost-thunder/sm8"),
    ("Dragon Majesty", "dragon-majesty/sm75"),
    ("Celestial Storm", "celestial-storm/sm7"),
    ("Forbidden Light", "forbidden-light/sm6"),
    ("Ultra Prism", "ultra-prism/sm5"),
    ("Crimson Invasion", "crimson-invasion/sm4"),
    ("Shining Legends", "shining-legends/sm35"),
    ("Burning Shadows", "burning-shadows/sm3"),
    ("Guardians Rising", "guardians-rising/sm2"),
    ("SM Black Star Promos", "sm-black-star-promos/smp"),
    ("Sun & Moon", "sun-moon/sm1"),
    # XY
    ("Evolutions", "evolutions/xy12"),
    ("Steam Siege", "steam-siege/xy11"),
    ("Fates Collide", "fates-collide/xy10"),
    ("Generations", "generations/g1"),
    ("BREAKpoint", "breakpoint/xy9"),
    ("BREAKthrough", "breakthrough/xy8"),
    ("Ancient Origins", "ancient-origins/xy7"),
    ("Roaring Skies", "roaring-skies/xy6"),
    ("Double Crisis", "double-crisis/dc1"),
    ("Primal Clash", "primal-clash/xy5"),
    ("Phantom Forces", "phantom-forces/xy4"),
    ("Furious Fists", "furious-fists/xy3"),
    ("Flashfire", "flashfire/xy2"),
    ("XY", "xy/xy1"),
    ("Kalos Starter Set", "kalos-starter-set/xy0"),
    ("XY Black Star Promos", "xy-black-star-promos/xyp"),
    # Black & White
    ("Legendary Treasures", "legendary-treasures/bw11"),
    ("Plasma Blast", "plasma-blast/bw10"),
    ("Plasma Freeze", "plasma-freeze/bw9"),
    ("Plasma Storm", "plasma-storm/bw8"),
    ("Boundaries Crossed", "boundaries-crossed/bw7"),
    ("Dragon Vault", "dragon-vault/dv1"),
    ("Dragons Exalted", "dragons-exalted/bw6"),
    ("Dark Explorers", "dark-explorers/bw5"),
    ("Next Destinies", "next-destinies/bw4"),
    ("Noble Victories", "noble-victories/bw3"),
    ("Emerging Powers", "emerging-powers/bw2"),
    ("Black & White", "black-white/bw1"),
    ("BW Black Star Promos", "bw-black-star-promos/bwp"),
    # HeartGold & SoulSilver
    ("Call of Legends", "call-of-legends/col1"),
    ("HS Triumphant", "hstriumphant/hgss4"),
    ("HS Undaunted", "hsundaunted/hgss3"),
    ("HS Unleashed", "hsunleashed/hgss2"),
    ("HGSS Black Star Promos", "hgss-black-star-promos/hsp"),
    ("HeartGold & SoulSilver", "heartgold-soulsilver/hgss1"),
    # Platinum
    ("Arceus", "arceus/pl4"),
    ("Supreme Victors", "supreme-victors/pl3"),
    ("Rising Rivals", "rising-rivals/pl2"),
    ("Platinum", "platinum/pl1"),
    # POP
    ("POP Series 9", "pop-series-9/pop9"),
    ("POP Series 8", "pop-series-8/pop8"),
    ("POP Series 7", "pop-series-7/pop7"),
    ("POP Series 6", "pop-series-6/pop6"),
    ("POP Series 5", "pop-series-5/pop5"),
    ("POP Series 4", "pop-series-4/pop4"),
    ("POP Series 3", "pop-series-3/pop3"),
    ("POP Series 2", "pop-series-2/pop2"),
    ("POP Series 1", "pop-series-1/pop1"),
    # Diamond & Pearl
    ("Stormfront", "stormfront/dp7"),
    ("Legends Awakened", "legends-awakened/dp6"),
    ("Majestic Dawn", "majestic-dawn/dp5"),
    ("Great Encounters", "great-encounters/dp4"),
    ("Secret Wonders", "secret-wonders/dp3"),
    ("Mysterious Treasures", "mysterious-treasures/dp2"),
    ("DP Black Star Promos", "dp-black-star-promos/dpp"),
    ("Diamond & Pearl", "diamond-pearl/dp1"),
    # EX
    ("Power Keepers", "power-keepers/ex16"),
    ("Dragon Frontiers", "dragon-frontiers/ex15"),
    ("Crystal Guardians", "crystal-guardians/ex14"),
    ("Holon Phantoms", "holon-phantoms/ex13"),
    ("EX Trainer Kit 2 Minun", "ex-trainer-kit-2-minun/tk2b"),
    ("EX Trainer Kit 2 Plusle", "ex-trainer-kit-2-plusle/tk2a"),
    ("Legend Maker", "legend-maker/ex12"),
    ("Delta Species", "delta-species/ex11"),
    ("Unseen Forces", "unseen-forces/ex10"),
    ("Emerald", "emerald/ex9"),
    ("Deoxys", "deoxys/ex8"),
    ("Team Rocket Returns", "team-rocket-returns/ex7"),
    ("FireRed & LeafGreen", "firered-leafgreen/ex6"),
    ("Hidden Legends", "hidden-legends/ex5"),
    ("EX Trainer Kit Latios", "ex-trainer-kit-latios/tk1b"),
    ("EX Trainer Kit Latias", "ex-trainer-kit-latias/tk1a"),
    ("Team Magma vs Team Aqua", "team-magma-vs-team-aqua/ex4"),
    ("Dragon", "dragon/ex3"),
    ("Sandstorm", "sandstorm/ex2"),
    ("Ruby & Sapphire", "ruby-sapphire/ex1"),
    # E-Card
    ("Skyridge", "skyridge/ecard3"),
    ("Aquapolis", "aquapolis/ecard2"),
    ("Expedition Base Set", "expedition-base-set/ecard1"),
    # Neo
    ("Neo Destiny", "neo-destiny/neo4"),
    ("Neo Revelation", "neo-revelation/neo3"),
    ("Neo Discovery", "neo-discovery/neo2"),
    ("Neo Genesis", "neo-genesis/neo1"),
    # Gym
    ("Gym Challenge", "gym-challenge/gym2"),
    ("Gym Heroes", "gym-heroes/gym1"),
    # Base
    ("Team Rocket", "team-rocket/base5"),
    ("Base Set 2", "base-set-2/base4"),
    ("Fossil", "fossil/base3"),
    ("Wizards Black Star Promos", "wizards-black-star-promos/basep"),
    ("Jungle", "jungle/base2"),
    ("Base", "base/base1"),
    # Other
    ("McDonald's Collection 2024", "mcdonalds-collection-2024/mcd24"),
    ("Pokemon TCG Classic Venusaur", "pokmon-tcg-classic-venusaur/clv"),
    ("Pokemon TCG Classic Charizard", "pokmon-tcg-classic-charizard/clc"),
    ("Pokemon TCG Classic Blastoise", "pokmon-tcg-classic-blastoise/clb"),
    ("McDonald's Collection 2023", "mcdonalds-collection-2023/mcd23"),
    ("McDonald's Collection 2022", "mcdonalds-collection-2022/mcd22"),
    ("McDonald's Collection 2021", "mcdonalds-collection-2021/mcd21"),
    ("Pokemon Futsal Collection", "pokmon-futsal-collection/fut20"),
    ("McDonald's Collection 2019", "mcdonalds-collection-2019/mcd19"),
    ("McDonald's Collection 2018", "mcdonalds-collection-2018/mcd18"),
    ("McDonald's Collection 2017", "mcdonalds-collection-2017/mcd17"),
    ("McDonald's Collection 2016", "mcdonalds-collection-2016/mcd16"),
    ("McDonald's Collection 2015", "mcdonalds-collection-2015/mcd15"),
    ("McDonald's Collection 2014", "mcdonalds-collection-2014/mcd14"),
    ("McDonald's Collection 2012", "mcdonalds-collection-2012/mcd12"),
    ("McDonald's Collection 2011", "mcdonalds-collection-2011/mcd11"),
    ("Pokemon Rumble", "pokmon-rumble/ru1"),
    ("Poke Card Creator Pack", "pok-card-creator-pack/wb1"),
    ("Best of Game", "best-of-game/bp"),
    ("Legendary Collection", "legendary-collection/base6"),
    ("Southern Islands", "southern-islands/si1"),
    ("Nintendo Black Star Promos", "nintendo-black-star-promos/np"),
]

# Regex to extract card data from expansion page HTML
CARD_PATTERN = re.compile(
    r'font-bold text-body-16\">([^<]+)</span><span[^>]+>#(\d+[a-zA-Z]*)</span>.*?text-body-14\">([^<]+)</div>',
    re.DOTALL
)


def get_set_code(slug_code: str) -> str:
    """Extract set code from 'slug/code' string."""
    return slug_code.split('/')[-1]


def scrape_expansion(name: str, slug_code: str) -> list[dict]:
    """Fetch expansion page and extract card data."""
    code = get_set_code(slug_code)
    url = f"{BASE_URL}/{slug_code}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return []

    matches = CARD_PATTERN.findall(r.text)
    cards = []
    for card_name, number, rarity in matches:
        card_id = f"{code}-{number}"
        image_url = IMAGE_URL_TEMPLATE.format(card_id=card_id)
        cards.append({
            'id': card_id,
            'name': card_name.strip(),
            'number': number,
            'rarity': rarity.strip(),
            'set_id': code,
            'set_name': name,
            'image_url': image_url,
            'scrydex_url': url,
        })

    return cards


def upsert_cards(cursor, cards: list[dict], set_name: str, set_code: str):
    """Upsert card records into DB."""
    if not cards:
        return 0

    # Ensure set exists
    cursor.execute("""
        INSERT INTO pokemon_sets (id, name, series)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
    """, (set_code, set_name, ''))

    count = 0
    for card in cards:
        cursor.execute("""
            INSERT INTO pokemon_cards (id, name, number, rarity, set_id, images, scrydex_url, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                number = EXCLUDED.number,
                rarity = EXCLUDED.rarity,
                set_id = EXCLUDED.set_id,
                image_url = EXCLUDED.image_url,
                scrydex_url = EXCLUDED.scrydex_url,
                updated_at = NOW()
        """, (
            card['id'],
            card['name'],
            card['number'],
            card['rarity'],
            card['set_id'],
            json.dumps({'small': card['image_url']}),
            card['scrydex_url'],
            card['image_url'],
        ))
        count += 1

    return count


def export_json(all_sets: list[dict], all_cards: list[dict]):
    """Export data to JSON files."""
    output_dir = Path.home() / 'pokemon_card_data'
    output_dir.mkdir(exist_ok=True)
    by_set_dir = output_dir / 'cards_by_set'
    by_set_dir.mkdir(exist_ok=True)

    # Write sets.json
    with open(output_dir / 'sets.json', 'w') as f:
        json.dump(all_sets, f, indent=2)
    print(f"  Wrote sets.json ({len(all_sets)} sets)")

    # Write cards.json
    with open(output_dir / 'cards.json', 'w') as f:
        json.dump(all_cards, f, indent=2)
    print(f"  Wrote cards.json ({len(all_cards)} cards)")

    # Write per-set files
    cards_by_set = {}
    for card in all_cards:
        sid = card['set_id']
        cards_by_set.setdefault(sid, []).append(card)

    for set_id, cards in cards_by_set.items():
        with open(by_set_dir / f"{set_id}.json", 'w') as f:
            json.dump(cards, f, indent=2)

    print(f"  Wrote {len(cards_by_set)} per-set JSON files to cards_by_set/")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dbname', default='future_sight')
    parser.add_argument('--user', default=os.environ.get('USER', 'clawdbot1'))
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='5432')
    parser.add_argument('--skip-db', action='store_true', help='Skip DB updates, just export JSON')
    parser.add_argument('--set', help='Only process this set code (e.g. sv1)')
    parser.add_argument('--resume-from', help='Resume from this set code')
    args = parser.parse_args()

    # Connect to DB
    conn = None
    if not args.skip_db:
        conn = psycopg2.connect(
            host=args.host, port=args.port,
            dbname=args.dbname, user=args.user
        )
        conn.autocommit = False
        cursor = conn.cursor()
        # Add image_url column if missing
        cursor.execute("""
            ALTER TABLE pokemon_cards
            ADD COLUMN IF NOT EXISTS image_url TEXT
        """)
        conn.commit()
        print(f"Connected to {args.dbname}")

    all_cards = []
    all_sets = []
    total_cards = 0
    errors = []

    expansions = EXPANSIONS
    if args.set:
        expansions = [(n, s) for n, s in EXPANSIONS if get_set_code(s) == args.set]
    elif args.resume_from:
        codes = [get_set_code(s) for _, s in EXPANSIONS]
        if args.resume_from in codes:
            idx = codes.index(args.resume_from)
            expansions = EXPANSIONS[idx:]
            print(f"Resuming from {args.resume_from} ({len(expansions)} sets remaining)")

    print(f"\nProcessing {len(expansions)} expansions...\n")

    for i, (name, slug_code) in enumerate(expansions, 1):
        code = get_set_code(slug_code)
        print(f"[{i}/{len(expansions)}] {name} ({code})", end="", flush=True)

        cards = scrape_expansion(name, slug_code)

        if not cards:
            print(f" - 0 cards (skipped)")
            errors.append(f"{code}: no cards found")
            time.sleep(DELAY)
            continue

        print(f" - {len(cards)} cards", end="", flush=True)

        if conn:
            try:
                count = upsert_cards(cursor, cards, name, code)
                conn.commit()
                print(f" - DB updated", end="", flush=True)
            except Exception as e:
                conn.rollback()
                print(f" - DB ERROR: {e}")
                errors.append(f"{code}: {e}")

        all_cards.extend(cards)
        all_sets.append({'id': code, 'name': name, 'slug': slug_code, 'card_count': len(cards)})
        total_cards += len(cards)
        print()

        time.sleep(DELAY)

    # Export JSON
    print(f"\nExporting JSON...")
    export_json(all_sets, all_cards)

    if conn:
        cursor.close()
        conn.close()

    print(f"\n=== Done ===")
    print(f"Sets processed: {len(all_sets)}")
    print(f"Total cards: {total_cards}")
    if errors:
        print(f"Errors ({len(errors)}): {errors[:5]}")


if __name__ == '__main__':
    main()
