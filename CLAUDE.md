# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Como executar

```bash
# Via script
./iniciar_app.sh

# Diretamente
cd app && python3 -m streamlit run app.py
```

## Arquitetura

App Streamlit single-page com roteamento manual via `st.session_state["pagina"]`. O ponto de entrada é `app/app.py`, que inicializa o banco, monta o sidebar e despacha para o módulo de página correto.

```
app/
├── app.py              # Entrada, sidebar, roteamento
├── models.py           # Dataclasses: Cliente, Emprestimo
├── database.py         # Acesso SQLite (dados.db) — funções CRUD diretas, sem ORM
├── validators.py       # Validação/formatação de CPF, CNPJ, e-mail, telefone
├── calculators/
│   ├── sac.py          # calcular_sac() → DataFrame com tabela SAC
│   ├── price.py        # calcular_price() → DataFrame com tabela PRICE
│   └── cashflow.py     # Fluxo de caixa consolidado
├── pages/
│   ├── clientes.py     # CRUD de clientes
│   ├── endividamento.py # Listagem e gestão de empréstimos por cliente
│   ├── simulador.py    # Simulação SAC/PRICE sem salvar no banco
│   └── fluxo_caixa.py  # Visualização do fluxo de caixa
└── reports/
    └── pdf_generator.py # Geração de relatório PDF com ReportLab
```

## Fluxo de dados

- `database.py` é a única camada que toca o SQLite (`dados.db` dentro de `app/`)
- As páginas importam `database as db` e `models` diretamente — não há camada de serviço intermediária
- As calculadoras recebem parâmetros primitivos e retornam `pd.DataFrame`; são stateless e não acessam o banco
- O cliente selecionado é propagado entre páginas via `st.session_state["cliente_selecionado_id"]`

## Convenções

- `taxa_mensal` é sempre armazenada e manipulada em decimal (ex: `0.0132` = 1,32%)
- `primeira_parcela` é string ISO `"YYYY-MM-DD"` no banco e nos modelos; as calculadoras recebem `date`
- Ambas as tabelas (SAC e PRICE) suportam **carência total**: durante os `carencia` primeiros meses não há pagamento e os juros são capitalizados no saldo (`saldo_final = saldo + juros`); a amortização/PMT é recalculada sobre o saldo acumulado ao fim da carência
- `carencia` é campo `int` em `Emprestimo` (default `0`); valor `0` mantém comportamento idêntico ao sem carência
- Migrações de schema são feitas inline em `init_db()` com `ALTER TABLE` condicional — não há sistema de migrations
