# FilmPro: especificação técnica

Este documento descreve como o FilmPro funciona por dentro: o fluxo de uma requisição, o contrato da API, as regras de negócio e as decisões de arquitetura. Para a visão geral do projeto e para rodá-lo, veja o [README](README.md).

## Fluxo de uma requisição

```
site/index.html
  └─ POST /recommendations
      └─ api/routers.py
          └─ agent.core.recommendations()
              ├─ cache em memória ─── acerto? devolve na hora
              ├─ Etapa 1: agente Agno + Claude (1 chamada, sem ferramentas)
              │     └─ SeedList: título, ano, sinopse, motivo, plataformas
              ├─ Etapa 2: OMDb, um filme por requisição, todas em paralelo
              │     └─ pôster, diretor, elenco, nota, duração, gêneros, idioma, classificação
              └─ merge + tradução (agent/enrich.py) → MovieRecommendation
```

| Etapa | Tempo típico |
|---|---|
| Etapa 1 (modelo) | 11 a 14 s |
| Etapa 2 (OMDb, 10 filmes) | cerca de 0,3 s |
| Consulta repetida (cache) | instantânea |

O agente não usa ferramentas. Ele faz uma única chamada ao modelo, e quem consulta o OMDb é o backend, depois que o modelo termina.

## API

### `POST /recommendations`

Gera as recomendações.

**Requisição**

```json
{
  "preferences": "Gosto de ficção científica dos anos 80 e thrillers psicológicos"
}
```

| Campo | Tipo | Regra |
|---|---|---|
| `preferences` | string | entre 10 e 500 caracteres |

**Resposta `200`**

```json
{
  "success": true,
  "message": "Recomendações geradas com sucesso",
  "data": {
    "total_recommendations": 10,
    "movies": [
      {
        "title": "Blade Runner",
        "year": 1982,
        "director": "Ridley Scott",
        "genres": ["Ação", "Drama", "Ficção Científica"],
        "imdb_rating": 8.1,
        "duration": "117 min",
        "duration_minutes": 117,
        "language": "Inglês",
        "age_rating": "R (16)",
        "synopsis": "Um caçador de androides persegue replicantes fugitivos em uma Los Angeles distópica.",
        "recommendation_reason": "Clássico essencial da ficção científica dos anos 80 que você pediu.",
        "cast": [
          { "name": "Harrison Ford", "character": null },
          { "name": "Rutger Hauer", "character": null },
          { "name": "Sean Young", "character": null }
        ],
        "poster_url": "https://m.media-amazon.com/images/M/...jpg",
        "streaming_platforms": ["Netflix"],
        "content_warnings": null
      }
    ]
  }
}
```

**Erros**

| Status | Quando |
|---|---|
| `422` | `preferences` ausente, com menos de 10 ou mais de 500 caracteres |
| `500` | falha ao gerar as recomendações; a mensagem vem em `detail` |

### `GET /health`

Verificação de disponibilidade. O front-end usa este endpoint para mostrar o indicador "API ativa".

```json
{ "status": "ok", "service": "FilmPro API", "version": "1.0.0" }
```

### `GET /`

Nome, versão e lista de endpoints. A documentação interativa fica em `/docs` (Swagger) e `/redoc`.

## Modelos de dados

Os schemas ficam em `agent/models/movies.py` e se dividem em dois grupos com papéis diferentes.

### O que o modelo escreve: `MovieSeed` / `SeedList`

| Campo | Descrição |
|---|---|
| `title` | título **original** exato do IMDb, sem tradução e sem o ano |
| `release_year` | ano de lançamento, 4 dígitos |
| `synopsis` | uma frase em português, até 140 caracteres |
| `recommendation_reason` | uma frase em português, até 140 caracteres, ligada às preferências |
| `streaming_platforms` | plataformas no Brasil, opcional |

As descrições em `Field(description=...)` vão para o modelo como parte do schema de saída estruturada. Editá-las muda o comportamento do curador.

### O que a API devolve: `Movie` / `MovieRecommendation`

| Campo | Origem |
|---|---|
| `title` | OMDb (grafia canônica); se não houver, o do modelo |
| `year` | OMDb; se não houver, o do modelo |
| `director`, `imdb_rating`, `poster_url` | OMDb |
| `genres`, `language`, `age_rating` | OMDb, traduzidos para o português |
| `duration`, `duration_minutes` | OMDb (`"117 min"` e `117`) |
| `cast` | OMDb, até 4 atores, `character` sempre `null` |
| `synopsis`, `recommendation_reason`, `streaming_platforms` | modelo |
| `content_warnings` | reservado; hoje sempre `null` |

Os nomes dos campos seguem o que `site/index.html` lê (`year`, `duration`, `language`).

## Regras de negócio

