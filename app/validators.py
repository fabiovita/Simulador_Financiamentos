"""
Funções de validação e formatação para CNPJ, CPF, e-mail e telefone.
"""
import re


# ── CNPJ ──────────────────────────────────────────────────────────────────────

def _apenas_digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def validar_cnpj(cnpj: str) -> bool:
    nums = _apenas_digitos(cnpj)
    if len(nums) != 14 or len(set(nums)) == 1:
        return False

    def calcular_digito(nums, pesos):
        soma = sum(int(n) * p for n, p in zip(nums, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calcular_digito(nums[:12], pesos1)
    d2 = calcular_digito(nums[:13], pesos2)

    return nums[12] == str(d1) and nums[13] == str(d2)


def formatar_cnpj(cnpj: str) -> str:
    nums = _apenas_digitos(cnpj)
    if len(nums) != 14:
        return cnpj
    return f"{nums[:2]}.{nums[2:5]}.{nums[5:8]}/{nums[8:12]}-{nums[12:]}"


# ── CPF ───────────────────────────────────────────────────────────────────────

def validar_cpf(cpf: str) -> bool:
    nums = _apenas_digitos(cpf)
    if len(nums) != 11 or len(set(nums)) == 1:
        return False

    def calcular_digito(nums, peso_inicial):
        soma = sum(int(n) * p for n, p in zip(nums, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto >= 10 else resto

    d1 = calcular_digito(nums[:9], 10)
    d2 = calcular_digito(nums[:10], 11)

    return nums[9] == str(d1) and nums[10] == str(d2)


def formatar_cpf(cpf: str) -> str:
    nums = _apenas_digitos(cpf)
    if len(nums) != 11:
        return cpf
    return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"


# ── CPF ou CNPJ (detecta pelo tamanho) ───────────────────────────────────────

def validar_cnpj_cpf(valor: str) -> tuple[bool, str]:
    """
    Retorna (valido, mensagem_erro).
    Aceita CPF (11 dígitos) ou CNPJ (14 dígitos).
    """
    if not valor.strip():
        return True, ""  # campo opcional

    nums = _apenas_digitos(valor)
    if len(nums) == 11:
        if not validar_cpf(valor):
            return False, "CPF inválido. Verifique os dígitos verificadores."
        return True, ""
    elif len(nums) == 14:
        if not validar_cnpj(valor):
            return False, "CNPJ inválido. Verifique os dígitos verificadores."
        return True, ""
    else:
        return False, "Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)."


def formatar_cnpj_cpf(valor: str) -> str:
    nums = _apenas_digitos(valor)
    if len(nums) == 11:
        return formatar_cpf(valor)
    if len(nums) == 14:
        return formatar_cnpj(valor)
    return valor


# ── E-mail ────────────────────────────────────────────────────────────────────

_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validar_email(email: str) -> tuple[bool, str]:
    if not email.strip():
        return True, ""  # campo opcional
    if not _RE_EMAIL.match(email.strip()):
        return False, "E-mail inválido. Use o formato nome@dominio.com"
    return True, ""


# ── Telefone ──────────────────────────────────────────────────────────────────

def validar_telefone(tel: str) -> tuple[bool, str]:
    if not tel.strip():
        return True, ""  # campo opcional
    nums = _apenas_digitos(tel)
    if len(nums) not in (10, 11):
        return False, "Telefone inválido. Use (XX) XXXX-XXXX ou (XX) XXXXX-XXXX."
    return True, ""


def formatar_telefone(tel: str) -> str:
    nums = _apenas_digitos(tel)
    if len(nums) == 11:
        return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
    if len(nums) == 10:
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    return tel
