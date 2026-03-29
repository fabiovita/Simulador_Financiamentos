import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Dashboard de Ações B3",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Dashboard de Ações B3")
st.markdown("Análise de performance: **Petrobras (PETR4)**, **Itaú (ITUB4)** e **Vale (VALE3)**")

# --- Sidebar ---
st.sidebar.header("Configurações")

periodo_opcoes = {
    "1 Mês": "1mo",
    "3 Meses": "3mo",
    "6 Meses": "6mo",
    "1 Ano": "1y",
    "2 Anos": "2y",
    "5 Anos": "5y",
}
periodo_label = st.sidebar.selectbox("Período", list(periodo_opcoes.keys()), index=3)
periodo = periodo_opcoes[periodo_label]

st.sidebar.markdown("---")
st.sidebar.subheader("Ações")
acoes_config = {
    "PETR4.SA": {"nome": "Petrobras", "cor": "#009B3A", "exibir": st.sidebar.checkbox("Petrobras (PETR4)", value=True)},
    "ITUB4.SA": {"nome": "Itaú",      "cor": "#003087", "exibir": st.sidebar.checkbox("Itaú (ITUB4)",      value=True)},
    "VALE3.SA": {"nome": "Vale",       "cor": "#0099CC", "exibir": st.sidebar.checkbox("Vale (VALE3)",       value=True)},
}

tickers_selecionados = [t for t, cfg in acoes_config.items() if cfg["exibir"]]

if not tickers_selecionados:
    st.warning("Selecione ao menos uma ação na barra lateral.")
    st.stop()

# --- Carregamento de dados ---
@st.cache_data(ttl=300)
def carregar_dados(tickers, periodo):
    dados = {}
    for ticker in tickers:
        df = yf.download(ticker, period=periodo, auto_adjust=True, progress=False)
        if not df.empty:
            df.columns = df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns
            dados[ticker] = df
    return dados

with st.spinner("Carregando dados..."):
    dados = carregar_dados(tickers_selecionados, periodo)

if not dados:
    st.error("Não foi possível carregar os dados. Verifique sua conexão.")
    st.stop()

# --- Métricas resumo ---
st.subheader("Resumo do Período")
cols = st.columns(len(tickers_selecionados))
for i, ticker in enumerate(tickers_selecionados):
    df = dados[ticker]
    cfg = acoes_config[ticker]
    preco_atual = df["Close"].iloc[-1]
    preco_inicial = df["Close"].iloc[0]
    retorno = ((preco_atual / preco_inicial) - 1) * 100
    variacao_dia = ((df["Close"].iloc[-1] / df["Close"].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
    maximo = df["High"].max()
    minimo = df["Low"].min()

    with cols[i]:
        st.metric(
            label=f"{cfg['nome']} ({ticker.replace('.SA', '')})",
            value=f"R$ {preco_atual:.2f}",
            delta=f"{variacao_dia:+.2f}% hoje"
        )
        st.caption(f"Retorno no período: **{retorno:+.2f}%**")
        st.caption(f"Máx: R$ {maximo:.2f} | Mín: R$ {minimo:.2f}")

st.markdown("---")

# --- Gráfico 1: Preço histórico ---
st.subheader("Preço de Fechamento (R$)")
fig_preco = go.Figure()
for ticker in tickers_selecionados:
    df = dados[ticker]
    cfg = acoes_config[ticker]
    fig_preco.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        name=cfg["nome"],
        line=dict(color=cfg["cor"], width=2),
        hovertemplate=f"<b>{cfg['nome']}</b><br>Data: %{{x|%d/%m/%Y}}<br>Preço: R$ %{{y:.2f}}<extra></extra>"
    ))
fig_preco.update_layout(
    xaxis_title="Data",
    yaxis_title="Preço (R$)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=400
)
st.plotly_chart(fig_preco, use_container_width=True)

# --- Gráfico 2: Retorno acumulado ---
st.subheader("Retorno Acumulado (%)")
fig_retorno = go.Figure()
for ticker in tickers_selecionados:
    df = dados[ticker]
    cfg = acoes_config[ticker]
    retorno_acum = ((df["Close"] / df["Close"].iloc[0]) - 1) * 100
    fig_retorno.add_trace(go.Scatter(
        x=df.index,
        y=retorno_acum,
        name=cfg["nome"],
        line=dict(color=cfg["cor"], width=2),
        hovertemplate=f"<b>{cfg['nome']}</b><br>Data: %{{x|%d/%m/%Y}}<br>Retorno: %{{y:+.2f}}%<extra></extra>"
    ))
fig_retorno.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig_retorno.update_layout(
    xaxis_title="Data",
    yaxis_title="Retorno Acumulado (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=400
)
st.plotly_chart(fig_retorno, use_container_width=True)

# --- Gráfico 3: Volume negociado ---
st.subheader("Volume Negociado")
fig_volume = go.Figure()
for ticker in tickers_selecionados:
    df = dados[ticker]
    cfg = acoes_config[ticker]
    fig_volume.add_trace(go.Bar(
        x=df.index,
        y=df["Volume"],
        name=cfg["nome"],
        marker_color=cfg["cor"],
        opacity=0.7,
        hovertemplate=f"<b>{cfg['nome']}</b><br>Data: %{{x|%d/%m/%Y}}<br>Volume: %{{y:,.0f}}<extra></extra>"
    ))
fig_volume.update_layout(
    xaxis_title="Data",
    yaxis_title="Volume",
    barmode="group",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=350
)
st.plotly_chart(fig_volume, use_container_width=True)

# --- Gráfico 4: Volatilidade ---
st.subheader("Volatilidade (Desvio Padrão Móvel 30 dias)")
fig_vol = go.Figure()
for ticker in tickers_selecionados:
    df = dados[ticker]
    cfg = acoes_config[ticker]
    retornos_diarios = df["Close"].pct_change()
    volatilidade = retornos_diarios.rolling(window=30).std() * 100
    fig_vol.add_trace(go.Scatter(
        x=df.index,
        y=volatilidade,
        name=cfg["nome"],
        line=dict(color=cfg["cor"], width=2),
        hovertemplate=f"<b>{cfg['nome']}</b><br>Data: %{{x|%d/%m/%Y}}<br>Volatilidade: %{{y:.2f}}%<extra></extra>"
    ))
fig_vol.update_layout(
    xaxis_title="Data",
    yaxis_title="Volatilidade (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=350
)
st.plotly_chart(fig_vol, use_container_width=True)

st.caption("Dados fornecidos pelo Yahoo Finance via yfinance. Atualizado a cada 5 minutos.")
