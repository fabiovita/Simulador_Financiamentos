"""
Registry de extratores por banco.

Acrescentar um banco é escrever um módulo com `reconhece(texto)` e `extrair(pdf)`
e registrá-lo aqui — nada no cálculo muda.
"""
from typing import List, Optional

from analise.modelo import Proposta
from analise.extratores import sicoob
from analise.extratores.texto import extrair_texto, disponivel, PdftotextAusente

EXTRATORES = [sicoob]


def detectar(caminho_pdf: str):
    """Devolve o módulo capaz de ler o arquivo, ou None."""
    texto = extrair_texto(caminho_pdf)
    for mod in EXTRATORES:
        if mod.reconhece(texto):
            return mod
    return None


def extrair(caminho_pdf: str) -> Proposta:
    mod = detectar(caminho_pdf)
    if mod is None:
        raise ValueError(
            "Nenhum extrator reconhece este documento. Bancos suportados: "
            + ", ".join(m.NOME for m in EXTRATORES)
            + ". Se o PDF for uma foto ou digitalização, use a opção de colar o plano."
        )
    return mod.extrair(caminho_pdf)


def bancos_suportados() -> List[str]:
    return [m.NOME for m in EXTRATORES]
