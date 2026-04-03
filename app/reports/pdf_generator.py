"""
Geração de relatório PDF de endividamento usando reportlab.
"""
import io
import os
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models import Cliente, Emprestimo
from calculators.sac import calcular_sac
from calculators.price import calcular_price
from calculators.cashflow import gerar_fluxo_caixa


# ── Paleta PRANA ──────────────────────────────────────────────────────────────
AZUL       = colors.HexColor("#0C0CF2")
AZUL_MEDIO = colors.HexColor("#3D7CF2")
AZUL_CLARO = colors.HexColor("#9DBBF2")
FUNDO      = colors.HexColor("#F7F9FF")
PRETO_AZUL = colors.HexColor("#00051C")
VERDE      = colors.HexColor("#033315")

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_LOGO_PATH  = os.path.join(_ASSETS_DIR, "logo_prana.png")

# Proporção real da logo: 2640 × 1440 px  →  ratio = 11/6
_LOGO_RATIO = 2640 / 1440
_LOGO_H     = 1.3 * cm
_LOGO_W     = _LOGO_H * _LOGO_RATIO   # ≈ 2.38 cm


def _fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _saldo_atual(emp: Emprestimo) -> float:
    primeira = date.fromisoformat(emp.primeira_parcela)
    if emp.tabela == "SAC":
        df = calcular_sac(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia, emp.carencia_tipo)
    else:
        df = calcular_price(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia, emp.carencia_tipo)
    pagas = min(emp.parcelas_pagas, len(df))
    return float(df.iloc[pagas - 1]["saldo_final"]) if pagas > 0 else emp.valor_liquido


