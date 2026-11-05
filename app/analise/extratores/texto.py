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

    # Captura bytes e decodifica aqui: com text=True o Python usa a codificação do
    # sistema (cp1252 no servidor Windows), que não define o byte 0x8d do "Í" em UTF-8.
    # No Windows esse erro morre na thread de leitura e stdout volta None, sem exceção.
    proc = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-layout", caminho_pdf, "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        erro = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Falha ao ler o PDF: {erro}")
    return proc.stdout.decode("utf-8", errors="replace")
