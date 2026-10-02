"""Combina a curadoria do agente com os dados factuais do OMDb.

O OMDb responde em inglês, e todo texto voltado ao usuário no FilmPro é em
português. Como os campos traduzidos aqui vêm de listas fechadas (o IMDb usa
cerca de 28 gêneros), mapas estáticos resolvem: custam zero tokens, são
determinísticos e não dependem do modelo. Um valor desconhecido cai no
original em vez de desaparecer.
"""

import re
from typing import Any, Optional

from .models.movies import Cast, Movie, MovieSeed

GENRE_PT = {
    "Action": "Ação",
    "Adult": "Adulto",
    "Adventure": "Aventura",
    "Animation": "Animação",
    "Biography": "Biografia",
    "Comedy": "Comédia",
    "Crime": "Crime",
    "Documentary": "Documentário",
    "Drama": "Drama",
    "Family": "Família",
    "Fantasy": "Fantasia",
    "Film-Noir": "Film Noir",
    "Game-Show": "Game Show",
    "History": "História",
    "Horror": "Terror",
    "Music": "Música",
    "Musical": "Musical",
    "Mystery": "Mistério",
    "News": "Jornalismo",
    "Reality-TV": "Reality",
    "Romance": "Romance",
    "Sci-Fi": "Ficção Científica",
    "Short": "Curta",
    "Sport": "Esporte",
    "Talk-Show": "Talk Show",
    "Thriller": "Suspense",
    "War": "Guerra",
    "Western": "Faroeste",
}

LANG_PT = {
    "Arabic": "Árabe",
    "Bengali": "Bengali",
    "Cantonese": "Cantonês",
    "Czech": "Tcheco",
    "Danish": "Dinamarquês",
    "Dutch": "Holandês",
    "English": "Inglês",
    "Finnish": "Finlandês",
    "French": "Francês",
    "German": "Alemão",
    "Greek": "Grego",
    "Hebrew": "Hebraico",
    "Hindi": "Híndi",
    "Hungarian": "Húngaro",
    "Italian": "Italiano",
    "Japanese": "Japonês",
    "Korean": "Coreano",
    "Latin": "Latim",
    "Mandarin": "Mandarim",
    "Norwegian": "Norueguês",
    "Persian": "Persa",
    "Polish": "Polonês",
    "Portuguese": "Português",
    "Russian": "Russo",
    "Spanish": "Espanhol",
    "Swedish": "Sueco",
    "Thai": "Tailandês",
    "Turkish": "Turco",
}

# O OMDb mistura padrões de cinema e de TV, e inclui valores herdados do
# código de produção antigo dos EUA ("Approved", "Passed").
RATING_PT = {
    "G": "Livre",
    "TV-G": "Livre",
    "TV-Y": "Livre",
    "TV-Y7": "Livre",
    "Approved": "Livre",
    "Passed": "Livre",
    "PG": "PG (10)",
    "TV-PG": "PG (10)",
    "PG-13": "PG-13 (13)",
    "TV-14": "14",
    "R": "R (16)",
    "TV-MA": "18",
    "NC-17": "18",
    "X": "18",
    # Sem informação útil: melhor omitir o campo que exibir "Not Rated".
    "Not Rated": None,
    "Unrated": None,
    "N/A": None,
}

# Quantos atores levar para o front. O card não mostra elenco e o modal
# mostra poucos, então não vale carregar a lista inteira.
MAX_CAST = 4
MAX_GENRES = 3


def _clean(value: Any) -> Optional[str]:
    """Normaliza os vazios do OMDb, que usa a string "N/A" em vez de null."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in ("", "N/A") else text


def _first_int(value: Optional[str]) -> Optional[int]:
    """Extrai o primeiro inteiro, para campos como "117 min" ou "1982–1984"."""
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _translate_genres(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    names = [name.strip() for name in raw.split(",") if name.strip()]
    return [GENRE_PT.get(name, name) for name in names[:MAX_GENRES]]


def _translate_language(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    first = raw.split(",")[0].strip()
    return LANG_PT.get(first, first) or None


def _translate_rating(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    if raw in RATING_PT:
        return RATING_PT[raw]
    return _clean(raw)


def _parse_cast(raw: Optional[str]) -> list[Cast]:
    if not raw:
        return []
    names = [name.strip() for name in raw.split(",") if name.strip()]
    # O OMDb não informa os personagens; o campo fica null, como manda o schema.
    return [Cast(name=name) for name in names[:MAX_CAST]]


def _parse_rating(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def merge(seed: MovieSeed, omdb: Optional[dict[str, Any]]) -> Movie:
    """Monta o filme final a partir da curadoria do agente e dos dados do OMDb.

    Sem resposta do OMDb, o filme é devolvido com o que o agente gerou: o front
    esconde os campos ausentes e exibe o pôster placeholder.
    """
    movie = Movie(
        title=seed.title,
        year=seed.release_year,
        synopsis=seed.synopsis,
        recommendation_reason=seed.recommendation_reason,
        streaming_platforms=seed.streaming_platforms or None,
    )

    if not omdb:
        return movie

    # O título do OMDb é a grafia canônica; o do agente pode ter variações.
    movie.title = _clean(omdb.get("Title")) or seed.title
    movie.year = _first_int(_clean(omdb.get("Year"))) or seed.release_year
    movie.director = _clean(omdb.get("Director"))
    movie.genres = _translate_genres(_clean(omdb.get("Genre")))
    movie.imdb_rating = _parse_rating(_clean(omdb.get("imdbRating")))
    movie.language = _translate_language(_clean(omdb.get("Language")))
    movie.age_rating = _translate_rating(omdb.get("Rated"))
    movie.cast = _parse_cast(_clean(omdb.get("Actors")))
    movie.poster_url = _clean(omdb.get("Poster"))

    minutes = _first_int(_clean(omdb.get("Runtime")))
    movie.duration_minutes = minutes
    # O front renderiza este campo direto, então ele já vem formatado.
    movie.duration = f"{minutes} min" if minutes else None

    return movie
