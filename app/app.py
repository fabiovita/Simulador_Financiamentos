import streamlit as st
import sys
import os

# Garante que o diretório do app está no path
sys.path.insert(0, os.path.dirname(__file__))

import database as db
from pages import clientes, endividamento, simulador, fluxo_caixa

# ── Inicialização ─────────────────────────────────────────────────────────────
db.init_db()

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "Clientes"

# Migração: renomeia estado legado "Endividamento" → "Financiamentos"
if st.session_state.get("pagina") == "Endividamento":
    st.session_state["pagina"] = "Financiamentos"

if "mostrar_form_emprestimo" not in st.session_state:
    st.session_state["mostrar_form_emprestimo"] = False

if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="PRANA — Simulador de Financiamentos",
    page_icon="assets/logo_prana.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_theme():
    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', Arial, sans-serif; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; min-height: 1.2rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; white-space: nowrap !important; overflow: visible !important; }
    """

    if st.session_state["dark_mode"]:
        css = f"""
        <style>
        {base_css}
        /* Fundos principais — tom mais suave */
        .stApp {{ background-color: #0B1224 !important; }}
        [data-testid="stAppViewContainer"] {{ background-color: #0B1224 !important; }}
        [data-testid="stSidebar"] {{ background-color: #111B36 !important; }}
        [data-testid="stSidebar"] * {{ color: #E8ECF4 !important; }}
        [data-testid="stHeader"] {{ background-color: #0B1224 !important; }}

        /* Textos */
        .stMarkdown, .stText, p, h1, h2, h3, h4, label, span,
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stText"] {{ color: #E8ECF4 !important; }}
        [data-testid="stMetricValue"] {{ color: #E8ECF4 !important; }}
        [data-testid="stMetricLabel"] label, [data-testid="stMetricLabel"] p,
        [data-testid="stMetricLabel"] div {{ color: #99A8C7 !important; }}

        /* Containers e expanders */
        [data-testid="stExpander"] {{ background-color: #131D3A !important; border-color: #253560 !important; }}
        [data-testid="stExpander"] summary span {{ color: #E8ECF4 !important; }}
        div[data-testid="stContainer"] {{ background-color: #131D3A !important; }}
        .stDataFrame {{ background-color: #131D3A !important; }}

        /* ====== INPUTS GLOBAL — cobertura total ====== */
        input, textarea {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            border-color: #253560 !important;
            caret-color: #E8ECF4 !important;
        }}
        input::placeholder, textarea::placeholder {{ color: #6878A0 !important; }}

        /* number_input spinner buttons */
        [data-testid="stNumberInput"] button {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            border-color: #253560 !important;
        }}

        /* text_input, number_input wrapper */
        [data-baseweb="input"] {{
            background-color: #1A2545 !important;
            border-color: #253560 !important;
        }}
        [data-baseweb="input"] input {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            -webkit-text-fill-color: #E8ECF4 !important;
        }}

        /* select / selectbox */
        [data-baseweb="select"] {{ background-color: #1A2545 !important; }}
        [data-baseweb="select"] * {{ color: #E8ECF4 !important; }}
        [data-baseweb="select"] > div {{
            background-color: #1A2545 !important;
            border-color: #253560 !important;
        }}
        [data-baseweb="select"] [data-baseweb="tag"] {{
            background-color: #253560 !important;
        }}

        /* dropdown menu */
        [data-baseweb="popover"] {{ background-color: #1A2545 !important; }}
        [data-baseweb="menu"] {{ background-color: #1A2545 !important; }}
        [data-baseweb="menu"] li {{ color: #E8ECF4 !important; }}
        [data-baseweb="menu"] li:hover {{ background-color: #253560 !important; }}
        [role="listbox"] {{ background-color: #1A2545 !important; }}
        [role="option"] {{ color: #E8ECF4 !important; }}
        [role="option"]:hover {{ background-color: #253560 !important; }}

        /* date_input */
        .stDateInput input {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            -webkit-text-fill-color: #E8ECF4 !important;
        }}
        [data-baseweb="calendar"] {{ background-color: #1A2545 !important; color: #E8ECF4 !important; }}
        [data-baseweb="calendar"] * {{ color: #E8ECF4 !important; }}

        /* slider */
        .stSlider label {{ color: #E8ECF4 !important; }}
        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"] {{ color: #99A8C7 !important; }}

        /* toggle / checkbox */
        .stCheckbox label span {{ color: #E8ECF4 !important; }}

        /* form border */
        [data-testid="stForm"] {{ border-color: #253560 !important; }}

        /* info, success, error, warning boxes */
        [data-testid="stAlert"] {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            border-color: #253560 !important;
        }}
        [data-testid="stAlert"] p {{ color: #E8ECF4 !important; }}

        /* Tabs */
        .stTabs [data-baseweb="tab"] {{ color: #99A8C7 !important; }}
        .stTabs [aria-selected="true"] {{ color: #E8ECF4 !important; }}
        .stTabs [data-baseweb="tab-panel"] {{ background-color: #0B1224 !important; }}

        /* Caption */
        .stCaption, [data-testid="stCaptionContainer"] {{ color: #8090B0 !important; }}

        /* Divider */
        [data-testid="stDivider"], hr {{ border-color: #253560 !important; }}

        /* Buttons secondary */
        .stButton button[kind="secondary"] {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            border-color: #253560 !important;
        }}

        /* Download button */
        .stDownloadButton button {{
            background-color: #1A2545 !important;
            color: #E8ECF4 !important;
            border-color: #253560 !important;
        }}

        /* DataFrame / table */
        .stDataFrame [data-testid="glideDataEditor"] {{
            background-color: #131D3A !important;
        }}
        </style>"""
    else:
        css = f"""
        <style>
        {base_css}
        </style>"""
    st.markdown(css, unsafe_allow_html=True)


_inject_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    logo = "assets/logo_prana_dark.png" if st.session_state["dark_mode"] else "assets/logo_prana.png"
    st.image(logo, width="stretch")
    st.divider()

    st.toggle("Modo escuro", key="dark_mode")
    st.divider()

    paginas = ["Clientes", "Financiamentos", "Simulador SAC/PRICE", "Fluxo de Caixa"]
    for p in paginas:
        ativo = st.session_state["pagina"] == p
        if st.button(p, use_container_width=True, type="primary" if ativo else "secondary"):
            st.session_state["pagina"] = p
            st.rerun()

    # Cliente selecionado
    cliente_id = st.session_state.get("cliente_selecionado_id")
    if cliente_id:
        cliente = db.buscar_cliente(cliente_id)
        if cliente:
            st.divider()
            st.caption("Cliente ativo")
            st.markdown(f"**{cliente.nome}**")
            st.caption(cliente.cnpj_cpf or "")
            if st.button("Trocar cliente", use_container_width=True):
                st.session_state.pop("cliente_selecionado_id", None)
                st.session_state["pagina"] = "Clientes"
                st.rerun()

# ── Roteamento ────────────────────────────────────────────────────────────────
pagina = st.session_state["pagina"]

if pagina == "Clientes":
    clientes.render()
elif pagina == "Financiamentos":
    endividamento.render()
elif pagina == "Simulador SAC/PRICE":
    simulador.render()
elif pagina == "Fluxo de Caixa":
    fluxo_caixa.render()
