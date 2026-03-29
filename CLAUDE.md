# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos Essenciais

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar a aplicação
streamlit run app.py
```

A aplicação sobe em `http://localhost:8501` por padrão.

## Arquitetura

Projeto de arquivo único (`app.py`) — um dashboard financeiro Streamlit para o mercado de ações brasileiro (B3).

**Fluxo de dados:**
1. Usuário configura período e ações no sidebar
2. `carregar_dados()` busca dados via yfinance (cache de 5 min via `@st.cache_data(ttl=300)`)
3. Pandas processa os dados brutos em métricas
4. Plotly renderiza 4 gráficos independentes (preço, retorno acumulado, volume, volatilidade)
5. Streamlit atualiza tudo reativamente

**Ações monitoradas:**
- `PETR4.SA` — Petrobras
- `ITUB4.SA` — Itaú
- `VALE3.SA` — Vale

**Dependências principais:** `streamlit`, `yfinance`, `pandas`, `plotly`

## Pontos de Atenção

- yfinance retorna colunas multi-índice quando múltiplas ações são buscadas — o código trata isso explicitamente ao achatar os nomes de colunas.
- O sufixo `.SA` é obrigatório no ticker para ações da B3.
- Toda a interface está em português, incluindo rótulos de gráficos e formatação de moeda (R$).
