/**
 * Read-only RunDeck x KWGT proxy.
 *
 * Uses only the existing public Supabase anon key. Authentication and data
 * selection happen in public.widget_snapshot(), which checks a SHA-256 hash
 * against a per-account token and returns a minimal snapshot.
 *
 * First run supabase/widget_uplink.sql in the Supabase SQL editor.
 * NEVER use the service-role key here or in KWGT.
 */
const config = require('../config.js');

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'private, no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ status: 'METHOD_NOT_ALLOWED' });
  }

  const token = typeof req.query?.token === 'string' ? req.query.token : '';
  if (!/^[0-9a-f]{64}$/.test(token)) {
    return res.status(401).json({ status: 'UNAUTHORIZED' });
  }

  if (!/^https:\/\//.test(config.supabaseUrl || '') || !config.supabaseAnonKey) {
    return res.status(503).json({ status: 'NOT_CONFIGURED' });
  }

  try {
    const response = await fetch(
      config.supabaseUrl.replace(/\/$/, '') + '/rest/v1/rpc/widget_snapshot',
      {
        method: 'POST',
        headers: {
          apikey: config.supabaseAnonKey,
          Authorization: 'Bearer ' + config.supabaseAnonKey,
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify({ p_token: token }),
        signal: AbortSignal.timeout(8000)
      }
    );
    if (!response.ok) {
      // A missing RPC is an uninstalled migration; keep SQL errors private.
      return res.status(response.status === 404 ? 503 : 502).json({
        status: response.status === 404 ? 'MIGRATION_REQUIRED' : 'SYNC_ERROR'
      });
    }
    const snapshot = await response.json();
    if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot)) {
      return res.status(401).json({ status: 'UNAUTHORIZED' });
    }
    return res.status(200).json(snapshot);
  } catch (_err) {
    return res.status(502).json({ status: 'SYNC_ERROR' });
  }
};
