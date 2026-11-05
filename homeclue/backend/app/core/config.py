from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da Homeclue, lida de variáveis de ambiente / .env.

    Toda integração externa é opcional: sem as chaves, o produto continua
    funcionando em modo degradado (busca por regras em vez de IA, troca de
    plano manual em vez de Stripe).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./homeclue.db"

    jwt_secret_key: str = "troque-esta-chave-antes-de-ir-para-producao"
    jwt_algorithm: str = "HS256"
    jwt_expira_minutos: int = 60 * 12

    # IA (Claude). O modelo é configurável porque o custo por busca é o que
    # decide o preço da assinatura — veja o relatório de custo no /admin.html.
    anthropic_api_key: str | None = None
    anthropic_modelo: str = "claude-opus-5-5"

    # Stripe — sem STRIPE_SECRET_KEY o checkout fica desativado.
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_preco_essencial: str | None = None
    stripe_preco_profissional: str | None = None
    stripe_preco_premium: str | None = None
    # Cobrança por resultado: preço "metered" ligado a um Meter do Stripe.
    stripe_preco_por_lead: str | None = None
    stripe_evento_lead: str = "homeclue_lead"
    # Maquete 3D avulsa (pagamento único por imóvel, fora do Premium).
    stripe_preco_maquete: str | None = None

    # Preços exibidos dos planos (R$/mês). Ficam em variável porque o
    # documento de produto deixa o preço "a definir" depois de medir o custo de IA.
    preco_plano_essencial: int = 297
    preco_plano_profissional: int = 497
    preco_plano_premium: int = 997

    # URL pública do app (snippet do widget, retornos do Stripe, User-Agent).
    url_publica: str = "http://localhost:8000"

    ambiente: str = "desenvolvimento"

    # E-mails (separados por vírgula) com acesso ao painel do dono do SaaS.
    admin_emails: str = ""

    # Envio de e-mail por SMTP (Resend, Brevo, Amazon SES, Gmail…): "esqueci
    # minha senha" e aviso de novo lead. Sem SMTP_HOST, o e-mail só vai para o log.
    smtp_host: str = ""
    smtp_porta: int = 587  # 587 = STARTTLS; 465 = TLS direto
    smtp_usuario: str = ""
    smtp_senha: str = ""
    email_remetente: str = "Homeclue <nao-responda@homeclue.com.br>"

    # Fila de tarefas (feed, contexto do bairro, análise de fotos).
    tarefas_em_segundo_plano: bool = True
    feed_intervalo_horas: int = 6
    # Só para testes locais: permite baixar feed de endereço de rede interna.
    permitir_feed_rede_privada: bool = False

    # Uma ou mais instâncias do Overpass, separadas por vírgula (tenta em ordem).
    overpass_url: str = "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter"
    nominatim_url: str = "https://nominatim.openstreetmap.org"

    @property
    def database_url_normalizada(self) -> str:
        # Railway/Heroku entregam "postgres://" (o SQLAlchemy 2 não aceita) ou
        # "postgresql://" (o SQLAlchemy 2.1 tentaria o driver psycopg 3, que não
        # instalamos). Os dois viram psycopg2; driver explícito fica como está.
        for prefixo in ("postgres://", "postgresql://"):
            if self.database_url.startswith(prefixo):
                return "postgresql+psycopg2://" + self.database_url[len(prefixo):]
        return self.database_url

    @property
    def lista_admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def user_agent(self) -> str:
        return f"Homeclue/1.0 (+{self.url_publica})"


@lru_cache
def obter_settings() -> Settings:
    return Settings()
