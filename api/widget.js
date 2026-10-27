/**
 * RunDeck x KWGT — read-only snapshot endpoint for a SINGLE configured account.
 * Install at /api/widget.js in the RunDeck Vercel project.
 * Requires RUNDECK_WIDGET_TOKEN, RUNDECK_WIDGET_USER_ID,
 * SUPABASE_SERVICE_ROLE_KEY and SUPABASE_URL environment variables.
 * Never expose the Supabase service-role key to KWGT, config.js, or GitHub.
 */
const { createHash, timingSafeEqual } = require('node:crypto');

function sameSecret(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const x = createHash('sha256').update(a).digest();
  const y = createHash('sha256').update(b).digest();
  return timingSafeEqual(x, y);
}

const text = v => (typeof v === 'string' ? v : '');
const num = v => (Number.isFinite(Number(v)) ? Number(v) : 0);
const pad2 = n => String(n).padStart(2, '0');
const timeZone = process.env.RUNDECK_WIDGET_TIMEZONE || 'Europe/Stockholm';
function localDay(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(d).filter(x => x.type !== 'literal').map(x => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
function mondayOf(dateText) {
  const d = new Date(`${dateText}T12:00:00Z`);
  const back = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - back);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth()+1)}-${pad2(d.getUTCDate())}`;
}
function xpLevel(xp) {
  let level = 1;
  let left = Math.max(0, Math.floor(num(xp)));
  while (left >= 80 + 40 * level && level < 10000) {
    left -= 80 + 40 * level;
    level++;
  }
  return level;
}
function publicSnapshot(deck) {
  const today = localDay();
  const yesterday = localDay(-1);
  const beforeYesterday = localDay(-2);
  const tasks = Array.isArray(deck.tasks) ? deck.tasks : [];
  const fresh = deck.day === today;
  // Match RunDeck's daily rollover: routine tasks reset; finished non-routine
  // tasks are archived on the next day when the app opens.
  const queue = tasks.filter(t => {
    if (!t || !['today', 'routine'].includes(t.list)) return false;
    if (t.list === 'routine') return true;
    return !t.done && !t.failed || fresh;
  });
  const done = queue.filter(t => fresh && (t.done || t.failed)).length;
  const open = queue.filter(t => !(fresh && (t.done || t.failed))).length;
  const total = open + done;
  const progress = total ? Math.round(100 * done / total) : 0;
  const streak = deck.streak || {};
  const monday = mondayOf(today);
  const shieldFree = text(streak.shield) !== monday ||
    (Array.isArray(deck.items) && deck.items.some(i => i && i.t === 'shield'));
  const liveStreak = [today, yesterday].includes(streak.last) ||
    (streak.last === beforeYesterday && shieldFree) ? Math.max(0, Math.floor(num(streak.n))) : 0;
  const priority = tasks.find(t => t && t.id === deck.target && !t.done && !t.failed);
  const next = priority || queue.find(t => !(fresh && (t.done || t.failed)));
  const nextRaw = (text(next?.title).replace(/\s+/g, ' ').trim() || 'ALL OBJECTIVES CLEAR');
  const nextTitle = nextRaw.length > 27 ? nextRaw.slice(0, 26) + '…' : nextRaw;
  return {
    status: 'LIVE',
    today_open: open,
    open_display: String(open).padStart(2, '0'),
    today_done: done,
    today_total: total,
    total_display: String(total).padStart(2, '0'),
    progress_pct: progress,
    level: xpLevel(deck.xp),
    level_display: String(xpLevel(deck.xp)).padStart(2, '0'),
    streak: liveStreak,
    xp: Math.floor(num(deck.xp)),
    next_title: nextTitle,
    synced_at: new Date().toISOString()
  };
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'private, no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (req.method !== 'GET') return res.status(405).json({ status: 'METHOD_NOT_ALLOWED' });
  const token = typeof req.query.token === 'string' ? req.query.token : '';
  const expected = process.env.RUNDECK_WIDGET_TOKEN;
  if (!expected || expected.length < 32 || !sameSecret(token, expected)) {
    return res.status(401).json({ status: 'UNAUTHORIZED' });
  }
  const userId = process.env.RUNDECK_WIDGET_USER_ID;
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!userId || !supabaseUrl || !serviceKey) {
    return res.status(503).json({ status: 'NOT_CONFIGURED' });
  }
  if (!/^[0-9a-f-]{36}$/i.test(userId)) return res.status(503).json({ status: 'BAD_USER_CONFIG' });
  try {
    const url = `${supabaseUrl.replace(/\/$/, '')}/rest/v1/decks?user_id=eq.${encodeURIComponent(userId)}&select=data`;
    const response = await fetch(url, {
      headers: { apikey: serviceKey, Authorization: `Bearer ${serviceKey}`, Accept: 'application/json' },
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error('Supabase request failed');
    const rows = await response.json();
    if (!Array.isArray(rows) || !rows[0]?.data) {
      return res.status(404).json({ status: 'NO_DECK' });
    }
    return res.status(200).json(publicSnapshot(rows[0].data));
  } catch (_error) {
    // Don't leak error details about Supabase or the account to clients.
    return res.status(502).json({ status: 'SYNC_ERROR' });
  }
}
