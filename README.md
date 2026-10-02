# 🎬 FilmPro

**Recomendações de filmes com IA, a partir de uma descrição em linguagem natural.**

Você escreve o que tem vontade de assistir, do jeito que falaria com um amigo:

> *"Gosto de ficção científica dos anos 80 e thrillers psicológicos"*

e o FilmPro devolve uma lista de 10 filmes escolhida para você, cada um com:

- 🎞️ **pôster**, ano, duração e nota no IMDb
- 🎭 **elenco** e **direção**
- 🏷️ **gêneros** e classificação etária
- 📝 **sinopse** em português
- 💡 **por que** aquele filme combina com o que você pediu
- 📺 **onde assistir**, quando a informação existe

Todo o conteúdo é em português, mesmo quando a busca é feita em outro idioma.

## Como funciona

O FilmPro combina duas fontes, cada uma fazendo o que faz melhor:

1. **Um curador com IA**, um agente construído com [Agno](https://docs.agno.com) sobre o **Claude** da Anthropic. Ele interpreta as preferências, escolhe os filmes e escreve a sinopse e o motivo de cada recomendação.
2. **Uma base de dados de cinema**, a [OMDb API](https://www.omdbapi.com/). Dela vêm os dados factuais, como pôster, elenco, nota e duração, consultados em paralelo para cada filme.

Assim a IA cuida da curadoria e do texto, e os fatos vêm de uma fonte confiável em vez da memória do modelo.

```
Você descreve o que quer
        │
        ▼
  Curador com IA (Claude)  ──►  escolhe 10 filmes e escreve sinopse e motivo
        │
        ▼
  OMDb, em paralelo        ──►  pôster, elenco, nota, duração, gêneros
        │
        ▼
  Lista pronta na tela
```

Uma recomendação leva cerca de 12 segundos. Buscas repetidas saem de um cache e chegam quase na hora.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| IA | Claude (Anthropic) com o framework de agentes Agno |
| API | Python 3.12, FastAPI, Pydantic |
| Dados de filmes | OMDb API |
| Front-end | HTML e Tailwind CSS, sem build |
| Dependências | uv |

## Rodando localmente

**Pré-requisitos:** Python 3.12, [uv](https://docs.astral.sh/uv/), uma chave da [API da Anthropic](https://console.anthropic.com/) e uma chave gratuita do [OMDb](https://www.omdbapi.com/apikey.aspx).

1. Instale as dependências:

   ```bash
   uv sync
   ```

2. Crie um arquivo `.env` na raiz do projeto com as duas chaves:

   ```env
   ANTHROPIC_API_KEY=sua_chave_da_anthropic
   OMDB_API_KEY=sua_chave_do_omdb
   ```

3. Suba a API (ela fica em `http://localhost:8000`):

   ```bash
   uv run python main.py
   ```

4. Em outro terminal, sirva o front-end e abra `http://localhost:8080` no navegador:

   ```bash
   cd site
   uv run python -m http.server 8080
   ```

A documentação interativa da API fica em `http://localhost:8000/docs`.

Para testar só a API, sem o front-end:

```bash
curl -X POST localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"preferences": "Gosto de ficção científica dos anos 80 e thrillers psicológicos"}'
```

## Estrutura do projeto

```
├── main.py              # ponto de entrada: sobe a API com uvicorn
├── api/                 # app FastAPI e rotas
├── agent/
│   ├── core.py          # orquestra a curadoria e o enriquecimento
│   ├── enrich.py        # junta os dados e traduz para o português
│   ├── models/          # schemas Pydantic
│   ├── prompts/         # instruções do curador
│   └── tools/omdb.py    # cliente da OMDb API
└── site/index.html      # front-end
```

Para os detalhes técnicos (contrato da API, regras de negócio e decisões de arquitetura), veja o [spec.md](spec.md).
