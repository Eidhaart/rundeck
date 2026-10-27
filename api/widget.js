/**
 * Read-only RunDeck x KWGT endpoint.
 * JSON ?token=<secret>: operator stats and today's tasks
 * JPEG ?token=<secret>&image=1: the same user's uploaded profile portrait
 *
 * Only the existing public Supabase anon key is used.
 * SECURITY: Supabase validates the 256-bit bearer token using the stored
 * SHA-256 hash; never log the query string or include an admin key.
 *
 * Migration: supabase/widget_profile_upgrade.sql
 */
const config = require('../config.js');

const headers = {
  apikey: config.supabaseAnonKey,
  Authorization: 'Bearer ' + config.supabaseAnonKey,
  'Content-Type': 'application/json',
  Accept: 'application/json'
};

async function widgetRpc(name, token) {
  return await fetch(
    config.supabaseUrl.replace(/\/$/, '') + '/rest/v1/rpc/' + name,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({p_token: token}),
      signal: AbortSignal.timeout(9000)
    }
  );
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'private, no-store, max-age=0');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({status: 'METHOD_NOT_ALLOWED'});
  }
  const token = typeof req.query?.token === 'string' ? req.query.token : '';
  if (!/^[0-9a-f]{64}$/.test(token)) {
    return res.status(401).json({status: 'UNAUTHORIZED'});
  }
  if (!/^https:\/\//.test(config.supabaseUrl || '') || !config.supabaseAnonKey) {
    return res.status(503).json({status: 'NOT_CONFIGURED'});
  }

  const wantsImage = req.query?.image === '1';
  try {
    const response = await widgetRpc(
      wantsImage ? 'widget_profile_image' : 'widget_profile_snapshot',
      token
    );
    if (!response.ok) {
      // Don't expose private database errors in a publicly reachable endpoint.
      return res.status(response.status === 404 ? 503 : 502).json({
        status: response.status === 404 ? 'MIGRATION_REQUIRED' : 'SYNC_ERROR'
      });
    }

    const value = await response.json();
    if (wantsImage) {
      if (typeof value !== 'string' || !value.startsWith('data:image/jpeg;base64,')) {
        return res.status(404).json({status: 'NO_PORTRAIT'});
      }
      const encoded = value.slice('data:image/jpeg;base64,'.length);
      if (encoded.length > 1500000 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) {
        return res.status(502).json({status: 'BAD_PORTRAIT'});
      }
      const pixels = Buffer.from(encoded, 'base64');
      if (!pixels.length || pixels[0] !== 0xff || pixels[1] !== 0xd8) {
        return res.status(502).json({status: 'BAD_PORTRAIT'});
      }
      res.setHeader('Content-Type', 'image/jpeg');
      return res.status(200).end(pixels);
    }

    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return res.status(401).json({status: 'UNAUTHORIZED'});
    }
    return res.status(200).json(value);
  } catch (_error) {
    return res.status(502).json({status: 'SYNC_ERROR'});
  }
};
