"""Send a partner verification code after the caller authorizes the recipient."""

import os
import hmac
import secrets
import time
from http.server import BaseHTTPRequestHandler
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "mail.ocastelomedieval.com.br"
SMTP_PORT = 465
SENDER = "parceria@ocastelomedieval.com.br"


def send_access_code(recipient: str, code: str) -> None:
    """Send through the Castelo mail server and raise on delivery submission failure."""
    password = os.environ.get("SMTP_PASSWORD")
    if not password:
        raise RuntimeError("SMTP_PASSWORD is not configured")

    message = EmailMessage()
    message["From"] = f"Portal do Parceiro de O Castelo <{SENDER}>"
    message["To"] = recipient
    message["Subject"] = "Seu código de acesso ao Portal do Parceiro"
    message.set_content(
        f"Seu código de teste é {code}.\n\n"
        "Este teste verifica o envio automático pelo Portal do Parceiro. O código não libera materiais.\n"
        "Se você não solicitou este código, ignore esta mensagem.\n"
    )

    with smtplib.SMTP_SSL(
        SMTP_HOST, SMTP_PORT, timeout=8, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(SENDER, password)
        smtp.send_message(message, from_addr=SENDER, to_addrs=[recipient])


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        token = os.environ.get("PARTNER_MAIL_TEST_TOKEN", "")
        recipient = os.environ.get("PARTNER_MAIL_TEST_RECIPIENT", "")
        authorization = self.headers.get("Authorization", "").encode()
        expected = f"Bearer {token}".encode()
        expires, _, nonce = token.partition(".")
        if (
            not recipient or not nonce or not expires.isascii() or not expires.isdecimal()
            or int(expires) <= time.time() or not hmac.compare_digest(authorization, expected)
        ):
            self.respond(404)
            return

        try:
            send_access_code(recipient, f"{secrets.randbelow(1_000_000):06d}")
        except (OSError, smtplib.SMTPException, RuntimeError):
            self.respond(502)
            return
        self.respond(204)

    def respond(self, status):
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
