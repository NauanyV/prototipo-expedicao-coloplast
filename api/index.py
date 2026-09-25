from http.server import BaseHTTPRequestHandler
import json
import base64
import os
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse

API_KEY = os.environ.get("API_KEY")
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")


def send_json(handler, status, payload):
    data = json.dumps(
        payload,
        ensure_ascii=False,
        default=str
    ).encode("utf-8")

    handler.send_response(status)
    handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8"
    )
    handler.send_header(
        "Access-Control-Allow-Origin",
        "*"
    )
    handler.send_header(
        "Access-Control-Allow-Headers",
        "Content-Type, x-api-key"
    )
    handler.send_header(
        "Access-Control-Allow-Methods",
        "GET, POST, OPTIONS"
    )
    handler.send_header(
        "Content-Length",
        str(len(data))
    )
    handler.end_headers()

    if status != 204:
        handler.wfile.write(data)


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL nao configurada."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        send_json(self, 204, {})

    def _auth(self):
        return (
            API_KEY is not None
            and self.headers.get("x-api-key
