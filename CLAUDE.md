# CLAUDE.md

Este arquivo orienta o Claude Code (claude.ai/code) ao trabalhar com o código deste repositório.

## Idioma

Comunique-se com o usuário **sempre em português-br**. Isso vale para respostas, explicações, mensagens de commit e descrições de PR.

## Projeto

FilmPro é um serviço FastAPI que devolve recomendações de filmes estruturadas. Quem gera as recomendações é um agente [Agno](https://docs.agno.com) rodando sobre o Anthropic Claude. Prompts, descrições de campos, mensagens da API e a saída do agente estão todos em **português (pt-BR)**, então todo texto novo voltado ao usuário e todo conteúdo de prompt também deve ser escrito em português.

O `README.md` é a apresentação do projeto para quem visita o repositório; o `spec.md` traz o contrato da API, as regras de negócio e as decisões de arquitetura. Ao mudar comportamento (campos da resposta, regras, cache, integração com o OMDb), atualize o `spec.md` junto. O provedor do modelo é a Anthropic e as dependências são gerenciadas com `uv`.

## Comandos

As dependências são gerenciadas com `uv` (`pyproject.toml` + `uv.lock`, Python 3.12).

```bash
uv sync                      # instala as dependências no .venv
uv run python main.py        # sobe a API com uvicorn em 0.0.0.0:8000 (com reload)
uv add <pacote>              # adiciona uma dependência
```

Com a API rodando, a documentação interativa fica em `/docs` (Swagger) e `/redoc`. Endpoint principal:

```bash
curl -X POST localhost:8000/recommendations -H "Content-Type: application/json" \
  -d '{"preferences": "Gosto de ficção científica dos anos 80 e thrillers psicológicos"}'
```

O campo `preferences` deve ter entre 10 e 500 caracteres. Uma requisição leva cerca de 12s, quase toda nela a chamada ao modelo; consultas repetidas são servidas do cache em memória.

Ainda não há suíte de testes, linter nem formatador configurados.

## Variáveis de ambiente obrigatórias

Arquivo `.env` na raiz do repositório, carregado por `agent/config.py` via `python-dotenv`:

- `ANTHROPIC_API_KEY`
- `OMDB_API_KEY`

`Config.validate()` roda **no momento do import** em `agent/core.py` e em `agent/tools/omdb.py`. Por isso, importar qualquer coisa de `agent` (inclusive subir a API) falha na hora se alguma das duas chaves estiver faltando.

## Arquitetura

Fluxo de uma requisição: `main.py` → `api/app.py` (app FastAPI, CORS, `/` e `/health`) → `api/routers.py` (`POST /recommendations`) → `agent.core.recommendations()` → `Agent.arun()` do Agno (etapa 1) → OMDb em paralelo (etapa 2) → `MovieRecommendation`.

O agente **não tem ferramentas**. Ele faz uma única chamada ao modelo e devolve apenas curadoria e texto em português (`SeedList`); os dados factuais vêm depois, do OMDb, em paralelo.

Essa divisão é a decisão de desempenho central do projeto, e vem de medição: o tempo de resposta é quase linear nos tokens de saída do modelo (~110 tokens/s). Quando o modelo também escrevia diretor, elenco, nota, duração e pôster, eram 3814 tokens de saída e 40s por requisição; os mesmos dados vindos do OMDb custam 0,3s, e o total caiu para ~12s. **Qualquer campo novo que o modelo tenha que escrever custa tempo de resposta.** Antes de adicionar um campo ao `SeedList`, verifique se o OMDb já o fornece.

- **`agent/core.py`**: cria um único `movie_recommendation_agent` no nível do módulo, com `output_schema=SeedList` e sem ferramentas. `recommendations()` orquestra as duas etapas, faz o merge e guarda o resultado num cache em memória por preferência normalizada (TTL de 1h). Loga o tempo de cada etapa (`llm=... omdb=...`), que é como regressões de latência aparecem.
- **`agent/models/movies.py`**: dois grupos de schemas, e a distinção importa. `MovieSeed`/`SeedList` é o que o **modelo escreve** — as strings em `Field(description=...)` vão para o modelo como parte do schema de saída estruturada, então editá-las muda o comportamento dele e o custo da requisição. `Movie`/`MovieRecommendation` é o que a **API devolve**, e os nomes dos campos seguem o que `site/index.html` já lê (`year`, `duration`, `language`, e não `release_year`, `duration_minutes`, `primary_language`).
- **`agent/prompts/movie_search.py`**: o `description` e as `instructions` do agente, mais as constantes `MOVIE_COUNT` (10) e `TEXT_LIMIT` (140). Duas regras são de desempenho, não de estilo: o limite de caracteres em `synopsis` e `recommendation_reason` evita que o modelo se solte (uma consulta chegou a 4089 tokens e 35s sem ele), e a exigência de **título original do IMDb, sem tradução e sem o ano** é o que faz a busca no OMDb casar — um título traduzido devolve o filme sem pôster.
- **`agent/tools/omdb.py`**: cliente do OMDb, **não** é mais ferramenta do agente. `search_movies()` resolve a lista inteira em paralelo com uma única `ClientSession`. `search_movie()` tenta três estratégias antes de desistir (título + ano → título sozinho → busca aproximada e depois `imdbID`), porque o ano do modelo às vezes diverge do OMDb. Mantém o padrão de devolver ausência de dados em vez de lançar exceção: um filme sem resposta do OMDb ainda é exibido com o que o modelo gerou. Atenção: o OMDb responde `Response: True` com todos os campos em `"N/A"`, então checar só o `Response` não basta — daí o `_is_complete()`.
- **`agent/enrich.py`**: o merge `seed + OMDb → Movie` e os mapas `GENRE_PT`, `LANG_PT` e `RATING_PT`. O OMDb responde em inglês e todo texto do FilmPro é em pt-BR; como são listas fechadas, a tradução é estática em vez de pedida ao modelo, o que custa zero tokens e é determinístico. Valor desconhecido cai no original em vez de desaparecer.

Dois detalhes de empacotamento afetam os imports:

- A aplicação roda a partir da raiz do repositório e importa `api` e `agent` como pacotes de nível superior. Eles não fazem parte do pacote instalável. `src/film_pro_v1/` é só o esqueleto gerado pelo `uv init` para o script `film-pro-v1` e não é usado pela aplicação.
- `agent/` não tem `__init__.py` e funciona como namespace package. `agent/init.py` é um arquivo vazio, provavelmente um `__init__.py` com o nome digitado errado.

`design/` guarda um export estático de design em HTML/CSS. Nenhum código o referencia.
