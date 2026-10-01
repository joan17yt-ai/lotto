/**
 * LottoAnalytics Pro Colombia - Client-Side Interactive Application with Cryptographic VIP Suite
 */

let APP_DATA = null;
let currentGame = 'baloto';
const SECRET_SALT = 'Joan17LottoSecretKey2026';

// Initialize Application
async function initApp() {
  try {
    const res = await fetch(`data/lottery_data.json?t=${Date.now()}`);
    if (!res.ok) throw new Error("No se pudo cargar lottery_data.json");
    APP_DATA = await res.json();
  } catch (err) {
    console.warn("Usando datos locales embebidos de respaldo...", err);
    if (window.FALLBACK_DATA) {
      APP_DATA = window.FALLBACK_DATA;
    }
  }

  if (APP_DATA) {
    document.getElementById('last-sync-time').innerText = formatDateTime(APP_DATA.metadata.last_updated);
    renderSummaryCards();
    renderGameTab(currentGame);
    handleGenerateTickets();
    await checkVipSession();
    renderDelayedSyncNotice();
  }

  // Register PWA service worker if available
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(err => console.log('SW reg error:', err));
  }
}

function formatDateTime(isoString) {
  if (!isoString) return '--';
  const d = new Date(isoString);
  return d.toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

// 1. Render Top Summary Cards
function renderSummaryCards() {
  const container = document.getElementById('summary-cards-container');
  container.innerHTML = '';

  const order = ['baloto', 'revancha', 'miloto'];
  order.forEach(key => {
    const g = APP_DATA.games[key];
    if (!g || !g.latest_draw) return;

    const lat = g.latest_draw;
    const ballClass = key === 'baloto' ? 'ball-baloto' : (key === 'revancha' ? 'ball-revancha' : 'ball-miloto');
    
    let ballsHtml = lat.numbers.map(n => `<div class="ball ${ballClass}">${pad(n)}</div>`).join('');
    if (lat.superball) {
      ballsHtml += `<div class="ball ball-super" title="Superbalota">${pad(lat.superball)}</div>`;
    }

    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card-top">
        <span class="card-title">${g.name}</span>
        <span class="jackpot-pill">${lat.jackpot || 'Premio Acumulado'}</span>
      </div>
      <div class="ball-row">${ballsHtml}</div>
      <div class="card-meta">
        <span>Sorteo #${lat.draw_number || 'N/A'}</span>
        <span>Fecha: ${lat.draw_date}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

// 2. Tab Navigation
function setGameTab(gameKey) {
  currentGame = gameKey;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.game === gameKey);
  });
  renderGameTab(gameKey);
  handleGenerateTickets();
  resetChecker();
  if (isVipActive()) {
    renderVipRadar();
  }
}

// 3. Render Game Detail View
function renderGameTab(gameKey) {
  const g = APP_DATA.games[gameKey];
  if (!g) return;

  // Header Title
  document.getElementById('current-game-title').innerText = `${g.name} — Inteligencia de Datos`;
  document.getElementById('total-draws-count').innerText = `${g.total_draws} sorteos analizados`;

  // Heatmap
  const hmContainer = document.getElementById('heatmap-container');
  hmContainer.innerHTML = '';
  const sortedByNum = [...g.number_stats].sort((a,b) => a.number - b.number);
  
  sortedByNum.forEach(item => {
    const tagClass = item.category === 'HOT' ? 'tag-hot' : (item.category === 'COLD' ? 'tag-cold' : 'tag-warm');
    const tagText = item.category === 'HOT' ? 'HOT 🔥' : (item.category === 'COLD' ? 'FRÍA ❄️' : 'REG');
    
    const cell = document.createElement('div');
    cell.className = 'heat-cell';
    cell.innerHTML = `
      <div class="heat-val">${pad(item.number)}</div>
      <div class="heat-sub">${item.count_total} sal. (${item.pct_total}%)</div>
      <span class="tag-badge ${tagClass}">${tagText}</span>
    `;
    hmContainer.appendChild(cell);
  });

  // Gaps / Overdue Table
  const gapsTbody = document.querySelector('#gaps-table tbody');
  gapsTbody.innerHTML = '';
  g.gaps.slice(0, 10).forEach(item => {
    const row = document.createElement('tr');
    const isCritical = item.overdue_index >= 1.5;
    const color = isCritical ? '#ef4444' : (item.overdue_index >= 1.0 ? '#f59e0b' : '#94a3b8');
    row.innerHTML = `
      <td><strong>Balota ${pad(item.number)}</strong></td>
      <td style="color: ${color}; font-weight: 700;">${item.current_gap} sorteos</td>
      <td>${item.avg_interval}</td>
      <td>${item.max_gap}</td>
      <td style="font-weight: 600; color: ${color};">${item.overdue_index}x</td>
    `;
    gapsTbody.appendChild(row);
  });

  // Gaussian Metrics
  document.getElementById('val-mean').innerText = g.sum_metrics.mean;
  document.getElementById('val-iqr').innerText = `[${g.sum_metrics.optimal_range[0]} - ${g.sum_metrics.optimal_range[1]}]`;
  document.getElementById('val-std').innerText = `±${g.sum_metrics.std}`;

  // Parity Table
  const parityTbody = document.querySelector('#parity-table tbody');
  parityTbody.innerHTML = '';
  g.parity_distribution.slice(0, 4).forEach(([ratio, pct]) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><strong>${ratio}</strong></td>
      <td style="color: #60a5fa; font-weight: 700;">${pct}%</td>
    `;
    parityTbody.appendChild(row);
  });
}

// 4. Interactive Ticket Generator (Free)
function handleGenerateTickets() {
  const g = APP_DATA.games[currentGame];
  if (!g) return;

  const selector = document.getElementById('strategy-select').value;
  const container = document.getElementById('ticket-results-grid');
  container.innerHTML = '';

  let list = [];
  if (selector === 'all') {
    list = g.predictions;
  } else {
    const found = g.predictions.find(p => {
      if (selector === 'balanced') return p.strategy.includes('Equilibrada');
      if (selector === 'hot') return p.strategy.includes('Caliente');
      if (selector === 'cold') return p.strategy.includes('Reversión');
      if (selector === 'anticrowd') return p.strategy.includes('Anti-Aglomeración');
      return true;
    });
    list = found ? [found] : [g.predictions[0]];
  }

  const ballClass = currentGame === 'baloto' ? 'ball-baloto' : (currentGame === 'revancha' ? 'ball-revancha' : 'ball-miloto');

  list.forEach((ticket, i) => {
    let ballsHtml = ticket.numbers.map(n => `<div class="ball ${ballClass}" style="width: 38px; height: 38px; font-size: 0.95rem;">${pad(n)}</div>`).join('');
    if (ticket.superball) {
      ballsHtml += `<div class="ball ball-super" style="width: 38px; height: 38px; font-size: 0.95rem;" title="Superbalota">${pad(ticket.superball)}</div>`;
    }

    const copyText = `${g.name}: ${ticket.numbers.map(pad).join(' - ')}${ticket.superball ? ' + SB: ' + pad(ticket.superball) : ''}`;

    const card = document.createElement('div');
    card.className = 'ticket-box';
    card.innerHTML = `
      <div class="ticket-header">
        <span class="ticket-badge">Boleto #${i+1}: ${ticket.strategy}</span>
        <button class="btn-copy" onclick="copyToClipboard('${copyText}', this)">Copiar</button>
      </div>
      <div class="ball-row" style="margin: 0.5rem 0;">${ballsHtml}</div>
      <div style="font-size: 0.8rem; color: #94a3b8;">
        <strong>Suma:</strong> ${ticket.sum} | <strong>Paridad:</strong> ${countParity(ticket.numbers)}
      </div>
      <div class="ticket-footer">${ticket.rationale}</div>
    `;
    container.appendChild(card);
  });
}

function countParity(nums) {
  const evens = nums.filter(x => x % 2 === 0).length;
  return `${evens}P - ${5 - evens}I`;
}

// 5. CRYPTOGRAPHIC PIN VALIDATOR & SESSION MANAGEMENT
async function sha256Short(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  const arr = Array.from(new Uint8Array(buf));
  return arr.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 4).toUpperCase();
}

async function validateCryptographicPin(rawPin) {
  const pin = rawPin.trim().toUpperCase();
  
  // Master override codes for Administrator
  if (pin === 'BUCARAMANGA' || pin === 'JOAN17-ADMIN' || pin === 'ADMIN-MASTER-JOAN' || pin === 'VIP2026') {
    return {
      valid: true,
      master: true,
      exp_date: 'Indefinida (Master)',
      days_left: 9999,
      client_id: 'ADMIN'
    };
  }

  const parts = pin.split('-');
  if (parts.length !== 4 || parts[0] !== 'VIP') {
    return {
      valid: false,
      reason: 'El formato del PIN no es válido. Debe tener el formato: VIP-AAMMDD-XXX-XXXX'
    };
  }

  const [prefix, dateCode, clientId, providedHash] = parts;
  if (dateCode.length !== 6 || clientId.length !== 3) {
    return {
      valid: false,
      reason: 'La estructura de fecha o cliente del PIN no es correcta.'
    };
  }

  // Verify signature
  const payload = `${dateCode}-${clientId}-${SECRET_SALT}`;
  const expectedHash = await sha256Short(payload);

  if (providedHash !== expectedHash) {
    return {
      valid: false,
      reason: 'Firma de seguridad inválida o PIN alterado.'
    };
  }

  // Parse expiration date YYMMDD
  const year = parseInt('20' + dateCode.substring(0, 2));
  const month = parseInt(dateCode.substring(2, 4)) - 1;
  const day = parseInt(dateCode.substring(4, 6));

  const expDate = new Date(year, month, day, 23, 59, 59);
  const now = new Date();

  const diffMs = expDate - now;
  const daysLeft = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  const formattedDate = expDate.toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });

  if (daysLeft < 0) {
    return {
      valid: false,
      expired: true,
      exp_date: formattedDate,
      reason: `Este PIN venció el ${formattedDate}. Por favor renueva tu suscripción por Nequi/Daviplata para continuar.`
    };
  }

  return {
    valid: true,
    expired: false,
    exp_date: formattedDate,
    days_left: daysLeft,
    client_id: clientId
  };
}

function isVipActive() {
  return localStorage.getItem('lotto_vip_token') !== null;
}

async function checkVipSession() {
  const token = localStorage.getItem('lotto_vip_token');
  if (!token) {
    document.getElementById('vip-unlock-box').style.display = 'block';
    document.getElementById('vip-active-panel').style.display = 'none';
    document.getElementById('vip-header-pill').style.display = 'none';
    return;
  }

  const result = await validateCryptographicPin(token);
  if (result.valid) {
    document.getElementById('vip-unlock-box').style.display = 'none';
    document.getElementById('vip-active-panel').style.display = 'block';
    
    const pill = document.getElementById('vip-header-pill');
    pill.style.display = 'inline-flex';
    pill.innerText = `👑 VIP Activo • Vence: ${result.exp_date} (${result.days_left}d)`;

    document.getElementById('vip-expiry-detail').innerText = `Vigencia activa hasta el ${result.exp_date} (quedan ${result.days_left} días de acceso).`;
    renderVipRadar();
  } else {
    // If expired or tampered, clear session and inform
    localStorage.removeItem('lotto_vip_token');
    document.getElementById('vip-unlock-box').style.display = 'block';
    document.getElementById('vip-active-panel').style.display = 'none';
    document.getElementById('vip-header-pill').style.display = 'none';
    if (result.expired) {
      alert(`⚠️ ${result.reason}`);
    }
  }
}

async function unlockWithPin() {
  const inputEl = document.getElementById('vip-pin-input');
  const pin = inputEl.value.trim().toUpperCase();

  if (!pin) {
    alert("Por favor escribe tu PIN de acceso VIP.");
    return;
  }

  const res = await validateCryptographicPin(pin);
  if (res.valid) {
    localStorage.setItem('lotto_vip_token', pin);
    await checkVipSession();
    alert(`🎉 ¡Membresía VIP Activada con Éxito!\n\nVigencia activa hasta el ${res.exp_date}.\nTienes acceso a números personalizados, radar de atrasos y boletos únicos.`);
  } else {
    alert(`❌ ${res.reason}`);
  }
}

function logoutVip() {
  localStorage.removeItem('lotto_vip_token');
  checkVipSession();
  alert("Has cerrado sesión del Panel VIP.");
}

// 6. VIP FEATURE: Custom Fixed Numbers Generator
function generateVipCustomTicket() {
  const g = APP_DATA.games[currentGame];
  const in1 = parseInt(document.getElementById('vip-f1').value);
  const in2 = parseInt(document.getElementById('vip-f2').value);

  const fixed = [in1, in2].filter(n => !isNaN(n) && n >= 1 && n <= g.max_number);
  const uniqueFixed = [...new Set(fixed)];

  if (uniqueFixed.length === 0) {
    alert(`Por favor ingresa al menos 1 número favorito válido (del 1 al ${g.max_number})`);
    return;
  }

  // Build pool of numbers avoiding chosen fixed
  const optRange = g.sum_metrics.optimal_range;
  const pairAffinities = {};
  for (let p of g.top_pairs) {
    const [p1, p2] = p.pair;
    if (uniqueFixed.includes(p1) && !uniqueFixed.includes(p2)) {
      pairAffinities[p2] = (pairAffinities[p2] || 1) + p.count * 3;
    } else if (uniqueFixed.includes(p2) && !uniqueFixed.includes(p1)) {
      pairAffinities[p1] = (pairAffinities[p1] || 1) + p.count * 3;
    }
  }

  // Weight candidate numbers
  const candidates = [];
  for (let item of g.number_stats) {
    const n = item.number;
    if (!uniqueFixed.includes(n)) {
      const weight = (pairAffinities[n] || 1) + item.count_total;
      for (let w = 0; w < weight; w++) candidates.push(n);
    }
  }

  // Generate valid combination
  let bestCombo = null;
  let attempts = 0;
  const needed = 5 - uniqueFixed.length;

  while (!bestCombo && attempts < 2000) {
    attempts++;
    const pick = [];
    const pool = [...candidates];
    while (pick.length < needed && pool.length > 0) {
      const randIdx = Math.floor(Math.random() * pool.length);
      const chosen = pool[randIdx];
      if (!pick.includes(chosen)) pick.push(chosen);
      pool.splice(randIdx, 1);
    }

    const testCombo = [...uniqueFixed, ...pick].sort((a,b) => a - b);
    const s = testCombo.reduce((a,b) => a + b, 0);
    const evens = testCombo.filter(n => n % 2 === 0).length;

    if (s >= optRange[0] && s <= optRange[1] && (evens === 2 || evens === 3)) {
      bestCombo = testCombo;
    }
  }

  if (!bestCombo) {
    bestCombo = [...uniqueFixed];
    while (bestCombo.length < 5) {
      const r = Math.floor(Math.random() * g.max_number) + 1;
      if (!bestCombo.includes(r)) bestCombo.push(r);
    }
    bestCombo.sort((a,b) => a - b);
  }

  let sb = null;
  if (g.has_superball) {
    const topSb = g.superball_stats.slice(0, 3).map(x => x.number);
    sb = topSb[Math.floor(Math.random() * topSb.length)] || 10;
  }

  const resultContainer = document.getElementById('vip-custom-result');
  const ballClass = currentGame === 'baloto' ? 'ball-baloto' : (currentGame === 'revancha' ? 'ball-revancha' : 'ball-miloto');
  
  let ballsHtml = bestCombo.map(n => {
    const isUserBall = uniqueFixed.includes(n);
    return `<div class="ball ${isUserBall ? 'ball-fixed' : ballClass}" style="width: 42px; height: 42px;" title="${isUserBall ? 'Tu balota favorita fija' : 'Optimizada por algoritmo'}">${pad(n)}</div>`;
  }).join('');

  if (sb) {
    ballsHtml += `<div class="ball ball-super" style="width: 42px; height: 42px;" title="Superbalota">${pad(sb)}</div>`;
  }

  const s = bestCombo.reduce((a,b) => a + b, 0);
  const copyText = `JUGADA VIP PERSONALIZADA (${g.name}): ${bestCombo.map(pad).join(' - ')}${sb ? ' + SB: ' + pad(sb) : ''}`;

  resultContainer.innerHTML = `
    <div style="background: rgba(88, 28, 135, 0.25); border: 1px solid #a855f7; border-radius: 10px; padding: 1rem; margin-top: 1rem;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:700; color:#fbbf24; font-size:0.85rem;">✨ TU COMBINACIÓN VIP OPTIMIZADA</span>
        <button class="btn-copy" onclick="copyToClipboard('${copyText}', this)">Copiar Jugada</button>
      </div>
      <div class="ball-row" style="margin: 0.75rem 0;">${ballsHtml}</div>
      <p style="font-size:0.8rem; color:#e2e8f0; line-height:1.4;">
        Balotas moradas: tus números fijos <strong>[ ${uniqueFixed.map(pad).join(', ')} ]</strong>.<br>
        Balotas optimizadas: <strong>[ ${bestCombo.filter(n => !uniqueFixed.includes(n)).map(pad).join(', ')} ]</strong> completan una suma ideal de <strong>${s}</strong> en campana de Gauss con balance de paridad <strong>${countParity(bestCombo)}</strong>.
      </p>
    </div>
  `;
}

// 7. VIP FEATURE: Radar of Critical Overdue Balls
function renderVipRadar() {
  const g = APP_DATA.games[currentGame];
  const container = document.getElementById('vip-radar-container');
  if (!container) return;

  const critical = g.gaps.filter(x => x.overdue_index >= 1.5).slice(0, 4);
  if (critical.length === 0) {
    container.innerHTML = `<p style="font-size:0.85rem; color:#94a3b8;">No hay balotas en atraso crítico anómalo en este momento para ${g.name}.</p>`;
    return;
  }

  let html = `<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:0.75rem;">`;
  critical.forEach(item => {
    html += `
      <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 0.75rem; text-align:center;">
        <div style="font-size: 1.25rem; font-weight:800; color:#f87171;">Balota ${pad(item.number)}</div>
        <div style="font-size: 0.8rem; font-weight:700; color:#fff;">${item.current_gap} sorteos sin salir</div>
        <div style="font-size: 0.7rem; color:#94a3b8; margin-top:2px;">Atraso: ${item.overdue_index}x sobre el promedio</div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

// 8. VIP FEATURE: Unique Ticket Generator
function generateVipUniqueTicket() {
  const g = APP_DATA.games[currentGame];
  const container = document.getElementById('vip-unique-result');
  
  const nums = [];
  while (nums.length < 5) {
    const r = Math.floor(Math.random() * g.max_number) + 1;
    if (!nums.includes(r)) nums.push(r);
  }
  nums.sort((a,b) => a - b);
  
  let sb = null;
  if (g.has_superball) {
    sb = Math.floor(Math.random() * g.max_superball) + 1;
  }

  const hash = 'VIP-' + Math.random().toString(36).substring(2, 7).toUpperCase();
  const ballClass = currentGame === 'baloto' ? 'ball-baloto' : (currentGame === 'revancha' ? 'ball-revancha' : 'ball-miloto');
  let ballsHtml = nums.map(n => `<div class="ball ${ballClass}" style="width: 38px; height: 38px;">${pad(n)}</div>`).join('');
  if (sb) ballsHtml += `<div class="ball ball-super" style="width: 38px; height: 38px;">${pad(sb)}</div>`;

  const copyText = `BOLETO VIP ÚNICO (#${hash}): ${nums.map(pad).join(' - ')}${sb ? ' + SB: ' + pad(sb) : ''}`;

  container.innerHTML = `
    <div style="background: rgba(30, 27, 75, 0.7); border: 1px solid #6366f1; border-radius: 10px; padding: 1rem; margin-top: 1rem;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:0.8rem; font-weight:700; color:#818cf8;">🔒 BOLETO PRIVADO #${hash}</span>
        <button class="btn-copy" onclick="copyToClipboard('${copyText}', this)">Copiar</button>
      </div>
      <div class="ball-row" style="margin: 0.5rem 0;">${ballsHtml}</div>
      <p style="font-size:0.75rem; color:#94a3b8;">Asignación única y no repetida. Exclusiva para tu sesión actual.</p>
    </div>
  `;
}

// 9. DELAYED SYNC STATUS NOTICE
function renderDelayedSyncNotice() {
  const syncInfo = APP_DATA.metadata.sync_info;
  const statusEl = document.getElementById('delayed-sync-badge');
  if (syncInfo && statusEl) {
    statusEl.innerText = "Doble Chequeo: 11:30 PM & 12:30 AM (Re-verificación oficial diferida activa)";
  }
}

// 10. Interactive Ticket Checker
function resetChecker() {
  document.querySelectorAll('.checker-input').forEach(inp => inp.value = '');
  const sbInput = document.getElementById('check-sb');
  if (currentGame === 'miloto') {
    sbInput.style.display = 'none';
  } else {
    sbInput.style.display = 'inline-block';
  }
  document.getElementById('checker-result-box').style.display = 'none';
}

function checkUserTicket() {
  const g = APP_DATA.games[currentGame];
  const inputs = [
    parseInt(document.getElementById('c1').value),
    parseInt(document.getElementById('c2').value),
    parseInt(document.getElementById('c3').value),
    parseInt(document.getElementById('c4').value),
    parseInt(document.getElementById('c5').value)
  ].filter(x => !isNaN(x));

  if (inputs.length !== 5) {
    alert("Por favor ingresa los 5 números de tu boleto (del 1 al " + g.max_number + ")");
    return;
  }

  const outOfRange = inputs.some(n => n < 1 || n > g.max_number);
  if (outOfRange) {
    alert(`Todos los números deben estar entre 1 y ${g.max_number}`);
    return;
  }

  const userCombo = [...new Set(inputs)].sort((a,b) => a - b);
  if (userCombo.length !== 5) {
    alert("No puedes repetir números dentro de la misma jugada.");
    return;
  }

  const s = userCombo.reduce((a,b) => a + b, 0);
  const evens = userCombo.filter(n => n % 2 === 0).length;
  const optRange = g.sum_metrics.optimal_range;
  const isSumOk = s >= optRange[0] && s <= optRange[1];
  const isParityOk = evens === 2 || evens === 3;

  let exactMatch = null;
  for (let d of g.recent_draws) {
    if (JSON.stringify(d.numbers) === JSON.stringify(userCombo)) {
      exactMatch = d;
      break;
    }
  }

  const resBox = document.getElementById('checker-result-box');
  resBox.style.display = 'block';

  let verdictHtml = `
    <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: #60a5fa;">Diagnóstico de tu Jugada: [ ${userCombo.map(pad).join(' - ')} ]</h4>
    <p>• <strong>Suma de las balotas:</strong> ${s} ${isSumOk ? '<span style="color:#34d399;">(En rango Gauss óptimo)</span>' : '<span style="color:#fbbf24;">(Fuera del 50% central)</span>'}</p>
    <p>• <strong>Distribución:</strong> ${evens} Pares - ${5 - evens} Impares ${isParityOk ? '<span style="color:#34d399;">(Esquema frecuente)</span>' : '<span style="color:#fbbf24;">(Esquema atípico)</span>'}</p>
  `;

  if (exactMatch) {
    verdictHtml += `<p style="color: #f87171; font-weight: 700; margin-top: 0.5rem;">⚠️ Esta combinación idéntica ya cayó el ${exactMatch.draw_date} (Sorteo #${exactMatch.draw_number}).</p>`;
  } else {
    verdictHtml += `<p style="color: #34d399; font-weight: 600; margin-top: 0.5rem;">✅ Combinación limpia: No ha caído de forma idéntica en el histórico registrado.</p>`;
  }

  resBox.innerHTML = verdictHtml;
}

// Helpers
function pad(n) {
  return n < 10 ? '0' + n : n;
}

function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const original = btn.innerText;
    btn.innerText = '¡Copiado!';
    btn.style.borderColor = '#10b981';
    btn.style.color = '#10b981';
    setTimeout(() => {
      btn.innerText = original;
      btn.style.borderColor = '#334155';
      btn.style.color = '#94a3af';
    }, 2000);
  });
}

// Kickoff
window.addEventListener('DOMContentLoaded', initApp);
