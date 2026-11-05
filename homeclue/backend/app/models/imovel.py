from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Imovel(Base):
    """Um anúncio. Campos numéricos opcionais são None quando o anúncio não
    informa — e a busca diz "não informado" em vez de chutar (trava contra
    invenção)."""

    __tablename__ = "imoveis"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    origem: Mapped[str] = mapped_column(String(10), default="manual", nullable=False)  # "manual" | "feed"
    codigo_referencia: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)  # ver services.vocabulario.TIPOS
    finalidade: Mapped[str] = mapped_column(String(15), default="venda", nullable=False)  # venda | aluguel | venda_aluguel
    preco: Mapped[float] = mapped_column(Float, nullable=False)  # venda; ou aluguel mensal se finalidade == "aluguel"
    preco_aluguel: Mapped[float | None] = mapped_column(Float, nullable=True)  # só quando "venda_aluguel"
    condominio: Mapped[float | None] = mapped_column(Float, nullable=True)
    iptu: Mapped[float | None] = mapped_column(Float, nullable=True)

    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(300), nullable=True)
    mostrar_endereco: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    coordenadas_aproximadas: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    quartos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suites: Mapped[int | None] = mapped_column(Integer, nullable=True)
    banheiros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vagas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_terreno: Mapped[float | None] = mapped_column(Float, nullable=True)

    descricao: Mapped[str] = mapped_column(Text, default="", nullable=False)
    caracteristicas: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    # Itens do anúncio que não estão no vocabulário (ex.: "Fogão a lenha"), guardados como vieram.
    comodidades: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    fotos: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)  # [{"url", "legenda"}]
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_drone_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url_anuncio: Mapped[str | None] = mapped_column(String(500), nullable=True)

    corretor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    # Premium: planta com cômodos desenhados ({"imagem": url, "comodos": [...]}).
    planta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    maquete_liberada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Calculados em segundo plano (services.tarefas).
    contexto: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contexto_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    analise_fotos: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    removido_do_feed_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="imoveis")
    corretor: Mapped["Usuario | None"] = relationship()

    @property
    def visivel(self) -> bool:
        return self.ativo and self.removido_do_feed_em is None

    def preco_para(self, finalidade: str | None) -> float:
        """Preço que importa para quem quer comprar ou alugar."""
        if finalidade == "aluguel" and self.finalidade == "venda_aluguel" and self.preco_aluguel:
            return self.preco_aluguel
        return self.preco

    def atende_finalidade(self, finalidade: str | None) -> bool:
        if not finalidade:
            return True
        return self.finalidade == finalidade or self.finalidade == "venda_aluguel"
