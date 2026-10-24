from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração do Kaza Pro, lida de variáveis de ambiente / .env.

    Tudo que é integração externa (IA, pagamentos) é opcional: sem as
    chaves, o produto continua funcionando em modo degradado — busca por
    regras em vez de IA, e troca de plano manual em vez de Stripe.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./kaza_pro.db"

    jwt_secret_key: str = "troque-esta-chave-antes-de-ir-para-producao"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60 * 12

    anthropic_api_key: str | None = None

    # Stripe — se STRIPE_SECRET_KEY ficar vazio, o checkout fica desativado
    # e o painel mostra os planos sem botão de pagamento.
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_preco_pro: str | None = None  # price_... do plano Pro
    stripe_preco_escala: str | None = None  # price_... do plano Escala

    # URL pública do app (usada nos links de retorno do Stripe e no snippet do widget).
    url_publica: str = "http://localhost:8000"

    ambiente: str = "desenvolvimento"

    @property
    def database_url_normalizada(self) -> str:
        # Railway/Heroku entregam "postgres://", que o SQLAlchemy 2 não aceita.
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg2://", 1)
        return self.database_url


@lru_cache
def obter_settings() -> Settings:
    return Settings()
