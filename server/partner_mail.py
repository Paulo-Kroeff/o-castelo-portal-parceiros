"""Send a partner verification code after the caller authorizes the recipient."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from html import escape

SMTP_HOST = "mail.ocastelomedieval.com.br"
SMTP_PORT = 465
SENDER = "parceria@ocastelomedieval.com.br"
PORTAL = "https://o-castelo-portal-parceiros.vercel.app"


def access_message(recipient: str, code: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"Portal do Parceiro de O Castelo <{SENDER}>"
    message["To"] = recipient
    message["Subject"] = "O Castelo | Seu código de acesso"
    message.set_content(
        f"O Castelo · Portal do Parceiro\n\nSeu código de acesso é {code}.\n\n"
        f"Digite o código em {PORTAL}/api/partner-login?step=code. Ele vale por 10 minutos.\n\n"
        "Se você não solicitou este código, ignore esta mensagem.\n"
        "O Castelo · São Roque, SP | https://ocastelomedieval.com.br\n"
    )
    message.add_alternative(f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;background:#f5f2eb;color:#102735;font-family:Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#f5f2eb">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"
style="max-width:540px;border:1px solid #ddd5c5">
<tr><td align="center" bgcolor="#102735" style="padding:24px 16px;border-bottom:3px solid #cba661">
<img src="{PORTAL}/assets/icon-192.png" width="60" height="60" alt=""
style="display:block;margin:0 auto 10px">
<p style="margin:0;color:#fff;font:30px Georgia,serif">O Castelo</p>
<p style="margin:7px 0 0;color:#efce96;font-size:11px;letter-spacing:2px">PORTAL DO PARCEIRO</p>
</td></tr>
<tr><td align="center" bgcolor="#ffffff" style="padding:30px 22px">
<h1 style="margin:0 0 12px;font:28px Georgia,serif;color:#102735">Seu código de acesso</h1>
<p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#344b57">
Digite este código na tela de acesso do portal. Ele vale por 10 minutos.</p>
<table role="presentation" cellspacing="0" cellpadding="0" align="center">
<tr><td align="center" bgcolor="#f5f2eb"
style="padding:13px 16px;border:1px solid #cba661;color:#102735;font:bold 27px monospace;letter-spacing:5px">
{escape(code)}</td></tr></table>
<p style="margin:22px 0 0">
<a href="{PORTAL}/api/partner-login?step=code" style="color:#102735;font-size:14px">Abrir o Portal do Parceiro</a></p>
</td></tr>
<tr><td align="center" style="padding:17px;color:#435661;font-size:12px;line-height:1.6">
Se você não solicitou este código, ignore esta mensagem.<br>
<a href="https://ocastelomedieval.com.br/" style="color:#435661">O Castelo · São Roque, SP</a>
</td></tr></table>
</td></tr></table>
</body></html>""", subtype="html")
    return message


def send_access_code(recipient: str, code: str) -> None:
    """Send through the Castelo mail server and raise on delivery submission failure."""
    password = os.environ.get("SMTP_PASSWORD")
    if not password:
        raise RuntimeError("SMTP_PASSWORD is not configured")

    message = access_message(recipient, code)
    with smtplib.SMTP_SSL(
        SMTP_HOST, SMTP_PORT, timeout=8, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(SENDER, password)
        smtp.send_message(message, from_addr=SENDER, to_addrs=[recipient])
