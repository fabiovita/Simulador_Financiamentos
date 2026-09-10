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
├── models.py           # Dataclasses: Cliente, Emprestimo, PropostaSalva, ParcelaSalva
├── database.py         # Acesso SQLite (dados.db) — funções CRUD diretas, sem ORM
├── validators.py       # Validação/formatação de CPF, CNPJ, e-mail, telefone
├── calculators/
│   ├── sac.py          # calcular_sac() → DataFrame com tabela SAC
│   ├── price.py        # calcular_price() → DataFrame com tabela PRICE
│   ├── periodo.py      # Juros do período conforme a convenção de contagem
│   ├── tir.py          # xnpv/xirr — TIR com datas irregulares (equivale ao XTIR)
│   └── cashflow.py     # Fluxo de caixa consolidado
├── analise/            # Avaliação de propostas já emitidas por bancos
│   ├── modelo.py       # Proposta e ParcelaPlano — formato normalizado
│   ├── calculo.py      # Indicadores a partir do formato normalizado
│   ├── conferencia.py  # Reconciliação com os totais impressos pelo banco
│   ├── colagem.py      # Leitura de plano colado de PDF ou planilha
│   ├── reconstrucao.py # Geração do plano a partir da capa da proposta
│   ├── persistencia.py # Ponte entre Proposta e as tabelas do banco
│   └── extratores/     # Um módulo por banco; registry em __init__.py
├── pages/
│   ├── clientes.py     # CRUD de clientes
│   ├── endividamento.py # Listagem e gestão de empréstimos por cliente
│   ├── simulador.py    # Simulação SAC/PRICE sem salvar no banco
│   ├── analise_proposta.py # Avaliação de proposta: TIR, alertas, comparação
│   └── fluxo_caixa.py  # Visualização do fluxo de caixa
├── reports/
│   └── pdf_generator.py # Geração de relatório PDF com ReportLab
└── tests/
    ├── fixtures/       # Planos já extraídos, em JSON (PDFs ficam fora do git)
    └── verificar.py    # Verificação sem framework: python3 tests/verificar.py
```

## Os dois modos do app

- **Simular** (`pages/simulador.py`): não existe proposta ainda. Recebe valor, taxa e prazo
  e gera a tabela. Serve para planejar.
- **Avaliar proposta** (`pages/analise_proposta.py`): a proposta existe e o plano está
  impresso. Devolve a TIR do contrato. Não pede taxa nem carência — a taxa é o que se quer
  descobrir, e a carência já está nas datas das parcelas.

Usar o modo Simular para reproduzir uma proposta emitida não funciona: bancos contam juros
por dias corridos e o gerado não fecha com o impresso.

## Fluxo de dados

- `database.py` é a única camada que toca o SQLite (`dados.db` dentro de `app/`)
- As páginas importam `database as db` e `models` diretamente — não há camada de serviço intermediária
- As calculadoras recebem parâmetros primitivos e retornam `pd.DataFrame`; são stateless e não acessam o banco
- O cliente selecionado é propagado entre páginas via `st.session_state["cliente_selecionado_id"]`

## Git

- Commitar a cada mudança lógica completa e testada (ex: correção de cálculo, novo campo, ajuste de layout)
- Não acumular todas as alterações da sessão em um único commit no final
- Mensagens de commit em português, descrevendo o que mudou e por quê

## Convenções

- `taxa_mensal` é sempre armazenada e manipulada em decimal (ex: `0.0132` = 1,32%)
- `primeira_parcela` é string ISO `"YYYY-MM-DD"` no banco e nos modelos; as calculadoras recebem `date`
- Ambas as tabelas (SAC e PRICE) suportam **carência total**: durante os `carencia` primeiros meses não há pagamento e os juros são capitalizados no saldo (`saldo_final = saldo + juros`); a amortização/PMT é recalculada sobre o saldo acumulado ao fim da carência
- `carencia` é campo `int` em `Emprestimo` (default `0`); valor `0` mantém comportamento idêntico ao sem carência
- Migrações de schema são feitas inline em `init_db()` com `ALTER TABLE` condicional — não há sistema de migrations
- `convencao` nas calculadoras: `"mes_cheio"` (default, preserva o comportamento antigo) ou
  `"dias"`, que cobra juros pro-rata pelos dias corridos do período em base 30. Mudar o default
  alteraria os financiamentos já cadastrados e o Fluxo de Caixa
- No módulo `analise/`, o cálculo é universal e só a extração é específica de cada banco.
  Acrescentar um banco é escrever um módulo com `reconhece(texto)` e `extrair(pdf)` e registrá-lo
  em `analise/extratores/__init__.py` — nada no cálculo muda
- Nenhum número calculado é exibido sem se reconciliar com algum total impresso pelo próprio
  documento (`analise/conferencia.py`). Extração que não confere é erro; CET que não confere é
  a análise (checagem não bloqueante)
- Proposta pós-fixada (campo `Índice Pós`) não pode ser reconstruída pela capa: a taxa impressa
  é só o spread sobre o indexador
