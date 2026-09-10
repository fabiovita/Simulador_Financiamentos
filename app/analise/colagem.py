"""
Leitura do plano de pagamento colado do PDF ou de uma planilha.

Aceita duas formas:
  1. data e valor na mesma linha, em qualquer separador (tab, ; , ou espaços)
  2. só a coluna de valores — as datas são geradas a partir do primeiro vencimento

Números aceitam o formato brasileiro (1.234,56) e o americano (1234.56).
"""
import re
from datetime import date, datetime
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from analise.modelo import ParcelaPlano

DATA = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
NUMERO = re.compile(r"-?[\d.,]+")


def ler(texto: str, primeiro_vencimento: Optional[date] = None) -> List[ParcelaPlano]:
    linhas = [l.strip() for l in texto.strip().splitlines() if l.strip()]
    if not linhas:
        raise ValueError("Nada foi colado.")

    parcelas: List[ParcelaPlano] = []
    valores_soltos: List[float] = []

    for linha in linhas:
        if _e_cabecalho(linha) or _tem_texto(linha):
            continue

        m = DATA.search(linha)
        if m:
            venc = _data(m)
            valor = _valor_da_linha(linha, m)
            if valor is None:
                continue
            parcelas.append(ParcelaPlano(numero=len(parcelas) + 1,
                                         vencimento=venc, valor_parcela=valor))
        else:
            v = _primeiro_numero(linha)
            if v is not None:
                valores_soltos.append(v)

    if parcelas:
        parcelas.sort(key=lambda p: p.vencimento)
        for i, p in enumerate(parcelas, 1):
            p.numero = i
        return parcelas

    if valores_soltos:
        if primeiro_vencimento is None:
            raise ValueError(
                "O texto colado não traz datas. Informe a data do primeiro vencimento "
                "para que as demais sejam geradas mês a mês."
            )
        return [
            ParcelaPlano(numero=i + 1,
                         vencimento=primeiro_vencimento + relativedelta(months=i),
                         valor_parcela=v)
            for i, v in enumerate(valores_soltos)
        ]

    raise ValueError("Nenhuma parcela reconhecida no texto colado.")


def _tem_texto(linha: str) -> bool:
    """
    Linha do plano é só data e números. Palavra por extenso indica outra coisa —
    tipicamente a linha do Plano de Carência ("... 180 NÃO 411.593,42 ..."), cujo
    prazo em dias seria lido como valor de parcela.
    """
    return bool(re.search(r"[A-Za-zÀ-ÿ]{2,}", linha))


def _e_cabecalho(linha: str) -> bool:
    baixa = linha.lower()
    if any(t in baixa for t in ("parcela", "vencimento", "amortiza", "saldo", "totais", "total")):
        return not DATA.search(linha)
    return False


def _data(m) -> date:
    dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if ano < 100:
        ano += 2000
    return date(ano, mes, dia)


def _valor_da_linha(linha: str, m_data) -> Optional[float]:
    """
    Numa linha do plano, o valor da parcela é o número seguinte à data em quem
    cola só duas colunas. Quando a linha inteira do Sicoob é colada, a ordem é
    amortização, valor da parcela, IOF, juros, percentual e saldo — então o valor
    da parcela é o segundo número após a data.
    """
    resto = linha[m_data.end():]
    # Zeros contam como coluna (o "Perc. %" do Sicoob é 0,00); descartá-los
    # deslocaria a contagem e faria a amortização passar por valor da parcela.
    numeros = [n for n in (_num(t) for t in NUMERO.findall(resto)) if n is not None]
    if not numeros:
        return None
    if len(numeros) >= 6:
        return numeros[1]
    positivos = [n for n in numeros if n > 0]
    return positivos[0] if positivos else None


def _primeiro_numero(linha: str) -> Optional[float]:
    for t in NUMERO.findall(linha):
        v = _num(t)
        if v is not None and v > 0:
            return v
    return None


def _num(t: str) -> Optional[float]:
    t = t.strip()
    if not t or t in (".", ",", "-"):
        return None
    # 1.234,56 (brasileiro) x 1,234.56 (americano): manda o último separador
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None