def _section_title(text: str, page_width: float) -> Table:
    """Título de seção com barra de acento azul à esquerda."""
    bar_w  = 0.25 * cm
    text_w = page_width - bar_w - 0.3 * cm
    style  = ParagraphStyle(
        "sec_title", fontSize=11, textColor=PRETO_AZUL,
        fontName="Helvetica-Bold", leading=14,
    )
    t = Table(
        [[" ", Paragraph(text, style)]],
        colWidths=[bar_w, text_w],
        rowHeights=[0.55 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), AZUL),
        ("LEFTPADDING",   (1, 0), (1, 0), 8),
        ("RIGHTPADDING",  (1, 0), (1, 0), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def gerar_pdf_cliente(cliente: Cliente, emprestimos: List[Emprestimo]) -> bytes:
    import pandas as pd

    buffer   = io.BytesIO()
    page_w   = A4[0]
    margin   = 2 * cm
    usable_w = page_w - 2 * margin

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=margin, leftMargin=margin,
        topMargin=margin, bottomMargin=2 * cm,
    )

    # ── Estilos ───────────────────────────────────────────────────────────────
    titulo = ParagraphStyle(
        "titulo", fontSize=20, textColor=PRETO_AZUL,
        fontName="Helvetica-Bold", leading=24, spaceAfter=2,
    )
    subtag = ParagraphStyle(
        "subtag", fontSize=9, textColor=AZUL_MEDIO,
        fontName="Helvetica", leading=12,
    )
    rodape_style = ParagraphStyle(
        "rodape", fontSize=8, textColor=AZUL_CLARO, alignment=TA_CENTER,
    )
    info_label = ParagraphStyle(
        "info_label", fontSize=9, textColor=AZUL_MEDIO,
        fontName="Helvetica-Bold",
    )
    info_valor = ParagraphStyle(
        "info_valor", fontSize=9, textColor=PRETO_AZUL, fontName="Helvetica",
    )

    story = []

    # ── Cabeçalho: logo + título lado a lado ──────────────────────────────────
    if os.path.exists(_LOGO_PATH):
        logo_img = Image(_LOGO_PATH, width=_LOGO_W, height=_LOGO_H)
    else:
        logo_img = Paragraph("PRANA", titulo)

    titulo_bloco = [
        Paragraph("Relatório de Financiamentos", titulo),
        Paragraph("Levantamento de Endividamento", subtag),
    ]

    header_table = Table(
        [[logo_img, titulo_bloco]],
        colWidths=[_LOGO_W + 0.5 * cm, usable_w - _LOGO_W - 0.5 * cm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=0))
    story.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_CLARO, spaceBefore=2, spaceAfter=10))

    # ── Dados do cliente ──────────────────────────────────────────────────────
    campos = [
        ("Cliente",   cliente.nome),
        ("CNPJ/CPF",  cliente.cnpj_cpf or "—"),
        ("E-mail",    cliente.email or "—"),
        ("Telefone",  cliente.telefone or "—"),
        ("Data",      date.today().strftime("%d/%m/%Y")),
    ]
    info_rows = [
        [Paragraph(l, info_label), Paragraph(v, info_valor)]
        for l, v in campos
    ]
    info_table = Table(info_rows, colWidths=[2.8 * cm, usable_w - 2.8 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), FUNDO),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.3, colors.HexColor("#DDE3F5")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.7 * cm))

    # ── Seção 1: Resumo Executivo ─────────────────────────────────────────────
    ativos = [e for e in emprestimos if e.status == "ativo"]

    if ativos:
        total_divida   = sum(_saldo_atual(e) for e in ativos)
        total_parcela  = 0
        for e in ativos:
            primeira = date.fromisoformat(e.primeira_parcela)
            df = (calcular_sac if e.tabela == "SAC" else calcular_price)(
                e.valor_liquido, e.taxa_mensal, e.num_parcelas, primeira, e.carencia, e.carencia_tipo
            )
            idx = min(e.parcelas_pagas, len(df) - 1)
            total_parcela += float(df.iloc[idx]["prestacao"])

        prazo_max = max(
            date.fromisoformat(e.primeira_parcela) + relativedelta(months=e.num_parcelas - 1)
            for e in ativos
        )

        # Métricas em cards lado a lado
        card_style_label = ParagraphStyle(
            "card_label", fontSize=8, textColor=AZUL_MEDIO,
            fontName="Helvetica", alignment=TA_CENTER,
        )
        card_style_valor = ParagraphStyle(
            "card_valor", fontSize=13, textColor=PRETO_AZUL,
            fontName="Helvetica-Bold", alignment=TA_CENTER, leading=16,
        )

        metricas = [
            ("Saldo Total em Dívida", _fmt(total_divida)),
            ("Comprometimento Mensal", _fmt(total_parcela)),
            ("Empréstimos Ativos", str(len(ativos))),
            ("Quitação Mais Longa", prazo_max.strftime("%m/%Y")),
        ]

        card_w = usable_w / len(metricas)
        cards_data = [[
            Table(
                [[Paragraph(v, card_style_valor)], [Paragraph(l, card_style_label)]],
                colWidths=[card_w - 0.4 * cm],
            )
            for l, v in metricas
        ]]
        cards_table = Table(cards_data, colWidths=[card_w] * len(metricas))
        cards_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), FUNDO),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("LINEBEFORE",    (1, 0), (-1, -1), 0.5, AZUL_CLARO),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))

        story.append(KeepTogether([
            _section_title("1. Resumo Executivo", usable_w),
            Spacer(1, 0.25 * cm),
            cards_table,
            Spacer(1, 0.7 * cm),
        ]))

    # ── Seção 2: Mapa de Endividamento ────────────────────────────────────────
    headers = ["Credor", "Produto", "Tabela", "Valor Original", "Taxa/mês", "Parcelas", "Carência", "Saldo Atual", "Status"]
    rows = [headers]
    for e in emprestimos:
        saldo     = _saldo_atual(e)
        restantes = e.num_parcelas - e.parcelas_pagas
        rows.append([
            e.credor,
            e.produto or "—",
            e.tabela,
            _fmt(e.valor_liquido),
            f"{e.taxa_mensal * 100:.2f}%",
            f"{restantes}/{e.num_parcelas}",
            f"{e.carencia}m {'(cap.)' if e.carencia_tipo == 'capitalizado' else '(j.pagos)'}" if e.carencia > 0 else "—",
            _fmt(saldo),
            "Ativo" if e.status == "ativo" else "Quitado",
        ])

    col_widths = [2.8 * cm, 2.2 * cm, 1.3 * cm, 2.3 * cm, 1.5 * cm, 1.6 * cm, 2.0 * cm, 2.3 * cm, 1.4 * cm]
    mapa_table = Table(rows, colWidths=col_widths, repeatRows=1)
    mapa_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, FUNDO]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE3F5")),
        ("ALIGN",         (3, 1), (7, -1), "RIGHT"),
        ("ALIGN",         (4, 0), (7, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("TEXTCOLOR",     (0, 1), (-1, -1), PRETO_AZUL),
    ]))

    story.append(KeepTogether([
        _section_title("2. Mapa de Financiamentos", usable_w),
        Spacer(1, 0.25 * cm),
    ]))
    story.append(mapa_table)
    story.append(Spacer(1, 0.7 * cm))

    # ── Seção 3: Fluxo de Caixa até a quitação ───────────────────────────────
    if ativos:
        hoje = date.today()
        prazo_max_fc = max(
            date.fromisoformat(e.primeira_parcela) + relativedelta(months=e.num_parcelas - 1)
            for e in ativos
        )
        meses_necessarios = (
            (prazo_max_fc.year - hoje.year) * 12 + (prazo_max_fc.month - hoje.month) + 2
        )

        df_fluxo = gerar_fluxo_caixa(ativos, meses=meses_necessarios)

        if not df_fluxo.empty:
            credores    = sorted(df_fluxo["credor"].unique())
            usar_pivot  = len(credores) <= 4

            if usar_pivot:
                pivot = (
                    df_fluxo.groupby(["mes", "credor"])["prestacao"]
                    .sum().unstack(fill_value=0).reset_index()
                )
                pivot["Total"] = pivot[credores].sum(axis=1)
                fc_headers  = ["Mês"] + list(credores) + ["Total"]
                fc_rows     = [fc_headers]
                for _, row in pivot.iterrows():
                    mes_str = pd.Timestamp(row["mes"]).strftime("%b/%Y")
                    fc_rows.append(
                        [mes_str] + [_fmt(row[c]) for c in credores] + [_fmt(row["Total"])]
                    )
                n_cols       = len(fc_headers)
                col_w_mes    = 2.4 * cm
                col_w_outros = (usable_w - col_w_mes) / (n_cols - 1)
                fc_col_w     = [col_w_mes] + [col_w_outros] * (n_cols - 1)
            else:
                resumo = df_fluxo.groupby("mes")["prestacao"].sum().reset_index()
                resumo.columns = ["mes", "total"]
                fc_rows = [["Mês", "Total de Parcelas"]]
                for _, row in resumo.iterrows():
                    fc_rows.append([
                        pd.Timestamp(row["mes"]).strftime("%b/%Y"),
                        _fmt(row["total"]),
                    ])
                fc_col_w = [4 * cm, 5 * cm]

            fc_table = Table(fc_rows, colWidths=fc_col_w, repeatRows=1)
            last_col = len(fc_col_w) - 1
            fc_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, FUNDO]),
                ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE3F5")),
                ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("TEXTCOLOR",     (0, 1), (-1, -1), PRETO_AZUL),
                # Coluna Total destacada
                ("BACKGROUND",    (last_col, 1), (last_col, -1), colors.HexColor("#EBF0FF")),
                ("FONTNAME",      (last_col, 1), (last_col, -1), "Helvetica-Bold"),
            ]))

            story.append(KeepTogether([
                _section_title("3. Fluxo de Caixa — Até a Quitação", usable_w),
                Spacer(1, 0.25 * cm),
            ]))
            story.append(fc_table)
            story.append(Spacer(1, 0.7 * cm))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=AZUL_CLARO))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Relatório gerado em {date.today().strftime('%d/%m/%Y')} · PRANA Gestão Financeira",
        rodape_style,
    ))

    doc.build(story)
    return buffer.getvalue()
