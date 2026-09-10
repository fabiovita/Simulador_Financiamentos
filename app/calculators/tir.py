"""
Taxa interna de retorno sobre fluxos com datas irregulares (equivalente ao XTIR do Excel).

Usado para achar o custo efetivo de uma proposta a partir do fluxo de caixa real:
o líquido que entra na liberação contra as parcelas nas datas de vencimento.
"""
from datetime import date
from typing import List, Tuple

Fluxo = List[Tuple[date, float]]


def xnpv(taxa: float, fluxos: Fluxo) -> float:
    """Valor presente líquido com datas. A primeira data é a referência."""
    d0 = fluxos[0][0]
    return sum(v / (1 + taxa) ** ((d - d0).days / 365.0) for d, v in fluxos)


def xirr(fluxos: Fluxo, lo: float = -0.99, hi: float = 10.0, iteracoes: int = 200) -> float:
    """
    TIR anual por bisseção. Convergência garantida no intervalo, sem depender de
    chute inicial — ao contrário de Newton-Raphson, que oscila em fluxos com carência.

    Retorna a taxa anual efetiva (0.2797 = 27,97% a.a.).
    """
    if len(fluxos) < 2:
        raise ValueError("O fluxo precisa de ao menos uma entrada e uma saída.")

    fluxos = sorted(fluxos, key=lambda f: f[0])

    if xnpv(lo, fluxos) * xnpv(hi, fluxos) > 0:
        raise ValueError(
            "A TIR não existe no intervalo pesquisado — confira os sinais do fluxo "
            "(a liberação entra negativa, as parcelas positivas)."
        )

    for _ in range(iteracoes):
        meio = (lo + hi) / 2
        if xnpv(meio, fluxos) > 0:
            lo = meio
        else:
            hi = meio
    return (lo + hi) / 2


def anual_para_mensal(taxa_anual: float) -> float:
    """0.2797 a.a. → 0.0208 a.m."""
    return (1 + taxa_anual) ** (1 / 12) - 1


def mensal_para_anual(taxa_mensal: float) -> float:
    """0.0175 a.m. → 0.2314 a.a."""
    return (1 + taxa_mensal) ** 12 - 1
