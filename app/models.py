from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Cliente:
    nome: str
    cnpj_cpf: str
    email: str = ""
    telefone: str = ""
    id: Optional[int] = None
    criado_em: Optional[str] = None


@dataclass
class PropostaSalva:
    """
    Cabeçalho de uma proposta analisada, ligada ao cliente. As parcelas ficam em
    ParcelaSalva; juntos, reconstroem a Proposta de analise/modelo.py.
    """
    cliente_id: int
    apelido: str                      # como Fabio identifica a proposta ("Sicoob FGI 42x")
    banco: str = ""
    linha: str = ""
    sistema: str = ""
    data_proposta: str = ""           # ISO "YYYY-MM-DD"
    valor_proposta: float = 0.0
    valor_contratado: float = 0.0
    valor_liberado: float = 0.0
    iof: float = 0.0
    tac: float = 0.0
    seguro: float = 0.0
    financia_iof: bool = False
    financia_tac: bool = False
    financia_seguro: bool = False
    taxa_nominal_am: Optional[float] = None
    cet_aa_informado: Optional[float] = None
    indice_pos: Optional[str] = None
    perc_pos: Optional[float] = None
    origem: str = "manual"            # "pdf" | "colado" | "capa"
    arquivo: str = ""
    id: Optional[int] = None
    criado_em: Optional[str] = None


@dataclass
class ParcelaSalva:
    proposta_id: int
    numero: int
    vencimento: str                   # ISO "YYYY-MM-DD"
    valor_parcela: float
    amortizacao: Optional[float] = None
    juros: Optional[float] = None
    iof: Optional[float] = None
    saldo_devedor: Optional[float] = None
    id: Optional[int] = None


@dataclass
class Emprestimo:
    cliente_id: int
    credor: str
    produto: str
    tabela: str          # "SAC" ou "PRICE"
    valor_liquido: float
    taxa_mensal: float   # em decimal, ex: 0.0132 para 1,32%
    num_parcelas: int
    primeira_parcela: str  # ISO date string "YYYY-MM-DD"
    carencia: int = 0
    carencia_tipo: str = "capitalizado"  # "capitalizado" | "juros_pagos"
    parcelas_pagas: int = 0
    status: str = "ativo"  # "ativo" ou "quitado"
    id: Optional[int] = None
