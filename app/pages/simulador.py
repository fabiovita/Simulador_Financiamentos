from datetime import date
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from calculators.sac import calcular_sac
from calculators.price import calcular_price
import database as db
from models import Emprestimo


def _fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render():
    st.header("Simulador SAC vs PRICE")

    # ── Seletor de financiamento cadastrado ───────────────────────────────────
    cliente_id = st.session_state.get("cliente_selecionado_id")
    emp_ref = None

    if cliente_id:
        emprestimos = db.listar_emprestimos(cliente_id)
        ativos = [e for e in emprestimos if e.status == "ativo"]
        if len(ativos) > 1:
            cliente = db.buscar_cliente(cliente_id)
            st.caption(f"Cliente: **{cliente.nome}**")
            opcoes_label = {
                f"{e.credor} — {e.produto or e.tabela} (R$ {e.valor_liquido:,.0f}, {e.num_parcelas}x)": e
                for e in ativos
            }
            escolha = st.selectbox(
                "Carregar financiamento cadastrado",
                ["(inserir manualmente)"] + list(opcoes_label.keys()),
            )
            if escolha != "(inserir manualmente)":
                emp_ref = opcoes_label[escolha]
        elif len(ativos) == 1:
            emp_ref = ativos[0]

    # Limpa o estado dos campos quando muda o financiamento de referência
    emp_ref_id = emp_ref.id if emp_ref else None
    if st.session_state.get("_sim_emp_ref_id") != emp_ref_id:
        st.session_state["_sim_emp_ref_id"] = emp_ref_id
        if emp_ref:
            st.session_state["sim_valor"]         = float(emp_ref.valor_liquido)
            st.session_state["sim_taxa"]          = round(emp_ref.taxa_mensal * 100, 4)
            st.session_state["sim_parcelas"]      = int(emp_ref.num_parcelas)
            st.session_state["sim_carencia"]      = int(emp_ref.carencia)
            st.session_state["sim_carencia_tipo"] = emp_ref.carencia_tipo
        else:
            for key in ("sim_valor", "sim_taxa", "sim_parcelas", "sim_carencia", "sim_carencia_tipo"):
                st.session_state.pop(key, None)

    default_valor = emp_ref.valor_liquido if emp_ref else None
    default_taxa = round(emp_ref.taxa_mensal * 100, 4) if emp_ref else None
    default_parcelas = emp_ref.num_parcelas if emp_ref else None
    default_data = date.fromisoformat(emp_ref.primeira_parcela) if emp_ref else None
    default_carencia = emp_ref.carencia if emp_ref else 0

    # ── Parâmetros ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Parâmetros")
        c1, c2, c3 = st.columns(3)
        valor = c1.number_input("Valor (R$)", min_value=0.0, step=1000.0, placeholder="0,00", key="sim_valor")
        taxa = c2.number_input("Taxa (%)", min_value=0.0, max_value=30.0, step=0.01, placeholder="0,00", key="sim_taxa",
                               help="Taxa mensal fixa")
        parcelas = c3.number_input("Parcelas", min_value=0, max_value=360, placeholder="0", key="sim_parcelas")

        c4, c5, c6 = st.columns(3)
        primeira = c4.date_input("Início", value=default_data, format="DD/MM/YYYY")
        carencia = c5.number_input("Carência", min_value=0, max_value=360,
                                   help="Meses sem pagamento", key="sim_carencia")
        carencia_tipo = c6.selectbox(
            "Tipo de carência",
            ["capitalizado", "juros_pagos"],
            format_func=lambda x: "Juros capitalizados" if x == "capitalizado" else "Juros pagos",
            key="sim_carencia_tipo",
            help="Capitalizado: juros acumulam no saldo. Juros pagos: paga só os juros durante a carência.",
        )

    # Só calcula e exibe resultados se os campos obrigatórios estiverem preenchidos
    if not valor or not taxa or not parcelas:
        st.info("Preencha os parâmetros acima para visualizar a simulação.")
        return

    taxa_decimal = taxa / 100
    primeira_date = primeira if primeira else date.today()

    df_sac = calcular_sac(valor, taxa_decimal, int(parcelas), primeira_date, int(carencia), carencia_tipo)
    df_price = calcular_price(valor, taxa_decimal, int(parcelas), primeira_date, int(carencia), carencia_tipo)

    total_juros_sac = df_sac["juros"].sum()
    total_juros_price = df_price["juros"].sum()
    total_pago_sac = df_sac["prestacao"].sum()
    total_pago_price = df_price["prestacao"].sum()
    diferenca = total_pago_price - total_pago_sac

    # Primeira parcela real (pós-carência, com prestação > 0)
    carencia_int = int(carencia)
    df_sac_pagto = df_sac[df_sac["prestacao"] > 0]
    df_price_pagto = df_price[df_price["prestacao"] > 0]
    primeira_sac = float(df_sac_pagto.iloc[0]["prestacao"]) if not df_sac_pagto.empty else 0.0
    primeira_price = float(df_price_pagto.iloc[0]["prestacao"]) if not df_price_pagto.empty else 0.0

    # ── Resumo comparativo ────────────────────────────────────────────────────
    st.subheader("Resumo Comparativo")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**SAC**")
        st.metric("1ª Parcela", _fmt(primeira_sac))
        st.metric("Última", _fmt(df_sac.iloc[-1]["prestacao"]))
        st.metric("Juros", _fmt(total_juros_sac))
        st.metric("Total", _fmt(total_pago_sac))

    with col2:
        st.markdown("**PRICE**")
        st.metric("Parcela", _fmt(primeira_price))
        st.metric("Última", _fmt(df_price.iloc[-1]["prestacao"]))
        st.metric("Juros", _fmt(total_juros_price))
        st.metric("Total", _fmt(total_pago_price))

    with col3:
        st.markdown("**Diferença**")
        pct = (diferenca / total_pago_sac) * 100 if total_pago_sac else 0
        st.metric("PRICE - SAC", _fmt(diferenca), delta=f"{pct:.1f}%")
        st.caption("SAC custa menos no total, parcelas iniciais maiores." if diferenca > 0
                   else "Custo semelhante entre os sistemas.")
        if carencia_int > 0:
            tipo_label = "juros capitalizados" if carencia_tipo == "capitalizado" else "juros pagos no período"
            st.caption(f"Carência: {carencia_int} meses ({tipo_label})")

    # ── Gráficos ──────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["Evolução das Parcelas", "Saldo Devedor"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_sac["parcela"], y=df_sac["prestacao"],
            name="SAC", mode="lines+markers", line=dict(color="#0C0CF2"),
        ))
        fig.add_trace(go.Scatter(
            x=df_price["parcela"], y=df_price["prestacao"],
            name="PRICE", mode="lines", line=dict(color="#3D7CF2", dash="dash"),
        ))
        fig.update_layout(
            title="Valor da Parcela por Período",
            xaxis_title="Parcela", yaxis_title="R$",
            legend=dict(orientation="h"), height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_sac["parcela"], y=df_sac["saldo_final"],
            name="SAC", fill="tozeroy", line=dict(color="#0C0CF2"),
        ))
        fig2.add_trace(go.Scatter(
            x=df_price["parcela"], y=df_price["saldo_final"],
            name="PRICE", fill="tozeroy", line=dict(color="#3D7CF2", dash="dash"),
            fillcolor="rgba(61,124,242,0.1)",
        ))
        fig2.update_layout(
            title="Evolução do Saldo Devedor",
            xaxis_title="Parcela", yaxis_title="R$",
            legend=dict(orientation="h"), height=400,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tabelas detalhadas ────────────────────────────────────────────────────
    with st.expander("Ver tabela SAC completa"):
        df_sac_fmt = df_sac.copy()
        df_sac_fmt["vencimento"] = df_sac_fmt["vencimento"].apply(lambda d: d.strftime("%d/%m/%Y"))
        for col in ["saldo_inicial", "juros", "amortizacao", "prestacao", "saldo_final"]:
            df_sac_fmt[col] = df_sac_fmt[col].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_sac_fmt, use_container_width=True, hide_index=True)

    with st.expander("Ver tabela PRICE completa"):
        df_price_fmt = df_price.copy()
        df_price_fmt["vencimento"] = df_price_fmt["vencimento"].apply(lambda d: d.strftime("%d/%m/%Y"))
        for col in ["saldo_inicial", "juros", "amortizacao", "prestacao", "saldo_final"]:
            df_price_fmt[col] = df_price_fmt[col].apply(lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.dataframe(df_price_fmt, use_container_width=True, hide_index=True)

    # ── Salvar simulação como financiamento ───────────────────────────────────
    st.divider()
    clientes = db.listar_clientes()

    if clientes:
        st.subheader("Salvar simulação como financiamento")
        opcoes = {f"{c.nome}": c.id for c in clientes}
        col_c, col_t, col_cred = st.columns(3)
        cliente_nome = col_c.selectbox("Cliente", list(opcoes.keys()),
                                        index=list(opcoes.values()).index(cliente_id) if cliente_id in opcoes.values() else 0)
        tabela_salvar = col_t.selectbox("Tabela a salvar", ["PRICE", "SAC"])
        credor_salvar = col_cred.text_input("Credor", placeholder="Ex: Banco do Brasil")
        produto_salvar = st.text_input("Produto", placeholder="Ex: Capital de Giro")

        if st.button("Salvar como financiamento do cliente"):
            if not credor_salvar:
                st.error("Informe o credor.")
            else:
                db.inserir_emprestimo(Emprestimo(
                    cliente_id=opcoes[cliente_nome],
                    credor=credor_salvar, produto=produto_salvar,
                    tabela=tabela_salvar, valor_liquido=valor,
                    taxa_mensal=taxa_decimal, num_parcelas=int(parcelas),
                    primeira_parcela=primeira_date.isoformat(),
                    carencia=carencia_int,
                ))
                st.success(f"Financiamento salvo para {cliente_nome}.")
