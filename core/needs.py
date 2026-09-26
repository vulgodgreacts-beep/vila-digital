"""
Necessidades internas de cada morador: fome, energia e vontade de companhia.

Isso roda SEM chamar o LLM — é aritmética pura. A função delas é dar
motivação própria pro morador: ele não age porque um modelo sorteou algo,
age porque está com fome, ou exausto, ou sozinho demais.

Escala de 0 a 100, onde 100 é urgência máxima.
"""

import json
import os


# quanto cada necessidade sobe por tick, em condições normais
RITMO = {"fome": 4.5, "cansaco": 3.2, "solidao": 5.0}

# o que cada lugar da vila alivia, e com que força por tick
ALIVIO_POR_LUGAR = {
    "mercado":       {"fome": -14},
    "refeitório":    {"fome": -20},
    "alojamento":    {"cansaco": -22},
    "biblioteca":    {"cansaco": -6},
    "praça central": {"solidao": -4},
}


class Needs:
    def __init__(self, nome: str, state_dir: str = "state"):
        self.nome = nome
        self.valores = {"fome": 20.0, "cansaco": 15.0, "solidao": 25.0}
        self.caminho = os.path.join(state_dir, f"{nome}_needs.json")
        self._carregar()

    # --- evolução ---

    def avancar(self, local: str, acompanhado: bool):
        """Um tick de tempo passando: as necessidades sobem, o ambiente alivia."""
        for chave, passo in RITMO.items():
            self.valores[chave] = min(100.0, self.valores[chave] + passo)

        # estar com gente mata a solidão rápido
        if acompanhado:
            self.valores["solidao"] = max(0.0, self.valores["solidao"] - 16)

        for chave, delta in ALIVIO_POR_LUGAR.get(local, {}).items():
            self.valores[chave] = max(0.0, self.valores[chave] + delta)

        self._salvar()

    def dormir(self):
        """Fim de dia: descansa bastante, mas acorda com fome."""
        self.valores["cansaco"] = 5.0
        self.valores["fome"] = min(100.0, self.valores["fome"] + 25)
        self._salvar()

    # --- leitura ---

    def urgente(self) -> str | None:
        """A necessidade mais gritante agora, se alguma passou do limite."""
        candidatas = [(v, k) for k, v in self.valores.items() if v >= 65]
        if not candidatas:
            return None
        return max(candidatas)[1]

    def descrever(self) -> str:
        """Como o morador sente o próprio corpo agora, em linguagem humana."""
        partes = []
        f, c, s = self.valores["fome"], self.valores["cansaco"], self.valores["solidao"]

        if f >= 80:   partes.append("está com muita fome")
        elif f >= 55: partes.append("está começando a sentir fome")

        if c >= 80:   partes.append("está exausto, mal consegue se concentrar")
        elif c >= 55: partes.append("está cansado")

        if s >= 80:   partes.append("está se sentindo muito sozinho e queria companhia")
        elif s >= 55: partes.append("está com vontade de conversar com alguém")

        if not partes:
            return "Você está bem: sem fome, descansado e sem carência de companhia."
        return "Como você está agora: você " + ", ".join(partes) + "."

    # --- persistência ---

    def _salvar(self):
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        tmp = self.caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.valores, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.caminho)

    def _carregar(self):
        if os.path.exists(self.caminho):
            try:
                with open(self.caminho, encoding="utf-8") as f:
                    self.valores.update(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
