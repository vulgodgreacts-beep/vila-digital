"""
Fluxo de memória de cada agente: guarda observações e reflexões,
e recupera as mais relevantes na hora de decidir uma ação.

A relevância usa TF-IDF + similaridade de cosseno (leve, roda offline,
sem precisar baixar nenhum modelo de embeddings). Combinada com recência
e importância, dá o mesmo efeito do paper original (Park et al., 2023).
"""

import json
import os
from dataclasses import dataclass, asdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Esquecimento. Sem isso, um morador rodando meses na nuvem acumularia
# dezenas de milhares de memórias — o arquivo incha e a busca fica lenta.
#
# O critério é o da memória humana: o trivial some, o que marcou fica.
# Conclusões e viradas de opinião (importância alta) nunca são apagadas;
# as ações banais do dia a dia só sobrevivem enquanto são recentes.
LIMITE_TOTAL = 400          # a partir daqui começa a esquecer
GUARDAR_SEMPRE = 7          # importância mínima pra nunca ser esquecida
BANAIS_RECENTES = 150       # quantas memórias comuns ficam


@dataclass
class MemoryEntry:
    text: str
    created_tick: int
    importance: int  # 1 (trivial) a 10 (marcante)
    kind: str = "observation"  # observation | reflection


class MemoryStream:
    def __init__(self, agent_name: str, state_dir: str = "state"):
        self.agent_name = agent_name
        self.entries: list[MemoryEntry] = []
        self.state_path = os.path.join(state_dir, f"{agent_name}_memory.json")
        self._load()

    def add(self, text: str, tick: int, importance: int = 3, kind: str = "observation"):
        self.entries.append(MemoryEntry(text=text, created_tick=tick, importance=importance, kind=kind))
        if len(self.entries) > LIMITE_TOTAL:
            self._esquecer()
        self._save()

    def _esquecer(self):
        """Descarta o banal antigo, preserva tudo que foi marcante."""
        marcantes = [e for e in self.entries if e.importance >= GUARDAR_SEMPRE]
        banais = [e for e in self.entries if e.importance < GUARDAR_SEMPRE]
        banais = banais[-BANAIS_RECENTES:]
        # remonta na ordem cronológica original
        self.entries = sorted(marcantes + banais, key=lambda e: e.created_tick)

    def retrieve(self, query: str, current_tick: int, top_k: int = 5) -> list[MemoryEntry]:
        if not self.entries:
            return []

        texts = [e.text for e in self.entries]
        vectorizer = TfidfVectorizer().fit(texts + [query])
        vectors = vectorizer.transform(texts + [query])
        relevance = cosine_similarity(vectors[-1], vectors[:-1])[0]

        scored = []
        for entry, rel in zip(self.entries, relevance):
            age = max(current_tick - entry.created_tick, 0)
            recency = 0.99 ** age
            importance_score = entry.importance / 10
            score = rel + recency + importance_score
            scored.append((score, entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def _save(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.entries], f, ensure_ascii=False, indent=2)

    def _load(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as f:
                data = json.load(f)
            self.entries = [MemoryEntry(**d) for d in data]
