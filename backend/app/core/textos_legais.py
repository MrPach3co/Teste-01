"""Textos de consentimento versionados.

Guardamos o texto (não só um booleano) junto com o aceite do usuário no
banco, para termos prova do que exatamente foi consentido. Se o texto
mudar no futuro, crie uma nova constante (ex. TEXTO_CONSENTIMENTO_LGPD_V2)
em vez de editar esta — os aceites antigos continuam válidos para a versão
que existia quando foram dados.
"""

TEXTO_CONSENTIMENTO_LGPD_V1 = (
    "Concordo que a Kaza IA armazene meu e-mail e, se eu criar conta, minha "
    "senha (de forma criptografada) e minhas buscas salvas, para os fins de "
    "fornecer o serviço e me contatar sobre o produto. Posso pedir a "
    "exportação ou exclusão dos meus dados a qualquer momento, conforme a "
    "Lei Geral de Proteção de Dados (LGPD)."
)
