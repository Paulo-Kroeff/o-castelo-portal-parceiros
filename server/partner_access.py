"""Server-side email verification for the partner portal."""

import hashlib
import hmac
import json
import os
import re
import secrets
from urllib.request import Request, urlopen

from .partner_mail import send_access_code

CODE_TTL = 600
RESEND_DELAY = 60
MAX_ATTEMPTS = 5
SESSION_TTL = 8 * 60 * 60

# The checks and writes run together, including when requests reach different
# instances of the serverless function.
ISSUE = """
if not redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3], 'NX') then
  return 0
end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[4])
redis.call('DEL', KEYS[3])
return 1
"""

VERIFY = """
local digest = redis.call('GET', KEYS[1])
if not digest then return 0 end
if digest ~= ARGV[1] then
  local attempts = redis.call('INCR', KEYS[2])
  if attempts == 1 then
    redis.call('EXPIRE', KEYS[2], redis.call('TTL', KEYS[1]) + 1)
  end
  if attempts >= tonumber(ARGV[2]) then redis.call('DEL', KEYS[1], KEYS[2]) end
  return 0
end
redis.call('SET', KEYS[3], ARGV[3], 'EX', ARGV[4])
redis.call('DEL', KEYS[1], KEYS[2])
return 1
"""

CANCEL = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('DEL', KEYS[1], KEYS[2])
end
return 1
"""


def redis(*command):
    endpoint = (os.environ.get("KV_REST_API_URL")
                or os.environ["UPSTASH_REDIS_REST_URL"]).rstrip("/")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ["UPSTASH_REDIS_REST_TOKEN"]
    if not endpoint.startswith("https://"):
        raise ValueError("Redis endpoint must use HTTPS")
    request = Request(
        endpoint,
        data=json.dumps(command).encode(),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError("Partner access storage is unavailable")
    return payload["result"]


def normalize(email):
    return email.strip().lower()


def allowed(email):
    configured = os.environ.get("PARTNER_ALLOWED_EMAILS", "")
    return bool(email) and email in {normalize(item) for item in configured.split(",")}


def digest(value):
    key = os.environ["PARTNER_AUTH_SECRET"].encode()
    if len(key) < 32:
        raise RuntimeError("Invalid partner access secret")
    return hmac.digest(key, value.encode(), "sha256").hex()


def storage_keys(email):
    base = "castelo:partner:" + digest("email:" + email)
    return base + ":cooldown", base + ":code", base + ":attempts"


def request_code(email):
    """Send a code to an authorized address. Return no account status to callers."""
    email = normalize(email)
    if not allowed(email):
        return
    cooldown, code_key, attempts = storage_keys(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_digest = digest(f"code:{email}:{code}")
    if not redis("EVAL", ISSUE, 3, cooldown, code_key, attempts,
                 code_digest, code_digest, RESEND_DELAY, CODE_TTL):
        return
    try:
        send_access_code(email, code)
    except Exception:
        redis("EVAL", CANCEL, 2, cooldown, code_key, code_digest)
        raise


def session_key(token):
    return "castelo:session:" + hashlib.sha256(token.encode()).hexdigest()


def verify_code(email, code):
    """Consume the code and create a session in the same Redis operation."""
    email = normalize(email)
    if not allowed(email) or not re.fullmatch(r"[0-9]{6}", code):
        return None
    _, code_key, attempts = storage_keys(email)
    token = secrets.token_urlsafe(32)
    verified = redis("EVAL", VERIFY, 3, code_key, attempts, session_key(token),
                     digest(f"code:{email}:{code}"), MAX_ATTEMPTS, email, SESSION_TTL)
    return token if verified else None


def session_email(token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    email = redis("GET", session_key(token))
    return email if email and allowed(email) else None


def sign_out(token):
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        redis("DEL", session_key(token))
