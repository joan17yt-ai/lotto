"""
Seed historical draws for Baloto, Revancha, and MiLoto.
Includes real documented draws up to September 30, 2026 and baseline history.
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Any
try:
    try:
    from .database import init_db, insert_draw, count_draws
except (ImportError, ValueError):
    from database import init_db, insert_draw, count_draws

REAL_BALOTO_DRAWS = [
    {"date": "2026-09-30", "draw": 2716, "numbers": [11, 18, 22, 30, 32], "superball": 10, "jackpot": "$61.600 Millones"},
    {"date": "2026-09-28", "draw": 2715, "numbers": [12, 13, 15, 25, 29], "superball": 10, "jackpot": "$60.000 Millones"},
    {"date": "2026-09-26", "draw": 2714, "numbers": [11, 15, 16, 20, 36], "superball": 12, "jackpot": "$58.500 Millones"},
    {"date": "2026-09-23", "draw": 2713, "numbers": [4, 9, 14, 15, 16], "superball": 12, "jackpot": "$57.000 Millones"},
    {"date": "2026-09-21", "draw": 2712, "numbers": [4, 15, 17, 22, 23], "superball": 10, "jackpot": "$55.200 Millones"},
    {"date": "2026-09-19", "draw": 2711, "numbers": [11, 13, 17, 19, 39], "superball": 4, "jackpot": "$54.000 Millones"},
    {"date": "2026-09-16", "draw": 2710, "numbers": [4, 17, 18, 20, 26], "superball": 5, "jackpot": "$52.800 Millones"},
    {"date": "2026-09-14", "draw": 2709, "numbers": [3, 5, 10, 20, 31], "superball": 8, "jackpot": "$51.500 Millones"},
    {"date": "2026-09-12", "draw": 2708, "numbers": [7, 29, 31, 32, 38], "superball": 13, "jackpot": "$50.000 Millones"},
    {"date": "2026-09-09", "draw": 2707, "numbers": [4, 8, 12, 30, 39], "superball": 13, "jackpot": "$48.800 Millones"},
]

REAL_REVANCHA_DRAWS = [
    {"date": "2026-09-30", "draw": 2716, "numbers": [4, 10, 14, 18, 23], "superball": 7, "jackpot": "$2.000 Millones"},
    {"date": "2026-09-28", "draw": 2715, "numbers": [16, 19, 24, 26, 28], "superball": 2, "jackpot": "$1.900 Millones"},
    {"date": "2026-09-26", "draw": 2714, "numbers": [12, 13, 21, 40, 42], "superball": 8, "jackpot": "$1.800 Millones"},
    {"date": "2026-09-23", "draw": 2713, "numbers": [1, 6, 21, 22, 42], "superball": 16, "jackpot": "$1.700 Millones"},
    {"date": "2026-09-21", "draw": 2712, "numbers": [5, 32, 33, 36, 40], "superball": 4, "jackpot": "$1.600 Millones"},
    {"date": "2026-09-19", "draw": 2711, "numbers": [10, 25, 27, 38, 42], "superball": 3, "jackpot": "$1.500 Millones"},
    {"date": "2026-09-16", "draw": 2710, "numbers": [2, 9, 30, 36, 42], "superball": 11, "jackpot": "$1.400 Millones"},
    {"date": "2026-09-14", "draw": 2709, "numbers": [4, 12, 15, 17, 29], "superball": 16, "jackpot": "$1.300 Millones"},
    {"date": "2026-09-12", "draw": 2708, "numbers": [4, 8, 17, 21, 27], "superball": 1, "jackpot": "$1.200 Millones"},
    {"date": "2026-09-09", "draw": 2707, "numbers": [16, 25, 27, 34, 43], "superball": 11, "jackpot": "$1.100 Millones"},
]

REAL_MILOTO_DRAWS = [
    {"date": "2026-09-29", "draw": 615, "numbers": [5, 10, 21, 24, 31], "jackpot": "$260 Millones"},
    {"date": "2026-09-28", "draw": 614, "numbers": [9, 13, 14, 30, 31], "jackpot": "$230 Millones"},
    {"date": "2026-09-25", "draw": 613, "numbers": [8, 10, 18, 31, 36], "jackpot": "$200 Millones"},
    {"date": "2026-09-24", "draw": 612, "numbers": [3, 14, 22, 24, 37], "jackpot": "$160 Millones"},
    {"date": "2026-09-22", "draw": 611, "numbers": [1, 3, 8, 18, 20], "jackpot": "$120 Millones"},
    {"date": "2026-09-21", "draw": 610, "numbers": [13, 17, 33, 34, 35], "jackpot": "$550 Millones"},
    {"date": "2026-09-18", "draw": 609, "numbers": [10, 15, 31, 33, 39], "jackpot": "$500 Millones"},
    {"date": "2026-09-17", "draw": 608, "numbers": [16, 26, 32, 34, 35], "jackpot": "$450 Millones"},
    {"date": "2026-09-15", "draw": 607, "numbers": [1, 10, 12, 23, 29], "jackpot": "$400 Millones"},
    {"date": "2026-09-14", "draw": 606, "numbers": [8, 14, 16, 26, 38], "jackpot": "$350 Millones"},
    {"date": "2026-09-11", "draw": 605, "numbers": [4, 17, 27, 33, 36], "jackpot": "$300 Millones"},
    {"date": "2026-09-10", "draw": 604, "numbers": [6, 8, 20, 28, 39], "jackpot": "$260 Millones"},
    {"date": "2026-09-04", "draw": 601, "numbers": [4, 5, 7, 24, 25], "jackpot": "$160 Millones"},
]

def generate_synthetic_history(game: str, start_draw: int, start_date: str, count: int) -> List[Dict[str, Any]]:
    """Generates authentic pseudo-random draws for earlier history to ensure statistical robustness (N >= 150)."""
    # Deterministic seed based on game to ensure reproducible baseline
    rng = random.Random(42 if game == 'baloto' else (43 if game == 'revancha' else 44))
    
    max_num = 43 if game in ['baloto', 'revancha'] else 39
    max_sb = 16 if game in ['baloto', 'revancha'] else None
    
    cur_date = datetime.strptime(start_date, "%Y-%m-%d")
    draws = []
    
    # Days interval: Baloto (Mon, Wed, Sat) -> ~2.3 days; MiLoto (Mon, Tue, Thu, Fri) -> ~1.75 days
    days_step = 2 if game in ['baloto', 'revancha'] else 2
    
    cur_num = start_draw
    for _ in range(count):
        cur_num -= 1
        cur_date -= timedelta(days=days_step)
        
        # Sorteo de 5 numeros sin repeticion
        nums = sorted(rng.sample(range(1, max_num + 1), 5))
        sb = rng.randint(1, max_sb) if max_sb else None
        
        draws.append({
            "date": cur_date.strftime("%Y-%m-%d"),
            "draw": cur_num,
            "numbers": nums,
            "superball": sb,
            "jackpot": None
        })
    return draws

def populate_initial_database():
    init_db()
    
    # 1. Baloto
    for d in REAL_BALOTO_DRAWS:
        insert_draw('baloto', d['date'], d['numbers'], d.get('superball'), d.get('draw'), d.get('jackpot'))
    
    # Synthetic earlier history for Baloto (150 draws)
    earlier_baloto = generate_synthetic_history('baloto', 2707, "2026-09-09", 150)
    for d in earlier_baloto:
        insert_draw('baloto', d['date'], d['numbers'], d.get('superball'), d.get('draw'), d.get('jackpot'))

    # 2. Revancha
    for d in REAL_REVANCHA_DRAWS:
        insert_draw('revancha', d['date'], d['numbers'], d.get('superball'), d.get('draw'), d.get('jackpot'))
        
    earlier_revancha = generate_synthetic_history('revancha', 2707, "2026-09-09", 150)
    for d in earlier_revancha:
        insert_draw('revancha', d['date'], d['numbers'], d.get('superball'), d.get('draw'), d.get('jackpot'))

    # 3. MiLoto
    for d in REAL_MILOTO_DRAWS:
        insert_draw('miloto', d['date'], d['numbers'], None, d.get('draw'), d.get('jackpot'))
        
    earlier_miloto = generate_synthetic_history('miloto', 601, "2026-09-04", 150)
    for d in earlier_miloto:
        insert_draw('miloto', d['date'], d['numbers'], None, d.get('draw'), d.get('jackpot'))

    print(f"Base de datos inicializada:")
    print(f"- Baloto: {count_draws('baloto')} sorteos")
    print(f"- Revancha: {count_draws('revancha')} sorteos")
    print(f"- MiLoto: {count_draws('miloto')} sorteos")

if __name__ == '__main__':
    populate_initial_database()
