# Vila Digital — simulação com agentes de IA

Uma vila pequena com 3 moradores. Cada um é um agente de LLM com ocupação,
personalidade, objetivo próprio e memória persistente. Inspirado no paper
"Generative Agents" (Stanford/Google, 2023).

## Os moradores

| Quem | Ocupação | O que move ele |
|---|---|---|
| **Marina** | Mecânica | Terminar os consertos empilhados na bancada |
| **Teo** | Bibliotecário | Organizar o acervo e achar com quem conversar |
| **Iris** | Vendedora do mercado | Vender bem e manter a vila informada |

Os moradores se deslocam entre os 4 lugares por conta própria: se a ação que o
LLM gerou menciona outro lugar ("vou até a praça"), o agente vai pra lá no tick
seguinte.

## Como funciona cada tick

1. A vila pode ter um **acontecimento** (chuva forte, apagão, dia de feira,
   cachorro perdido...). Ele altera o estado da vila e **todos ficam sabendo**,
   com importância alta na memória.
2. Cada agente monta sua percepção: onde está, como está a vila, o que está
   acontecendo, quem está no mesmo lugar.
3. Ele recupera as **memórias mais relevantes** (similaridade + recência +
   importância) e o LLM decide uma ação curta, que pode incluir falar com quem
   estiver junto.
4. **Quem estava no mesmo local registra essa ação na própria memória.** É daqui
   que sai a conversa: o outro responde no tick seguinte porque lembra do que
   foi dito.
5. Se o agente mencionou outro local na ação ("vou até a praça"), ele se desloca.
6. A cada N ticks, todos **refletem**: viram uma conclusão de nível mais alto
   sobre a vila ou sobre alguém que conhecem.

Tudo persiste em `state/` — memórias individuais, estado da vila e log de
eventos. Dá pra parar e retomar sem perder nada.

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
```

Escolha o provedor de LLM no `.env`:

- **`ollama`** (padrão, local e de graça): instale o [Ollama](https://ollama.com),
  rode `ollama pull llama3` e deixe ele aberto.
- **`anthropic`**: `LLM_PROVIDER=anthropic` + sua `ANTHROPIC_API_KEY`.
- **`openai`**: `LLM_PROVIDER=openai` + sua `OPENAI_API_KEY`.

## Rodando

```bash
python main.py --ticks 12
```

Parâmetros úteis:

```bash
--delay 1.5              # pausa entre ticks, pra ler como se fosse ao vivo
--incident-chance 0.5    # vila mais movimentada (padrão 0.25)
--incident-chance 0.05   # quase nada acontece; foco no convívio
--ticks-por-dia 6        # dias mais curtos (padrão 8)
```

**Dica**: rode com `--incident-chance 0.05` primeiro pra ver os três no dia a
dia, depois suba pra 0.5 e veja como eles reagem quando a vila vira.

## Vendo a vila (painel no navegador)

Além do texto no terminal, tem um painel que mostra o mapa da vila com os
moradores se movendo e o registro de tudo que foi dito.

Abra **duas janelas de terminal**, as duas na pasta do projeto:

```bash
# janela 1 — a simulação
python main.py --ticks 20 --delay 3

# janela 2 — o painel
python viewer.py
```

O navegador abre sozinho em `http://localhost:8800`. A simulação grava o estado
a cada tick e o painel relê a cada 3 segundos, então o mapa acompanha tudo ao
vivo, sem precisar esperar a execução terminar.

- **Reproduzir** toca o dia do começo ao fim, um tick por vez
- A **barra** ao lado volta e avança no tempo pra rever qualquer momento
- Acontecimentos da vila aparecem em vermelho no registro

O `--delay 3` na simulação existe só pra dar tempo de assistir. Sem ele, os
ticks passam o mais rápido que a API responder.

Você pode rodar só o `viewer.py` depois, sem a simulação — ele lê o que já está
salvo em `state/` e deixa você reproduzir o que aconteceu.

### Versão 3D

O mesmo dia, em cena 3D navegável: `http://localhost:8800/3d`

Os moradores caminham pelo terreno entre a oficina, a biblioteca, o mercado e a
praça, com a fala de cada um num balão sobre a cabeça. Arraste para girar a
câmera e use a roda do mouse para aproximar.

O Three.js vai junto no projeto (`viewer/three.min.js`), então a cena funciona
sem internet. Precisa de um navegador com WebGL, que é qualquer um atual.

Os dois painéis leem exatamente os mesmos dados — dá pra deixar as duas abas
abertas ao mesmo tempo.

## O que dá vida a eles

Três sistemas que rodam junto com o LLM. Dois deles **não custam nada de API**:

**Necessidades** (`core/needs.py`, sem LLM) — cada morador tem fome, cansaço e
solidão subindo a cada tick. Lugares aliviam: o mercado mata a fome, o
alojamento o cansaço, a praça a solidão. Quando algo passa de 65, isso entra no
prompt e ele age por conta disso. É a diferença entre "o modelo sorteou ir ao
mercado" e "ele foi porque estava com fome".

