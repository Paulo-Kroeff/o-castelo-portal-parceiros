"""Send a partner verification code after the caller authorizes the recipient."""

import os
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
        f"Seu código de acesso é {code}.\n\n"
        "Digite o código na página do Portal do Parceiro onde você o solicitou.\n"
        "Se você não solicitou este código, ignore esta mensagem.\n"
    )

    with smtplib.SMTP_SSL(
        SMTP_HOST, SMTP_PORT, timeout=8, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(SENDER, password)
        smtp.send_message(message, from_addr=SENDER, to_addrs=[recipient])
