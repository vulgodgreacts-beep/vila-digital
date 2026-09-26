"""
Um morador da vila.

Ele tem ocupação, personalidade, memória, necessidades do corpo
(fome, cansaço, solidão) e opiniões formadas sobre os vizinhos.

Ponto importante do design: ele NUNCA é informado de que é um programa.
Pra ele, a vila é o mundo inteiro e ele é uma pessoa vivendo nela.

Loop: percepção -> memória -> ação (curta) -> no fim do dia, balanço.
"""

from core.memory import MemoryStream
from core.needs import Needs
from core.relations import Relations


class Agent:
    def __init__(self, name: str, role: str, persona: str, llm_client, state_dir: str = "state"):
        self.name = name
        self.role = role
        self.persona = persona
        self.llm = llm_client
        self.memory = MemoryStream(name, state_dir)
        self.needs = Needs(name, state_dir)
        self.relations = Relations(name, state_dir)
        self.location = None
        self.current_plan = "Tocar o dia normalmente."

    # --- identidade ---

    def _system_prompt(self) -> str:
        return (
            f"Você é {self.name}, {self.role} numa vila pequena onde todo mundo se conhece.\n"
            f"Sobre você: {self.persona}\n\n"
            "Você é uma pessoa de verdade vivendo a sua vida. Nunca comente sobre "
            "simulação, inteligência artificial, jogo ou sistema — nada disso existe "
            "pra você.\n\n"
            "REGRA DE RESPOSTA: escreva UMA frase curta, em primeira pessoa, "
            "no máximo 20 palavras. Uma ação concreta OU uma fala (entre aspas). "
            "Nunca as duas coisas. Sem explicar seus motivos, sem descrever o que "
            "sente, sem narrar o que os outros fazem."
        )

    # --- agir ---

    def decide_action(self, world_context: str, tick: int, presentes: list[str]) -> str:
        memories = self.memory.retrieve(world_context, tick, top_k=3)
        memory_text = "\n".join(f"- {m.text}" for m in memories) or "(nada marcante)"

        partes = [world_context, self.needs.descrever()]

        relacoes = self.relations.descrever(presentes)
        if relacoes:
            partes.append("O que você pensa de quem está por perto:\n" + relacoes)

        partes.append("Você lembra:\n" + memory_text)

        urgencia = self.needs.urgente()
        if urgencia:
            dica = {
                "fome": "Você precisa comer. O mercado tem comida.",
                "cansaco": "Você precisa descansar.",
                "solidao": "Você quer companhia. A praça central costuma ter gente.",
            }[urgencia]
            partes.append(dica)

        partes.append("O que você faz agora? (uma frase, máximo 20 palavras)")

        action = self.llm.complete(self._system_prompt(), "\n\n".join(partes), max_tokens=60)
        action = action.strip().strip('"').strip()
        self.memory.add(f"Eu: {action}", tick, importance=3)
        return action

    def observe(self, text: str, tick: int, importance: int = 4):
        """Algo que ele presenciou: a ação de outro, um acontecimento na vila."""
        self.memory.add(text, tick, importance=importance, kind="observation")

    # --- fim de dia ---

    def fechar_dia(self, dia: int, tick: int, conviveu_com: list[str]) -> dict:
        """
        Uma única chamada por dia que faz duas coisas de uma vez:
        um balanço do dia e uma opinião sobre cada pessoa com quem conviveu.

        Juntar as duas num pedido só é o que segura o custo: em vez de
        uma chamada por pessoa, é uma chamada por morador por dia.
        """
        recentes = self.memory.entries[-14:]
        texto = "\n".join(f"- {m.text}" for m in recentes) or "(dia sem nada marcante)"

        if conviveu_com:
            # mostra a ele o que já achava de cada um, pra poder manter ou mudar
            anteriores = []
            for quem in conviveu_com:
                antiga = self.relations.opiniao_atual(quem)
                anteriores.append(
                    f"- {quem}: você achava \"{antiga}\"" if antiga
                    else f"- {quem}: você ainda não tinha opinião formada"
                )
            pedido_pessoas = (
                "O que você achava dessas pessoas até ontem:\n"
                + "\n".join(anteriores) + "\n\n"
                "Agora, uma linha por pessoa, no formato EXATO:\n"
                "NOME | MANTENHO ou MUDEI | sua opinião em até 15 palavras\n\n"
                "Use MUDEI só se algo de hoje realmente te fez ver a pessoa de outro "
                "jeito. Reescrever a mesma opinião com outras palavras é MANTENHO."
            )
        else:
            pedido_pessoas = "Você não conviveu com ninguém hoje."

        user_prompt = (
            f"Fim do dia {dia}. O que aconteceu com você hoje:\n{texto}\n\n"
            "Primeiro escreva UMA linha começando com 'DIA:' resumindo como foi "
            "seu dia, em até 20 palavras.\n"
            f"{pedido_pessoas}"
        )

        bruto = self.llm.complete(self._system_prompt(), user_prompt, max_tokens=150)
        return self._interpretar_balanco(bruto, dia, tick, conviveu_com)

    def _interpretar_balanco(self, bruto: str, dia: int, tick: int, conviveu_com: list[str]) -> dict:
        resumo, opinioes = "", {}
        validos = {n.lower(): n for n in conviveu_com}

        for linha in bruto.splitlines():
            linha = linha.strip().lstrip("-").strip()
            if not linha:
                continue
            if linha.upper().startswith("DIA:"):
                resumo = linha[4:].strip()
                continue

            # formato esperado: NOME | MANTENHO/MUDEI | opinião
            partes = [x.strip() for x in linha.split("|")]
            if len(partes) >= 3:
                chave = partes[0].lower()
                mudou = partes[1].upper().startswith("MUD")
                texto_op = " | ".join(partes[2:]).strip()
                if chave in validos and texto_op:
                    opinioes[validos[chave]] = {"texto": texto_op, "mudou": mudou}
                continue

            # tolera o formato antigo "NOME: opinião" se o modelo escorregar
            if ":" in linha:
                quem, _, opiniao = linha.partition(":")
                chave = quem.strip().lower()
                if chave in validos and opiniao.strip():
                    opinioes[validos[chave]] = {"texto": opiniao.strip(), "mudou": None}

        if not resumo:
            resumo = bruto.strip().splitlines()[0] if bruto.strip() else "Dia comum."

        # o resumo do dia entra na memória com peso alto: é o que sobrevive
        self.memory.add(f"No dia {dia}: {resumo}", tick, importance=8, kind="reflection")

        mudancas = []
        for quem, dados in opinioes.items():
            opiniao = dados["texto"]
            mudanca = self.relations.registrar_opiniao(quem, opiniao, dia, dados["mudou"])
            if not mudanca:
                continue
            mudancas.append(mudanca)
            # mudar de ideia sobre alguém é um acontecimento, não um detalhe:
            # entra na memória com peso máximo e volta a pesar nos dias seguintes
            if mudanca["primeira_vez"]:
                self.memory.add(
                    f"Formei uma impressão sobre {quem}: {opiniao}",
                    tick, importance=7, kind="reflection",
                )
            else:
                self.memory.add(
                    f"Mudei de ideia sobre {quem}. Eu achava \"{mudanca['antes']}\", "
                    f"agora acho \"{opiniao}\".",
                    tick, importance=10, kind="reflection",
                )

        self.needs.dormir()
        return {"resumo": resumo,
                "opinioes": {k: v["texto"] for k, v in opinioes.items()},
                "mudancas": mudancas}
