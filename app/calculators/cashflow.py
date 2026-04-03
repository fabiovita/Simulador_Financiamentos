"""
Gerador de fluxo de caixa consolidado para todos os empréstimos ativos de um cliente.
"""
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List
import pandas as pd

from calculators.sac import calcular_sac
from calculators.price import calcular_price
from models import Emprestimo


def gerar_fluxo_caixa(emprestimos: List[Emprestimo], meses: int = 24) -> pd.DataFrame:
    """
    Para cada empréstimo ativo, calcula as parcelas futuras a partir de hoje
    e retorna DataFrame consolidado agrupado por mês:

    Colunas: mes (date), credor, prestacao
    """
    hoje = date.today()
    registros = []

    for emp in emprestimos:
        if emp.status != "ativo":
            continue

        primeira = date.fromisoformat(emp.primeira_parcela)

        if emp.tabela == "SAC":
            df = calcular_sac(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)
        else:
            df = calcular_price(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)

        # Filtra apenas parcelas futuras (a partir deste mês)
        limite = hoje + relativedelta(months=meses)
        for _, row in df.iterrows():
            venc = row["vencimento"]
            if venc >= hoje.replace(day=1) and venc <= limite:
                registros.append({
                    "mes": venc.replace(day=1),  # agrupa pelo 1º dia do mês
                    "credor": emp.credor,
                    "produto": emp.produto or emp.credor,
                    "prestacao": row["prestacao"],
                })

    if not registros:
        return pd.DataFrame(columns=["mes", "credor", "produto", "prestacao"])

    df_total = pd.DataFrame(registros)
    return df_total.sort_values("mes")