**Relações com história** (`core/relations.py`, familiaridade sem LLM) — cada
tick que dois passam no mesmo lugar conta como convivência. Sobre essa base, no
fim do dia, cada um escreve o que acha do outro — vendo antes o que já achava,
e declarando se MANTENHO ou MUDEI.

Quando alguém muda de ideia sobre outro, isso não sobrescreve nada em silêncio:
a opinião antiga vai pro histórico, a virada vira memória de peso máximo (10), e
nos dias seguintes ele carrega as duas coisas — "acho X dela, mas já achei Y".
Quem decide se houve mudança é o próprio morador, não uma comparação de texto:
só ele sabe se "gente boa" virando "pessoa legal" é a mesma opinião reescrita
ou uma virada de verdade.

**Ciclo de dia** — a cada `ticks_por_dia` (padrão 8), cada morador faz um
balanço: resume o próprio dia e forma uma opinião de uma linha sobre cada pessoa
com quem conviveu. Essas opiniões são gravadas e **voltam no prompt do dia
seguinte**. É por isso que o dia 5 não é igual ao dia 1: ele chega nele já com
uma ideia formada sobre cada vizinho.

O balanço e as opiniões saem de **uma única chamada** por morador por dia — se
fosse uma chamada por pessoa, o custo triplicaria.

Os moradores nunca são informados de que são um programa. O prompt deles proíbe
mencionar simulação, IA ou sistema: pra eles, a vila é o mundo inteiro.

## Rodando sem o seu PC

Todo o estado vive em `state/`, então a vila pode rodar em rajadas curtas na
nuvem e retomar exatamente de onde parou. Tem uma automação pronta em
`.github/workflows/vila.yml` que faz isso de graça com GitHub Actions, e o
painel pode ser publicado no GitHub Pages.

O passo a passo completo está em **[HOSPEDAGEM.md](HOSPEDAGEM.md)**.

Os painéis funcionam nos dois modos sem configuração: se o `viewer.py` estiver
rodando, eles usam ele; se estiverem num site estático, leem os arquivos JSON
direto do repositório.

### Esquecimento

Pra poder rodar por meses, os moradores esquecem. Ao passar de 400 memórias,
as ações banais antigas são descartadas e **tudo que foi marcante é preservado**
— conclusões de fim de dia, impressões formadas e viradas de opinião nunca sumem.
O log de eventos guarda os 1500 mais recentes, porque ele só alimenta o painel;
a memória de verdade vive nos arquivos de cada morador.

## Customizando

- **Moradores**: `data/agents.json` — `name`, `role`, `persona`, `goal` e
  `starting_location`. O `goal` é o que mais muda o comportamento: é ele que
  cria o atrito. Quer uma equipe harmoniosa? Dê objetivos alinhados. Quer
  drama? Dê objetivos que se contradizem.
- **Lugares e acontecimentos**: `data/world.json` — locais, estado inicial e a
  lista de acontecimentos. Cada um tem `title`, `description` e `state_changes`
  (o que ele altera no estado da vila). Se você criar um lugar novo, ele
  aparece sozinho no painel.
- **Zerar tudo**: `rm -rf state/` e a simulação recomeça do zero.

Trocar de cenário é só reescrever esses dois JSONs. Plataforma offshore, base em
Marte, submarino, bunker — a mecânica é a mesma.

## Estrutura

```
ai_cidade/
├── core/
│   ├── llm_client.py   # abstração Anthropic / OpenAI / Ollama
│   ├── memory.py        # memória (relevância + recência + importância)
│   ├── needs.py         # fome, cansaço, solidão (sem LLM)
│   ├── relations.py     # familiaridade e opiniões sobre os vizinhos
│   ├── agent.py          # percepção -> memória -> ação -> reflexão
│   ├── world.py          # locais, estado da vila e acontecimentos
│   └── simulation.py     # motor de tick, propagação social, deslocamento
├── data/
│   ├── agents.json       # os moradores
│   └── world.json        # os lugares e os acontecimentos possíveis
├── viewer/
│   ├── index.html        # painel 2D (mapa da vila)
│   ├── 3d.html           # cena 3D navegável
│   └── three.min.js      # biblioteca 3D, embutida (licença MIT junto)
├── viewer.py              # servidor local do painel
├── state/                 # criado ao rodar (memórias + estado + log)
└── main.py
```

## Próximos passos possíveis

- **Diálogo turno-a-turno**: hoje a conversa acontece "em diferido" (um fala, o
  outro responde no tick seguinte). Dá pra detectar quando dois estão no mesmo
  local e alternar 3-4 falas seguidas entre eles antes de avançar o tick.
- **Resolver acontecimentos**: hoje eles expiram sozinhos após 6 ticks. Dá pra
  fazer um agente declarar que resolveu e chamar `world.resolve_incident()`.
- **Relacionamentos explícitos**: uma matriz de afinidade entre eles que sobe e
  desce conforme as interações, alimentando o prompt de volta.
- **Fofoca**: hoje ninguém comenta sobre uma terceira pessoa. A Iris pode achar
  o Teo falso e nunca mencionar isso pra Marina. Fofoca faria a opinião se
  espalhar entre quem nem presenciou o fato.
