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
