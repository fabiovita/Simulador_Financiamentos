"""
Reconciliação entre o que foi extraído e o que o banco imprimiu.

Nenhum número sai daqui sem bater com algo impresso no próprio documento. É a
diferença entre "não confere, revise" e entregar um valor errado com cara de certo
— o modo de falha que este módulo existe para evitar.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from analise.modelo import Proposta

TOLERANCIA = 0.02  # centavos de arredondamento


@dataclass
class Checagem:
    nome: str
    impresso: Optional[float]
    calculado: float
    ok: bool
    observacao: str = ""
    # Bloqueante = falha indica erro de leitura, e o resultado não deve ser exibido.
    # Não bloqueante = divergência informativa, que é a própria análise (ver CET abaixo).
    bloqueante: bool = True

    @property
    def diferenca(self) -> Optional[float]:
        if self.impresso is None:
            return None
        return self.calculado - self.impresso


@dataclass
class Resultado:
    checagens: List[Checagem] = field(default_factory=list)

    @property
    def confere(self) -> bool:
        """Verdadeiro se toda checagem bloqueante possível passou."""
        return all(c.ok for c in self.checagens if c.impresso is not None and c.bloqueante)

    @property
    def houve_checagem(self) -> bool:
        return any(c.impresso is not None and c.bloqueante for c in self.checagens)

    @property
    def falhas(self) -> List[Checagem]:
        return [c for c in self.checagens
                if c.impresso is not None and c.bloqueante and not c.ok]

    @property
    def alertas(self) -> List[Checagem]:
        """Divergências que não invalidam a leitura, mas contam algo sobre a proposta."""
        return [c for c in self.checagens
                if c.impresso is not None and not c.bloqueante and not c.ok]


def conferir(proposta: Proposta, tir_real_aa: Optional[float] = None) -> Resultado:
    """
    Confere a proposta contra os totais que o banco imprimiu.

    `tir_real_aa` é opcional: quando informado, o CET impresso também é usado como
    verificação. Divergência aí não significa erro de leitura — pode ser CET
    calculado só sobre o spread, como na opção pós-fixada da Rafamed —, por isso
    entra com observação em vez de reprovar a extração.
    """
    res = Resultado()
    totais = proposta.totais_impressos or {}

    soma_parcelas = sum(p.valor_parcela for p in proposta.parcelas)
    impresso_parcelas = totais.get("total_parcelas")
    res.checagens.append(Checagem(
        nome="Total das parcelas",
        impresso=impresso_parcelas,
        calculado=soma_parcelas,
        ok=impresso_parcelas is None or abs(soma_parcelas - impresso_parcelas) <= TOLERANCIA,
        observacao="Soma da coluna do plano contra a linha de totais do documento.",
    ))

    for chave, rotulo, atributo in (
        ("total_amortizacao", "Total de amortização", "amortizacao"),
        ("total_juros", "Total de juros", "juros"),
        ("total_iof", "Total de IOF", "iof"),
    ):
        impresso = totais.get(chave)
        if impresso is None:
            continue
        valores = [getattr(p, atributo) for p in proposta.parcelas]
        if any(v is None for v in valores):
            continue
        soma = sum(valores)
        res.checagens.append(Checagem(
            nome=rotulo,
            impresso=impresso,
            calculado=soma,
            ok=abs(soma - impresso) <= TOLERANCIA,
        ))

    # Contagem de parcelas informada no cabeçalho
    esperado = totais.get("num_parcelas")
    if esperado is not None:
        res.checagens.append(Checagem(
            nome="Quantidade de parcelas",
            impresso=float(esperado),
            calculado=float(len(proposta.parcelas)),
            ok=int(esperado) == len(proposta.parcelas),
            observacao="Linhas lidas contra o campo 'Parcelas' do cabeçalho.",
        ))

    if tir_real_aa is not None and proposta.cet_aa_informado is not None:
        dif = abs(tir_real_aa - proposta.cet_aa_informado)
        bate = dif <= 0.0005  # 0,05 p.p.
        obs = ("O CET impresso reproduz o plano de pagamento."
               if bate else
               "O CET impresso não reproduz o plano. Em proposta pós-fixada isso costuma "
               "significar CET calculado só sobre o spread; confira o campo Índice Pós.")
        res.checagens.append(Checagem(
            nome="CET informado × recalculado",
            impresso=proposta.cet_aa_informado,
            calculado=tir_real_aa,
            ok=bate,
            observacao=obs,
            bloqueante=False,
        ))

    return res
