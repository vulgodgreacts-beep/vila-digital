"""
Servidor local do painel de supervisão.

Lê o que a simulação escreveu em state/ e serve pro navegador — inclusive os
arquivos da cena 3D (bibliotecas e modelos .vrm), que agora vivem em
viewer/vendor/ e viewer/modelos/.

Roda em paralelo com a simulação: abra dois terminais, um com
`python main.py` e outro com `python viewer.py`.

    python viewer.py
    → abre http://localhost:8800
"""

import json
import mimetypes
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlsplit

PORTA = 8800
RAIZ = os.path.dirname(os.path.abspath(__file__))
VIEWER_DIR = os.path.join(RAIZ, "viewer")
STATE_DIR = os.path.join(RAIZ, "state")

# o .vrm não tem tipo MIME padrão no sistema — registra pra não cair em None
mimetypes.add_type("application/octet-stream", ".vrm")


def ler_json(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return padrao


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silencia o log de cada request

    def _enviar(self, conteudo, tipo="application/json"):
        dados = conteudo if isinstance(conteudo, bytes) else conteudo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8" if tipo.startswith("text") or "json" in tipo else tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def _enviar_arquivo(self, caminho_absoluto):
        try:
            with open(caminho_absoluto, "rb") as f:
                dados = f.read()
        except OSError:
            self.send_error(404, "arquivo nao encontrado")
            return
        tipo, _ = mimetypes.guess_type(caminho_absoluto)
        self._enviar(dados, tipo or "application/octet-stream")

    def do_GET(self):
        caminho = unquote(urlsplit(self.path).path)

        if caminho.startswith("/api/estado"):
            payload = {
                "mundo": ler_json(os.path.join(RAIZ, "data", "world.json"), {}),
                "moradores": ler_json(os.path.join(RAIZ, "data", "agents.json"), []),
                "eventos": ler_json(os.path.join(STATE_DIR, "event_log.json"), []),
                "estado_atual": ler_json(os.path.join(STATE_DIR, "world_state.json"), {}),
            }
            self._enviar(json.dumps(payload, ensure_ascii=False))
            return

        if caminho in ("/", ""):
            self._enviar_arquivo(os.path.join(VIEWER_DIR, "index.html"))
            return

        if caminho == "/3d":
            self._enviar_arquivo(os.path.join(VIEWER_DIR, "3d.html"))
            return

        # qualquer outra coisa (vendor/, modelos/, etc.) é um arquivo estático
        # dentro de viewer/ — resolve com cuidado pra não escapar da pasta
        relativo = caminho.lstrip("/")
        candidato = os.path.realpath(os.path.join(VIEWER_DIR, relativo))
        if os.path.commonpath([candidato, VIEWER_DIR]) != VIEWER_DIR:
            self.send_error(403, "caminho invalido")
            return
        self._enviar_arquivo(candidato)


def main():
    endereco = f"http://localhost:{PORTA}"
    print(f"Painel da vila rodando em {endereco}")
    print(f"Versao 3D em            {endereco}/3d")
    print("Deixe esta janela aberta. Ctrl+C para encerrar.\n")
    try:
        webbrowser.open(endereco)
    except Exception:
        pass
    HTTPServer(("localhost", PORTA), Handler).serve_forever()


if __name__ == "__main__":
    main()
