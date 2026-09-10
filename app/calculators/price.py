"""
Calculadora da Tabela PRICE (Sistema Francês de Amortização).
Prestação fixa, amortização crescente, juros decrescentes.
"""
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd

from calculators.periodo import _juros_periodo


def calcular_pmt(valor: float, taxa_mensal: float, num_parcelas: int) -> float:
    """Fórmula: PMT = PV * [r(1+r)^n] / [(1+r)^n - 1]"""
    r = taxa_mensal
    n = num_parcelas
    return valor * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def calcular_price(
    valor: float,
    taxa_mensal: float,
    num_parcelas: int,
    primeira_parcela: date,
    carencia: int = 0,
    carencia_tipo: str = "capitalizado",
    convencao: str = "mes_cheio",
    data_base: date = None,
) -> pd.DataFrame:
    """
    Retorna DataFrame com as colunas:
    parcela, vencimento, saldo_inicial, juros, amortizacao, prestacao, saldo_final

    convencao: "mes_cheio" (default) ou "dias" — ver calculators/periodo.py.
    data_base: início da contagem de juros da primeira linha quando convencao="dias".
    """
    rows = []
    saldo = valor
    pmt = None
    anterior = data_base

    total_meses = carencia + num_parcelas
    for i in range(1, total_meses + 1):
        vencimento = primeira_parcela + relativedelta(months=i - 1)
        juros = _juros_periodo(saldo, taxa_mensal, anterior, vencimento, convencao)
        anterior = vencimento

        if i <= carencia:
            if carencia_tipo == "juros_pagos":
                # Paga apenas os juros; saldo não se altera
                prestacao = juros
                amort = 0.0
                saldo_final = saldo
            else:
                # Capitalizado: sem pagamento, juros incorporados ao saldo
                prestacao = 0.0
                amort = 0.0
                saldo_final = saldo + juros
        else:
            if pmt is None:
                pmt = calcular_pmt(saldo, taxa_mensal, num_parcelas)
            amort = pmt - juros
            prestacao = pmt
            saldo_final = max(saldo - amort, 0.0)

        rows.append({
            "parcela": i,
            "vencimento": vencimento,
            "saldo_inicial": round(saldo, 2),
            "juros": round(juros, 2),
            "amortizacao": round(amort, 2),
            "prestacao": round(prestacao, 2),
            "saldo_final": round(saldo_final, 2),
        })

        saldo = saldo_final

    return pd.DataFrame(rows)
