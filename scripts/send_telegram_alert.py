"""
Automated Cloud Telegram Alert Sender for GitHub Actions.
Sends:
  1. 6:30 PM Draw-day reminders with website link.
  2. Post-draw results notification with winning numbers and jackpots.
  3. Huge jackpot alerts.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
DATA_JSON_PATH = os.path.join(root_dir, 'data', 'lottery_data.json')
WEB_URL = os.environ.get('LOTTO_WEB_URL', 'https://lotto-colombia.netlify.app')

def load_data() -> dict:
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando data: {e}")
    return {}

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id or token == 'YOUR_TOKEN':
        print("Aviso: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados en GitHub Secrets.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            if res.get("ok"):
                print("Mensaje de Telegram enviado con éxito en la nube.")
                return True
            else:
                print(f"Error de Telegram: {res}")
                return False
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")
        return False

def alert_reminder_630pm(token: str, chat_id: str):
    data = load_data()
    today = datetime.now().date()
    weekday = today.weekday() # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat

    games_today = []
    if weekday in [0, 2, 5]: # Lun, Mié, Sáb
        games_today.append("Baloto y Revancha")
    if weekday in [0, 1, 3, 4]: # Lun, Mar, Jue, Vie
        games_today.append("MiLoto")

    if not games_today:
        print("Hoy no es día de sorteo de Baloto ni MiLoto. No se envía recordatorio.")
        return

    baloto_jp = data.get('games', {}).get('baloto', {}).get('latest_draw', {}).get('jackpot', '$61.600 Millones')
    miloto_jp = data.get('games', {}).get('miloto', {}).get('latest_draw', {}).get('jackpot', '$260 Millones')

    msg = (
        f"🔔 *¡RECORDATORIO DE SORTEO HOY!* 🇨🇴\n\n"
        f"Esta noche juegan: *{' y '.join(games_today)}*.\n"
        f"💰 *Acumulado Baloto:* {baloto_jp}\n"
        f"💰 *Acumulado MiLoto:* {miloto_jp}\n\n"
        f"👉 *No olvides ingresar a la página y buscar tus números optimizados para hoy:*\n"
        f"🔗 {WEB_URL}\n\n"
        f"🍀 *Recuerda realizar tu jugada antes del cierre de ventas esta noche.*"
    )
    send_telegram_message(token, chat_id, msg)

def alert_post_draw(token: str, chat_id: str):
    data = load_data()
    if not data:
        return

    b = data.get('games', {}).get('baloto', {}).get('latest_draw', {})
    r = data.get('games', {}).get('revancha', {}).get('latest_draw', {})
    m = data.get('games', {}).get('miloto', {}).get('latest_draw', {})

    msg = (
        f"📢 *NUEVOS RESULTADOS OFICIALES ACTUALIZADOS* 🇨🇴\n\n"
        f"🟡 *Baloto Tradicional* ({b.get('draw_date')})\n"
        f"• Sorteo #{b.get('draw_number', '')}\n"
        f"• Balotas: `{b.get('numbers')}` + SB: `{b.get('superball')}`\n"
        f"• Acumulado: *{b.get('jackpot', '')}*\n\n"
        f"🔴 *Baloto Revancha* ({r.get('draw_date')})\n"
        f"• Balotas: `{r.get('numbers')}` + SB: `{r.get('superball')}`\n"
        f"• Acumulado: *{r.get('jackpot', '')}*\n\n"
        f"🟢 *MiLoto* ({m.get('draw_date')})\n"
        f"• Sorteo #{m.get('draw_number', '')}\n"
        f"• Balotas: `{m.get('numbers')}`\n"
        f"• Acumulado: *{m.get('jackpot', '')}*\n\n"
        f"Consulta el desglose de atrasos y los nuevos pronósticos aquí:\n"
        f"👉 {WEB_URL}"
    )
    send_telegram_message(token, chat_id, msg)

def main():
    parser = argparse.ArgumentParser(description="Envío de alertas de Telegram en la nube")
    parser.add_argument("--type", choices=["reminder_630pm", "post_draw"], required=True)
    args = parser.parse_args()

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no encontrados en el entorno. Omitiendo envío.")
        return

    if args.type == "reminder_630pm":
        alert_reminder_630pm(token, chat_id)
    elif args.type == "post_draw":
        alert_post_draw(token, chat_id)

if __name__ == '__main__':
    main()
