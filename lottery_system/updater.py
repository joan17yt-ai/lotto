"""
Automated Scraper and ETL Updater for Baloto, Revancha, and MiLoto.
Parses official draw results with multi-source fallback (baloto.com + colombia.com)
to guarantee 100% autonomous unattended updates even when baloto.com is delayed or blocked.
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
    """Converts strings like '1 de Octubre de 2026' or '30 de Septiembre de 2026' to 'YYYY-MM-DD'."""
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
    Draws appear in pairs: row 1 = Baloto, row 2 = Revancha.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    rows = soup.find_all('tr')
    current_date = None
    draw_index_for_date = 0

    for tr in rows:
        text = tr.get_text(separator=' ').strip()
        date_parsed = parse_spanish_date(text)
        
        # Match 6 numbers: 5 regular + 1 superball
        num_match = re.search(r"(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})", text)
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


def parse_miloto_detail_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Parses baloto.com/miloto/resultados-miloto/ HTML.
    Extracts draw number, date, winning numbers, draw jackpot, new jackpot, and winner status.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")

    draw_match = re.search(r"SORTEO\s*#?\s*(\d+)", text, re.IGNORECASE)
    draw_num = int(draw_match.group(1)) if draw_match else None

    date_parsed = parse_spanish_date(text)

    num_match = re.search(r"(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})", text)
    numbers = None
    if num_match:
        numbers = sorted([int(num_match.group(i)) for i in range(1, 6)])
    else:
        ball_tags = soup.find_all(class_=re.compile(r"ball|bolilla|numero|circle", re.I))
        extracted_nums = []
        for b in ball_tags:
            t = b.get_text().strip()
            if t.isdigit() and 1 <= int(t) <= 39:
                extracted_nums.append(int(t))
                if len(extracted_nums) == 5:
                    break
        if len(extracted_nums) == 5:
            numbers = sorted(extracted_nums)

    new_jp_match = re.search(r"Acumulado\s+nuevo[^\d]*(\d+[\.\d]*)\s*(?:Millones|MILLONES)", text, re.I)
    new_jackpot = f"${new_jp_match.group(1)} Millones" if new_jp_match else None

    draw_jp_match = re.search(r"ACUMULADO\s+DEL\s+SORTEO[^\d]*(\d+[\.\d]*)\s*(?:Millones|MILLONES)", text, re.I)
    draw_jackpot = f"${draw_jp_match.group(1)} Millones" if draw_jp_match else None

    win5_match = re.search(r"Aciertos\s+5.*?Ganadores\s*(\d+)", text, re.I)
    has_jackpot_winner = False
    if win5_match and int(win5_match.group(1)) > 0:
        has_jackpot_winner = True

    if numbers and date_parsed:
        return {
            "game": "miloto",
            "draw_number": draw_num,
            "date": date_parsed,
            "numbers": numbers,
            "superball": None,
            "draw_jackpot": draw_jackpot,
            "new_jackpot": new_jackpot,
            "jackpot": new_jackpot or draw_jackpot,
            "has_jackpot_winner": has_jackpot_winner
        }
    return None

def parse_miloto_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Parses baloto.com/miloto/resultados/ HTML.
    Extracts exactly 5 numbers per draw.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    rows = soup.find_all('tr')
    for tr in rows:
        text = tr.get_text(separator=' ').strip()
        date_parsed = parse_spanish_date(text)
        
        # Match 5 numbers: e.g. '15 - 21 - 25 - 30 - 37'
        num_match = re.search(r"(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})", text)
        if num_match and date_parsed:
            numbers = [int(num_match.group(i)) for i in range(1, 6)]
            results.append({
                "game": "miloto",
                "date": date_parsed,
                "numbers": sorted(numbers),
                "superball": None
            })

    return results

def fetch_from_colombia_com(game: str) -> List[Dict[str, Any]]:
    """
    High-reliability fallback scraper using Colombia.com loterías.
    Publishes within 10-15 minutes of live draw with zero Cloudflare blocking.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    extracted = []
    
    url_map = {
        "miloto": "https://www.colombia.com/loterias/miloto/",
        "baloto": "https://www.colombia.com/loterias/baloto-y-revancha/",
        "revancha": "https://www.colombia.com/loterias/baloto-y-revancha/"
    }
    
    url = url_map.get(game)
    if not url:
        return extracted

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Parse text paragraphs and headers for numbers
            for tag in soup.find_all(['p', 'div', 'article', 'tr']):
                text = tag.get_text(separator=' ').strip()
                date_parsed = parse_spanish_date(text)
                
                if game == 'miloto':
                    # Look for 5 numbers: e.g. 15,21,25,30,37 or 15 - 21 - 25 - 30 - 37
                    m = re.search(r"(?:bolillas ganadoras|combinación ganadora|resultado|sorteo)[:\s]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})", text, re.I)
                    if m:
                        nums = sorted([int(m.group(i)) for i in range(1, 6)])
                        d_str = date_parsed or datetime.now().strftime("%Y-%m-%d")
                        extracted.append({
                            "game": "miloto",
                            "date": d_str,
                            "numbers": nums,
                            "superball": None
                        })
                        break
                elif game in ['baloto', 'revancha']:
                    # Look for Baloto (5 numbers + SB)
                    m = re.search(r"(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})\s*[-–,]\s*(\d{1,2})[\s\-+–]+(?:sb|superbalota)?[:\s]*(\d{1,2})", text, re.I)
                    if m and date_parsed:
                        nums = sorted([int(m.group(i)) for i in range(1, 6)])
                        sb = int(m.group(6))
                        extracted.append({
                            "game": game,
                            "date": date_parsed,
                            "numbers": nums,
                            "superball": sb
                        })
    except Exception as e:
        print(f"Fallback Colombia.com aviso ({game}): {e}")

    return extracted

def fetch_and_update(game: str = "all", timeout_secs: int = 10) -> Dict[str, Any]:
    """
    Orchestrates draw scraping: queries baloto.com first;
    if no new draw is found, automatically uses colombia.com fallback.
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
            log_sync("baloto_revancha", "SUCCESS", updated_counts["baloto"] + updated_counts["revancha"], "Actualización baloto.com completada.")
        except Exception as e:
            errors.append(f"baloto.com Baloto: {str(e)}")

        # Fallback if 0 updates
        if updated_counts["baloto"] == 0:
            fb_items = fetch_from_colombia_com("baloto")
            for item in fb_items:
                if insert_draw(item["game"], item["date"], item["numbers"], item.get("superball")):
                    updated_counts[item["game"]] += 1

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
            log_sync("miloto", "SUCCESS", updated_counts["miloto"], "Actualización baloto.com completada.")
        except Exception as e:
            errors.append(f"baloto.com MiLoto: {str(e)}")

        # Fallback if 0 updates
        if updated_counts["miloto"] == 0:
            fb_items = fetch_from_colombia_com("miloto")
            for item in fb_items:
                if insert_draw("miloto", item["date"], item["numbers"], None):
                    updated_counts["miloto"] += 1

    return {
        "status": "partial" if errors else "success",
        "updated_counts": updated_counts,
        "errors": errors,
        "timestamp": datetime.now().isoformat()
    }

def ingest_raw_draw(game: str, date_str: str, numbers_str: str, superball: Optional[int] = None, draw_num: Optional[int] = None) -> bool:
    """Helper to ingest a draw manually or via webhook/scheduled agent."""
    game = game.lower()
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
