"""Browser entry point for partner email verification."""

import html
import logging
import os
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from server.partner_access import SESSION_TTL, request_code, session_email, sign_out, verify_code

PATH = "/api/partner-login"
COOKIE = "__Host-castelo-partner"


class handler(BaseHTTPRequestHandler):
    def page(self, message="", email="", status=200, cookie=None, signed_in=False):
        fields = ""
        if not signed_in:
            escaped_email = html.escape(email, quote=True)
            fields = f"""
<form method="post" action="{PATH}">
<label>E-mail <input name="email" type="email" autocomplete="email"
required maxlength="254" value="{escaped_email}"></label>
<button name="action" value="send">Enviar código</button>
</form>
<form method="post" action="{PATH}">
<label>E-mail <input name="email" type="email" autocomplete="email"
required maxlength="254" value="{escaped_email}"></label>
<label>Código <input name="code" inputmode="numeric" autocomplete="one-time-code"
pattern="[0-9]{{6}}" maxlength="6" required></label>
<button name="action" value="verify">Entrar</button>
</form>"""
        fields += f"""
<form method="post" action="{PATH}">
<button name="action" value="{'logout' if signed_in else 'session'}">
{'Sair' if signed_in else 'Verificar sessão'}</button>
</form>"""
        body = f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Acesso ao Portal do Parceiro</title>
<main><h1>Acesso ao Portal do Parceiro</h1>
<p>{html.escape(message)}</p>{fields}<p><a href="/">Voltar ao portal</a></p>
</main></html>""".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.page()

    def do_POST(self):
        origin = os.environ.get("PARTNER_PORTAL_ORIGIN", "https://o-castelo-portal-parceiros.vercel.app")
        if self.headers.get("Origin") != origin:
            return self.page("Abra a página de acesso pelo endereço oficial do portal.", status=403)

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096 or self.headers.get_content_type() != "application/x-www-form-urlencoded":
                raise ValueError
            fields = parse_qs(self.rfile.read(length).decode(), max_num_fields=3)
            if any(len(values) != 1 for values in fields.values()):
                raise ValueError
            action = fields.get("action", [""])[0]
            email = fields.get("email", [""])[0].strip()
            code = fields.get("code", [""])[0].strip()
            if len(email) > 254 or len(code) > 6:
                raise ValueError
            cookies = SimpleCookie()
            cookies.load(self.headers.get("Cookie", ""))
            token = cookies[COOKIE].value if COOKIE in cookies else ""
        except (ValueError, CookieError):
            return self.page("Dados inválidos. Confira os campos e tente novamente.", status=400)

        try:
            if action == "send":
                request_code(email)
                return self.page("Se o e-mail tiver acesso, você receberá um código.", email)
            if action == "verify":
                token = verify_code(email, code)
                if token:
                    return self.page("Código validado. Sessão iniciada.", cookie=self.session_cookie(token, SESSION_TTL), signed_in=True)
                return self.page("Código inválido ou expirado. Confira o código ou solicite outro.", email, 401)
            if action == "session":
                if session_email(token):
                    return self.page("Sua sessão está ativa.", signed_in=True)
                return self.page("Entre com um código para iniciar uma sessão.", status=401)
            if action == "logout":
                sign_out(token)
                return self.page("Sessão encerrada.", cookie=self.session_cookie("", 0))
        except Exception as error:
            logging.error("Partner login operation failed: %s", type(error).__name__)
            return self.page("O acesso está temporariamente indisponível. Tente novamente.", status=503)
        self.page("Ação inválida.", status=400)

    @staticmethod
    def session_cookie(token, max_age):
        return f"{COOKIE}={token}; Path=/; Max-Age={max_age}; Secure; HttpOnly; SameSite=Lax"
