"""
Calculadora do Sistema de Amortização Constante (SAC).
Amortização fixa, parcelas decrescentes.
"""
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd


def calcular_sac(
    valor: float,
    taxa_mensal: float,
    num_parcelas: int,
    primeira_parcela: date,
    carencia: int = 0,
) -> pd.DataFrame:
    """
    Retorna DataFrame com as colunas:
    parcela, vencimento, saldo_inicial, juros, amortizacao, prestacao, saldo_final
    """
    rows = []
    saldo = valor
    amortizacao = None

    for i in range(1, num_parcelas + 1):
        vencimento = primeira_parcela + relativedelta(months=i - 1)
        juros = saldo * taxa_mensal

        if i <= carencia:
            # Durante carência total: sem pagamento, juros capitalizados
            prestacao = 0.0
            amort = 0.0
            saldo_final = saldo + juros
        else:
            if amortizacao is None:
                amortizacao = saldo / (num_parcelas - carencia)
            amort = amortizacao
            prestacao = juros + amort
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
