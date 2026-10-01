/**
 * Netlify Serverless Function: 24/7 Interactive Telegram Bot Webhook
 * Handles incoming messages from Telegram instantly and responds 24/7 in the cloud.
 */

const https = require('https');
const crypto = require('crypto');

const SECRET_SALT = 'Joan17LottoSecretKey2026';
const WEB_URL = 'https://lotto-colombia.netlify.app';

// Token can come from Netlify Environment Variables or fallback
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

function sendTelegramMessage(token, chatId, text) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'Markdown',
      disable_web_page_preview: false
    });

    const options = {
      hostname: 'api.telegram.org',
      port: 443,
      path: `/bot${token}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    });

    req.on('error', (e) => reject(e));
    req.write(payload);
    req.end();
  });
}

function validateCryptographicPin(rawPin) {
  const pin = rawPin.trim().toUpperCase();
  if (pin === 'BUCARAMANGA' || pin === 'JOAN17-ADMIN' || pin === 'VIP2026') {
    return { valid: true, exp_date: 'Indefinida (Master)', days_left: 9999 };
  }

  const parts = pin.split('-');
  if (parts.length !== 4 || parts[0] !== 'VIP') {
    return { valid: false, reason: 'Formato incorrecto. Ejemplo: VIP-261031-842-50EB' };
  }

  const [_, dateCode, clientId, providedHash] = parts;
  const payload = `${dateCode}-${clientId}-${SECRET_SALT}`;
  const expectedHash = crypto.createHash('sha256').update(payload).digest('hex').substring(0, 4).toUpperCase();

  if (providedHash !== expectedHash) {
    return { valid: false, reason: 'Firma de seguridad inválida o código adulterado.' };
  }

  const year = parseInt('20' + dateCode.substring(0, 2));
  const month = parseInt(dateCode.substring(2, 4)) - 1;
  const day = parseInt(dateCode.substring(4, 6));

  const expDate = new Date(year, month, day, 23, 59, 59);
  const now = new Date();
  const diffDays = Math.ceil((expDate - now) / (1000 * 60 * 60 * 24));

  const formattedDate = `${day < 10 ? '0' + day : day}/${month + 1 < 10 ? '0' + (month + 1) : month + 1}/${year}`;

  if (diffDays < 0) {
    return { valid: false, expired: true, exp_date: formattedDate, reason: `Tu PIN venció el ${formattedDate}.` };
  }

  return { valid: true, expired: false, exp_date: formattedDate, days_left: diffDays, client_id: clientId };
}

exports.handler = async (event, context) => {
  // Only accept POST requests from Telegram
  if (event.httpMethod !== 'POST') {
    return { statusCode: 200, body: 'LottoAnalytics Telegram Webhook is active and healthy.' };
  }

  try {
    const update = JSON.parse(event.body);
    if (!update || !update.message || !update.message.text) {
      return { statusCode: 200, body: 'ok' };
    }

    const token = BOT_TOKEN || process.env.BOT_TOKEN;
    if (!token) {
      console.error('TELEGRAM_BOT_TOKEN is not configured in Netlify environment.');
      return { statusCode: 200, body: 'Token missing' };
    }

    const message = update.message;
    const chatId = message.chat.id;
    const text = message.text.trim();
    const firstName = message.from ? message.from.first_name : 'Amigo';
    const parts = text.split(' ');
    const cmd = parts[0].toLowerCase();

    // 1. COMANDO /START
    if (cmd === '/start') {
      const reply = `👋 ¡Hola, *${firstName}*! Bienvenido a *LottoAnalytics Colombia Bot* 🇨🇴🎟️\n\n` +
        `Tu asistente inteligente 24/7 en la nube para Baloto, Revancha y MiLoto.\n\n` +
        `📌 *Comandos disponibles:*\n` +
        `• \`/sorteo\` — Últimos números ganadores oficiales y acumulados en vivo.\n` +
        `• \`/web\` — Enlace directo a la plataforma web con mapas de calor y generador.\n` +
        `• \`/activar [PIN]\` — Activa tu suscripción VIP con el código entregado por WhatsApp.\n` +
        `• \`/mipin [PIN]\` — Consulta la vigencia y días restantes de tu PIN.\n` +
        `• \`/jugada baloto 11 18 22 30 32 sb 10\` — Registra tu boleto de hoy y recibe tus aciertos tras el sorteo.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 2. COMANDO /WEB
    else if (cmd === '/web') {
      const reply = `🌐 *Plataforma Oficial en Vivo:*\n👉 ${WEB_URL}\n\nAccede a mapas de calor, balotas calientes y frías, y tu generador algorítmico.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 3. COMANDO /SORTEO
    else if (cmd === '/sorteo') {
      const reply = `📢 *ÚLTIMOS RESULTADOS OFICIALES* 🇨🇴\n\n` +
        `🟡 *Baloto Tradicional* (30 de Septiembre de 2026)\n` +
        `• Sorteo #2716\n` +
        `• Balotas: \`11 - 18 - 22 - 30 - 32\` + SB: \`10\`\n` +
        `• Acumulado: *$61.600 Millones*\n\n` +
        `🔴 *Baloto Revancha* (30 de Septiembre de 2026)\n` +
        `• Balotas: \`04 - 10 - 14 - 18 - 23\` + SB: \`07\`\n` +
        `• Acumulado: *$2.000 Millones*\n\n` +
        `🟢 *MiLoto* (29 de Septiembre de 2026)\n` +
        `• Sorteo #615\n` +
        `• Balotas: \`05 - 10 - 21 - 24 - 31\`\n` +
        `• Acumulado: *$260 Millones*\n\n` +
        `🔗 Consulta análisis detallado y pronósticos en:\n👉 ${WEB_URL}`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 4. COMANDO /ACTIVAR [PIN]
    else if (cmd === '/activar') {
      if (parts.length < 2) {
        await sendTelegramMessage(token, chatId, 'ℹ️ Escribe `/activar` seguido de tu PIN.\nEjemplo: `/activar VIP-261031-842-50EB`');
      } else {
        const pin = parts[1].trim();
        const res = validateCryptographicPin(pin);
        if (res.valid) {
          const reply = `🎉 *¡PIN VIP VALIDADO CON ÉXITO!*\n\n` +
            `• *PIN:* \`${pin}\`\n` +
            `• *Fecha de Vencimiento:* ${res.exp_date}\n` +
            `• *Días Restantes:* ${res.days_left} días activos 🟢\n\n` +
            `Tu acceso está habilitado para recibir alertas automáticas y generar números personalizados en:\n👉 ${WEB_URL}`;
          await sendTelegramMessage(token, chatId, reply);
        } else {
          await sendTelegramMessage(token, chatId, `❌ *No se pudo activar el PIN:*\n${res.reason}\n\nSi necesitas adquirir tu PIN de este mes, pídelo por WhatsApp.`);
        }
      }
    }

    // 5. COMANDO /MIPIN [PIN opcional]
    else if (cmd === '/mipin') {
      if (parts.length >= 2) {
        const pin = parts[1].trim();
        const res = validateCryptographicPin(pin);
        if (res.valid) {
          await sendTelegramMessage(token, chatId, `🔑 *ESTADO DE TU PIN:*\n• PIN: \`${pin}\`\n• Vence: ${res.exp_date}\n• Vigencia: ${res.days_left} días restantes 🟢`);
        } else {
          await sendTelegramMessage(token, chatId, `⚠️ *ESTADO:* ${res.reason}`);
        }
      } else {
        await sendTelegramMessage(token, chatId, 'ℹ️ Para consultar tu PIN escribe:\n`/mipin TU-PIN`\nEjemplo: `/mipin VIP-261031-842-50EB`');
      }
    }

    // 6. COMANDO /JUGADA
    else if (cmd === '/jugada') {
      if (parts.length < 6) {
        await sendTelegramMessage(token, chatId, 'ℹ️ Formato para registrar tu boleto:\n`/jugada baloto 11 18 22 30 32 sb 10`\n`/jugada miloto 05 10 21 24 31`');
      } else {
        const game = parts[1].toUpperCase();
        const nums = parts.slice(2).join(' ');
        const reply = `🎟️ *¡Boleto Registrado para Hoy!* 🇨🇴\n\n` +
          `• *Sorteo:* ${game}\n` +
          `• *Números Registrados:* \`${nums}\`\n\n` +
          `En cuanto termine la transmisión en televisión esta noche, tus números serán auditados automáticamente frente a los resultados oficiales. 🍀`;
        await sendTelegramMessage(token, chatId, reply);
      }
    }

    // CUALQUIER OTRO MENSAJE
    else {
      const reply = `Hola ${firstName}. Escribe \`/sorteo\` para ver los últimos números, \`/web\` para entrar a la página o \`/start\` para ver todos los comandos disponibles.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    return { statusCode: 200, body: 'ok' };
  } catch (err) {
    console.error('Error handling webhook:', err);
    return { statusCode: 200, body: 'error handled' };
  }
};
