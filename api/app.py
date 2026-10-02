import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import router

# O uvicorn configura apenas os próprios loggers, então sem isto os logs da
# aplicação (incluindo os tempos de cada etapa em agent/core.py) não aparecem.
# Fica aqui, e não em main.py, porque com reload=True é este módulo que o
# processo worker importa.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Cria instância da aplicação FastAPI
app = FastAPI(
    title="FilmPro API",
    description="API de recomendação inteligente de filmes usando IA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configura CORS para acessos externos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ HEALTH CHECKS ============

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Verificar saúde da API",
    description="Retorna o status da API"
)
async def health_check():
    """Endpoint simples para verificar se a API está online."""
    return {
        "status": "ok",
        "service": "FilmPro API",
        "version": "1.0.0"
    }


@app.get(
    "/",
    tags=["Sistema"],
    summary="Informações da API",
    description="Retorna informações sobre a API FilmPro"
)
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "name": "FilmPro API",
        "description": "Sistema de recomendação inteligente de filmes",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "recommendations": "/recommendations",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

app.include_router(router)