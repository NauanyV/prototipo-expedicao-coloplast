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
        return send_json(
            self,
            204,
            {}
        )

    def is_authorized(self):
        received_key = self.headers.get("x-api-key")

        return (
            API_KEY is not None
            and received_key == API_KEY
        )

    def do_GET(self):
        try:
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
                return send_json(
                    self,
                    200,
                    {
                        "api": "Protótipo Analytics Coloplast",
                        "status": "online",
                        "banco": "Neon PostgreSQL",
                        "rotas": [
                            "GET /api?rota=cargas",
                            "GET /api?rota=carga&id=141501",
                            "GET /api?rota=documento&id=141501",
                            "POST /api?rota=documentos"
                        ]
                    }
                )

            if route == "cargas":
                return self.list_loads()

            if route == "carga":
                return self.get_load(load_id)

            if route == "documento":
                return self.get_document(load_id)

            return send_json(
                self,
                404,
                {
                    "erro": "Rota não encontrada.",
                    "rota": route
                }
            )

        except Exception as error:
            print(
                "Erro geral no GET:",
                repr(error)
            )

            return send_json(
                self,
                500,
                {
                    "erro": "Erro interno da API.",
                    "detalhe": str(error)
                }
            )

    def list_loads(self):
        try:
            with get_database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id_carga,
                            cliente,
                            nf,
                            status,
                            documento_nome,
                            documento_tipo,
                            CASE
                                WHEN documento_base64 IS NOT NULL
                                     AND documento_base64 <> ''
                                THEN TRUE
                                ELSE FALSE
                            END AS possui_documento,
                            data_atualizacao
                        FROM cargas
                        ORDER BY id_carga
                        """
                    )

                    loads = cursor.fetchall()

            return send_json(
                self,
                200,
                {
                    "cargas": loads
                }
            )

        except Exception as error:
            print(
                "Erro ao listar cargas:",
                repr(error)
            )

            return send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar o banco.",
                    "detalhe": str(error)
                }
            )

    def get_load(self, load_id):
        if not load_id:
            return send_json(
                self,
                400,
                {
                    "erro": "ID da carga não informado."
                }
            )

        try:
            with get_database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id_carga,
                            cliente,
                            nf,
                            status,
                            documento_nome,
                            documento_tipo,
                            CASE
                                WHEN documento_base64 IS NOT NULL
                                     AND documento_base64 <> ''
                                THEN TRUE
                                ELSE FALSE
                            END AS possui_documento,
                            data_atualizacao
                        FROM cargas
                        WHERE id_carga = %s
                        """,
                        (load_id,)
                    )

                    load = cursor.fetchone()

            if not load:
                return send_json(
                    self,
                    404,
                    {
                        "erro": "Carga não encontrada.",
                        "id_carga": load_id
                    }
                )

            return send_json(
                self,
                200,
                load
            )

        except Exception as error:
            print(
                "Erro ao consultar carga:",
                repr(error)
            )

            return send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar o banco.",
                    "detalhe": str(error)
                }
            )

    def get_document(self, load_id):
        if not load_id:
            return send_json(
                self,
                400,
                {
                    "erro": "ID da carga não informado."
                }
            )

        try:
            with get_database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id_carga,
                            documento_nome,
                            documento_tipo,
                            documento_base64
                        FROM cargas
                        WHERE id_carga = %s
                        """,
                        (load_id,)
                    )

                    document = cursor.fetchone()

            if not document:
                return send_json(
                    self,
                    404,
                    {
                        "erro": "Carga não encontrada.",
                        "id_carga": load_id
                    }
                )

            if not document["documento_base64"]:
                return send_json(
                    self,
                    404,
                    {
                        "erro": "A carga não possui documento salvo.",
                        "id_carga": load_id
                    }
                )

            return send_json(
                self,
                200,
                {
                    "id_carga": document["id_carga"],
                    "documento_nome": document["documento_nome"],
                    "documento_tipo": (
                        document["documento_tipo"]
                        or "application/octet-stream"
                    ),
                    "documento_base64": document["documento_base64"]
                }
            )

        except Exception as error:
            print(
                "Erro ao consultar documento:",
                repr(error)
            )

            return send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar o documento.",
                    "detalhe": str(error)
                }
            )

    def do_POST(self):
        try:
            if not self.is_authorized():
                return send_json(
                    self,
                    401,
                    {
                        "erro": "API key inválida."
                    }
                )

            route, _ = get_query_parameters(self)

            if route != "documentos":
                return send_json(
                    self,
                    404,
                    {
                        "erro": "Rota não encontrada.",
                        "rota": route
                    }
                )

            return self.save_document()

        except Exception as error:
            print(
                "Erro geral no POST:",
                repr(error)
            )

            return send_json(
                self,
                500,
                {
                    "erro": "Erro interno da API.",
                    "detalhe": str(error)
                }
            )

    def save_document(self):
        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            if content_length <= 0:
                return send_json(
                    self,
                    400,
                    {
                        "erro": "Corpo da requisição vazio."
                    }
                )

            body = self.rfile.read(content_length)

            payload = json.loads(
                body.decode("utf-8")
            )

        except Exception as error:
            return send_json(
                self,
                400,
                {
                    "erro": "JSON inválido.",
                    "detalhe": str(error)
                }
            )

        client = str(
            payload.get("cliente", "")
        ).strip()

        invoice = str(
            payload.get("nf", "")
        ).strip()

        load_id = str(
            payload.get("id_carga", "")
        ).strip()

        document = payload.get("documento") or {}

        document_name = str(
            document.get("nome", "")
        ).strip()

        document_type = str(
            document.get("tipo", "")
        ).strip()

        document_base64 = str(
            document.get("conteudo_base64", "")
        ).strip()

        if not document_type:
            document_type = "application/octet-stream"

        if (
            not client
            or not invoice
            or not load_id
            or not document_name
            or not document_base64
        ):
            return send_json(
                self,
                400,
                {
                    "erro": "Campos obrigatórios ausentes.",
                    "campos_obrigatorios": [
                        "cliente",
                        "nf",
                        "id_carga",
                        "documento.nome",
                        "documento.conteudo_base64"
                    ]
                }
            )

        try:
            document_bytes = base64.b64decode(
                document_base64
            )

        except Exception as error:
            return send_json(
                self,
                400,
                {
                    "erro": "Arquivo Base64 inválido.",
                    "detalhe": str(error)
                }
            )

        if not document_bytes:
            return send_json(
                self,
                400,
                {
                    "erro": "O arquivo recebido está vazio."
                }
            )

        maximum_size = 20 * 1024 * 1024

        if len(document_bytes) > maximum_size:
            return send_json(
                self,
                413,
                {
                    "erro": "Arquivo acima do limite de 20 MB."
                }
            )

        try:
            with get_database_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id_carga,
                            cliente,
                            nf,
                            status
                        FROM cargas
                        WHERE id_carga = %s
                        """,
                        (load_id,)
                    )

                    load = cursor.fetchone()

                    if not load:
                        return send_json(
                            self,
                            404,
                            {
                                "erro": "ID da carga não encontrado.",
                                "id_carga": load_id
                            }
                        )

                    expected_client = str(
                        load["cliente"]
                    ).strip()

                    expected_invoice = str(
                        load["nf"]
                    ).strip()

                    if expected_client.lower() != client.lower():
                        return send_json(
                            self,
                            409,
                            {
                                "erro": (
                                    "Cliente não corresponde à carga."
                                ),
                                "esperado": expected_client,
                                "recebido": client
                            }
                        )

                    if expected_invoice != invoice:
                        return send_json(
                            self,
                            409,
                            {
                                "erro": (
                                    "Número da NF não corresponde à carga."
                                ),
                                "esperado": expected_invoice,
                                "recebido": invoice
                            }
                        )

                    cursor.execute(
                        """
                        UPDATE cargas
                        SET
                            status = 'EXPEDIDA',
                            documento_nome = %s,
                            documento_tipo = %s,
                            documento_base64 = %s,
                            data_atualizacao = CURRENT_TIMESTAMP
                        WHERE id_carga = %s
                        RETURNING
                            id_carga,
                            cliente,
                            nf,
                            status,
