"""
O que cada morador pensa dos outros — e como essa opinião MUDA com o tempo.

Três camadas:

1. FAMILIARIDADE (automática, sem LLM): quantos ticks os dois passaram juntos.

2. OPINIÃO ATUAL: uma frase que ele formou sobre a pessoa, revista a cada dia.

3. HISTÓRICO: o que ele já achou dessa pessoa antes. É isso que permite
   "eu achava que ele era X, mudei de ideia" — em vez de a opinião de ontem
   simplesmente sumir.

Uma mudança de opinião não é só sobrescrever texto: é um acontecimento na vida
do morador, que vira memória de peso alto e volta a assombrá-lo depois.
"""

import json
import os
from difflib import SequenceMatcher

# quão parecidas duas frases precisam ser pra contarem como "a mesma opinião"
LIMIAR_IGUALDADE = 0.78

# quantas opiniões antigas guardar por pessoa (as mais recentes)
MAX_HISTORICO = 4


def _parecidas(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= LIMIAR_IGUALDADE


class Relations:
    def __init__(self, nome: str, state_dir: str = "state"):
        self.nome = nome
        self.dados: dict[str, dict] = {}
        self.caminho = os.path.join(state_dir, f"{nome}_relacoes.json")
        self._carregar()

    def _garantir(self, outro: str):
        if outro not in self.dados:
            self.dados[outro] = {"familiaridade": 0, "opiniao": "", "desde_dia": None, "historico": []}
        # compatibilidade com arquivos gravados por versões antigas
        self.dados[outro].setdefault("historico", [])
        self.dados[outro].setdefault("desde_dia", None)

    def conviver(self, outro: str):
        self._garantir(outro)
        self.dados[outro]["familiaridade"] += 1
        self._salvar()

    def opiniao_atual(self, outro: str) -> str:
        return self.dados.get(outro, {}).get("opiniao", "")

    def registrar_opiniao(self, outro: str, frase: str, dia: int,
                          declarou_mudanca: bool | None = None) -> dict | None:
        """
        Guarda a opinião do dia. Devolve o que mudou, ou None se ele
        apenas reafirmou o que já achava.

        Quem decide se houve mudança é o PRÓPRIO morador (declarou_mudanca),
        porque só ele sabe se "gente boa" virando "pessoa legal" é a mesma
        opinião reescrita ou uma virada de verdade. Comparação de texto não
        distingue as duas coisas. Se ele não declarar, caímos na semelhança
        textual como último recurso.
        """
        self._garantir(outro)
        d = self.dados[outro]
        frase = frase.strip()
        anterior = d["opiniao"]

        if anterior:
            if declarou_mudanca is False:
                self._salvar()
                return None
            if declarou_mudanca is None and _parecidas(anterior, frase):
                self._salvar()
                return None

        if anterior:
            d["historico"].append({"dia": d["desde_dia"], "opiniao": anterior})
            d["historico"] = d["historico"][-MAX_HISTORICO:]

        d["opiniao"] = frase
        d["desde_dia"] = dia
        self._salvar()

        return {"pessoa": outro, "antes": anterior, "agora": frase, "primeira_vez": not anterior}

    def conhecidos(self) -> list[str]:
        return sorted(self.dados, key=lambda o: -self.dados[o]["familiaridade"])

    def descrever(self, presentes: list[str] | None = None) -> str:
        """
        O que ele pensa das pessoas, incluindo o que já pensou antes.
        Priorizando quem está na frente dele agora.
        """
        alvos = presentes if presentes else self.conhecidos()[:3]
        linhas = []
        for outro in alvos:
            d = self.dados.get(outro)
            if not d:
                linhas.append(f"- {outro}: você ainda não conhece direito.")
                continue

            if d.get("opiniao"):
                linha = f"- {outro}: {d['opiniao']}"
                antigas = d.get("historico", [])
                if antigas:
                    velha = antigas[-1]["opiniao"]
                    linha += f" (você já achou outra coisa: \"{velha}\")"
                linhas.append(linha)
            elif d["familiaridade"] >= 3:
                linhas.append(f"- {outro}: convivem bastante, mas você não formou opinião ainda.")
            else:
                linhas.append(f"- {outro}: mal se cruzaram até agora.")
        return "\n".join(linhas)

    # --- persistência ---

    def _salvar(self):
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        tmp = self.caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.caminho)

    def _carregar(self):
        if os.path.exists(self.caminho):
            try:
                with open(self.caminho, encoding="utf-8") as f:
                    self.dados = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.dados = {}
