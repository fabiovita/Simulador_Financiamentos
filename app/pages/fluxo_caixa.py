import streamlit as st
import plotly.graph_objects as go
import pandas as pd

import database as db
from calculators.cashflow import gerar_fluxo_caixa


def render():
    st.header("Fluxo de Caixa Consolidado")

    cliente_id = st.session_state.get("cliente_selecionado_id")

    if not cliente_id:
        st.info("Selecione um cliente na aba **Clientes** para ver o fluxo de caixa.")
        return

    cliente = db.buscar_cliente(cliente_id)
    if not cliente:
        st.error("Cliente não encontrado.")
        return

    st.subheader(f"{cliente.nome}")

    emprestimos = db.listar_emprestimos(cliente_id)
    ativos = [e for e in emprestimos if e.status == "ativo"]

    if not ativos:
        st.info("Nenhum empréstimo ativo para este cliente.")
        return

    col1, col2 = st.columns([2, 1])
    meses = col1.slider("Horizonte (meses)", min_value=6, max_value=120, value=24, step=6)

    df = gerar_fluxo_caixa(ativos, meses=meses)

    if df.empty:
        st.info("Sem parcelas futuras no horizonte selecionado.")
        return

    # ── Gráfico de barras empilhadas ──────────────────────────────────────────
    pivot = df.pivot_table(index="mes", columns="credor", values="prestacao", aggfunc="sum").fillna(0)
    pivot.index = pd.to_datetime(pivot.index)

    fig = go.Figure()
    colors = ["#0C0CF2", "#3D7CF2", "#79F2A8", "#F2C80C", "#AB3DCC", "#F2170C", "#9DBBF2"]
    for i, credor in enumerate(pivot.columns):
        fig.add_trace(go.Bar(
            x=pivot.index.strftime("%m/%Y"),
            y=pivot[credor],
            name=credor,
            marker_color=colors[i % len(colors)],
        ))

    fig.update_layout(
        barmode="stack",
        title="Parcelas mensais por credor",
        xaxis_title="Mês", yaxis_title="R$",
        legend=dict(orientation="h"),
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Tabela resumo mensal ───────────────────────────────────────────────────
    st.subheader("Tabela de Fluxo Mensal")

    resumo = df.groupby("mes")["prestacao"].sum().reset_index()
    resumo.columns = ["Mês", "Total"]
    resumo["Mês"] = pd.to_datetime(resumo["Mês"]).dt.strftime("%B/%Y")
    resumo["Total"] = resumo["Total"].apply(
        lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    # Breakdown por credor
    for credor in pivot.columns:
        valores = pivot[credor].reset_index()
        valores.columns = ["mes", credor]
        valores["mes"] = valores["mes"].dt.strftime("%B/%Y")
        valores[credor] = valores[credor].apply(
            lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        resumo = resumo.merge(valores, left_on="Mês", right_on="mes", how="left").drop(columns="mes")

    st.dataframe(resumo, use_container_width=True, hide_index=True)

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    total_periodo = df["prestacao"].sum()
    media_mensal = df.groupby("mes")["prestacao"].sum().mean()
    mes_pico = df.groupby("mes")["prestacao"].sum().idxmax()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", f"R$ {total_periodo:,.0f}".replace(",", "."))
    col2.metric("Média/mês", f"R$ {media_mensal:,.0f}".replace(",", "."))
    col3.metric("Mês pico", pd.Timestamp(mes_pico).strftime("%m/%Y"))
