"""
Automated Data Updater and JSON Generator for Netlify Web App.
Includes multi-pass delayed verification (immediate + 1 hour later) for delayed lottery publications.
"""

import os
import sys
import json
import re
import urllib.request
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from bs4 import BeautifulSoup

# Ensure local packages are importable
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, os.path.join(root_dir, 'lottery_system'))
sys.path.insert(0, os.path.join(root_dir, 'lottery_engine'))

try:
    from database import get_draws, get_latest_draw, insert_draw, log_sync
    from analyzer import LotteryAnalyzer
    from predictor import LotteryPredictor
    from updater import fetch_and_update
except ImportError:
    sys.path.insert(0, root_dir)
    from lottery_system.database import get_draws, get_latest_draw, insert_draw, log_sync
    from lottery_system.analyzer import LotteryAnalyzer
    from lottery_system.predictor import LotteryPredictor
    from lottery_system.updater import fetch_and_update

OUTPUT_JSON_PATH = os.path.join(os.path.dirname(current_dir), 'data', 'lottery_data.json')

def is_draw_day(game: str, check_date: date) -> bool:
    """Returns True if check_date is an official draw day for the game."""
    weekday = check_date.weekday() # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    if game in ['baloto', 'revancha']:
        return weekday in [0, 2, 5] # Lunes, Miércoles, Sábado
    elif game == 'miloto':
        return weekday in [0, 1, 3, 4] # Lunes, Martes, Jueves, Viernes
    return False

def check_publication_status(game: str) -> Dict[str, Any]:
    """Evaluates whether today's draw has been published or if a 1-hour delay check is needed."""
    today = datetime.now().date()
    latest = get_latest_draw(game)
    latest_date_str = latest.get("draw_date") if latest else None
    
    if not is_draw_day(game, today):
        return {
            "is_draw_day": False,
            "status": "up_to_date",
            "message": f"Hoy no es día de sorteo de {game.capitalize()}. Último sorteo registrado: {latest_date_str}."
        }

    # If it is draw day:
    if latest_date_str == today.strftime("%Y-%m-%d"):
        return {
            "is_draw_day": True,
            "status": "published",
            "message": f"Sorteo de hoy ({today}) ya publicado y registrado con éxito."
        }
    else:
        return {
            "is_draw_day": True,
            "status": "pending_verification",
            "message": f"Sorteo de hoy ({today}) aún pendiente en web oficial. Se activará la re-verificación a la hora siguiente."
        }

def update_and_export():
    now_iso = datetime.now().isoformat()
    print(f"[{now_iso}] Iniciando ciclo de verificación y actualización de sorteos...")
    
    # 1. Intentar extracción web oficial
    sync_result = {"status": "offline_mode", "updated_counts": {}}
    try:
        sync_result = fetch_and_update()
        print(f"Resultado de consulta oficial: {sync_result.get('status')}")
    except Exception as e:
        print(f"Aviso de conexión: {e}. Usando datos locales almacenados.")

    # 2. Diagnóstico de publicación para cada juego
    pub_status = {}
    for g in ['baloto', 'revancha', 'miloto']:
        pub_status[g] = check_publication_status(g)
        print(f"• {g.upper()}: {pub_status[g]['status']} -> {pub_status[g]['message']}")

    # 3. Generar el payload analítico completo
    games = ['baloto', 'revancha', 'miloto']
    payload = {
        "metadata": {
            "title": "LottoAnalytics Colombia",
            "last_updated": now_iso,
            "status": "online",
            "publication_status": pub_status,
            "sync_info": {
                "auto_sync_active": True,
                "multi_pass_active": True,
                "verification_policy": "Doble chequeo: 11:30 PM y re-verificación 1 hora después (12:30 AM) ante demoras oficiales."
            }
        },
        "games": {}
    }

    for g in games:
        analyzer = LotteryAnalyzer(g)
        predictor = LotteryPredictor(g)
        
        freq = analyzer.get_frequency_stats()
        gaps = analyzer.get_gap_and_delay_stats()
        dist = analyzer.get_distribution_metrics()
        pairs = analyzer.get_top_pairs_and_triplets(top_n=10)
        latest = get_latest_draw(g)
        recent_draws = get_draws(g, limit=10)
        pack = predictor.generate_full_ticket_pack()

        # Precompute VIP critical radar (balls with overdue index >= 1.5)
        critical_radar = [x for x in gaps if x["overdue_index"] >= 1.5]

        payload["games"][g] = {
            "id": g,
            "name": "Baloto Tradicional" if g == 'baloto' else ("Baloto Revancha" if g == 'revancha' else "MiLoto"),
            "max_number": analyzer.max_number,
            "has_superball": analyzer.has_superball,
            "max_superball": analyzer.max_superball,
            "total_draws": analyzer.total_draws_count(),
            "latest_draw": latest,
            "recent_draws": recent_draws,
            "sum_metrics": dist["sum_metrics"],
            "parity_distribution": dist["parity_distribution"],
            "number_stats": freq["number_stats"],
            "superball_stats": freq.get("superball_stats", []),
            "gaps": gaps,
            "critical_radar": critical_radar,
            "top_pairs": pairs["top_pairs"],
            "top_triplets": pairs["top_triplets"],
            "predictions": pack
        }

    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Archivo exportado con éxito en: {OUTPUT_JSON_PATH}")
    print(f"Tamaño de datos: {os.path.getsize(OUTPUT_JSON_PATH) / 1024:.2f} KB")

if __name__ == '__main__':
    update_and_export()
