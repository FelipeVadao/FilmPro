import os
from dotenv import load_dotenv

# carrega o arquivo .env 
load_dotenv()

class Config:
    """Gerenciador de configurações centralizado."""

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OMDB_API_KEY = os.getenv("OMDB_API_KEY")

    @classmethod
    def validate(cls):
        """Valida se as variáveis de ambiente obrigatórias estão definidas."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY não está definida no arquivo .env")
        if not cls.OMDB_API_KEY:
            raise ValueError("OMDB_API_KEY não está definida no arquivo .env")
