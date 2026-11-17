const { createHash, sign } = require('node:crypto');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { Readable } = require('node:stream');
const { pipeline } = require('node:stream/promises');

const tokenEndpoint = 'https://oauth2.googleapis.com/token';
const driveEndpoint = 'https://www.googleapis.com/drive/v3/files';
const driveScope = 'https://www.googleapis.com/auth/drive.readonly';
const googleDocument = 'application/vnd.google-apps.document';
const wordDocument = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
let accessToken;
let expiresAt = 0;
let refreshingToken;
let catalog;

function assets() {
  if (catalog) return catalog;
  const source = readFileSync(join(__dirname, '../dist/data.js'), 'utf8').trim();
  const data = JSON.parse(source.slice('window.CASTELO_DATA = '.length, -1));
  catalog = new Map(data.files.map(file => [file.id, file]));
  return catalog;
}

async function authorized(cookie = '') {
  const session = cookie.match(/(?:^|;\s*)__Host-castelo-partner=([A-Za-z0-9_-]{43})(?:;|$)/)?.[1];
  if (!session) return false;
  const redisUrl = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const redisToken = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!redisUrl?.startsWith('https://') || !redisToken) throw new Error('Redis is unavailable');
  const digest = createHash('sha256').update(session).digest('hex');
  const response = await fetch(redisUrl, {
    method: 'POST',
    headers: { Authorization: `Bearer ${redisToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(['GET', `castelo:session:${digest}`]),
    signal: AbortSignal.timeout(5000)
  });
  if (!response.ok) throw new Error('Session lookup failed');
  const { result, error } = await response.json();
  if (error) throw new Error('Session lookup failed');
  const allowed = (process.env.PARTNER_ALLOWED_EMAILS || '')
    .split(',').map(email => email.trim().toLowerCase()).filter(Boolean);
  return typeof result === 'string' && allowed.includes(result);
}

function base64url(value) {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

async function mintToken() {
  const credentials = JSON.parse(process.env.GOOGLE_DRIVE_SERVICE_ACCOUNT);
  const now = Math.floor(Date.now() / 1000);
  const assertion = [
    base64url({ alg: 'RS256', typ: 'JWT' }),
    base64url({ iss: credentials.client_email, scope: driveScope, aud: tokenEndpoint, iat: now, exp: now + 3600 })
  ].join('.');
  const signature = sign('RSA-SHA256', Buffer.from(assertion), credentials.private_key).toString('base64url');
  const response = await fetch(tokenEndpoint, {
    method: 'POST',
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: `${assertion}.${signature}`
    }),
    signal: AbortSignal.timeout(8000)
  });
  if (!response.ok) throw new Error('Drive authorization failed');
  const token = await response.json();
  if (!token.access_token || !Number.isFinite(token.expires_in)) throw new Error('Drive token missing');
  accessToken = token.access_token;
  expiresAt = Date.now() + token.expires_in * 1000;
  return accessToken;
}

function driveToken() {
  if (accessToken && expiresAt > Date.now() + 60_000) return Promise.resolve(accessToken);
  refreshingToken ||= mintToken().finally(() => { refreshingToken = undefined; });
  return refreshingToken;
}

function disposition(name, download) {
  const ascii = name.replace(/[^a-zA-Z0-9._ -]/g, '_');
  const utf8 = encodeURIComponent(name).replace(/['()*]/g, char => '%' + char.charCodeAt(0).toString(16));
  return `${download ? 'attachment' : 'inline'}; filename="${ascii}"; filename*=UTF-8''${utf8}`;
}

function answer(res, status, message) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.end(message);
}

module.exports = async function partnerMedia(req, res) {
  res.setHeader('Cache-Control', 'private, no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Security-Policy', "sandbox; default-src 'none'");
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return answer(res, 405, 'Método indisponível.');
  }

  try {
    if (!await authorized(req.headers.cookie)) return answer(res, 401, 'Entre no Portal do Parceiro para acessar o arquivo.');
    const query = new URL(req.url, 'http://localhost').searchParams;
    const file = assets().get(query.get('id'));
    if (!file) return answer(res, 404, 'Arquivo não encontrado.');
    if (!process.env.GOOGLE_DRIVE_SERVICE_ACCOUNT) return answer(res, 503, 'Entrega de arquivos indisponível.');
    const range = req.headers.range;
    if (range && !/^bytes=(?:\d{1,16}-\d{0,16}|-\d{1,16})$/.test(range)) {
      return answer(res, 416, 'Intervalo de leitura inválido.');
    }

    const exported = file.mime === googleDocument;
    const fileUrl = `${driveEndpoint}/${encodeURIComponent(file.id)}`;
    const upstream = exported
      ? `${fileUrl}/export?mimeType=${encodeURIComponent(wordDocument)}`
      : `${fileUrl}?alt=media&supportsAllDrives=true`;
    const headers = { Authorization: `Bearer ${await driveToken()}` };
    if (range && !exported) headers.Range = range;
    const abort = new AbortController();
    const cancel = () => abort.abort();
    res.once('close', cancel);
    try {
      const response = await fetch(upstream, { headers, signal: abort.signal });
      if (response.status === 416) {
        const contentRange = response.headers.get('content-range');
        if (contentRange) res.setHeader('Content-Range', contentRange);
        await response.body?.cancel();
        return answer(res, 416, 'Intervalo de leitura inválido.');
      }
      if (!response.ok || !response.body) {
        await response.body?.cancel();
        return answer(res, 502, 'Não foi possível obter o arquivo de origem.');
      }

      const inline = /^video\/mp4$|^image\/(jpeg|png)$|^application\/pdf$/.test(file.mime);
      const filename = exported && !/\.docx$/i.test(file.name) ? file.name + '.docx' : file.name;
      res.statusCode = response.status;
      res.setHeader('Content-Type', exported ? wordDocument : file.mime);
      res.setHeader('Content-Disposition', disposition(filename, !inline || query.get('download') === '1'));
      for (const header of ['content-range', 'accept-ranges']) {
        const value = response.headers.get(header);
        if (value) res.setHeader(header, value);
      }
      await pipeline(Readable.fromWeb(response.body), res);
    } finally {
      res.off('close', cancel);
    }
  } catch (error) {
    if (!res.headersSent && !res.destroyed) return answer(res, 503, 'Entrega de arquivos indisponível.');
    if (!res.destroyed) res.destroy(error);
  }
};
