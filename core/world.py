"""
Estado compartilhado do ambiente: locais, relógio, variáveis globais
(clima, equipamentos, suprimentos) e o histórico do que aconteceu.

Diferente da versão anterior, o mundo agora TEM ESTADO PRÓPRIO e pode
disparar incidentes — coisas que acontecem independente dos agentes e
que eles precisam reagir.
"""

import json
import os
import random


class World:
    def __init__(self, config_path: str = "data/world.json", state_dir: str = "state"):
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        self.name = data["name"]
        self.locations = data["locations"]
        self.state = data.get("state", {})
        self.incident_pool = data.get("incidents", [])
        self.tick = 0
        self.event_log = []
        self.active_incidents = []
        self.state_path = os.path.join(state_dir, "world_state.json")
        self._load()

    # --- descrição do ambiente ---

    def describe_location(self, location_name: str) -> str:
        loc = self.locations.get(location_name, {})
        return loc.get("description", "")

    def describe_state(self) -> str:
        """O que qualquer pessoa na vila percebe só de olhar em volta."""
        if not self.state:
            return ""
        partes = [f"{chave}: {valor}" for chave, valor in self.state.items()]
        return "Situação geral: " + "; ".join(partes) + "."

    def describe_incidents(self) -> str:
        if not self.active_incidents:
            return "Nenhuma ocorrência em andamento."
        return "Ocorrências em andamento: " + " | ".join(
            f"{i['title']} — {i['description']}" for i in self.active_incidents
        )

    # --- incidentes ---

    def maybe_trigger_incident(self, chance: float = 0.25):
        """
        A cada tick há uma chance de um incidente novo aparecer.
        Incidentes que já estão ativos não se repetem.
        """
        if not self.incident_pool or random.random() > chance:
            return None

        ativos = {i["title"] for i in self.active_incidents}
        candidatos = [i for i in self.incident_pool if i["title"] not in ativos]
        if not candidatos:
            return None

        incidente = dict(random.choice(candidatos))
        incidente["started_tick"] = self.tick
        self.active_incidents.append(incidente)

        for chave, valor in incidente.get("state_changes", {}).items():
            self.state[chave] = valor

        return incidente

    def resolve_incident(self, title: str):
        """Tira um incidente da lista de ativos (quando os agentes resolvem)."""
        self.active_incidents = [i for i in self.active_incidents if i["title"] != title]

    def expire_incidents(self, duracao: int = 6):
        """Incidentes antigos somem sozinhos, pra simulação não travar neles."""
        self.active_incidents = [
            i for i in self.active_incidents
            if self.tick - i.get("started_tick", self.tick) < duracao
        ]

    # --- log e tempo ---

    def log_event(self, agent_name: str, action: str, location: str):
        entry = {"tick": self.tick, "agent": agent_name, "location": location, "action": action}
        self.event_log.append(entry)
        return entry

    def advance(self):
        self.tick += 1

    # --- persistência ---

    def save(self):
        # escrita atômica: o painel nunca pega o arquivo pela metade
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        temporario = self.state_path + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(
                {"tick": self.tick, "state": self.state, "active_incidents": self.active_incidents},
                f, ensure_ascii=False, indent=2,
            )
        os.replace(temporario, self.state_path)

    def _load(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as f:
                data = json.load(f)
            self.tick = data.get("tick", 0)
            self.state.update(data.get("state", {}))
            self.active_incidents = data.get("active_incidents", [])
