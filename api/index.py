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

    request_handle*.send_header(
        "Access-Cont*ol-Allow-Headers",
        "Conten*-Type, x-api-key"
    )

    reque*t_handler.send_header(
        "Ac*ess-Control-Allow-Methods",
      * "GET, POST, OPTIONS"
    )

    r*quest_handler.send_header(
       *"Cache-Control",
        "no-store* no-cache, must-revalidate"
    )
*    request_handler.send_header(
 *      "Content-Length",
        st*(len(response_content))
    )

   *request_handler.end_headers()

   *if status_code != 204:
        req*est_handler.wfile.write(response_c*ntent)


def get_database_connecti*n():
    if not DATABASE_URL:
    *   raise RuntimeError(
           *"NEON_DATABASE_URL nao configurada*no Vercel."
        )

    return *sycopg.connect(
        DATABASE_U*L,
        row_factory=dict_row,
 *      connect_timeout=10
    )


d*f get_request_parameters(request_h*ndler):
    parsed_url = urlparse(*equest_handler.path)
    query_par*meters = parse_qs(parsed_url.query*

    route = query_parameters.get*
        "rota",
        [""]
    *[0]

    load_id = query_parameter*.get(
        "id",
        [""]
 *  )[0]

    return route.strip(), *oad_id.strip()


def decode_docume*t_base64(base64_content):
    clea*_content = str(
        base64_con*ent or ""
    ).strip()

    if ",* in clean_content:
        clean_c*ntent = clean_content.split(
     *      ",",
            1
        )*1]

    return base64.b64decode(
 *      clean_content,
        valid*te=True
    )


class handler(Base*TTPRequestHandler):

    def log_m*ssage(self, format_text, *args):
 *      return

    def do_OPTIONS(s*lf):
        send_json(
          * self,
            204,
          * {}
        )

    def is_authoriz*d(self):
        received_key = se*f.headers.get(
            "x-api-*ey"
        )

        if not API_*EY:
            return False

    *   return received_key == API_KEY
*    def require_authorization(self*:
        if self.is_authorized():*            return True

        s*nd_json(
            self,
       *    401,
            {
           *    "erro": "API key invalida."
  *         }
        )

        retu*n False

    def do_GET(self):
   *    if not self.require_authorizat*on():
            return

        *ry:
            route, load_id = g*t_request_parameters(
            *   self
            )

           *if route == "":
                se*f.get_api_information()
          *     return

            if route *= "cargas":
                self.l*st_loads()
                return
*            if route == "carga":
 *              self.get_load(load_i*)
                return

        *   if route == "documento":
      *         self.get_document(load_id*
                return

         *  send_json(
                self,*                404,
             *  {
                    "erro": "R*ta nao encontrada.",
             *      "rota": route
              * }
            )

        except E*ception as error:
            prin*(
                "GET ERROR:",
  *             repr(error)
         *  )

            send_json(
      *         self,
                500*
                {
               *    "erro": "Erro interno da API."*
                    "detalhe": st*(error)
                }
        *   )

    def get_api_information(*elf):
        send_json(
         *  self,
            200,
         *  {
                "api": "Protot*po Analytics Coloplast",
         *      "status": "online",
        *       "database": "Neon PostgreSQ*",
                "routes": [
                    "GET /api?rota=cargas",
                    "GET /api?rota=carga&id=141501",
                    "GET /api?rota=documento&id=141501",
                    "POST /api?rota=documentos"
                ]
            }
        )

   *def list_loads(self):
        try:*            with get_database_conn*ction() as connection:
           *    with connection.cursor() as cu*sor:
                    cursor.ex*cute(
                        """
*                       SELECT
    *                       id_carga,
 *                          cliente,*                            nf,
  *                         status,
 *                          document*_nome,
                           *documento_tipo,
                  *         CASE
                    *           WHEN documento_base64 I* NOT NULL
                        *        AND documento_base64 != ''*                                TH*N TRUE
                           *    ELSE FALSE
                   *        END AS possui_documento,
 *                          data_atu*lizacao
                        FR*M cargas
                        O*DER BY id_carga
                  *     """
                    )

  *                 loads = cursor.fe*chall()

            send_json(
  *             self,
               *200,
                {
           *        "cargas": loads
          *     }
            )

        exce*t Exception as error:
            *rint(
                "LIST LOADS *RROR:",
                repr(error*
            )

            send_j*on(
                self,
        *       500,
                {
    *               "erro": "Erro ao co*sultar o banco.",
                *   "detalhe": str(error)
         *      }
            )

    def get*load(self, load_id):
        if no* load_id:
            send_json(
 *              self,
              * 400,
                {
          *         "erro": "ID da carga nao *nformado."
                }
     *      )
            return

      * try:
            with get_databas*_connection() as connection:
     *          with connection.cursor()*as cursor:
                    cur*or.execute(
                      * """
                        SELEC*
                            id_ca*ga,
                            cl*ente,
                            *f,
                            sta*us,
                            do*umento_nome,
                     *      documento_tipo,
            *               CASE
              *                 WHEN documento_ba*e64 IS NOT NULL
                  *              AND documento_base64*!= ''
                            *   THEN TRUE
                     *          ELSE FALSE
             *              END AS possui_docume*to,
                            da*a_atualizacao
                    *   FROM cargas
                   *    WHERE id_carga = %s
          *             """,
                *       (load_id,)
                *   )

                    load = c*rsor.fetchone()

            if no* load:
                send_json(
*                   self,
         *          404,
                   *{
                        "erro": *Carga nao encontrada.",
          *             "id_carga": load_id
 *                  }
              * )
                return

       *    send_json(
                sel*,
                200,
           *    load
            )

        ex*ept Exception as error:
          * print(
                "GET LOAD *RROR:",
                repr(error*
            )

            send_j*on(
                self,
        *       500,
                {
    *               "erro": "Erro ao co*sultar a carga.",
                *   "detalhe": str(error)
         *      }
            )

    def get*document(self, load_id):
        i* not load_id:
            send_jso*(
                self,
          *     400,
                {
      *             "erro": "ID da carga *ao informado."
                }
 *          )
            return

  *     try:
            with get_dat*base_connection() as connection:
 *              with connection.curs*r() as cursor:
                   *cursor.execute(
                  *     """
                        S*LECT
                            i*_carga,
                          * documento_nome,
                 *          documento_tipo,
        *                   documento_base6*
                        FROM carg*s
                        WHERE id*carga = %s
                       *""",
                        (load*id,)
                    )

      *             document = cursor.fet*hone()

            if not documen*:
                send_json(
     *              self,
              *     404,
                    {
  *                     "erro": "Carg* nao encontrada.",
               *        "id_carga": load_id
      *             }
                )
 *              return

            *ocument_base64 = document[
                "documento_base64"
            ]

            if not document*base64:
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
                    "documento_base64": (
                        document_base64
                    )
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
