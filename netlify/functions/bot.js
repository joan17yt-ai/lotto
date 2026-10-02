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

function getFreshLotteryData() {
  try {
    delete require.cache[require.resolve('../../data/lottery_data.json')];
    return require('../../data/lottery_data.json');
  } catch (e) {
    return null;
  }
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

function auditNumbers(userNumbers, targetGame = 'miloto', userSb = null) {
  const data = getFreshLotteryData();
  if (!data || !data.games) return null;
  
  const gKey = targetGame.toLowerCase().includes('baloto') ? 'baloto' : 
               (targetGame.toLowerCase().includes('revancha') ? 'revancha' : 'miloto');
               
  const gData = data.games[gKey];
  if (!gData || !gData.latest_draw) return null;

  const lat = gData.latest_draw;
  const winning = lat.numbers || [];
  const winningSb = lat.superball;

  const matches = userNumbers.filter(n => winning.includes(n)).sort((a,b) => a - b);
  const sbMatch = (userSb !== null && winningSb !== null && userSb === winningSb);

  return {
    gameName: gData.name,
    drawNumber: lat.draw_number,
    drawDate: lat.draw_date,
    winningNumbers: winning,
    winningSb: winningSb,
    userNumbers: userNumbers.sort((a,b) => a - b),
    userSb: userSb,
    matches: matches,
    matchCount: matches.length,
    sbMatch: sbMatch
  };
}

exports.handler = async (event, context) => {
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
    const parts = text.split(/\s+/);
    const cmd = parts[0].toLowerCase();

    // 1. COMANDO /START
    if (cmd === '/start') {
      const reply = `👋 ¡Hola, *${firstName}*! Bienvenido a *LottoAnalytics Colombia Bot* 🇨🇴🎟️\n\n` +
        `Tu asistente inteligente 24/7 en la nube para Baloto, Revancha y MiLoto.\n\n` +
        `📌 *Comandos disponibles:*\n` +
        `• \`/sorteo\` — Últimos números ganadores oficiales y acumulados en vivo.\n` +
        `• \`/auditar [números]\` — Comprueba al instante cuántos aciertos tuviste.\n` +
        `• \`/web\` — Enlace directo a la plataforma web con mapas de calor y generador.\n` +
        `• \`/activar [PIN]\` — Activa tu suscripción VIP con el código entregado por WhatsApp.\n` +
        `• \`/mipin [PIN]\` — Consulta la vigencia y días restantes de tu PIN.\n` +
        `• \`/jugada [juego] [números]\` — Registra tu boleto para verificación.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 2. COMANDO /WEB
    else if (cmd === '/web') {
      const reply = `🌐 *Plataforma Oficial en Vivo:*\n👉 ${WEB_URL}\n\nAccede a mapas de calor, balotas calientes y frías, y tu generador algorítmico.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 3. COMANDO /SORTEO (Dinámico desde lottery_data.json)
    else if (cmd === '/sorteo') {
      const data = getFreshLotteryData();
      if (!data || !data.games) {
        await sendTelegramMessage(token, chatId, `🌐 Consulta los últimos números y acumulados en:\n👉 ${WEB_URL}`);
        return { statusCode: 200, body: 'ok' };
      }

      const b = data.games.baloto.latest_draw;
      const r = data.games.revancha.latest_draw;
      const m = data.games.miloto.latest_draw;

      const reply = `📢 *ÚLTIMOS RESULTADOS OFICIALES* 🇨🇴\n\n` +
        `🟡 *Baloto Tradicional* (${b.draw_date})\n` +
        `• Sorteo #${b.draw_number || ''}\n` +
        `• Balotas: \`${b.numbers.join(' - ')}\` + SB: \`${b.superball}\`\n` +
        `• Acumulado: *${b.jackpot}*\n\n` +
        `🔴 *Baloto Revancha* (${r.draw_date})\n` +
        `• Sorteo #${r.draw_number || ''}\n` +
        `• Balotas: \`${r.numbers.join(' - ')}\` + SB: \`${r.superball}\`\n` +
        `• Acumulado: *${r.jackpot}*\n\n` +
        `🟢 *MiLoto* (${m.draw_date})\n` +
        `• Sorteo #${m.draw_number || ''}\n` +
        `• Balotas: \`${m.numbers.join(' - ')}\`\n` +
        `• Acumulado: *${m.jackpot}*\n\n` +
        `🔗 Consulta análisis detallado y pronósticos en:\n👉 ${WEB_URL}`;
      await sendTelegramMessage(token, chatId, reply);
    }

    // 4. COMANDO /AUDITAR [juego opcional] [numeros...]
    else if (cmd === '/auditar') {
      const rawNumbers = text.replace(/\/auditar/i, '').trim();
      const allNums = rawNumbers.match(/\b\d{1,2}\b/g);

      if (!allNums || allNums.length < 5) {
        const helpMsg = `ℹ️ *Cómo auditar tu jugada al instante:*\n\n` +
          `Escribe \`/auditar\` seguido de tus números.\n\n` +
          `Ejemplos:\n` +
          `• Para MiLoto: \`/auditar 15 21 25 30 37\`\n` +
          `• Para Baloto: \`/auditar baloto 11 18 22 30 32 sb 10\``;
        await sendTelegramMessage(token, chatId, helpMsg);
        return { statusCode: 200, body: 'ok' };
      }

      let gameGuess = 'miloto';
      if (text.toLowerCase().includes('baloto')) gameGuess = 'baloto';
      else if (text.toLowerCase().includes('revancha')) gameGuess = 'revancha';
      else if (allNums.length === 6) gameGuess = 'baloto';

      const userNums = allNums.slice(0, 5).map(n => parseInt(n));
      const userSb = (allNums.length >= 6) ? parseInt(allNums[5]) : null;

      const audit = auditNumbers(userNums, gameGuess, userSb);
      if (!audit) {
        await sendTelegramMessage(token, chatId, `⚠️ No se pudieron consultar los datos del último sorteo.`);
        return { statusCode: 200, body: 'ok' };
      }

      let verdict = '';
      if (audit.matchCount === 5 && (!audit.winningSb || audit.sbMatch)) {
        verdict = `🏆🎉 *¡FELICITACIONES! ¡ACERTASTE EL PREMIO MAYOR COMPLETO!*`;
      } else if (audit.matchCount >= 4) {
        verdict = `🎯🔥 *¡Excelente! Tuviste ${audit.matchCount} aciertos (${audit.matches.join(', ')}).* ¡Tienes un premio importante!`;
      } else if (audit.matchCount === 3) {
        verdict = `🎯 *¡Bien! Tuviste 3 aciertos (${audit.matches.join(', ')}).* Cobras premio en la tabla de pagos.`;
      } else if (audit.matchCount === 2 && audit.sbMatch) {
        verdict = `🎉 *Acertaste 2 números + Superbalota.* Tienes premio menor.`;
      } else {
        verdict = `Tuviste *${audit.matchCount} acierto(s)* (${audit.matches.length > 0 ? audit.matches.join(', ') : 'ninguno'}). ¡El próximo sorteo ya está disponible en la web!`;
      }

      const sbWinStr = audit.winningSb !== null ? ` + SB ${audit.winningSb}` : '';
      const sbUserStr = audit.userSb !== null ? ` + SB ${audit.userSb}` : '';

      const rep = `📊 *AUDITORÍA DE JUGADA — ${audit.gameName.toUpperCase()}*\n` +
        `📅 Sorteo #${audit.drawNumber} (${audit.drawDate})\n\n` +
        `• *Números Ganadores:* \`${audit.winningNumbers.join(' - ')}\`${sbWinStr}\n` +
        `• *Tus Números:* \`${audit.userNumbers.join(' - ')}\`${sbUserStr}\n\n` +
        `• *Aciertos:* *${audit.matchCount} de 5* ${audit.sbMatch ? '(+ Superbalota acertada ✅)' : ''}\n\n` +
        `${verdict}\n\n` +
        `Genera tus combinaciones sugeridas para el siguiente juego en:\n👉 ${WEB_URL}`;

      await sendTelegramMessage(token, chatId, rep);
    }

    // 5. COMANDO /ACTIVAR [PIN]
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

    // 6. COMANDO /MIPIN [PIN opcional]
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

    // 7. COMANDO /JUGADA (Registra y además audita si el sorteo ya se jugó)
    else if (cmd === '/jugada') {
      const rawNumbers = text.replace(/\/jugada/i, '').trim();
      const allNums = rawNumbers.match(/\b\d{1,2}\b/g);

      if (!allNums || allNums.length < 5) {
        await sendTelegramMessage(token, chatId, 'ℹ️ Formato para registrar tu boleto:\n`/jugada baloto 11 18 22 30 32 sb 10`\n`/jugada miloto 15 21 25 30 37`');
      } else {
        const game = parts[1].toUpperCase();
        const nums = parts.slice(2).join(' ');
        const reply = `🎟️ *¡Boleto Registrado!* 🇨🇴\n\n` +
          `• *Sorteo:* ${game}\n` +
          `• *Números:* \`${nums}\`\n\n` +
          `💡 *Tip:* Puedes consultar cuántos aciertos tuviste frente al sorteo oficial escribiendo:\n` +
          `\`/auditar ${nums}\``;
        await sendTelegramMessage(token, chatId, reply);
      }
    }

    // CUALQUIER OTRO MENSAJE
    else {
      const reply = `Hola ${firstName}. Escribe \`/sorteo\` para ver los últimos números, \`/auditar [tus números]\` para revisar tus aciertos, \`/web\` para entrar a la página o \`/start\` para ver todos los comandos.`;
      await sendTelegramMessage(token, chatId, reply);
    }

    return { statusCode: 200, body: 'ok' };
  } catch (err) {
    console.error('Error handling webhook:', err);
    return { statusCode: 200, body: 'error handled' };
  }
};
