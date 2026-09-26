"""
O motor de tick da vila.

A cada passo:
  1. o mundo pode disparar um incidente (feira, chuva, apagão...)
  2. cada agente observa o local, a situação geral, quem está junto e as ocorrências
  3. o agente decide uma ação via LLM
  4. quem estiver no MESMO local vê essa ação e guarda na própria memória
  5. se o agente mencionou outro local, ele se desloca pra lá
"""

import json
import os
import time

from rich.console import Console

from core.agent import Agent
from core.llm_client import LLMClient
from core.world import World

console = Console()

# Quantos eventos o log guarda. Ele alimenta o painel, não a memória dos
# moradores (essa vive nos arquivos de cada um), então basta o passado
# recente. Sem esse teto, o arquivo cresceria uns 8 MB por ano.
MAX_EVENTOS_LOG = 1500


class Simulation:
    def __init__(
        self,
        agents_path: str = "data/agents.json",
        world_path: str = "data/world.json",
        state_dir: str = "state",
        ticks_por_dia: int = 8,
        incident_chance: float = 0.25,
    ):
        self.world = World(world_path, state_dir)
        self.llm = LLMClient()
        self.state_dir = state_dir
        self.ticks_por_dia = ticks_por_dia
        self.incident_chance = incident_chance

        with open(agents_path, encoding="utf-8") as f:
            agents_data = json.load(f)

        self.log_path = os.path.join(state_dir, "event_log.json")
        self.eventos_anteriores = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, encoding="utf-8") as f:
                    self.eventos_anteriores = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.eventos_anteriores = []

        self.convivio_do_dia = {}

        self.agents = []
        for a in agents_data:
            agent = Agent(a["name"], a["role"], a["persona"], self.llm, state_dir)
            agent.location = a.get("starting_location", next(iter(self.world.locations)))
            agent.current_plan = a.get("goal", agent.current_plan)
            self.agents.append(agent)

    # --- deslocamento ---

    def _detect_move(self, agent, action_text: str):
        """
        Se o agente mencionou outro local na ação, ele vai pra lá.
        Simples de propósito: evita uma segunda chamada de LLM só pra mover.
        """
        texto = action_text.lower()
        for nome_local in self.world.locations:
            if nome_local.lower() in texto and nome_local != agent.location:
                agent.location = nome_local
                return nome_local
        return None

    # --- loop principal ---

    def run(self, ticks: int = 10, delay: float = 0.0):
        for _ in range(ticks):
            self.world.advance()
            self.world.expire_incidents()
            console.rule(f"[bold]Tick {self.world.tick}[/bold]")

            incidente = self.world.maybe_trigger_incident(self.incident_chance)
            if incidente:
                aviso = f"ACONTECEU: {incidente['title']} — {incidente['description']}"
                console.print(f"[bold red]{aviso}[/bold red]")
                self.world.log_event("SISTEMA", aviso, "vila")
                for a in self.agents:
                    a.observe(aviso, self.world.tick, importance=9)

            for agent in self.agents:
                juntos = [
                    a for a in self.agents
                    if a.location == agent.location and a.name != agent.name
                ]
                presentes = [a.name for a in juntos]
                nomes_juntos = ", ".join(f"{a.name} ({a.role})" for a in juntos) or "ninguém"

                # conviver é o que constrói familiaridade — não custa API nenhuma
                for outro in juntos:
                    agent.relations.conviver(outro.name)
                    self.convivio_do_dia.setdefault(agent.name, set()).add(outro.name)

                agent.needs.avancar(agent.location, acompanhado=bool(juntos))

                context = (
                    f"Local: {agent.location}. {self.world.describe_location(agent.location)}\n"
                    f"{self.world.describe_state()}\n"
                    f"{self.world.describe_incidents()}\n"
                    f"Com você agora: {nomes_juntos}.\n"
                    f"Lugares pra onde pode ir: {', '.join(self.world.locations)}."
                )

                action = agent.decide_action(context, self.world.tick, presentes)
                self.world.log_event(agent.name, action, agent.location)
                console.print(f"[cyan]{agent.name}[/cyan] [dim]({agent.location})[/dim]: {action}")

                # quem estava junto presencia a ação
                for outro in juntos:
                    outro.observe(f"{agent.name}: {action}", self.world.tick, importance=5)

                destino = self._detect_move(agent, action)
                if destino:
                    console.print(f"  [dim]→ {agent.name} se desloca para {destino}[/dim]")

            # fim de dia: cada morador faz o balanço e forma opinião sobre quem viu
            if self.world.tick % self.ticks_por_dia == 0:
                dia = self.world.tick // self.ticks_por_dia
                console.print(f"\n[yellow]── fim do dia {dia} ──[/yellow]")
                for agent in self.agents:
                    conviveu = sorted(self.convivio_do_dia.get(agent.name, set()))
                    balanco = agent.fechar_dia(dia, self.world.tick, conviveu)
                    console.print(f"  [magenta]{agent.name}:[/magenta] {balanco['resumo']}")
                    for m in balanco.get("mudancas", []):
                        if m["primeira_vez"]:
                            console.print(f"     [dim]formou opinião sobre {m['pessoa']}: {m['agora']}[/dim]")
                        else:
                            console.print(
                                f"     [bold yellow]mudou de ideia sobre {m['pessoa']}[/bold yellow]"
                                f" [dim]— antes: {m['antes']}[/dim]"
                            )
                            console.print(f"       [yellow]agora: {m['agora']}[/yellow]")
                            self.world.log_event(
                                "SISTEMA",
                                f"{agent.name} mudou de ideia sobre {m['pessoa']}: {m['agora']}",
                                agent.location,
                            )
                self.convivio_do_dia = {}

            # grava a cada tick, pra quem estiver assistindo pelo painel
            self._salvar()

            if delay:
                time.sleep(delay)

        console.print(f"\n[green]Estado e log salvos em {self.state_dir}/[/green]")

    def _salvar(self):
        """
        Escreve o log e o estado a cada tick, pra que o painel (viewer.py)
        acompanhe a simulação ao vivo em vez de só no fim.

        Grava num arquivo temporário e depois renomeia: assim o painel nunca
        lê um JSON pela metade.
        """
        os.makedirs(self.state_dir, exist_ok=True)
        tudo = self.eventos_anteriores + self.world.event_log
        # o log é só pro painel mostrar — não precisa guardar a história inteira
        if len(tudo) > MAX_EVENTOS_LOG:
            tudo = tudo[-MAX_EVENTOS_LOG:]
        temporario = self.log_path + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(tudo, f, ensure_ascii=False, indent=2)
        os.replace(temporario, self.log_path)
        self.world.save()
