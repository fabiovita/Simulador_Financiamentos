"""
Extração de texto de PDF via pdftotext (poppler).

Isolado num módulo próprio para que os extratores de cada banco não repitam a
checagem de dependência externa.
"""
import shutil
import subprocess
from functools import lru_cache


class PdftotextAusente(RuntimeError):
    pass


def disponivel() -> bool:
    return shutil.which("pdftotext") is not None


@lru_cache(maxsize=32)
def extrair_texto(caminho_pdf: str) -> str:
    """
    Devolve o texto do PDF preservando o layout em colunas (-layout), que é o que
    mantém as linhas do plano de pagamento alinhadas para a regex.
    """
    if not disponivel():
        raise PdftotextAusente(
            "O utilitário pdftotext não está instalado. Instale com: brew install poppler"
        )

    proc = subprocess.run(
        ["pdftotext", "-layout", caminho_pdf, "-"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao ler o PDF: {proc.stderr.strip()}")
    return proc.stdout
