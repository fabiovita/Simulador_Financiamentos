"""
Formato normalizado de uma proposta de financiamento.

É o contrato entre a extração (específica de cada banco) e o cálculo (universal):
qualquer extrator devolve estas estruturas, e todo o resto do módulo trabalha só
sobre elas, sem saber de que banco o dado veio.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict


@dataclass
class ParcelaPlano:
    """Uma linha do plano de pagamento. Só numero, vencimento e valor são obrigatórios."""
    numero: int
    vencimento: date
    valor_parcela: float
    amortizacao: Optional[float] = None
    juros: Optional[float] = None
    iof: Optional[float] = None
    saldo_devedor: Optional[float] = None


@dataclass
class Proposta:
    data_proposta: date
    parcelas: List[ParcelaPlano]

    # Identificação
    banco: str = ""
    linha: str = ""
    sistema: str = ""

    # Dinheiro
    valor_proposta: float = 0.0
    valor_contratado: float = 0.0
    valor_liberado: float = 0.0
    iof: float = 0.0
    tac: float = 0.0
    seguro: float = 0.0
    financia_iof: bool = False
    financia_tac: bool = False
    financia_seguro: bool = False
    despesas_adicionais: float = 0.0

    # Taxas informadas pelo banco
    taxa_nominal_am: Optional[float] = None      # decimal: 0.0175 = 1,75% a.m.
    cet_aa_informado: Optional[float] = None     # decimal: 0.2797 = 27,97% a.a.
    indice_pos: Optional[str] = None             # "CDI", "SELIC" ou None se prefixada
    perc_pos: Optional[float] = None             # 100.0 = 100% do índice

    # Rastreabilidade
    totais_impressos: Optional[Dict[str, float]] = None  # checksum vindo do documento
    origem: str = "manual"                                # "pdf" | "colado" | "capa"
    arquivo: str = ""

    @property
    def pos_fixada(self) -> bool:
        """
        Proposta indexada a CDI/SELIC. Quando é o caso, a taxa nominal impressa é
        apenas o spread, e reconstruir o plano a partir dela produz um custo
        irreconhecível (na Rafamed: 5,99% a.a. contra 20,93% reais).
        """
        return bool(self.indice_pos) and bool(self.perc_pos)

    @property
    def descontado_na_liberacao(self) -> float:
        """Despesas que saem do valor liberado em vez de entrarem no contrato."""
        total = 0.0
        if not self.financia_iof:
            total += self.iof
        if not self.financia_tac:
            total += self.tac
        if not self.financia_seguro:
            total += self.seguro
        return total

    @property
    def liquido_recebido(self) -> float:
        """
        O dinheiro que efetivamente entra no caixa — base da TIR que interessa.
        É esta conta que separa R$ 400.000,00 (tudo financiado) de R$ 384.450,60
        (IOF e TAC descontados na liberação) em duas propostas do mesmo valor.
        """
        return self.valor_liberado - self.descontado_na_liberacao

    @property
    def total_pago(self) -> float:
        return sum(p.valor_parcela for p in self.parcelas)

    @property
    def num_parcelas(self) -> int:
        return len(self.parcelas)
