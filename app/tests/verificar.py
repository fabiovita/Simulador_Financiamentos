"""
Verificação do módulo de avaliação de propostas.

Roda sem framework: `python3 tests/verificar.py` a partir de app/.
Os valores esperados vêm da planilha PR.Comparativo propostas Sicoob Rafamed set2026.xlsx,
conferida manualmente contra os demonstrativos emitidos pelo Sicoob em 08/09/2026.

As fixtures em tests/fixtures/*.json são os planos já extraídos, para que a
verificação do cálculo não dependa dos PDFs (que ficam fora do git).
"""
import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analise.modelo import Proposta, ParcelaPlano
from analise.calculo import calcular
from analise.conferencia import conferir
from calculators.sac import calcular_sac

AQUI = os.path.dirname(os.path.abspath(__file__))
PDFS = ("/Users/fabiotorres/Library/CloudStorage/OneDrive-Pessoal/prana/Comercial/"
        "Clientes/Ativos/Rafamed/Financeiro/mapeamento das dividas/")

_falhas = []


def checa(nome, obtido, esperado, tol=0.01):
    ok = abs(obtido - esperado) <= tol
    print(f"  {'OK  ' if ok else 'FALHA'}  {nome:44} {obtido:>14,.4f}  (esperado {esperado:,.4f})")
    if not ok:
        _falhas.append(nome)


def checa_bool(nome, obtido, esperado=True):
    ok = obtido == esperado
    print(f"  {'OK  ' if ok else 'FALHA'}  {nome:44} {str(obtido):>14}  (esperado {esperado})")
    if not ok:
        _falhas.append(nome)


def carregar(slug) -> Proposta:
    with open(os.path.join(AQUI, "fixtures", f"{slug}.json")) as f:
        d = json.load(f)
    parcelas = [
        ParcelaPlano(
            numero=p["numero"],
            vencimento=date.fromisoformat(p["vencimento"]),
            valor_parcela=p["valor_parcela"],
            amortizacao=p.get("amortizacao"),
            juros=p.get("juros"),
            iof=p.get("iof"),
            saldo_devedor=p.get("saldo_devedor"),
        )
        for p in d.pop("parcelas")
    ]
    d["data_proposta"] = date.fromisoformat(d["data_proposta"])
    return Proposta(parcelas=parcelas, **d)


# ── Opção A — pós-fixada em CDI ───────────────────────────────────────────────
print("\nRafamed — opção A (PRICE MIX, 48x, pós-fixada em 100% do CDI)")
a = carregar("rafamed_a_posfixada")
ia = calcular(a)
ca = conferir(a, ia.tir_real_aa)

checa("total das parcelas", ia.total_pago, 562_982.94)
checa("líquido recebido (IOF e TAC financiados)", ia.liquido_recebido, 400_000.00)
checa("custo total", ia.custo_total, 162_982.94)
checa("custo por R$ 1,00 que entra", ia.custo_por_real, 1.4075, tol=0.0001)
checa("TIR real (a.a.)", ia.tir_real_aa, 0.2093, tol=0.0005)
checa("TIR do plano (a.a.)", ia.tir_plano_aa, 0.1860, tol=0.0005)
checa("divergência de CET (p.p.)", ia.divergencia_cet, 0.1485, tol=0.0005)
checa("indexador implícito — CDI projetado", ia.indexador_implicito, 0.1373, tol=0.0005)
checa_bool("detectada como pós-fixada", a.pos_fixada)
checa_bool("índice pós é CDI", a.indice_pos == "CDI")
checa_bool("extração confere com os totais impressos", ca.confere)
checa_bool("CET impresso sinalizado como divergente", len(ca.alertas) == 1)

# ── Opção B — prefixada com FGI ───────────────────────────────────────────────
print("\nRafamed — opção B (SAC, 42x, prefixada, 6 meses de carência)")
b = carregar("rafamed_b_fgi")
ib = calcular(b)
cb = conferir(b, ib.tir_real_aa)

checa("total das parcelas", ib.total_pago, 632_421.90)
checa("líquido recebido (IOF e TAC descontados)", ib.liquido_recebido, 384_450.60)
checa("custo total", ib.custo_total, 247_971.30)
checa("custo por R$ 1,00 que entra", ib.custo_por_real, 1.6450, tol=0.0001)
checa("TIR real (a.a.)", ib.tir_real_aa, 0.2797, tol=0.0005)
checa("CET impresso", b.cet_aa_informado, 0.279748, tol=0.0001)
checa("divergência de CET (p.p.)", ib.divergencia_cet, 0.0, tol=0.0005)
checa("maior parcela", ib.maior_parcela, 20_483.17)
checa("menor parcela", ib.menor_parcela, 11_059.18)
checa_bool("não é pós-fixada", b.pos_fixada, False)
checa_bool("extração confere com os totais impressos", cb.confere)
checa_bool("CET impresso reproduz o plano", len(cb.alertas) == 0)

# ── Comparação entre as duas ──────────────────────────────────────────────────
print("\nComparação A × B")
checa("diferença de custo total", ib.custo_total - ia.custo_total, 84_988.36)
checa("diferença de líquido no caixa", ib.liquido_recebido - ia.liquido_recebido, -15_549.40)
checa("diferença de TIR (p.p.)", ib.tir_real_aa - ia.tir_real_aa, 0.0704, tol=0.001)

# ── A conferência precisa reprovar um plano adulterado ────────────────────────
print("\nConferência com plano adulterado")
adulterada = carregar("rafamed_b_fgi")
adulterada.parcelas[10].valor_parcela += 1_000.00
checa_bool("adulteração é detectada", conferir(adulterada).confere, False)

# ── Convenção de dias no SAC ──────────────────────────────────────────────────
print("\nConvenção de juros pro-rata por dias (SAC)")
# Saldo ao fim da carência impresso na proposta B: 456.745,76, 42x, 1,75% a.m.
df_mes = calcular_sac(456_745.76, 0.0175, 42, date(2027, 4, 12), convencao="mes_cheio")
df_dias = calcular_sac(456_745.76, 0.0175, 42, date(2027, 4, 12),
                       convencao="dias", data_base=date(2027, 3, 7))
checa("1ª parcela, mês cheio (não reproduz o banco)", float(df_mes.iloc[0]["prestacao"]), 18_867.95, tol=0.5)
checa("1ª parcela, pro-rata por dias (36 dias)", float(df_dias.iloc[0]["prestacao"]), 20_483.17, tol=0.5)

# ── Resultado ─────────────────────────────────────────────────────────────────
print()
if _falhas:
    print(f"{len(_falhas)} verificação(ões) falharam:")
    for f in _falhas:
        print(f"  - {f}")
    sys.exit(1)
print("Todas as verificações passaram.")
