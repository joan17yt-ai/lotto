/**
 * LottoAnalytics Pro Colombia - Client-Side Interactive Application
 */

let APP_DATA = null;
let currentGame = 'baloto';

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

// 4. Interactive Ticket Generator
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

// 5. Interactive Ticket Checker
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

  // Validate range
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

  // Check history
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
