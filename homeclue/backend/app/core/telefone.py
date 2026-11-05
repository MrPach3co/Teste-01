import re


def so_digitos(telefone: str | None) -> str:
    return re.sub(r"\D", "", telefone or "")


def numero_whatsapp(telefone: str | None) -> str | None:
    """Número no formato do wa.me (com DDI). Números brasileiros sem DDI
    (10 ou 11 dígitos) ganham o 55 na frente."""
    digitos = so_digitos(telefone)
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    return digitos if 12 <= len(digitos) <= 15 else None
