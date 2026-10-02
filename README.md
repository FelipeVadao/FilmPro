# FilmPro - Agente de Recomendação de Filmes

Agente inteligente baseado em IA que fornece recomendações personalizadas de filmes usando **Agno** e **OpenAI**.

## Setup Rápido

```bash
# Criar e ativar venv
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install agno openai "python-dotenv[cli]" ddgs
```

> ⚠️ **Recomendado:** Para melhor controle de versões, use:
> ```bash
> pip install -r requirements.txt
> ```

```bash
# Configurar API key
echo "OPENAI_API_KEY=sua_chave_aqui" > .env

# Executar
dotenv run python main.py
```

## Estrutura

```
├── main.py              # Agente principal
├── prompts/movie_search.py  # Prompts e instruções
└── requirements.txt     # Dependências
```

## Funcionalidades

- 🎬 Recomendações personalizadas de filmes
- 🔍 Busca integrada na web
- 📋 Respostas em Markdown formatado
- 🌍 Suporte a múltiplos critérios (gênero, classificação, idioma)
- 🇧🇷 Respostas em português