- Cada resposta tem **exatamente 10 filmes** (`MOVIE_COUNT` em `agent/prompts/movie_search.py`).
- Sinopse e motivo têm **uma frase de até 140 caracteres** cada (`TEXT_LIMIT`).
- Todo texto voltado ao usuário é em **português**. Títulos de filmes e nomes de pessoas ficam no original.
- O curador deve variar gêneros e décadas, não repetir filmes, priorizar nota IMDb 7.5+ e ordenar por relevância.
- Campos sem informação vêm como `null` ou lista vazia, nunca como string vazia ou `"N/A"`.
- Um filme que o OMDb não encontra **continua na lista**, com os dados do modelo. O front-end esconde o que falta e mostra um pôster genérico.

## Integração com o OMDb

Cliente em `agent/tools/omdb.py`. Todas as buscas de uma requisição correm em paralelo, numa única sessão HTTP, com timeout de 8 s por chamada.

Cada título passa por até três tentativas:

1. título + ano
2. só o título, porque o ano do modelo às vezes difere do OMDb
3. busca aproximada (`s=`) e, com o `imdbID` do primeiro resultado, busca exata (`i=`)

Antes da busca, um ano colado no título é removido (`"Memento (2000)"` vira `"Memento"`). Uma resposta só é aceita se tiver diretor, porque o OMDb pode responder `Response: True` com todos os campos em `"N/A"`.

Falhas nunca derrubam a requisição: o filme fica sem os dados factuais.

## Tradução para o português

O OMDb responde em inglês. `agent/enrich.py` traduz com mapas fixos:

- `GENRE_PT`: os cerca de 28 gêneros do IMDb (`Sci-Fi` → `Ficção Científica`, `Thriller` → `Suspense`)
- `LANG_PT`: os idiomas mais comuns (`English` → `Inglês`)
- `RATING_PT`: classificações de cinema e TV dos EUA para um padrão único (`R` → `R (16)`, `PG-13` → `PG-13 (13)`). `Not Rated` e `Unrated` viram `null`.

Um valor fora do mapa aparece no original, em vez de sumir.

## Cache

| Cache | Chave | Validade | Limite |
|---|---|---|---|
| Recomendações (`agent/core.py`) | preferências em minúsculas, espaços normalizados | 1 hora | 128 entradas; sai a mais antiga |
| OMDb (`agent/tools/omdb.py`) | título limpo + ano | enquanto o processo viver | 512 entradas; esvazia ao lotar |

Os dois ficam em memória, por processo. Reiniciar a API limpa ambos.

## Front-end

`site/index.html` é uma página única, sem build, com Tailwind via CDN.

- Chama a API em `http://localhost:8000` (constante `API_BASE`).
- Mostra cards em grade com skeleton durante a espera e um modal de detalhes ao clicar.
- A busca tem timeout de 45 s; o indicador de saúde, de 4 s.

## Configuração

| Variável | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | chamada ao Claude |
| `OMDB_API_KEY` | consulta ao OMDb |

As duas vêm do arquivo `.env` na raiz e são obrigatórias. A validação roda no import de `agent/core.py` e `agent/tools/omdb.py`, então a API nem sobe se faltar alguma. O `.env` está no `.gitignore`.

## Decisões de arquitetura

**O modelo só escreve o que só ele sabe.** O tempo de resposta cresce quase em linha reta com os tokens que o modelo gera. Numa versão anterior, o modelo escrevia todos os 14 campos de cada filme: eram cerca de 3.800 tokens de saída e 40 s por requisição, e os pôsteres vinham vazios. Com o modelo limitado à curadoria e ao texto, e o OMDb fornecendo os fatos, a requisição caiu para cerca de 12 s e os pôsteres passaram a vir em todos os filmes. **Antes de adicionar um campo ao `SeedList`, verifique se o OMDb já o fornece.**

**Limite rígido de texto.** Sem o limite de 140 caracteres, algumas consultas faziam o modelo escrever demais: uma chegou a 4.089 tokens e 35 s. Com o limite, o tempo fica estável entre consultas.

**Sem busca na web.** A versão anterior tinha busca no DuckDuckGo. Ela falhava com frequência e acrescentava uma rodada extra ao modelo, de cerca de 10 s. O conhecimento do modelo, somado ao OMDb, cobre o caso de uso.

**Tradução estática.** Gêneros, idiomas e classificações são listas fechadas. Traduzir com mapas não gasta tokens e dá sempre o mesmo resultado.

## Limitações conhecidas

- `content_warnings` ainda não é preenchido.
- O OMDb às vezes informa o ano de lançamento nos EUA em vez do original (A Viagem de Chihiro aparece como 2003, não 2001).
- O curador não conhece as notas reais ao escolher, então alguns filmes podem ficar abaixo de 7.5.
- O cache é em memória: não é compartilhado entre processos e some quando a API reinicia.
- O CORS aceita qualquer origem (`allow_origins=["*"]`), adequado só para desenvolvimento.
- O endereço da API está fixo no front-end.
- Ainda não há testes automatizados.
