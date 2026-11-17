"""Serve the partner portal only after validating its server-side session."""

import logging
import mimetypes
import re
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from server.partner_access import session_email

ROOT = (Path(__file__).resolve().parent.parent / "dist").resolve()
COOKIE = "__Host-castelo-partner"
PRIVATE_FILES = {"index.html", "app.js", "data.js", "guide.js"}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.serve(include_body=True)

    def do_HEAD(self):
        self.serve(include_body=False)

    def serve(self, *, include_body):
        args = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
        paths = args.get("file", [])
        if len(paths) != 1:
            return self.respond(404)
        relative = paths[0]
        if relative not in PRIVATE_FILES and not re.fullmatch(
            r"assets/(?:[\w-]+/)*[\w.-]+\.(?:webp|jpg|jpeg|png|svg|gif|avif|ico)", relative, re.ASCII
        ):
            return self.respond(404)

        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookies[COOKIE].value if COOKIE in cookies else ""
        except CookieError:
            token = ""

        try:
            allowed_email = session_email(token)
        except Exception as error:
            logging.error("Partner portal session check failed: %s", type(error).__name__)
            return self.respond(503)
        if not allowed_email:
            if relative == "index.html":
                return self.respond(302, location="/api/partner-login?entry=invite")
            return self.respond(401)

        file = (ROOT / relative).resolve()
        if not file.is_relative_to(ROOT) or not file.is_file():
            return self.respond(404)
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if mime.startswith("text/"):
            mime += "; charset=utf-8"
        self.respond(200, mime=mime, length=file.stat().st_size)
        if include_body:
            with file.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    self.wfile.write(chunk)

    def respond(self, status, *, location=None, mime=None, length=0):
        self.send_response(status)
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(length))
        if location:
            self.send_header("Location", location)
        if mime:
            self.send_header("Content-Type", mime)
        self.end_headers()
