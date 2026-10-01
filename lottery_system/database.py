"""
Data storage and management engine for Baloto, Revancha, and MiLoto.
Uses JSON storage for universal filesystem portability (local, cloud, Docker, NFS).
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.environ.get('LOTTERY_DATA_DIR', os.path.join(BASE_DIR, 'data'))
STORE_FILE = os.path.join(DATA_DIR, 'lottery_store.json')

def _load_store(file_path: str = STORE_FILE) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        initial = {
            "draws": {
                "baloto": [],
                "revancha": [],
                "miloto": []
            },
            "predictions": [],
            "sync_logs": []
        }
        _save_store(initial, file_path)
        return initial
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        initial = {
            "draws": {"baloto": [], "revancha": [], "miloto": []},
            "predictions": [],
            "sync_logs": []
        }
        return initial

def _save_store(data: Dict[str, Any], file_path: str = STORE_FILE):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, file_path)

def init_db(file_path: str = STORE_FILE):
    _load_store(file_path)

def insert_draw(game: str, draw_date: str, numbers: List[int],
                superball: Optional[int] = None,
                draw_number: Optional[int] = None,
                jackpot: Optional[str] = None,
                file_path: str = STORE_FILE) -> bool:
    """Inserts or updates a draw. Returns True if inserted/updated."""
    game = game.lower()
    numbers = sorted([int(x) for x in numbers])
    if len(numbers) != 5:
        raise ValueError(f"Expected 5 numbers, got {len(numbers)}")
    
    store = _load_store(file_path)
    if game not in store["draws"]:
        store["draws"][game] = []

    draws_list = store["draws"][game]
    
    # Check if draw exists by date or draw_number
    existing_idx = None
    for idx, d in enumerate(draws_list):
        if (draw_number and d.get("draw_number") == draw_number) or (d.get("draw_date") == draw_date):
            existing_idx = idx
            break

    draw_record = {
        "game": game,
        "draw_number": draw_number,
        "draw_date": draw_date,
        "numbers": numbers,
        "superball": int(superball) if superball is not None else None,
        "jackpot": jackpot,
        "updated_at": datetime.now().isoformat()
    }

    if existing_idx is not None:
        draws_list[existing_idx] = draw_record
    else:
        draws_list.append(draw_record)

    # Sort draws descending by date
    draws_list.sort(key=lambda x: (x.get("draw_date", ""), x.get("draw_number") or 0), reverse=True)
    store["draws"][game] = draws_list
    _save_store(store, file_path)
    return True

def get_draws(game: str, limit: Optional[int] = None, file_path: str = STORE_FILE) -> List[Dict[str, Any]]:
    store = _load_store(file_path)
    game = game.lower()
    draws = store["draws"].get(game, [])
    if limit:
        return draws[:limit]
    return draws

def get_latest_draw(game: str, file_path: str = STORE_FILE) -> Optional[Dict[str, Any]]:
    draws = get_draws(game, limit=1, file_path=file_path)
    return draws[0] if draws else None

def count_draws(game: Optional[str] = None, file_path: str = STORE_FILE) -> int:
    store = _load_store(file_path)
    if game:
        return len(store["draws"].get(game.lower(), []))
    total = sum(len(d) for d in store["draws"].values())
    return total

def log_sync(game: str, status: str, new_draws_count: int = 0, message: str = "", file_path: str = STORE_FILE):
    store = _load_store(file_path)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "game": game,
        "status": status,
        "new_draws_count": new_draws_count,
        "message": message
    }
    store["sync_logs"].insert(0, log_entry)
    store["sync_logs"] = store["sync_logs"][:100]  # keep last 100
    _save_store(store, file_path)

def save_prediction(game: str, target_date: str, strategy: str,
                    numbers: List[int], superball: Optional[int] = None,
                    score: float = 0.0, rationale: str = "",
                    file_path: str = STORE_FILE):
    store = _load_store(file_path)
    pred_entry = {
        "id": len(store["predictions"]) + 1,
        "timestamp": datetime.now().isoformat(),
        "game": game,
        "target_date": target_date,
        "strategy": strategy,
        "numbers": sorted(numbers),
        "superball": superball,
        "score": score,
        "rationale": rationale,
        "status": "active"
    }
    store["predictions"].insert(0, pred_entry)
    _save_store(store, file_path)
    return pred_entry

def get_predictions(game: Optional[str] = None, limit: int = 10, file_path: str = STORE_FILE) -> List[Dict[str, Any]]:
    store = _load_store(file_path)
    preds = store["predictions"]
    if game:
        preds = [p for p in preds if p["game"] == game.lower()]
    return preds[:limit]
