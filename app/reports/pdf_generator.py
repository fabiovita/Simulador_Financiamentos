"""
Geração de relatório PDF de endividamento usando reportlab.
"""
import io
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models import Cliente, Emprestimo
from calculators.sac import calcular_sac
from calculators.price import calcular_price
from calculators.cashflow import gerar_fluxo_caixa


AZUL = colors.HexColor("#0C0CF2")
AZUL_CLARO = colors.HexColor("#E8EEFF")
CINZA = colors.HexColor("#F7F9FF")
VERDE = colors.HexColor("#033315")


def _fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _saldo_atual(emp: Emprestimo) -> float:
    primeira = date.fromisoformat(emp.primeira_parcela)
    if emp.tabela == "SAC":
        df = calcular_sac(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)
    else:
        df = calcular_price(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)
    pagas = min(emp.parcelas_pagas, len(df))
    return float(df.iloc[pagas - 1]["saldo_final"]) if pagas > 0 else emp.valor_liquido


def gerar_pdf_cliente(cliente: Cliente, emprestimos: List[Emprestimo]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", fontSize=18, textColor=AZUL, spaceAfter=4, alignment=TA_LEFT, fontName="Helvetica-Bold")
    subtitulo = ParagraphStyle("subtitulo", fontSize=13, textColor=AZUL, spaceAfter=2, fontName="Helvetica-Bold")
    normal = styles["Normal"]
    pequeno = ParagraphStyle("pequeno", fontSize=8, textColor=colors.grey)
    rodape_style = ParagraphStyle("rodape", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

    story = []

    # ── Capa ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Relatório de Financiamentos", titulo))
    story.append(HRFlowable(width="100%", thickness=2, color=AZUL))
    story.append(Spacer(1, 0.3 * cm))

    info_data = [
        ["Cliente:", cliente.nome],
        ["CNPJ/CPF:", cliente.cnpj_cpf or "—"],
        ["E-mail:", cliente.email or "—"],
        ["Telefone:", cliente.telefone or "—"],
        ["Data:", date.today().strftime("%d/%m/%Y")],
    ]
    info_table = Table(info_data, colWidths=[3 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Seção 1: Resumo Executivo ─────────────────────────────────────────────
    ativos = [e for e in emprestimos if e.status == "ativo"]

    if ativos:
        total_divida = sum(_saldo_atual(e) for e in ativos)
        total_parcela = 0
        for e in ativos:
            primeira = date.fromisoformat(e.primeira_parcela)
            if e.tabela == "SAC":
                df = calcular_sac(e.valor_liquido, e.taxa_mensal, e.num_parcelas, primeira, e.carencia)
            else:
                df = calcular_price(e.valor_liquido, e.taxa_mensal, e.num_parcelas, primeira, e.carencia)
            idx = min(e.parcelas_pagas, len(df) - 1)
            total_parcela += float(df.iloc[idx]["prestacao"])

        prazo_max = max(
            date.fromisoformat(e.primeira_parcela) + relativedelta(months=e.num_parcelas - 1)
            for e in ativos
        )

        story.append(Paragraph("1. Resumo Executivo", subtitulo))
        resumo_data = [
            ["Indicador", "Valor"],
            ["Total em dívida (saldo atual)", _fmt(total_divida)],
            ["Comprometimento mensal (parcelas)", _fmt(total_parcela)],
            ["Número de empréstimos ativos", str(len(ativos))],
            ["Prazo de quitação mais longo", prazo_max.strftime("%m/%Y")],
        ]
        resumo_table = Table(resumo_data, colWidths=[10 * cm, 5 * cm])
        resumo_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), CINZA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(resumo_table)
        story.append(Spacer(1, 0.5 * cm))

    # ── Seção 2: Mapa de Endividamento ────────────────────────────────────────
    story.append(Paragraph("2. Mapa de Financiamentos", subtitulo))

    headers = ["Credor", "Produto", "Tabela", "Valor Original", "Taxa/mês", "Parcelas", "Saldo Atual", "Status"]
    rows = [headers]
    for e in emprestimos:
        saldo = _saldo_atual(e)
        restantes = e.num_parcelas - e.parcelas_pagas
        rows.append([
            e.credor,
            e.produto or "—",
            e.tabela,
            _fmt(e.valor_liquido),
            f"{e.taxa_mensal * 100:.2f}%",
            f"{restantes}/{e.num_parcelas}",
            _fmt(saldo),
            "Ativo" if e.status == "ativo" else "Quitado",
        ])

    col_widths = [3 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm, 1.8 * cm, 1.8 * cm, 2.5 * cm, 1.5 * cm]
    mapa_table = Table(rows, colWidths=col_widths)
    mapa_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (3, 1), (6, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(mapa_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Seção 3: Fluxo de Caixa (próximos 12 meses) ───────────────────────────
    if ativos:
        story.append(Paragraph("3. Fluxo de Caixa — Próximos 12 meses", subtitulo))

        df_fluxo = gerar_fluxo_caixa(ativos, meses=12)
        if not df_fluxo.empty:
            import pandas as pd
            resumo_mensal = df_fluxo.groupby("mes")["prestacao"].sum().reset_index()
            resumo_mensal.columns = ["mes", "total"]

            fc_rows = [["Mês", "Total de Parcelas"]]
            for _, row in resumo_mensal.iterrows():
                import pandas as pd
                mes_str = pd.Timestamp(row["mes"]).strftime("%B/%Y")
                fc_rows.append([mes_str, _fmt(row["total"])])

            fc_table = Table(fc_rows, colWidths=[6 * cm, 5 * cm])
            fc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(fc_table)
            story.append(Spacer(1, 0.5 * cm))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Relatório gerado em {date.today().strftime('%d/%m/%Y')} — PRANA Gestão Financeira",
        rodape_style,
    ))

    doc.build(story)
    return buffer.getvalue()
