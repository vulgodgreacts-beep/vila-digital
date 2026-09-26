"""
Servidor local do painel de supervisão.

Lê o que a simulação escreveu em state/ e serve pro navegador.
Roda em paralelo com a simulação: abra dois terminais, um com
`python main.py` e outro com `python viewer.py`.

    python viewer.py
    → abre http://localhost:8800
"""

import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORTA = 8800
RAIZ = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(RAIZ, "state")


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
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/api/estado"):
            payload = {
                "mundo": ler_json(os.path.join(RAIZ, "data", "world.json"), {}),
                "moradores": ler_json(os.path.join(RAIZ, "data", "agents.json"), []),
                "eventos": ler_json(os.path.join(STATE_DIR, "event_log.json"), []),
                "estado_atual": ler_json(os.path.join(STATE_DIR, "world_state.json"), {}),
            }
            self._enviar(json.dumps(payload, ensure_ascii=False))
            return

        if self.path.startswith("/three.min.js"):
            try:
                with open(os.path.join(RAIZ, "viewer", "three.min.js"), "rb") as f:
                    self._enviar(f.read(), "application/javascript")
            except OSError:
                self.send_error(404, "viewer/three.min.js nao encontrado")
            return

        arquivo = "3d.html" if self.path.startswith("/3d") else "index.html"
        caminho_html = os.path.join(RAIZ, "viewer", arquivo)
        try:
            with open(caminho_html, "rb") as f:
                self._enviar(f.read(), "text/html")
        except OSError:
            self.send_error(404, f"viewer/{arquivo} nao encontrado")


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
