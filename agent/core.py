"""Orquestra a geração de recomendações em duas etapas.

O agente não tem ferramentas: ele faz uma única chamada ao modelo e devolve
apenas curadoria e texto. Os dados factuais vêm depois, do OMDb, em paralelo.

Essa divisão existe por causa de uma medição: o tempo de resposta é quase
linear nos tokens de saída do modelo (~110 tokens/s). Pedir ao modelo que
escrevesse também diretor, elenco, nota, duração e pôster custava 3814 tokens
de saída e 29s; os mesmos dados vindos do OMDb custam 0,3s.
"""

import logging
import re
import time
from typing import Optional

from agno.agent import Agent
from agno.models.anthropic import Claude

from .config import Config
from .enrich import merge
from .models.movies import MovieRecommendation, SeedList
from .prompts import description, instructions
from .tools.omdb import search_movies

Config.validate()

logger = logging.getLogger(__name__)

movie_recommendation_agent = Agent(
    name="FilmPro",
    model=Claude(id="claude-sonnet-5", api_key=Config.ANTHROPIC_API_KEY),
    description=description,
    instructions=instructions,
    output_schema=SeedList,
    markdown=False,
)

# Cache das recomendações por preferência. O custo da etapa 1 é o do modelo,
# então repetir a mesma consulta é o único caso em que há ganho real de cache
# (o OMDb já responde em 0,3s).
_CACHE_TTL_SECONDS = 3600
_CACHE_LIMIT = 128
_cache: dict[str, tuple[float, MovieRecommendation]] = {}


def _cache_key(preferences: str) -> str:
    return re.sub(r"\s+", " ", preferences.strip().lower())


def _cache_get(key: str) -> Optional[MovieRecommendation]:
    entry = _cache.get(key)
    if not entry:
        return None
    created_at, value = entry
    if time.time() - created_at > _CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: MovieRecommendation) -> None:
    if len(_cache) >= _CACHE_LIMIT:
        oldest = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest]
    _cache[key] = (time.time(), value)


async def recommendations(preferences: str) -> Optional[MovieRecommendation]:
    """Gera recomendações de filmes a partir das preferências do usuário."""
    key = _cache_key(preferences)

    cached = _cache_get(key)
    if cached:
        logger.info("recomendações servidas do cache")
        return cached

    # Etapa 1: curadoria e texto (a parte lenta, uma chamada ao modelo).
    started = time.perf_counter()
    result = await movie_recommendation_agent.arun(preferences, stream=False)
    llm_elapsed = time.perf_counter() - started

    if not result or not result.content or not result.content.movies:
        logger.warning("o agente não devolveu recomendações")
        return None

    seeds = result.content.movies

    # Etapa 2: dados factuais do OMDb, todos em paralelo.
    started = time.perf_counter()
    omdb_rows = await search_movies([(seed.title, seed.release_year) for seed in seeds])
    omdb_elapsed = time.perf_counter() - started

    movies = [merge(seed, row) for seed, row in zip(seeds, omdb_rows)]

    found = sum(1 for row in omdb_rows if row)
    logger.info(
        "recomendações geradas: %d filmes | llm=%.2fs omdb=%.2fs | OMDb %d/%d",
        len(movies),
        llm_elapsed,
        omdb_elapsed,
        found,
        len(movies),
    )

    data = MovieRecommendation(movies=movies, total_recommendations=len(movies))
    _cache_set(key, data)

    return data
