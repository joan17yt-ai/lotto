"""
Automated Scraper and ETL Updater for Baloto, Revancha, and MiLoto.
Parses official draw results, updates the database, and refreshes analytical metrics.
"""

import re
import urllib.request
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

try:
    from .database import insert_draw, get_latest_draw, log_sync
except (ImportError, ValueError):
    from database import insert_draw, get_latest_draw, log_sync

MONTH_MAP = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

def parse_spanish_date(date_str: str) -> Optional[str]:
    """Converts strings like '30 de Septiembre de 2026' or '29 de Septiembre de 2026' to 'YYYY-MM-DD'."""
    pattern = r"(\d{1,2})\s+de\s+([a-zA-ZáéíóúÁÉÍÓÚ]+)\s+de\s+(\d{4})"
    match = re.search(pattern, date_str, re.IGNORECASE)
    if match:
        day = match.group(1).zfill(2)
        month_name = match.group(2).lower()
        year = match.group(3)
        month = MONTH_MAP.get(month_name, "01")
        return f"{year}-{month}-{day}"
    return None

def parse_baloto_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses baloto.com/resultados HTML.
    On baloto.com, draws are listed in pairs: row 1 is Baloto, row 2 is Revancha.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    # Find table rows or text blocks matching draw formats
    rows = soup.find_all('tr')
    current_date = None
    draw_index_for_date = 0

    for tr in rows:
        text = tr.get_text(separator=' ').strip()
        date_parsed = parse_spanish_date(text)
        
        # Extract numbers like '11 - 18 - 22 - 30 - 32 - 10'
        num_match = re.search(r"(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})", text)
        if num_match and date_parsed:
            if date_parsed != current_date:
                current_date = date_parsed
                draw_index_for_date = 0
            else:
                draw_index_for_date += 1

            numbers = [int(num_match.group(i)) for i in range(1, 6)]
            superball = int(num_match.group(6))
            game = "baloto" if draw_index_for_date == 0 else "revancha"

            results.append({
                "game": game,
                "date": date_parsed,
                "numbers": sorted(numbers),
                "superball": superball
            })

    return results

def parse_miloto_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses baloto.com/miloto/resultados/ HTML.
    Extracts 5 numbers per draw.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    rows = soup.find_all('tr')
    for tr in rows:
        text = tr.get_text(separator=' ').strip()
        date_parsed = parse_spanish_date(text)
        
        # Extract 5 numbers: '05 - 10 - 21 - 24 - 31'
        num_match = re.search(r"(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(\d{2})", text)
        if num_match and date_parsed:
            numbers = [int(num_match.group(i)) for i in range(1, 6)]
            results.append({
                "game": "miloto",
                "date": date_parsed,
                "numbers": sorted(numbers),
                "superball": None
            })

    return results

def fetch_and_update(game: str = "all", timeout_secs: int = 10) -> Dict[str, Any]:
    """
    Connects to the official baloto.com endpoints, downloads results, and updates the database.
    Designed for production/server deployment with internet access.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    updated_counts = {"baloto": 0, "revancha": 0, "miloto": 0}
    errors = []

    # 1. Baloto & Revancha
    if game in ["all", "baloto", "revancha"]:
        try:
            req = urllib.request.Request("https://baloto.com/resultados", headers=headers)
            with urllib.request.urlopen(req, timeout=timeout_secs) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                items = parse_baloto_html(html)
                for item in items:
                    g = item["game"]
                    if insert_draw(g, item["date"], item["numbers"], item["superball"]):
                        updated_counts[g] += 1
            log_sync("baloto_revancha", "SUCCESS", updated_counts["baloto"] + updated_counts["revancha"], "Actualización web completada.")
        except Exception as e:
            errors.append(f"Error actualizando Baloto/Revancha: {str(e)}")
            log_sync("baloto_revancha", "ERROR", 0, str(e))

    # 2. MiLoto
    if game in ["all", "miloto"]:
        try:
            req = urllib.request.Request("https://baloto.com/miloto/resultados/", headers=headers)
            with urllib.request.urlopen(req, timeout=timeout_secs) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                items = parse_miloto_html(html)
                for item in items:
                    if insert_draw("miloto", item["date"], item["numbers"], None):
                        updated_counts["miloto"] += 1
            log_sync("miloto", "SUCCESS", updated_counts["miloto"], "Actualización web completada.")
        except Exception as e:
            errors.append(f"Error actualizando MiLoto: {str(e)}")
            log_sync("miloto", "ERROR", 0, str(e))

    return {
        "status": "partial" if errors else "success",
        "updated_counts": updated_counts,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }

def ingest_raw_draw(game: str, date_str: str, numbers_str: str, superball: Optional[int] = None, draw_num: Optional[int] = None) -> bool:
    """Helper to ingest a draw manually or via webhook/scheduled agent."""
    game = game.lower()
    # Parse numbers from '11, 18, 22, 30, 32' or '11 - 18 - 22 - 30 - 32'
    nums = [int(x.strip()) for x in re.split(r"[\s,\-]+", numbers_str.strip()) if x.strip()]
    if len(nums) == 6 and game in ['baloto', 'revancha'] and superball is None:
        superball = nums.pop()
    
    if len(nums) != 5:
        raise ValueError(f"Se esperaban 5 números principales, se obtuvieron: {nums}")

    date_iso = parse_spanish_date(date_str) or date_str
    success = insert_draw(game, date_iso, nums, superball, draw_num)
    if success:
        log_sync(game, "INGEST_SUCCESS", 1, f"Sorteo {date_iso} ingresado con éxito.")
    return success
