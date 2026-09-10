"""
Juros de um período, conforme a convenção de contagem.

Os bancos contam dias corridos; o simulador, por padrão, conta meses cheios. A
diferença aparece sempre que o intervalo entre vencimentos não é de 30 dias — na
proposta FGI da Rafamed, os 36 dias entre o fim da carência e o primeiro
vencimento respondem por R$ 1.615,22 na primeira parcela.
"""
from datetime import date
from dateutil.relativedelta import relativedelta


def _juros_periodo(saldo: float, taxa_mensal: float, anterior: date,
                   vencimento: date, convencao: str) -> float:
    if convencao != "dias":
        return saldo * taxa_mensal

    if anterior is None:
        anterior = vencimento - relativedelta(months=1)

    dias = (vencimento - anterior).days
    if dias <= 0:
        return 0.0
    return saldo * ((1 + taxa_mensal) ** (dias / 30) - 1)
