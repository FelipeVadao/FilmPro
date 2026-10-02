
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.core import recommendations 
from agent.models.movies import MovieRecommendation

router = APIRouter()

class RecommendationRequest(BaseModel):
    preferences: str = Field(
        description="Descrição das preferências do usuário para filmes",
        min_length=10,
        max_length=500,
    )

class RecommendationResponse(BaseModel):
    success: bool = Field(
        ..., description="Indica se a recomendação foi bem-sucedida"
    )
    data: MovieRecommendation = Field(..., description="Dados das recomendações")
    message: str = Field(default="Recomendações geradas com sucesso", description="Mensagem informativa")    

@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Obter recomendações de filmes",
    description="Gera recomendações personalizadas de filmes baseadas nas preferências do usuário",
    tags=["Recomendações"]
)
async def get_recommendations(request: RecommendationRequest)->RecommendationResponse:
    try:
        # Executa o agente com as preferências do usuário
        recommendations_resp = await recommendations(request.preferences)
        
        if not recommendations_resp:
            raise HTTPException(
                status_code=500,
                detail="Falha ao gerar recomendações. Tente novamente."
            )

        return RecommendationResponse(
            success=True,
            data=recommendations_resp,
            message="Recomendações geradas com sucesso"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar recomendações: {str(e)}"
    )