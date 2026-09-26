# Deixar a vila rodando sem o seu PC

O sistema foi feito pra isso: ele não precisa ficar ligado o tempo todo. Toda a
memória vive em arquivos dentro de `state/`, então dá pra rodar em rajadas
curtas — avança alguns ticks, salva, desliga — e retomar exatamente de onde
parou na próxima vez.

A opção abaixo é **gratuita** (você só paga a API da Anthropic) e não exige
servidor nenhum.

---

## GitHub Actions + GitHub Pages

- **Actions** roda a simulação de tempos em tempos e grava o `state/` de volta
- **Pages** publica o painel 3D num endereço fixo, que você abre de qualquer
  lugar, inclusive do celular

### 1. Criar o repositório

Crie um repositório **privado** no GitHub e suba a pasta do projeto.

> Privado importa: o `state/` fica visível pra quem tiver acesso ao repositório,
> e ele contém tudo que os moradores pensam uns dos outros. Se você não se
> importa que seja público, pode deixar público — só a chave da API é que
> **nunca** pode subir (o `.gitignore` já protege o `.env`).

Pelo terminal, dentro da pasta do projeto:

```bash
git init
git add .
git commit -m "vila inicial"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPO.git
git push -u origin main
```

Confira que o `.env` **não** foi junto:

```bash
git ls-files | findstr .env
```

Se aparecer só `.env.example`, está certo. Se aparecer `.env`, pare e remova
antes de continuar — e troque sua chave, porque ela já vazou.

### 2. Guardar a chave da API

No GitHub: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Secret: sua chave

Secrets não aparecem no código nem nos logs. É assim que a Action usa sua chave
sem ela estar no repositório.

Opcionalmente, na aba **Variables** ao lado, crie `TICKS` com o valor que quiser
(padrão 8, que é um dia de vila por execução).

### 3. Ligar a automação

O arquivo `.github/workflows/vila.yml` já está pronto. Ele roda **de 3 em 3
horas**. Pra mudar o ritmo, edite a linha do `cron`:

```yaml
- cron: "0 */3 * * *"    # de 3 em 3 horas
- cron: "0 */6 * * *"    # de 6 em 6 horas
- cron: "0 12 * * *"     # uma vez por dia, meio-dia UTC
```

Pra testar sem esperar: aba **Actions → Vida na vila → Run workflow**.

> O agendamento do GitHub não é pontual — pode atrasar alguns minutos em
> horários de pico. Pra uma vila isso não faz diferença nenhuma.

### 4. Publicar o painel

**Settings → Pages → Source: Deploy from a branch → Branch: `main`, pasta `/`**

Em um ou dois minutos o painel fica no ar em:

```
https://SEU-USUARIO.github.io/SEU-REPO/
```

O endereço raiz já leva pra versão 3D. A versão 2D fica em `/viewer/index.html`.

O painel lê os arquivos direto do repositório, então ele mostra o estado da
última execução da Action. Ele não atualiza em tempo real como no seu PC — a
vila avança em blocos, quando a Action roda.

---

## Quanto custa

Só a API. Com Haiku e 3 moradores, cada tick sai por volta de **US$ 0,0017**.

| Ritmo | Ticks por dia | Custo por mês |
|---|---|---|
| A cada 6h, 8 ticks | 32 | ~US$ 1,60 |
| A cada 3h, 8 ticks | 64 | ~US$ 3,30 |
| A cada 1h, 8 ticks | 192 | ~US$ 10,00 |

GitHub Actions é grátis pra repositório público e dá 2.000 minutos/mês pra
privado — cada execução dessas leva cerca de 1 minuto, então não chega perto do
limite.

**Proteção importante:** deixe a recarga automática **desligada** no
console.anthropic.com. Assim, se algo sair do controle, a API simplesmente para
quando o crédito acabar, em vez de cobrar mais.

---

## Alternativas

**Servidor 24h (VPS)** — se você quiser a vila avançando continuamente e o
painel ao vivo, aí precisa de uma máquina ligada direto. Oracle Cloud tem um
nível gratuito permanente; Fly.io e Railway têm planos baratos. Aí você roda
`python main.py --ticks 99999 --delay 300` num processo que não morre, e o
`viewer.py` servindo o painel.

**Raspberry Pi ou PC velho em casa** — mesma ideia, custo de energia em vez de
aluguel. Só não resolve seu pedido original, porque ainda depende de uma máquina
sua ligada.

A diferença prática entre GitHub Actions e um servidor é só essa: com Actions a
vila vive em blocos e o painel mostra o último bloco; com servidor ela vive
continuamente e você assiste ao vivo.
