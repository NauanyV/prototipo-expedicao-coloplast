from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import base64
import json
import os

import psycopg
from psycopg.rows import dict_row


API_KEY = os.environ.get("API_KEY")
DATABASE_URL = os.environ.get("NEON_DATABASE_URL")

MAXIMUM_FILE_SIZE = 20971520


def send_json(request_handler, status_code, payload):
    response_content = json.dumps(
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
        str(len(response_content))
    )

    request_handler.end_headers()

    if status_code != 204:
        request_handler.wfile.write(response_content)


def get_database_connection():
    if not DATABASE_URL:
        raise RuntimeError(
            "NEON_DATABASE_URL nao configurada no Vercel."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10
    )


def get_request_parameters(request_handler):
    parsed_url = urlparse(request_handler.path)
    query_parameters = parse_qs(parsed_url.query)

    route = query_parameters.get(
        "rota",
        [""]
    )[0]

    load_id = query_parameters.get(
        "id",
        [""]
    )[0]

    return route.strip(), load_id.strip()


def decode_document_base64(base64_content):
    clean_content = str(
        base64_content or ""
    ).strip()

    if "," in clean_content:
        clean_content = clean_content.split(
            ",",
            1
        )[1]

    return base64.b64decode(
        clean_content,
        validate=True
    )


