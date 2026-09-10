"""
Extrator do "Demonstrativo do Plano de Pagamento" do Sicoob.

Funciona com o PDF emitido pelo sistema (camada de texto). Foto de tela ou
documento escaneado não passa por aqui — nesses casos a página cai no modo colar.
"""
import re
from datetime import date, datetime
from typing import List, Optional

from analise.modelo import Proposta, ParcelaPlano
from analise.extratores.texto import extrair_texto

NOME = "Sicoob"

# Linha do plano: parcela, vencimento, amortização, valor, IOF, juros, perc, saldo
LINHA_PLANO = re.compile(
    r"^\s*(\d{1,3})\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
    r"\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s*$",
    re.M,
)


def reconhece(texto: str) -> bool:
    return "SICOOB" in texto.upper() and "PLANO DE PAGAMENTO" in texto.upper()


def extrair(caminho_pdf: str) -> Proposta:
    texto = extrair_texto(caminho_pdf)
    if not reconhece(texto):
        raise ValueError("O arquivo não parece um demonstrativo do Sicoob.")

    parcelas = [
        ParcelaPlano(
            numero=int(m.group(1)),
            vencimento=_data(m.group(2)),
            amortizacao=_num(m.group(3)),
            valor_parcela=_num(m.group(4)),
            iof=_num(m.group(5)),
            juros=_num(m.group(6)),
            saldo_devedor=_num(m.group(8)),
        )
        for m in LINHA_PLANO.finditer(texto)
    ]
    if not parcelas:
        raise ValueError(
            "Nenhuma linha do plano de pagamento foi encontrada. Se o PDF for uma foto "
            "ou digitalização, use a opção de colar o plano."
        )

    data_proposta = _data(_campo(texto, "Data da Proposta", r"(\d{2}/\d{2}/\d{4})"))

    proposta = Proposta(
        data_proposta=data_proposta,
        parcelas=parcelas,
        banco=NOME,
        linha=(_campo(texto, "Linha", r"(\d+-[^\n]+?)\s{2,}") or "").strip(),
        sistema=(_campo(texto, "Indicador de Cálculo", r"([A-ZÇ ]+?)\s*\*?\s*\n") or "").strip(),
        valor_proposta=_num(_campo(texto, "Valor da Proposta")) or 0.0,
        valor_contratado=_num(_campo(texto, "Valor Contratado")) or 0.0,
        valor_liberado=_num(_campo(texto, "Valor Liberado")) or 0.0,
        iof=_num(_campo(texto, "Valor IOF")) or 0.0,
        tac=_num(_campo(texto, "Valor TAC")) or 0.0,
        seguro=_num(_campo(texto, "Valor Seguro")) or 0.0,
        financia_iof=_sim(texto, "Financia IOF"),
        financia_tac=_sim(texto, "Financia TAC"),
        financia_seguro=_sim(texto, "Financia Seguro Prest"),
        despesas_adicionais=_num(_campo(texto, "Despesas Adicionais")) or 0.0,
        taxa_nominal_am=_percentual(_campo(texto, "Taxa de Juros Nominal", r"([\d,]+)% a\.m\.")),
        cet_aa_informado=_percentual(
            _campo(texto, "CET", r"[\d,]+% a\.m\. */ *([\d,]+)% a\.a\.")
        ),
        indice_pos=_indice_pos(texto),
        perc_pos=_percentual_bruto(_campo(texto, "% Pós", r"([\d.,]+)")),
        origem="pdf",
        arquivo=caminho_pdf.split("/")[-1],
    )

    proposta.totais_impressos = _totais(texto, parcelas)
    return proposta


# ── Auxiliares de leitura ─────────────────────────────────────────────────────

def _campo(texto: str, rotulo: str, padrao: str = r"([\d.]+,\d{2})") -> Optional[str]:
    m = re.search(re.escape(rotulo) + r"\s*:?\s*" + padrao, texto)
    return m.group(1) if m else None


def _num(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    return float(s.replace(".", "").replace(",", "."))


def _percentual(s: Optional[str]) -> Optional[float]:
    """'1,7500' → 0.0175 (decimal)."""
    v = _num(s)
    return v / 100 if v is not None else None


def _percentual_bruto(s: Optional[str]) -> Optional[float]:
    """'100,0000' → 100.0 (mantém como percentual)."""
    return _num(s)


def _data(s: Optional[str]) -> date:
    if not s:
        raise ValueError("Data da proposta não encontrada no documento.")
    return datetime.strptime(s, "%d/%m/%Y").date()


def _sim(texto: str, rotulo: str) -> bool:
    m = re.search(re.escape(rotulo) + r"\s*:?\s*(Sim|Não|Nao)", texto, re.I)
    return bool(m) and m.group(1).lower() == "sim"


def _indice_pos(texto: str) -> Optional[str]:
    """
    Campo que denuncia proposta pós-fixada. Sem ele, a taxa nominal impressa seria
    lida como a taxa da operação, quando é apenas o spread sobre o indexador.
    """
    m = re.search(r"Índice Pós\s*:?\s*([A-Za-z]+)", texto)
    if not m:
        return None
    valor = m.group(1).strip().upper()
    return valor if valor not in ("", "0", "NAO", "NÃO") else None


def _totais(texto: str, parcelas: List[ParcelaPlano]) -> dict:
    """Totais impressos no documento — servem de checksum da extração."""
    totais = {}

    m = re.search(
        r"Totais\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", texto
    )
    if m:
        totais["total_amortizacao"] = _num(m.group(1))
        totais["total_parcelas"] = _num(m.group(2))
        totais["total_iof"] = _num(m.group(3))
        totais["total_juros"] = _num(m.group(4))

    n = _campo(texto, "Parcelas", r"(\d+)")
    if n:
        totais["num_parcelas"] = int(n)

    return totais
