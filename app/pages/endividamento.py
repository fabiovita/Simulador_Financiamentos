from datetime import date
from dateutil.relativedelta import relativedelta
import streamlit as st
import pandas as pd

import database as db
from models import Emprestimo
from calculators.sac import calcular_sac
from calculators.price import calcular_price
from reports.pdf_generator import gerar_pdf_cliente


def _saldo_atual(emp: Emprestimo) -> float:
    """Calcula saldo devedor estimado com base nas parcelas pagas."""
    primeira = date.fromisoformat(emp.primeira_parcela)
    if emp.tabela == "SAC":
        df = calcular_sac(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)
    else:
        df = calcular_price(emp.valor_liquido, emp.taxa_mensal, emp.num_parcelas, primeira, emp.carencia)

    pagas = min(emp.parcelas_pagas, len(df))
    if pagas == 0:
        return emp.valor_liquido
    return float(df.iloc[pagas - 1]["saldo_final"])


def _proxima_parcela(emp: Emprestimo) -> date:
    primeira = date.fromisoformat(emp.primeira_parcela)
    return primeira + relativedelta(months=emp.parcelas_pagas)


def render():
    cliente_id = st.session_state.get("cliente_selecionado_id")

    if not cliente_id:
        st.info("Selecione um cliente na aba **Clientes** para ver os financiamentos.")
        return

    cliente = db.buscar_cliente(cliente_id)
    if not cliente:
        st.error("Cliente não encontrado.")
        return

    st.header(f"Financiamentos — {cliente.nome}")
    partes = [f"CNPJ/CPF: {cliente.cnpj_cpf or '—'}"]
    if cliente.email:
        partes.append(f"E-mail: {cliente.email}")
    if cliente.telefone:
        partes.append(f"Tel: {cliente.telefone}")
    st.caption("  |  ".join(partes))

    emprestimos = db.listar_emprestimos(cliente_id)
    ativos = [e for e in emprestimos if e.status == "ativo"]

    # ── Totalizadores ─────────────────────────────────────────────────────────
    if ativos:
        total_divida = sum(_saldo_atual(e) for e in ativos)
        total_parcela = sum(
            calcular_sac(e.valor_liquido, e.taxa_mensal, e.num_parcelas, date.fromisoformat(e.primeira_parcela), e.carencia)
            .iloc[e.parcelas_pagas]["prestacao"]
            if e.tabela == "SAC"
            else calcular_price(e.valor_liquido, e.taxa_mensal, e.num_parcelas, date.fromisoformat(e.primeira_parcela), e.carencia)
            .iloc[min(e.parcelas_pagas, e.num_parcelas - 1)]["prestacao"]
            for e in ativos
        )
        prazo_max = max(
            (date.fromisoformat(e.primeira_parcela) + relativedelta(months=e.num_parcelas - 1))
            for e in ativos
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("Dívida total", f"R$ {total_divida:,.0f}".replace(",", "."))
        col2.metric("Parcela mensal", f"R$ {total_parcela:,.0f}".replace(",", "."))
        col3.metric("Prazo final", prazo_max.strftime("%m/%Y"))

    # ── Botões de ação ────────────────────────────────────────────────────────
    col_add, col_pdf = st.columns([1, 1])

    with col_add:
        if st.button("+ Adicionar financiamento", type="primary"):
            st.session_state["mostrar_form_emprestimo"] = True

    with col_pdf:
        if emprestimos and st.button("Exportar PDF"):
            pdf_bytes = gerar_pdf_cliente(cliente, emprestimos)
            st.download_button(
                "Baixar relatório PDF",
                data=pdf_bytes,
                file_name=f"financiamentos_{cliente.nome.replace(' ', '_')}.pdf",
                mime="application/pdf",
            )

    # ── Formulário de novo empréstimo ─────────────────────────────────────────
    if st.session_state.get("mostrar_form_emprestimo"):
        with st.container(border=True):
            st.subheader("Novo financiamento")
            with st.form("form_emprestimo", clear_on_submit=True):
                c1, c2 = st.columns(2)
                credor = c1.text_input("Credor *", placeholder="Ex: Itaú, BNDES")
                produto = c2.text_input("Produto", placeholder="Ex: Pronampe, Capital de Giro")

                c3, c4, c5 = st.columns(3)
                tabela = c3.selectbox("Tabela", ["PRICE", "SAC"])
                valor = c4.number_input("Valor (R$) *", min_value=0.0, step=1000.0)
                taxa = c5.number_input("Taxa (%) *", min_value=0.0, max_value=30.0, value=None, step=0.01,
                                       placeholder="Ex: 1.32",
                                       help="Taxa mensal fixa. Ex: 1,32")

                c6, c7, c8, c9 = st.columns(4)
                parcelas = c6.number_input("Parcelas *", min_value=1, max_value=360, value=None,
                                           placeholder="Ex: 36")
                primeira = c7.date_input("Início *", value=date.today())
                carencia = c8.number_input("Carência", min_value=0, max_value=360, value=0, step=1,
                                           help="Meses sem pagamento")
                pagas = c9.number_input("Pagas", min_value=0, max_value=360, value=0)

                col_s, col_c = st.columns(2)
                salvar = col_s.form_submit_button("Salvar financiamento", type="primary")
                cancelar = col_c.form_submit_button("Cancelar")

            if salvar:
                erros = []
                if not credor:
                    erros.append("Credor é obrigatório.")
                if not valor or valor <= 0:
                    erros.append("Valor líquido é obrigatório.")
                if taxa is None:
                    erros.append("Taxa mensal é obrigatória.")
                if parcelas is None:
                    erros.append("Número de parcelas é obrigatório.")
                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    db.inserir_emprestimo(Emprestimo(
                        cliente_id=cliente_id,
                        credor=credor, produto=produto, tabela=tabela,
                        valor_liquido=valor, taxa_mensal=taxa / 100,
                        num_parcelas=int(parcelas),
                        primeira_parcela=primeira.isoformat(),
                        carencia=int(carencia),
                        parcelas_pagas=int(pagas),
                    ))
                    st.session_state["mostrar_form_emprestimo"] = False
                    st.success("Financiamento adicionado.")
                    st.rerun()

            if cancelar:
                st.session_state["mostrar_form_emprestimo"] = False
                st.rerun()

    # ── Tabela de empréstimos ─────────────────────────────────────────────────
    st.divider()

    if not emprestimos:
        st.info("Nenhum financiamento cadastrado para este cliente.")
        return

    for emp in emprestimos:
        saldo = _saldo_atual(emp)
        restantes = emp.num_parcelas - emp.parcelas_pagas
        proxima = _proxima_parcela(emp)
        cor = "🟢" if emp.status == "ativo" else "⚫"

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1.5])
            col1.markdown(f"{cor} **{emp.credor}** — {emp.produto or '—'}")
            col2.metric("Saldo", f"R$ {saldo:,.0f}".replace(",", "."))
            col3.metric("Parcelas", f"{restantes}/{emp.num_parcelas}")
            col4.metric("Taxa", f"{emp.taxa_mensal*100:.2f}%")

            info_parts = [emp.tabela, f"Próxima: {proxima.strftime('%d/%m/%y')}"]
            if emp.carencia > 0:
                info_parts.append(f"Carência: {emp.carencia}m")
            col5, col6, col7 = st.columns([3, 1, 1])
            col5.caption("  ·  ".join(info_parts))

            if col6.button("Editar", key=f"edit_{emp.id}"):
                st.session_state[f"editar_emp_{emp.id}"] = True

            if col7.button("Excluir", key=f"del_{emp.id}"):
                db.excluir_emprestimo(emp.id)
                st.rerun()

        # Formulário de edição inline
        if st.session_state.get(f"editar_emp_{emp.id}"):
            with st.container(border=True):
                with st.form(f"form_edit_{emp.id}"):
                    st.caption("Editar financiamento")
                    c1, c2 = st.columns(2)
                    credor_e = c1.text_input("Credor", value=emp.credor)
                    produto_e = c2.text_input("Produto", value=emp.produto or "")
                    c3, c4, c5 = st.columns(3)
                    tabela_e = c3.selectbox("Tabela", ["PRICE", "SAC"], index=0 if emp.tabela == "PRICE" else 1)
                    taxa_e = c4.number_input("Taxa (%)", value=round(emp.taxa_mensal * 100, 4), step=0.01)
                    parcelas_e = c5.number_input("Parcelas", value=emp.num_parcelas, min_value=1, max_value=360)
                    c6, c7, c8 = st.columns(3)
                    carencia_e = c6.number_input("Carência", value=emp.carencia, min_value=0, max_value=360, step=1)
                    pagas_e = c7.number_input("Pagas", value=emp.parcelas_pagas, min_value=0)
                    status_e = c8.selectbox("Status", ["ativo", "quitado"], index=0 if emp.status == "ativo" else 1)
                    salvar_e = st.form_submit_button("Salvar")

                if salvar_e:
                    emp.credor = credor_e
                    emp.produto = produto_e
                    emp.tabela = tabela_e
                    emp.taxa_mensal = taxa_e / 100
                    emp.num_parcelas = int(parcelas_e)
                    emp.carencia = int(carencia_e)
                    emp.parcelas_pagas = int(pagas_e)
                    emp.status = status_e
                    db.atualizar_emprestimo(emp)
                    st.session_state[f"editar_emp_{emp.id}"] = False
                    st.rerun()