class handler(BaseHTTPRequestHandler):

    def log_message(self, format_text, *args):
        return

    def do_OPTIONS(self):
        send_json(
            self,
            204,
            {}
        )

    def is_authorized(self):
        received_key = self.headers.get(
            "x-api-key"
        )

        if not API_KEY:
            return False

        return received_key == API_KEY

    def require_authorization(self):
        if self.is_authorized():
            return True

        send_json(
            self,
            401,
            {
                "erro": "API key invalida."
            }
        )

        return False

    def do_GET(self):
        if not self.require_authorization():
            return

        try:
            route, load_id = get_request_parameters(
                self
            )

            if route == "":
                self.get_api_information()
                return

            if route == "cargas":
                self.list_loads()
                return

            if route == "carga":
                self.get_load(load_id)
                return

            if route == "documento":
                self.get_document(load_id)
                return

            send_json(
                self,
                404,
                {
                    "erro": "Rota nao encontrada.",
                    "rota": route
                }
            )

        except Exception as error:
            print(
                "GET ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro interno da API.",
                    "detalhe": str(error)
                }
            )

    def get_api_information(self):
        send_json(
            self,
            200,
            {
                "api": "Prototipo Analytics Coloplast",
                "status": "online",
                "database": "Neon PostgreSQL",
                "routes": [
                    "GET /api?rota=cargas",
                    "GET /api?rota=carga&id=141501",
                    "GET /api?rota=documento&id=141501",
                    "POST /api?rota=documentos"
                ]
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
                                    AND documento_base64 != ''
                                THEN TRUE
                                ELSE FALSE
                            END AS possui_documento,
                            data_atualizacao
                        FROM cargas
                        ORDER BY id_carga
                        """
                    )

                    loads = cursor.fetchall()

            send_json(
                self,
                200,
                {
                    "cargas": loads
                }
            )

        except Exception as error:
            print(
                "LIST LOADS ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar o banco.",
                    "detalhe": str(error)
                }
            )

    def get_load(self, load_id):
        if not load_id:
            send_json(
                self,
                400,
                {
                    "erro": "ID da carga nao informado."
                }
            )
            return

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
                                    AND documento_base64 != ''
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
                send_json(
                    self,
                    404,
                    {
                        "erro": "Carga nao encontrada.",
                        "id_carga": load_id
                    }
                )
                return

            send_json(
                self,
                200,
                load
            )

        except Exception as error:
            print(
                "GET LOAD ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar a carga.",
                    "detalhe": str(error)
                }
            )

    def get_document(self, load_id):
        if not load_id:
            send_json(
                self,
                400,
                {
                    "erro": "ID da carga nao informado."
                }
            )
            return

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
                send_json(
                    self,
                    404,
                    {
                        "erro": "Carga nao encontrada.",
                        "id_carga": load_id
                    }
                )
                return

            document_base64 = document[
                "documento_base64"
            ]

            if not document_base64:
                send_json(
                    self,
                    404,
                    {
                        "erro": "A carga nao possui documento salvo.",
                        "id_carga": load_id
                    }
                )
                return

            send_json(
                self,
                200,
                {
                    "id_carga": document[
                        "id_carga"
                    ],
                    "documento_nome": (
                        document["documento_nome"]
                        or "documento"
                    ),
                    "documento_tipo": (
                        document["documento_tipo"]
                        or "application/octet-stream"
                    ),
                    "documento_base64": document_base64
                }
            )

        except Exception as error:
            print(
                "GET DOCUMENT ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro ao consultar o documento.",
                    "detalhe": str(error)
                }
            )

    def do_POST(self):
        if not self.require_authorization():
            return

        try:
            route, unused_load_id = (
                get_request_parameters(self)
            )

            if route != "documentos":
                send_json(
                    self,
                    404,
                    {
                        "erro": "Rota nao encontrada.",
                        "rota": route
                    }
                )
                return

            self.save_document()

        except Exception as error:
            print(
                "POST ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro interno da API.",
                    "detalhe": str(error)
                }
            )

    def read_request_json(self):
        content_length_text = self.headers.get(
            "Content-Length",
            "0"
        )

        content_length = int(
            content_length_text
        )

        if content_length <= 0:
            raise ValueError(
                "Corpo da requisicao vazio."
            )

        request_body = self.rfile.read(
            content_length
        )

        return json.loads(
            request_body.decode("utf-8")
        )

    def save_document(self):
        try:
            payload = self.read_request_json()

        except ValueError as error:
            send_json(
                self,
                400,
                {
                    "erro": str(error)
                }
            )
            return

        except Exception as error:
            send_json(
                self,
                400,
                {
                    "erro": "JSON invalido.",
                    "detalhe": str(error)
                }
            )
            return

        client = str(
            payload.get(
                "cliente",
                ""
            )
        ).strip()

        invoice = str(
            payload.get(
                "nf",
                ""
            )
        ).strip()

        load_id = str(
            payload.get(
                "id_carga",
                ""
            )
        ).strip()

        document = payload.get(
            "documento"
        ) or {}

        document_name = str(
            document.get(
                "nome",
                ""
            )
        ).strip()

        document_type = str(
            document.get(
                "tipo",
                ""
            )
        ).strip()

        document_base64 = str(
            document.get(
                "conteudo_base64",
                ""
            )
        ).strip()

        if not document_type:
            document_type = (
                "application/octet-stream"
            )

        missing_fields = []

        if not client:
            missing_fields.append(
                "cliente"
            )

        if not invoice:
            missing_fields.append(
                "nf"
            )

        if not load_id:
            missing_fields.append(
                "id_carga"
            )

        if not document_name:
            missing_fields.append(
                "documento.nome"
            )

        if not document_base64:
            missing_fields.append(
                "documento.conteudo_base64"
            )

        if missing_fields:
            send_json(
                self,
                400,
                {
                    "erro": "Campos obrigatorios ausentes.",
                    "campos": missing_fields
                }
            )
            return

        try:
            document_bytes = decode_document_base64(
                document_base64
            )

        except Exception as error:
            send_json(
                self,
                400,
                {
                    "erro": "Arquivo Base64 invalido.",
                    "detalhe": str(error)
                }
            )
            return

        if len(document_bytes) == 0:
            send_json(
                self,
                400,
                {
                    "erro": "O arquivo recebido esta vazio."
                }
            )
            return

        if len(document_bytes) > MAXIMUM_FILE_SIZE:
            send_json(
                self,
                413,
                {
                    "erro": "Arquivo acima do limite de 20 MB."
                }
            )
            return

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
                        send_json(
                            self,
                            404,
                            {
                                "erro": "ID da carga nao encontrado.",
                                "id_carga": load_id
                            }
                        )
                        return

                    expected_client = str(
                        load["cliente"]
                    ).strip()

                    expected_invoice = str(
                        load["nf"]
                    ).strip()

                    if (
                        expected_client.lower()
                        != client.lower()
                    ):
                        send_json(
                            self,
                            409,
                            {
                                "erro": (
                                    "Cliente nao corresponde a carga."
                                ),
                                "esperado": expected_client,
                                "recebido": client
                            }
                        )
                        return

                    if expected_invoice != invoice:
                        send_json(
                            self,
                            409,
                            {
                                "erro": (
                                    "Numero da NF nao corresponde a carga."
                                ),
                                "esperado": expected_invoice,
                                "recebido": invoice
                            }
                        )
                        return

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
                            documento_nome,
                            documento_tipo,
                            TRUE AS possui_documento,
                            data_atualizacao
                        """,
                        (
                            document_name,
                            document_type,
                            document_base64,
                            load_id
                        )
                    )

                    updated_load = cursor.fetchone()

                connection.commit()

            send_json(
                self,
                200,
                {
                    "sucesso": True,
                    "mensagem": (
                        "Documento integrado com sucesso."
                    ),
                    "documento": {
                        "nome": document_name,
                        "tipo": document_type,
                        "tamanho": len(
                            document_bytes
                        )
                    },
                    "carga": updated_load
                }
            )

        except Exception as error:
            print(
                "SAVE DOCUMENT ERROR:",
                repr(error)
            )

            send_json(
                self,
                500,
                {
                    "erro": "Erro ao atualizar a carga.",
                    "detalhe": str(error)
                }
            )
