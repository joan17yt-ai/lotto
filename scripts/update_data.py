"""
Automated Data Updater and JSON Generator for Netlify Web App.
Runs locally or inside GitHub Actions nightly to refresh lottery_data.json.
"""

import os
import sys
import json
import re
import urllib.request
from datetime import datetime
from bs4 import BeautifulSoup

# Ensure local packages are importable
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, os.path.join(root_dir, 'lottery_system'))
sys.path.insert(0, os.path.join(root_dir, 'lottery_engine'))

try:
    from database import get_draws, get_latest_draw, insert_draw
    from analyzer import LotteryAnalyzer
    from predictor import LotteryPredictor
    from updater import fetch_and_update
except ImportError:
    # Standalone fallback if run outside repo
    sys.path.insert(0, root_dir)
    from lottery_system.database import get_draws, get_latest_draw, insert_draw
    from lottery_system.analyzer import LotteryAnalyzer
    from lottery_system.predictor import LotteryPredictor
    from lottery_system.updater import fetch_and_update

OUTPUT_JSON_PATH = os.path.join(os.path.dirname(current_dir), 'data', 'lottery_data.json')

def update_and_export():
    print(f"[{datetime.now().isoformat()}] Iniciando actualización de datos...")
    
    # 1. Intentar actualizar desde la web si hay conexión a internet
    try:
        sync_result = fetch_and_update()
        print(f"Estado de sincronización web: {sync_result['status']}")
    except Exception as e:
        print(f"Aviso: No se pudo conectar a la web externa ({e}), utilizando datos locales almacenados.")

    # 2. Generar el payload analítico completo
    games = ['baloto', 'revancha', 'miloto']
    payload = {
        "metadata": {
            "title": "LottoAnalytics Colombia",
            "last_updated": datetime.now().isoformat(),
            "status": "online"
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
