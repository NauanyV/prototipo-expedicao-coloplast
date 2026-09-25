from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8000
API_KEY = "DEMO-COLOPLAST-2026"

# Banco de cargas fictício: substitui o Analytics só para demonstração.
CARGAS = {
    "141501": {"id": "141501", "cliente": "Coloplast", "nf": "21007", "status": "EM EXPEDICAO", "documento": None},
    "141502": {"id": "141502", "cliente": "Coloplast", "nf": "21008", "status": "EM EXPEDICAO", "documento": None},
    "141503": {"id": "141503", "cliente": "Coloplast", "nf": "21009", "status": "EM EXPEDICAO", "documento": None},
}

def send_json(handler, status, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, x-api-key")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, 204, {})

    def _auth(self):
        return self.headers.get("x-api-key") == API_KEY

    def do_GET(self):
        if not self._auth():
            return send_json(self, 401, {"erro": "API key inválida."})

        path = urlparse(self.path).path

        if path == "/":
            try:
                with open("prototipo_exp_coloplast.html", "rb") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            except FileNotFoundError:
                send_json(self, 404, {"erro": "Arquivo HTML não encontrado."})
            return

        if path == "/api/cargas":
            return send_json(self, 200, {"cargas": list(CARGAS.values())})

        if path.startswith("/api/cargas/"):
            carga_id = path.rsplit("/", 1)[-1]
            carga = CARGAS.get(carga_id)
            if not carga:
                return send_json(self, 404, {"erro": "Carga não encontrada."})
            return send_json(self, 200, carga)

        return send_json(self, 404, {"erro": "Endpoint não encontrado."})

    def do_POST(self):
        if not self._auth():
            return send_json(self, 401, {"erro": "API key inválida."})

        path = urlparse(self.path).path
        if path != "/api/documentos":
            return send_json(self, 404, {"erro": "Endpoint não encontrado."})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return send_json(self, 400, {"erro": "JSON inválido."})

        cliente = str(payload.get("cliente", "")).strip()
        nf = str(payload.get("nf", "")).strip()
        id_carga = str(payload.get("id_carga", "")).strip()
        doc = payload.get("documento") or {}

        if not cliente or not nf or not id_carga or not doc.get("nome") or not doc.get("conteudo_base64"):
            return send_json(self, 400, {"erro": "Campos obrigatórios ausentes."})

        carga = CARGAS.get(id_carga)
        if not carga:
            return send_json(self, 404, {
                "erro": "ID de carga não encontrado.",
                "id_carga": id_carga
            })

        if carga["cliente"].lower() != cliente.lower():
            return send_json(self, 409, {
                "erro": "Cliente não corresponde à carga.",
                "esperado": carga["cliente"],
                "recebido": cliente
            })

        if carga["nf"] != nf:
            return send_json(self, 409, {
                "erro": "Número da NF não corresponde à carga.",
                "esperado": carga["nf"],
                "recebido": nf
            })

        try:
            raw = base64.b64decode(doc["conteudo_base64"])
        except Exception:
            return send_json(self, 400, {"erro": "Arquivo em base64 inválido."})

        if len(raw) > 20 * 1024 * 1024:
            return send_json(self, 413, {"erro": "Arquivo acima do limite de 20 MB."})

        carga["documento"] = {
            "nome": doc["nome"],
            "tipo": doc.get("tipo", ""),
            "tamanho": len(raw),
            "registrado_via": "API MOCK"
        }
        carga["status"] = "EXPEDIDA"

        return send_json(self, 200, {
            "sucesso": True,
            "mensagem": "Documento registrado e carga atualizada.",
            "carga": carga,
            "simula": {
                "passo_1": "Receber dados",
                "passo_2": "Validar ID + cliente + NF",
                "passo_3": "Anexar documento",
                "passo_4": "Alterar status para EXPEDIDA"
            }
        })

if __name__ == "__main__":
    print(f"Servidor iniciado em http://{HOST}:{PORT}")
    print("API key de demonstração:", API_KEY)
    print("Endpoints: GET /api/cargas, GET /api/cargas/{id}, POST /api/documentos")
    HTTPServer((HOST, PORT), Handler).serve_forever()
