"""Browser entry point for partner email verification."""

import html
import logging
import os
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit

from server.partner_access import SESSION_TTL, request_code, session_email, sign_out, verify_code

PATH = "/api/partner-login"
COOKIE = "__Host-castelo-partner"


class handler(BaseHTTPRequestHandler):
    def session_response(self, status, token=None, location=None):
        self.send_response(status)
        self.send_header("Cache-Control", "private, no-store")
        if token:
            self.send_header("Set-Cookie", self.session_cookie(token, SESSION_TTL))
        if location:
            self.send_header("Location", location)
        self.end_headers()

    def page(self, message="", email="", status=200, cookie=None, signed_in=False, code_step=False):
        escaped_email = html.escape(email, quote=True)
        email_field = f"""<label for="partner-email">E-mail da agência</label>
<input id="partner-email" name="email" type="email" autocomplete="email"
required maxlength="254" value="{escaped_email}">"""
        heading = "Acesse o portal"
        description = "Informe o e-mail cadastrado para receber seu código de acesso."
        form = f"""{email_field}
<button class="button gold" name="action" value="send">Enviar código</button>"""
        secondary = f"""<a class="text-link" href="{PATH}?step=code">Já tenho um código</a>
"""
        if code_step:
            heading = "Confirme seu e-mail"
            description = "Use o código de seis dígitos que você recebeu por e-mail."
            identity_field = f'<input type="hidden" name="email" value="{escaped_email}">' if email else email_field
            form = f"""{identity_field}
<label for="partner-code">Código de acesso</label>
<input id="partner-code" class="partner-code" name="code" inputmode="numeric"
autocomplete="one-time-code" pattern="[0-9]{{6}}" maxlength="6" required>
<button class="button gold" name="action" value="verify">Entrar</button>
<button class="text-link partner-link" name="action" value="send" formnovalidate>Reenviar código</button>"""
            secondary = f'<a class="text-link" href="{PATH}">Usar outro e-mail</a>'
        if signed_in:
            heading = "Acesso confirmado"
            description = ""
            secondary = ""
            form = f"""<a class="button gold" href="/#inicio">Ir ao portal</a>
<button class="text-link partner-link" name="action" value="logout">Sair</button>"""
        contact = "" if signed_in else """<p class="partner-description partner-contact">
Entre em contato com a equipe de parceria para saber como tornar sua agência parceira de O Castelo.
<a class="text-link" href="mailto:parceria@ocastelomedieval.com.br?subject=Solicita%C3%A7%C3%A3o%20de%20acesso%20ao%20Portal%20do%20Parceiro">parceria@ocastelomedieval.com.br</a></p>"""
        status_message = (
            f'<p class="partner-status" role="{("alert" if status >= 400 else "status")}">'
            f'{html.escape(message)}</p>' if message else ""
        )
        body = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#102735">
<title>Acesso ao Portal do Parceiro · O Castelo</title>
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/assets/icon-192.png">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/partner-login.css">
</head>
<body class="partner-page">
<header class="partner-header">
<div class="brand">
<img src="/assets/12Fw7rfB6u47WnVpw5K6mamMKQyNY7wfW.svg" alt="O Castelo">
<span>PORTAL DO PARCEIRO</span>
</div>
</header>
<main class="partner-layout">
<div class="partner-photo" aria-hidden="true"></div>
<section class="partner-card" aria-labelledby="partner-heading">
<h1 id="partner-heading">{heading}</h1>
{f'<p class="partner-description">{html.escape(description)}</p>' if description else ""}
{status_message}
<form class="partner-form" method="post" action="{PATH}">{form}</form>
{secondary}
{contact}
</section>
</main>
<footer class="partner-footer">O Castelo · São Roque, SP</footer>
</body>
</html>""".encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'self'; img-src 'self'; manifest-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        query = urlsplit(self.path).query
        if query != "step=code":
            try:
                token = self.read_session_cookie()
                if session_email(token, renew=True):
                    if query == "entry=invite":
                        return self.session_response(303, token, "/#inicio")
                    return self.page("Sua sessão está ativa.",
                                     cookie=self.session_cookie(token, SESSION_TTL), signed_in=True)
            except (ValueError, CookieError):
                pass
            except Exception as error:
                logging.error("Partner session check failed: %s", type(error).__name__)
                return self.page("O acesso está temporariamente indisponível. Tente novamente.", status=503)
        self.page(code_step=query == "step=code")

    def read_session_cookie(self):
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        return cookies[COOKIE].value if COOKIE in cookies else ""

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
            token = self.read_session_cookie()
        except (ValueError, CookieError):
            return self.page("Dados inválidos. Confira os campos e tente novamente.", status=400)

        try:
            if action == "send":
                outcome = request_code(email)
                if outcome == "unregistered":
                    return self.page("Seu e-mail não está cadastrado. Você ainda não tem acesso.",
                                     email, status=403)
                message = ("Enviamos um código para o seu e-mail. Ele vale por 10 minutos."
                           if outcome == "sent" else
                           "Já recebemos um pedido de código para este e-mail. Aguarde um minuto para pedir outro.")
                return self.page(message, email, code_step=True)
            if action == "verify":
                token = verify_code(email, code)
                if token:
                    return self.session_response(303, token, "/#inicio")
                return self.page("Código inválido ou expirado. Confira o código ou solicite outro.",
                                 email, status=401, code_step=True)
            if action == "session":
                if session_email(token, renew=True):
                    return self.session_response(204, token)
                return self.session_response(401)
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
