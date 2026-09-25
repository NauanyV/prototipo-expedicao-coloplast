from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import base64
import json
import os

import psycopg
from psycopg.rows import dict_row


API_KEY = os.environ.get("API_KEY")
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")


def send_json(request_handler, status_code, payload):
    content = json.dumps(
        payload,
        ensure_ascii=False,
        default=str
    ).encode("utf-8")

    request_handler.send_response(status_code)

    request_handler.send_header(
        "Content-Type",
        "application/json; charset=utf-8"
    )

    request_handler.send_header(
        "Access-Control-Allow-Origin",
        "*"
    )

    request_handler.send_header(
        "Access-Control-Allow-Headers",
        "Content-Type, x-api-key"
    )

    request_handler.send_header(
        "Access-Control-Allow-Methods",
        "GET, POST, OPTIONS"
    )

    request_handler.send_header(
        "Cache-Control",
        "no-store, no-cache, must-revalidate"
    )

    request_handler.send_header(
        "Content-Length",
        str(len(content))
    )

    request_handler.end_headers()

    if status_code != 204:
        request_handler.wfile.write(content)


def get_database_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "NEON_DATABASE_URL não configurada no Vercel."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


def get_query_parameters(request_handler):
    parsed_url = urlparse(request_handler.path)
    query = parse_qs(parsed_url.query)

    route = query.get("rota", [""])[0]
    load_id = query.get("id", [""])[0]

    return route, load_id


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        send_json(self, 204, {})

    def is_authorized(self):
        received_key = self.headers.get("x-api-key")

        return (
            API_KEY is not None
            and received_key == API_KEY
        )

    def do_GET(self):
        if not self.is_authorized():
            return send_json(
                self,
                401,
                {
                    "erro": "API key inválida."
                }
            )

        route, load_id = get_query_parameters(self)

        if route == "":
            return
