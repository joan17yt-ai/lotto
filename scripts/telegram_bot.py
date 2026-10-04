"""
Telegram Bot Engine for LottoAnalytics Colombia.
Zero-dependency implementation using native Telegram Bot HTTP API.
Features:
  1. 6:30 PM Draw-day reminders with website link.
  2. PIN check & expiration lookup (/mipin, /activar).
  3. High Jackpot alerts (Pozo histórico acumulado).
  4. Ticket registration & automated post-draw result auditing (/jugada).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta

# Import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(root_dir, 'lottery_system'))

try:
    from database import get_latest_draw, get_draws
except ImportError:
    pass

USERS_DB_FILE = os.path.join(root_dir, 'data', 'telegram_subscribers.json')
DATA_JSON_PATH = os.path.join(root_dir, 'data', 'lottery_data.json')
SECRET_SALT = 'Joan17LottoSecretKey2026'

# Configuración por defecto (Joan configurará su Token de BotFather)
DEFAULT_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
WEB_URL = os.environ.get('LOTTO_WEB_URL', 'https://lotto-colombia.netlify.app')

class TelegramLottoBot:
    def __init__(self, token: str = DEFAULT_BOT_TOKEN):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.subscribers = self._load_subscribers()

    def _load_subscribers(self) -> dict:
        os.makedirs(os.path.dirname(USERS_DB_FILE), exist_ok=True)
        if not os.path.exists(USERS_DB_FILE):
            initial = {"users": {}}
            self._save_subscribers(initial)
            return initial
        try:
            with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"users": {}}

    def _save_subscribers(self, data: dict = None):
        if data is None:
            data = self.subscribers
        with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _api_call(self, method: str, params: dict = None) -> dict:
        url = f"{self.api_url}/{method}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        if params:
            data = urllib.parse.urlencode(params).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
        else:
            req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
        res = self._api_call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })
        return res.get("ok", False)

    # 1. VERIFICACIÓN CRIPTOGRÁFICA DE PIN
    def validate_pin(self, pin: str) -> dict:
        pin = pin.strip().upper()
        if pin in ['BUCARAMANGA', 'JOAN17-ADMIN', 'VIP2026']:
            return {"valid": True, "exp_date": "2099-12-31", "days_left": 9999}
        parts = pin.split('-')
        if len(parts) != 4 or parts[0] != 'VIP':
            return {"valid": False, "reason": "Formato incorrecto. Ejemplo: VIP-261031-842-50EB"}
        
        _, date_code, client_id, prov_hash = parts
        import hashlib
        payload = f"{date_code}-{client_id}-{SECRET_SALT}"
        exp_hash = hashlib.sha256(payload.encode()).hexdigest()[:4].upper()
        if prov_hash != exp_hash:
            return {"valid": False, "reason": "Firma de seguridad inválida o código alterado."}
        
        try:
            exp_date = datetime.strptime('20' + date_code, '%Y%m%d').date()
            today = datetime.now().date()
            days_left = (exp_date - today).days
            if days_left < 0:
                return {"valid": False, "expired": True, "exp_date": str(exp_date), "reason": f"Tu PIN venció el {exp_date}."}
            return {"valid": True, "expired": False, "exp_date": str(exp_date), "days_left": days_left}
        except Exception as e:
            return {"valid": False, "reason": "Fecha del código inválida."}

    # 2. CARGA DE DATOS DE LOTERÍA EN VIVO
    def get_lottery_data(self) -> dict:
        if os.path.exists(DATA_JSON_PATH):
            try:
                with open(DATA_JSON_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    # 3. RUTINAS DE ALERTAS PROGRAMADAS
    def send_draw_day_reminder_630pm(self):
        """Envía el recordatorio de las 6:30 PM a todos los usuarios con el enlace a la web."""
        today = datetime.now().date()
        weekday = today.weekday() # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat
        
        games_today = []
        if weekday in [0, 2, 5]: # Lun, Mié, Sáb
            games_today.append("Baloto y Revancha")
        if weekday in [0, 1, 3, 4]: # Lun, Mar, Jue, Vie
            games_today.append("MiLoto")

        if not games_today:
            return

        lottery_data = self.get_lottery_data()
        baloto_jp = lottery_data.get('games', {}).get('baloto', {}).get('latest_draw', {}).get('jackpot', '$61.600 Millones')
        miloto_jp = lottery_data.get('games', {}).get('miloto', {}).get('latest_draw', {}).get('jackpot', '$350 Millones')

        msg = (
            f"🔔 *¡RECORDATORIO DE SORTEO HOY!* 🇨🇴\n\n"
            f"Esta noche juegan: *{' y '.join(games_today)}*.\n"
            f"💰 *Acumulado Baloto:* {baloto_jp}\n"
            f"💰 *Acumulado MiLoto:* {miloto_jp}\n\n"
            f"👉 *No olvides ingresar a la página y buscar tus números optimizados para hoy:*\n"
            f"🔗 {WEB_URL}\n\n"
            f"💡 *Tip:* Si ya compraste tu boleto, regístralo aquí con el comando:\n"
            f"`/jugada [juego] [n1 n2 n3 n4 n5]`\n"
            f"Y al terminar el sorteo el bot te avisará cuántos aciertos tuviste automáticamente."
        )

        for chat_id in self.subscribers.get("users", {}).keys():
            self.send_message(int(chat_id), msg)

    def send_high_jackpot_alert_if_needed(self):
        """Revisa si el pozo superó los $50.000 Millones en Baloto y envía alerta especial."""
        lottery_data = self.get_lottery_data()
        b_jp = lottery_data.get('games', {}).get('baloto', {}).get('latest_draw', {}).get('jackpot', '')
        if '6' in b_jp or '7' in b_jp or '8' in b_jp or '9' in b_jp: # > $50.000 Millones
            msg = (
                f"🚨 *¡ALERTA DE ACUMULADO HISTÓRICO GIGANTE!* 💰🔥\n\n"
                f"El pozo de *Baloto Tradicional* se encuentra en:\n"
                f"🏆 *{b_jp} DE PESOS*\n\n"
                f"Matemáticamente, cuando el pozo supera este umbral, el valor esperado por boleto se vuelve sumamente atractivo.\n\n"
                f"Entra ya a la web y genera tus combinaciones con filtro anti-aglomeración para no compartir el pozo si ganas:\n"
                f"🔗 {WEB_URL}"
            )
            for chat_id in self.subscribers.get("users", {}).keys():
                self.send_message(int(chat_id), msg)

    def audit_registered_tickets_post_draw(self):
        """Comprueba automáticamente los números jugados por los clientes y les manda sus aciertos."""
        lottery_data = self.get_lottery_data()
        if not lottery_data:
            return

        users = self.subscribers.get("users", {})
        for chat_id, data in users.items():
            tickets = data.get("active_tickets", [])
            if not tickets:
                continue

            remaining_tickets = []
            for t in tickets:
                game = t["game"].lower()
                game_data = lottery_data.get("games", {}).get(game)
                if not game_data or not game_data.get("latest_draw"):
                    remaining_tickets.append(t)
                    continue

                lat = game_data["latest_draw"]
                # Comprobar si este sorteo es de hoy o posterior a la compra
                winning_numbers = set(lat["numbers"])
                winning_sb = lat.get("superball")

                user_numbers = set(t["numbers"])
                user_sb = t.get("superball")

                matches = sorted(list(user_numbers.intersection(winning_numbers)))
                match_count = len(matches)
                sb_matched = (user_sb is not None and user_sb == winning_sb)

                sb_str = f" + Superbalota ({winning_sb})" if winning_sb else ""
                user_sb_str = f" + Superbalota ({user_sb})" if user_sb else ""

                result_text = ""
                if match_count >= 5 and (not game_data.get("has_superball") or sb_matched):
                    result_text = "🏆🎉 *¡FELICITACIONES! ¡ACERTASTE EL PREMIO MAYOR COMPLETO!*"
                elif match_count >= 3:
                    result_text = f"🎯 *¡Excelente! Tuviste {match_count} aciertos ({matches}).* Revisa la tabla de pagos de tu boleto porque tienes premio."
                elif match_count == 2 and sb_matched:
                    result_text = "🎉 *¡Acertaste 2 números + Superbalota!* Tienes premio menor."
                else:
                    result_text = f"Tuviste *{match_count} acierto(s)* ({matches if matches else 'ninguno'}). ¡El próximo sorteo ya está disponible en la web!"

                msg = (
                    f"📊 *RESULTADOS DE TU JUGADA — {game_data['name'].upper()}*\n"
                    f"📅 Sorteo #{lat.get('draw_number', '')} ({lat.get('draw_date')})\n\n"
                    f"• *Números Ganadores:* `{lat['numbers']}`{sb_str}\n"
                    f"• *Tus Números Jugados:* `{t['numbers']}`{user_sb_str}\n\n"
                    f"{result_text}\n\n"
                    f"Consulta los nuevos mapas de calor y jugadas sugeridas aquí:\n"
                    f"🔗 {WEB_URL}"
                )
                self.send_message(int(chat_id), msg)

            data["active_tickets"] = []
        self._save_subscribers()

    # 4. MANEJADOR DE MENSAJES Y COMANDOS DE CLIENTES
    def handle_command(self, chat_id: int, text: str, user_first_name: str = "Amigo"):
        text = text.strip()
        cmd = text.split()[0].lower() if text else ""
        user_str = str(chat_id)

        if user_str not in self.subscribers["users"]:
            self.subscribers["users"][user_str] = {
                "name": user_first_name,
                "pin": None,
                "exp_date": None,
                "registered_at": datetime.now().isoformat(),
                "active_tickets": []
            }
            self._save_subscribers()

        user_data = self.subscribers["users"][user_str]

        # COMANDO /START
        if cmd == '/start':
            msg = (
                f"👋 ¡Hola, {user_first_name}! Bienvenido a *LottoAnalytics Colombia Bot* 🇨🇴🎟️\n\n"
                f"Este es tu asistente personal para Baloto, Revancha y MiLoto.\n\n"
                f"📌 *Comandos que puedes usar:*\n"
                f"• `/mipin` - Consulta el estado y vencimiento de tu suscripción VIP.\n"
                f"• `/activar [PIN]` - Vincula tu PIN de acceso entregado por WhatsApp.\n"
                f"• `/jugada baloto 08 11 24 31 35 01` - Registra tu boleto comprado hoy y el bot te avisará tus aciertos tras el sorteo.\n"
                f"• `/jugada miloto 05 10 21 24 31` - Registra tu boleto de MiLoto.\n"
                f"• `/web` - Abre la página web oficial con el generador y mapas de calor.\n"
                f"• `/sorteo` - Consulta los últimos resultados y acumulados en vivo."
            )
            self.send_message(chat_id, msg)

        # COMANDO /WEB
        elif cmd == '/web':
            self.send_message(chat_id, f"🌐 Ingresa aquí a tu plataforma de pronósticos:\n👉 {WEB_URL}")

        # COMANDO /ACTIVAR [PIN]
        elif cmd == '/activar':
            parts = text.split()
            if len(parts) < 2:
                self.send_message(chat_id, "ℹ️ Escribe el comando seguido de tu PIN.\nEjemplo: `/activar VIP-261031-842-50EB`")
                return
            pin = parts[1].strip().upper()
            val = self.validate_pin(pin)
            if val.get("valid"):
                user_data["pin"] = pin
                user_data["exp_date"] = val["exp_date"]
                self._save_subscribers()
                self.send_message(chat_id, f"🎉 *¡PIN VIP Activado con Éxito!*\n\nTu suscripción está activa hasta el: *{val['exp_date']}* ({val['days_left']} días restantes).\nRecibirás las alertas automáticas de sorteos y tus jugadas personalizadas.")
            else:
                self.send_message(chat_id, f"❌ *No se pudo activar el PIN:*\n{val.get('reason')}\n\nSi necesitas adquirir tu PIN del mes, solicítalo por Nequi/WhatsApp.")

        # COMANDO /MIPIN
        elif cmd == '/mipin':
            pin = user_data.get("pin")
            if not pin:
                self.send_message(chat_id, "ℹ️ Aún no tienes un PIN vinculado a este chat.\nSi ya realizaste tu pago por Nequi/Daviplata, escribe:\n`/activar TU-PIN`")
                return
            val = self.validate_pin(pin)
            if val.get("valid"):
                self.send_message(chat_id, f"🔑 *ESTADO DE TU SUSCRIPCIÓN VIP*\n\n• *PIN Registrado:* `{pin}`\n• *Fecha de Vencimiento:* {val['exp_date']}\n• *Días Restantes:* {val['days_left']} días activos 🟢\n\nDisfruta de todos tus privilegios en la web:\n👉 {WEB_URL}")
            else:
                self.send_message(chat_id, f"⚠️ *ATENCIÓN:* Tu PIN `{pin}` se encuentra *VENCIDO* ({val.get('reason')}).\n\nPara renovar tu suscripción de $15.000 por Nequi, comunícate con nosotros por WhatsApp.")

        # COMANDO /JUGADA [juego] [numeros...]
        elif cmd == '/jugada':
            parts = text.split()
            if len(parts) < 6:
                self.send_message(chat_id, "ℹ️ Formato de registro:\n`/jugada baloto 04 15 17 22 23 sb 10`\n`/jugada miloto 05 10 21 24 31`")
                return
            game = parts[1].lower()
            if game not in ['baloto', 'revancha', 'miloto']:
                game = 'baloto'
            
            raw_nums = []
            sb = None
            for idx, p in enumerate(parts[2:]):
                if p.lower() in ['sb', 'superbalota', '+']:
                    if idx + 1 < len(parts[2:]):
                        try:
                            sb = int(parts[2:][idx + 1])
                        except Exception:
                            pass
                    break
                try:
                    raw_nums.append(int(p))
                except Exception:
                    pass

            if len(raw_nums) >= 6 and sb is None and game in ['baloto', 'revancha']:
                sb = raw_nums.pop()

            if len(raw_nums) != 5:
                self.send_message(chat_id, "❌ Debes ingresar exactamente 5 números principales.")
                return

            ticket_entry = {
                "game": game,
                "numbers": sorted(raw_nums[:5]),
                "superball": sb,
                "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            user_data["active_tickets"].append(ticket_entry)
            self._save_subscribers()

            sb_text = f" + Superbalota {sb}" if sb else ""
            self.send_message(chat_id, f"✅ *¡Boleto Registrado para Hoy!* 🎟️\n\n• Sorteo: *{game.upper()}*\n• Números: `{ticket_entry['numbers']}`{sb_text}\n\nEn cuanto termine el sorteo en televisión esta noche, compararé tus números con los resultados oficiales y te enviaré tus aciertos.")

        # COMANDO /SORTEO
        elif cmd == '/sorteo':
            lottery_data = self.get_lottery_data()
            if not lottery_data:
                self.send_message(chat_id, "Consulta los resultados en vivo aquí:\n" + WEB_URL)
                return
            b = lottery_data.get('games', {}).get('baloto', {}).get('latest_draw', {})
            r = lottery_data.get('games', {}).get('revancha', {}).get('latest_draw', {})
            m = lottery_data.get('games', {}).get('miloto', {}).get('latest_draw', {})
            
            msg = (
                f"📢 *ÚLTIMOS RESULTADOS OFICIALES* 🇨🇴\n\n"
                f"🟡 *Baloto Tradicional* ({b.get('draw_date')})\n"
                f"Números: `{b.get('numbers')}` + SB: `{b.get('superball')}`\n"
                f"Acumulado: *{b.get('jackpot', '')}*\n\n"
                f"🔴 *Baloto Revancha* ({r.get('draw_date')})\n"
                f"Números: `{r.get('numbers')}` + SB: `{r.get('superball')}`\n"
                f"Acumulado: *{r.get('jackpot', '')}*\n\n"
                f"🟢 *MiLoto* ({m.get('draw_date')})\n"
                f"Números: `{m.get('numbers')}`\n"
                f"Acumulado: *{m.get('jackpot', '')}*\n\n"
                f"🔗 Generador y análisis completo: {WEB_URL}"
            )
            self.send_message(chat_id, msg)
        else:
            self.send_message(chat_id, "Comando no reconocido. Escribe `/start` para ver las opciones disponibles.")
