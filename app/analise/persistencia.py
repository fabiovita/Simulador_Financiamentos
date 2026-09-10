"""
Conversão entre a Proposta em memória e as linhas do banco.

Fica aqui, e não em database.py, para que a camada de dados continue sem saber
do módulo de análise.
"""
from datetime import date
from typing import List, Tuple

import database as db
from models import PropostaSalva, ParcelaSalva
from analise.modelo import Proposta, ParcelaPlano


def salvar(proposta: Proposta, cliente_id: int, apelido: str) -> int:
    cabecalho = PropostaSalva(
        cliente_id=cliente_id,
        apelido=apelido,
        banco=proposta.banco,
        linha=proposta.linha,
        sistema=proposta.sistema,
        data_proposta=proposta.data_proposta.isoformat(),
        valor_proposta=proposta.valor_proposta,
        valor_contratado=proposta.valor_contratado,
        valor_liberado=proposta.valor_liberado,
        iof=proposta.iof,
        tac=proposta.tac,
        seguro=proposta.seguro,
        financia_iof=proposta.financia_iof,
        financia_tac=proposta.financia_tac,
        financia_seguro=proposta.financia_seguro,
        taxa_nominal_am=proposta.taxa_nominal_am,
        cet_aa_informado=proposta.cet_aa_informado,
        indice_pos=proposta.indice_pos,
        perc_pos=proposta.perc_pos,
        origem=proposta.origem,
        arquivo=proposta.arquivo,
    )
    parcelas = [
        ParcelaSalva(
            proposta_id=0,  # preenchido pelo insert
            numero=p.numero,
            vencimento=p.vencimento.isoformat(),
            valor_parcela=p.valor_parcela,
            amortizacao=p.amortizacao,
            juros=p.juros,
            iof=p.iof,
            saldo_devedor=p.saldo_devedor,
        )
        for p in proposta.parcelas
    ]
    return db.inserir_proposta(cabecalho, parcelas)


def carregar(proposta_id: int) -> Proposta:
    cab = db.buscar_proposta(proposta_id)
    if cab is None:
        raise ValueError(f"Proposta {proposta_id} não encontrada.")
    linhas = db.listar_parcelas_proposta(proposta_id)

    return Proposta(
        data_proposta=date.fromisoformat(cab.data_proposta),
        parcelas=[
            ParcelaPlano(
                numero=x.numero,
                vencimento=date.fromisoformat(x.vencimento),
                valor_parcela=x.valor_parcela,
                amortizacao=x.amortizacao,
                juros=x.juros,
                iof=x.iof,
                saldo_devedor=x.saldo_devedor,
            )
            for x in linhas
        ],
        banco=cab.banco or "",
        linha=cab.linha or "",
        sistema=cab.sistema or "",
        valor_proposta=cab.valor_proposta or 0.0,
        valor_contratado=cab.valor_contratado or 0.0,
        valor_liberado=cab.valor_liberado or 0.0,
        iof=cab.iof or 0.0,
        tac=cab.tac or 0.0,
        seguro=cab.seguro or 0.0,
        financia_iof=cab.financia_iof,
        financia_tac=cab.financia_tac,
        financia_seguro=cab.financia_seguro,
        taxa_nominal_am=cab.taxa_nominal_am,
        cet_aa_informado=cab.cet_aa_informado,
        indice_pos=cab.indice_pos,
        perc_pos=cab.perc_pos,
        origem=cab.origem or "manual",
        arquivo=cab.arquivo or "",
    )
