"""
Indicadores de uma proposta. Universal: opera só sobre o formato normalizado,
sem saber de que banco veio o dado.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from calculators.tir import xirr, anual_para_mensal, mensal_para_anual
from analise.modelo import Proposta


@dataclass
class Indicadores:
    # O número de destaque: custo efetivo sobre o que entrou no caixa
    tir_real_aa: float
    tir_real_am: float
    # Juros que o próprio plano embute, sobre o valor contratado
    tir_plano_aa: float
    tir_plano_am: float

    custo_total: float
    custo_sobre_liquido: float
    custo_por_real: float

    liquido_recebido: float
    total_pago: float

    primeira_parcela: float
    maior_parcela: float
    menor_parcela: float
    parcela_media: float

    desembolso_por_ano: Dict[int, float]
    desembolso_12m: float

    cet_informado_aa: Optional[float] = None
    divergencia_cet: Optional[float] = None       # tir_real − cet informado, em decimal
    indexador_implicito: Optional[float] = None   # CDI/SELIC que o plano projeta

    fluxo_real: List[Tuple[date, float]] = field(default_factory=list)
    fluxo_plano: List[Tuple[date, float]] = field(default_factory=list)


def calcular(proposta: Proposta) -> Indicadores:
    if not proposta.parcelas:
        raise ValueError("A proposta não tem parcelas para calcular.")

    parcelas = sorted(proposta.parcelas, key=lambda p: p.vencimento)
    saidas = [(p.vencimento, p.valor_parcela) for p in parcelas]

    liquido = proposta.liquido_recebido
    fluxo_real = [(proposta.data_proposta, -liquido)] + saidas
    fluxo_plano = [(proposta.data_proposta, -proposta.valor_contratado)] + saidas

    tir_real = xirr(fluxo_real)
    tir_plano = xirr(fluxo_plano)

    total_pago = proposta.total_pago
    custo_total = total_pago - liquido
    valores = [p.valor_parcela for p in parcelas]

    # Desembolso por ano civil
    por_ano: Dict[int, float] = {}
    for p in parcelas:
        por_ano[p.vencimento.year] = por_ano.get(p.vencimento.year, 0.0) + p.valor_parcela

    # 12 meses contados da data da proposta
    limite = _mais_meses(proposta.data_proposta, 12)
    desembolso_12m = sum(p.valor_parcela for p in parcelas if p.vencimento <= limite)

    divergencia = None
    if proposta.cet_aa_informado is not None:
        divergencia = tir_real - proposta.cet_aa_informado

    # Em proposta pós-fixada, o plano projeta um indexador que a taxa nominal não mostra.
    # O desconto é composto: (1+juros do plano)/(1+spread) − 1.
    indexador = None
    if proposta.pos_fixada and proposta.taxa_nominal_am is not None:
        spread_aa = mensal_para_anual(proposta.taxa_nominal_am)
        indexador = (1 + tir_plano) / (1 + spread_aa) - 1

    return Indicadores(
        tir_real_aa=tir_real,
        tir_real_am=anual_para_mensal(tir_real),
        tir_plano_aa=tir_plano,
        tir_plano_am=anual_para_mensal(tir_plano),
        custo_total=custo_total,
        custo_sobre_liquido=custo_total / liquido if liquido else 0.0,
        custo_por_real=total_pago / liquido if liquido else 0.0,
        liquido_recebido=liquido,
        total_pago=total_pago,
        primeira_parcela=valores[0],
        maior_parcela=max(valores),
        menor_parcela=min(valores),
        parcela_media=sum(valores) / len(valores),
        desembolso_por_ano=dict(sorted(por_ano.items())),
        desembolso_12m=desembolso_12m,
        cet_informado_aa=proposta.cet_aa_informado,
        divergencia_cet=divergencia,
        indexador_implicito=indexador,
        fluxo_real=fluxo_real,
        fluxo_plano=fluxo_plano,
    )


def comparar(a: Proposta, b: Proposta) -> Dict[str, Tuple[float, float, float]]:
    """
    Confronta duas propostas. Devolve {indicador: (valor A, valor B, diferença B−A)}.
    A comparação em reais é a que não depende de convenção de taxa — foi ela que
    decidiu o caso Rafamed, onde os CETs impressos não eram comparáveis entre si.
    """
    ia, ib = calcular(a), calcular(b)
    campos = [
        ("liquido_recebido", ia.liquido_recebido, ib.liquido_recebido),
        ("total_pago", ia.total_pago, ib.total_pago),
        ("custo_total", ia.custo_total, ib.custo_total),
        ("custo_por_real", ia.custo_por_real, ib.custo_por_real),
        ("tir_real_aa", ia.tir_real_aa, ib.tir_real_aa),
        ("maior_parcela", ia.maior_parcela, ib.maior_parcela),
        ("desembolso_12m", ia.desembolso_12m, ib.desembolso_12m),
    ]
    return {nome: (va, vb, vb - va) for nome, va, vb in campos}


def _mais_meses(d: date, meses: int) -> date:
    ano = d.year + (d.month - 1 + meses) // 12
    mes = (d.month - 1 + meses) % 12 + 1
    dia = min(d.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return date(ano, mes, dia)
