import streamlit as st
import database as db
from models import Cliente
from validators import (
    validar_cnpj_cpf, formatar_cnpj_cpf,
    validar_email,
    validar_telefone, formatar_telefone,
)


def _validar_form(cnpj_cpf, email, telefone) -> list[str]:
    erros = []
    ok, msg = validar_cnpj_cpf(cnpj_cpf)
    if not ok:
        erros.append(msg)
    ok, msg = validar_email(email)
    if not ok:
        erros.append(msg)
    ok, msg = validar_telefone(telefone)
    if not ok:
        erros.append(msg)
    return erros


def render():
    st.header("Clientes")

    # ── Formulário de novo cliente ────────────────────────────────────────────
    with st.expander("Adicionar novo cliente", expanded=False):
        with st.form("form_novo_cliente", clear_on_submit=True):
            nome = st.text_input("Nome / Razão Social *")

            col1, col2 = st.columns(2)
            cnpj = col1.text_input(
                "CNPJ / CPF",
                placeholder="00.000.000/0001-00 ou 000.000.000-00",
                help="Digite apenas os números ou com pontuação.",
            )
            telefone = col2.text_input(
                "Telefone",
                placeholder="(11) 99999-9999",
                help="DDD + número com 8 ou 9 dígitos.",
            )
            email = st.text_input(
                "E-mail",
                placeholder="nome@empresa.com.br",
            )

            submitted = st.form_submit_button("Salvar", type="primary")

        if submitted:
            erros = []
            if not nome.strip():
                erros.append("Nome é obrigatório.")
            erros += _validar_form(cnpj, email, telefone)

            if erros:
                for e in erros:
                    st.error(e)
            else:
                db.inserir_cliente(Cliente(
                    nome=nome.strip(),
                    cnpj_cpf=formatar_cnpj_cpf(cnpj),
                    email=email.strip().lower(),
                    telefone=formatar_telefone(telefone),
                ))
                st.success(f"Cliente '{nome}' cadastrado.")
                st.rerun()

    # ── Listagem ──────────────────────────────────────────────────────────────
    clientes = db.listar_clientes()

    if not clientes:
        st.info("Nenhum cliente cadastrado ainda.")
        return

    busca = st.text_input("Buscar cliente", placeholder="Digite nome, CNPJ ou e-mail...")
    if busca:
        b = busca.lower()
        clientes = [
            c for c in clientes
            if b in c.nome.lower()
            or b in (c.cnpj_cpf or "").lower()
            or b in (c.email or "").lower()
        ]

    st.write(f"**{len(clientes)} cliente(s) encontrado(s)**")

    for cliente in clientes:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
            col1.markdown(f"**{cliente.nome}**")
            col2.caption(cliente.cnpj_cpf or "—")
            contato = []
            if cliente.email:
                contato.append(cliente.email)
            if cliente.telefone:
                contato.append(cliente.telefone)
            col3.caption("  ·  ".join(contato) if contato else "—")

            if col4.button("Selecionar", key=f"sel_{cliente.id}"):
                st.session_state["cliente_selecionado_id"] = cliente.id
                st.session_state["pagina"] = "Financiamentos"
                st.rerun()

    # ── Edição / Exclusão ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Editar ou excluir cliente")

    opcoes = {f"{c.nome} ({c.cnpj_cpf or 'sem CNPJ'})": c.id for c in db.listar_clientes()}
    escolha = st.selectbox("Selecione o cliente", list(opcoes.keys()), index=None, placeholder="Escolha...")

    if escolha:
        cliente = db.buscar_cliente(opcoes[escolha])

        with st.form("form_editar_cliente"):
            nome_edit = st.text_input("Nome", value=cliente.nome)

            col1, col2 = st.columns(2)
            cnpj_edit = col1.text_input(
                "CNPJ / CPF",
                value=cliente.cnpj_cpf or "",
                placeholder="00.000.000/0001-00 ou 000.000.000-00",
            )
            tel_edit = col2.text_input(
                "Telefone",
                value=cliente.telefone or "",
                placeholder="(11) 99999-9999",
            )
            email_edit = st.text_input("E-mail", value=cliente.email or "", placeholder="nome@empresa.com.br")

            col_save, col_del = st.columns(2)
            salvar = col_save.form_submit_button("Salvar alterações", type="primary")
            excluir = col_del.form_submit_button("Excluir cliente")

        if salvar:
            erros = _validar_form(cnpj_edit, email_edit, tel_edit)
            if erros:
                for e in erros:
                    st.error(e)
            else:
                db.atualizar_cliente(Cliente(
                    id=cliente.id,
                    nome=nome_edit,
                    cnpj_cpf=formatar_cnpj_cpf(cnpj_edit),
                    email=email_edit.strip().lower(),
                    telefone=formatar_telefone(tel_edit),
                ))
                st.success("Dados atualizados.")
                st.rerun()

        if excluir:
            db.excluir_cliente(cliente.id)
            st.success(f"Cliente '{cliente.nome}' excluído.")
            st.rerun()
