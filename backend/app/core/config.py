from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente / .env.

    Nenhum segredo tem valor padrão sensível aqui — quem roda em produção
    é obrigado a definir JWT_SECRET_KEY explicitamente (ver validação em
    app.main na inicialização).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./kaza_ia.db"

    jwt_secret_key: str = "troque-esta-chave-antes-de-ir-para-producao"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60

    anthropic_api_key: str | None = None

    cors_origens: str = "http://localhost:8000,http://127.0.0.1:8000"

    ambiente: str = "desenvolvimento"

    @property
    def lista_cors_origens(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origens.split(",") if origem.strip()]


@lru_cache
def obter_settings() -> Settings:
    return Settings()
