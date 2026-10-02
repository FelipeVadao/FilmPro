from pydantic import BaseModel, Field
from typing import Optional, List


# ============ SCHEMA DE GERAÇÃO (o que o modelo escreve) ============
#
# Só os campos que o modelo sabe melhor que uma base de dados: curadoria e
# texto em português. Os dados factuais vêm do OMDb em agent/enrich.py.
#
# As descrições abaixo vão para o modelo como parte do schema de saída
# estruturada, então elas governam o comportamento dele. Cada campo a mais
# aqui custa tokens de saída, e tokens de saída são tempo de resposta.


class MovieSeed(BaseModel):
    """Recomendação crua do agente, antes do enriquecimento."""
    title: str = Field(
        ...,
        description=(
            "Título ORIGINAL exato do filme como registrado no IMDb. "
            "NUNCA traduza e NUNCA inclua o ano. Ex: 'The Terminator', "
            "não 'O Exterminador do Futuro (1984)'"
        ),
    )
    release_year: int = Field(..., description="Ano de lançamento original, 4 dígitos")
    synopsis: str = Field(
        ..., description="UMA frase em português, no máximo 140 caracteres"
    )
    recommendation_reason: str = Field(
        ...,
        description=(
            "UMA frase em português, no máximo 140 caracteres, conectando "
            "diretamente às preferências citadas pelo usuário"
        ),
    )
    streaming_platforms: Optional[List[str]] = Field(
        None, description="Plataformas de streaming no Brasil, se souber"
    )


class SeedList(BaseModel):
    """Saída estruturada do agente."""
    movies: List[MovieSeed] = Field(..., description="Filmes recomendados")


# ============ SCHEMA DE RESPOSTA (o que a API devolve) ============
#
# Os nomes dos campos seguem o que site/index.html já lê. Renomear aqui faz
# pôster, ano, duração e idioma voltarem a aparecer no front sem alterar
# uma linha de JavaScript.


class Cast(BaseModel):
    """Informações sobre membro do elenco"""
    name: str = Field(..., description="Nome do ator/atriz")
    character: Optional[str] = Field(None, description="Nome do personagem interpretado")


class Movie(BaseModel):
    """Filme já enriquecido, pronto para o front."""
    title: str = Field(..., description="Título do filme")
    year: Optional[int] = Field(None, description="Ano de lançamento")
    director: Optional[str] = Field(None, description="Diretor principal")
    genres: List[str] = Field(default_factory=list, description="Gêneros, em português")
    imdb_rating: Optional[float] = Field(None, description="Classificação IMDb")
    duration: Optional[str] = Field(None, description="Duração formatada, ex: '117 min'")
    duration_minutes: Optional[int] = Field(None, description="Duração em minutos")
    language: Optional[str] = Field(None, description="Idioma principal, em português")
    synopsis: str = Field(..., description="Sinopse breve, em português")
    age_rating: Optional[str] = Field(None, description="Classificação etária")
    content_warnings: Optional[List[str]] = Field(None, description="Avisos de conteúdo")
    cast: List[Cast] = Field(default_factory=list, description="Elenco notável")
    poster_url: Optional[str] = Field(None, description="URL do pôster")
    streaming_platforms: Optional[List[str]] = Field(
        None, description="Plataformas de streaming"
    )
    recommendation_reason: str = Field(..., description="Por que este filme foi recomendado")


class MovieRecommendation(BaseModel):
    """Resposta estruturada com múltiplas recomendações"""
    movies: List[Movie] = Field(..., description="Lista de filmes recomendados")
    total_recommendations: int = Field(..., description="Quantidade de filmes recomendados")
