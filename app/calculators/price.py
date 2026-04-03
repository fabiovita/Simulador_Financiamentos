"""
Calculadora da Tabela PRICE (Sistema Francês de Amortização).
Prestação fixa, amortização crescente, juros decrescentes.
"""
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd


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
) -> pd.DataFrame:
    """
    Retorna DataFrame com as colunas:
    parcela, vencimento, saldo_inicial, juros, amortizacao, prestacao, saldo_final
    """
    rows = []
    saldo = valor
    pmt = None

    for i in range(1, num_parcelas + 1):
        vencimento = primeira_parcela + relativedelta(months=i - 1)
        juros = saldo * taxa_mensal

        if i <= carencia:
            # Durante carência total: sem pagamento, juros capitalizados
            prestacao = 0.0
            amort = 0.0
            saldo_final = saldo + juros
        else:
            if pmt is None:
                pmt = calcular_pmt(saldo, taxa_mensal, num_parcelas - carencia)
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
