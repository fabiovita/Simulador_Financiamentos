"""
Reconstrução do plano a partir da capa da proposta, quando não se tem o plano de
pagamento parcela a parcela.

Confiável apenas em proposta prefixada. Em pós-fixada a taxa impressa é só o
spread sobre o indexador, e reconstruir por ela devolve um custo irreconhecível —
na opção A da Rafamed, 5,99% a.a. contra 20,93% reais. Por isso `reconstruir`
recusa esse caso.
"""
from datetime import date
from typing import List

from dateutil.relativedelta import relativedelta

from analise.modelo import ParcelaPlano
from calculators.sac import calcular_sac
from calculators.price import calcular_price


class PosFixadaSemPlano(ValueError):
    """Levantada quando se tenta reconstruir uma proposta indexada a CDI/SELIC."""


def reconstruir(
    saldo_inicio_amortizacao: float,
    taxa_mensal: float,
    num_parcelas: int,
    primeiro_vencimento: date,
    sistema: str = "SAC",
    data_base: date = None,
    pos_fixada: bool = False,
) -> List[ParcelaPlano]:
    """
    `data_base` é a data em que os juros da primeira parcela começam a correr —
    o fim da carência, ou a liberação quando não há carência. É o que permite
    contar os dias reais do primeiro período, que raramente são 30.
    """
    if pos_fixada:
        raise PosFixadaSemPlano(
            "Proposta pós-fixada não pode ser reconstruída pela capa: a taxa impressa é "
            "apenas o spread sobre o indexador. Use o plano de pagamento."
        )
    if num_parcelas < 1:
        raise ValueError("Número de parcelas inválido.")

    calc = calcular_sac if sistema.upper().startswith("SAC") else calcular_price
    df = calc(
        saldo_inicio_amortizacao,
        taxa_mensal,
        num_parcelas,
        primeiro_vencimento,
        0,
        "capitalizado",
        convencao="dias",
        data_base=data_base,
    )

    return [
        ParcelaPlano(
            numero=int(linha["parcela"]),
            vencimento=linha["vencimento"],
            valor_parcela=float(linha["prestacao"]),
            amortizacao=float(linha["amortizacao"]),
            juros=float(linha["juros"]),
            saldo_devedor=float(linha["saldo_inicial"]),
        )
        for _, linha in df.iterrows()
    ]


def saldo_sugerido(valor_contratado: float, taxa_mensal: float, meses_carencia: int) -> float:
    """
    Sugestão para o campo de saldo no início da amortização, capitalizando a
    carência mês a mês. O valor impresso pela proposta ("Saldo Término da
    Carência") prevalece sempre que existir — a convenção de dias do banco na
    carência pode diferir desta conta.
    """
    if meses_carencia <= 0:
        return valor_contratado
    return valor_contratado * (1 + taxa_mensal) ** meses_carencia
