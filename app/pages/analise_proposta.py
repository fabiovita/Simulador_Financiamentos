"""
Página "Avaliar Proposta".

Caminho inverso ao do simulador: parte do plano que o banco já emitiu e devolve a
TIR do contrato, que é o número que decide na conversa com o cliente.
"""
import os
import tempfile
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import database as db
from analise import colagem, persistencia
from analise.calculo import calcular, comparar
from analise.conferencia import conferir
from analise.extratores import extrair, bancos_suportados
from analise.extratores.texto import PdftotextAusente, disponivel as pdftotext_ok
from analise.modelo import Proposta
from analise.reconstrucao import reconstruir, saldo_sugerido, PosFixadaSemPlano

AZUL = "#0C0CF2"
AZUL_CLARO = "#3D7CF2"


def _fmt(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(valor: float, casas: int = 2) -> str:
    return f"{valor * 100:,.{casas}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def _pp(valor: float) -> str:
    """Diferença em pontos percentuais, no padrão brasileiro."""
    return f"{valor * 100:+,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " p.p."


def render():
    st.header("Avaliar Proposta")
    st.caption(
        "Parte do plano de pagamento que o banco emitiu e devolve a TIR do contrato. "
        "Não pede taxa nem carência: a taxa é o que se quer descobrir, e a carência já "
        "está nas datas das parcelas."
    )

    cliente_id = st.session_state.get("cliente_selecionado_id")

    aba_nova, aba_salvas = st.tabs(["Nova análise", "Propostas salvas"])

    with aba_nova:
        proposta = _entrada()
        if proposta:
            _resultado(proposta, cliente_id)

    with aba_salvas:
        _salvas(cliente_id)


# ── Entrada ───────────────────────────────────────────────────────────────────

def _entrada():
    modo = st.radio(
        "De onde vem o plano",
        ["PDF da proposta", "Colar o plano", "Só a capa da proposta"],
        horizontal=True,
        help="O PDF precisa ter texto. Foto de tela ou digitalização não é lida — "
             "nesse caso, cole o plano ou use a capa.",
    )

    if modo == "PDF da proposta":
        return _entrada_pdf()
    if modo == "Colar o plano":
        return _entrada_colagem()
    return _entrada_capa()


def _entrada_pdf():
    if not pdftotext_ok():
        st.error("O utilitário pdftotext não está instalado. Instale com: brew install poppler")
        return None

    st.caption("Bancos reconhecidos: " + ", ".join(bancos_suportados()))
    arquivo = st.file_uploader("Demonstrativo do plano de pagamento", type=["pdf"])
    if not arquivo:
        return None

    caminho = os.path.join(tempfile.gettempdir(), arquivo.name)
    with open(caminho, "wb") as f:
        f.write(arquivo.getbuffer())

    try:
        proposta = extrair(caminho)
    except (ValueError, PdftotextAusente, RuntimeError) as e:
        st.error(str(e))
        return None

    st.success(
        f"{proposta.banco} · {proposta.sistema} · {proposta.num_parcelas} parcelas · "
        f"proposta de {proposta.data_proposta.strftime('%d/%m/%Y')}"
    )
    return proposta


def _entrada_colagem():
    with st.container(border=True):
        st.markdown("**1. As parcelas**")
        texto = st.text_area(
            "Cole o plano de pagamento",
            height=160,
            placeholder="12/04/2027\t20.483,17\n10/05/2027\t18.153,15\n...",
            help="Aceita a linha inteira do demonstrativo, duas colunas (data e valor) "
                 "ou só a coluna de valores.",
        )
        primeiro = st.date_input(
            "Data do primeiro vencimento (só se o texto colado não tiver datas)",
            value=None, format="DD/MM/YYYY",
        )

    if not texto.strip():
        return None

    try:
        parcelas = colagem.ler(texto, primeiro)
    except ValueError as e:
        st.error(str(e))
        return None

    st.success(f"{len(parcelas)} parcelas lidas · total {_fmt(sum(p.valor_parcela for p in parcelas))}")

    dados = _campos_dinheiro(chave="col")
    if dados is None:
        return None

    return Proposta(parcelas=parcelas, origem="colado", **dados)


def _entrada_capa():
    st.info(
        "A reconstrução pela capa é confiável em proposta **prefixada**. Em pós-fixada, a "
        "taxa impressa é apenas o spread sobre o índice, e o resultado não teria relação "
        "com o custo real."
    )

    with st.container(border=True):
        st.markdown("**1. O plano que o banco calcularia**")
        c1, c2, c3 = st.columns(3)
        pos = c1.checkbox("Proposta pós-fixada", help="Há 'Índice Pós' (CDI ou SELIC) na capa?")
        sistema = c2.selectbox("Sistema", ["SAC", "PRICE"])
        num = c3.number_input("Número de parcelas", min_value=1, max_value=360, value=42)

        c4, c5, c6 = st.columns(3)
        contratado_ref = c4.number_input("Valor contratado (R$)", min_value=0.0, step=1000.0, value=0.0)
        taxa = c5.number_input("Taxa (% a.m.)", min_value=0.0, max_value=30.0, step=0.01,
                               value=0.0, format="%.4f")
        carencia = c6.number_input("Carência (meses)", min_value=0, max_value=120, value=0)

        sugerido = saldo_sugerido(contratado_ref, taxa / 100, int(carencia)) if contratado_ref else 0.0
        c7, c8, c9 = st.columns(3)
        saldo = c7.number_input(
            "Saldo no início da amortização (R$)",
            min_value=0.0, step=1000.0, value=float(round(sugerido, 2)),
            help="Sugestão calculada da carência. O valor impresso na proposta "
                 "('Saldo Término da Carência') prevalece — sobrescreva se houver.",
        )
        primeiro = c8.date_input("1º vencimento", value=None, format="DD/MM/YYYY")
        fim_carencia = c9.date_input(
            "Início da contagem de juros", value=None, format="DD/MM/YYYY",
            help="Fim da carência, ou a data da liberação quando não há carência. "
                 "É o que permite contar os dias reais do primeiro período.",
        )

    if pos:
        st.error(
            "Proposta pós-fixada não pode ser avaliada pela capa. Peça o plano de pagamento "
            "ao gerente e use uma das outras duas entradas."
        )
        return None

    if not (saldo and taxa and primeiro):
        st.info("Preencha saldo, taxa e primeiro vencimento para reconstruir o plano.")
        return None

    try:
        parcelas = reconstruir(saldo, taxa / 100, int(num), primeiro, sistema,
                               data_base=fim_carencia, pos_fixada=False)
    except (PosFixadaSemPlano, ValueError) as e:
        st.error(str(e))
        return None

    st.success(f"{len(parcelas)} parcelas reconstruídas · total {_fmt(sum(p.valor_parcela for p in parcelas))}")

    dados = _campos_dinheiro(chave="capa", contratado_padrao=contratado_ref)
    if dados is None:
        return None

    return Proposta(parcelas=parcelas, origem="capa", **dados)


def _campos_dinheiro(chave: str, contratado_padrao: float = 0.0):
    """Campos comuns às entradas manuais: o que entra no caixa e o que a capa informa."""
    with st.container(border=True):
        st.markdown("**2. O dinheiro**")
        c1, c2, c3 = st.columns(3)
        data_proposta = c1.date_input("Data da proposta (liberação)", value=None,
                                      format="DD/MM/YYYY", key=f"{chave}_data")
        liberado = c2.number_input("Valor liberado (R$)", min_value=0.0, step=1000.0,
                                   value=0.0, key=f"{chave}_lib")
        contratado = c3.number_input("Valor contratado (R$)", min_value=0.0, step=1000.0,
                                     value=float(contratado_padrao), key=f"{chave}_ctr",
                                     help="Liberado mais as despesas financiadas.")

        c4, c5, c6 = st.columns(3)
        iof = c4.number_input("IOF (R$)", min_value=0.0, step=100.0, value=0.0, key=f"{chave}_iof")
        tac = c5.number_input("TAC (R$)", min_value=0.0, step=100.0, value=0.0, key=f"{chave}_tac")
        seguro = c6.number_input("Seguro (R$)", min_value=0.0, step=100.0, value=0.0, key=f"{chave}_seg")

        c7, c8, c9 = st.columns(3)
        fin_iof = c7.checkbox("Financia IOF", key=f"{chave}_fiof",
                              help="Marcado: soma ao contrato. Desmarcado: sai do que entra no caixa.")
        fin_tac = c8.checkbox("Financia TAC", key=f"{chave}_ftac")
        fin_seg = c9.checkbox("Financia seguro", key=f"{chave}_fseg")

        c10, c11 = st.columns(2)
        cet = c10.number_input("CET informado (% a.a.)", min_value=0.0, max_value=999.0,
                               step=0.01, value=0.0, key=f"{chave}_cet",
                               help="Opcional. Serve para confrontar com o custo recalculado.")
        banco = c11.text_input("Banco", key=f"{chave}_banco", placeholder="Ex: Sicoob")

    if not data_proposta or not liberado:
        st.info("Informe a data da proposta e o valor liberado para calcular.")
        return None

    return dict(
        data_proposta=data_proposta,
        banco=banco,
        valor_liberado=liberado,
        valor_proposta=liberado,
        valor_contratado=contratado or liberado,
        iof=iof, tac=tac, seguro=seguro,
        financia_iof=fin_iof, financia_tac=fin_tac, financia_seguro=fin_seg,
        cet_aa_informado=(cet / 100) if cet else None,
    )


# ── Resultado ─────────────────────────────────────────────────────────────────

def _resultado(proposta: Proposta, cliente_id):
    try:
        ind = calcular(proposta)
    except ValueError as e:
        st.error(str(e))
        return

    conf = conferir(proposta, ind.tir_real_aa)

    if conf.houve_checagem and not conf.confere:
        st.error("A leitura não bate com os totais impressos no documento. Confira antes de usar.")
        for c in conf.falhas:
            st.write(f"- **{c.nome}**: documento {_fmt(c.impresso)} · lido {_fmt(c.calculado)} "
                     f"· diferença {_fmt(c.diferenca)}")
        if not st.checkbox("Entendi a divergência e quero ver o resultado assim mesmo"):
            return
    elif conf.houve_checagem:
        st.success("Confere com os totais impressos no documento.")

    st.divider()
    st.subheader("Custo efetivo do contrato")
    c1, c2, c3 = st.columns(3)
    c1.metric("TIR sobre o líquido recebido", _pct(ind.tir_real_aa),
              help="O custo efetivo real: o que entrou no caixa contra as parcelas nas "
                   "datas de vencimento. É o número comparável entre propostas.")
    c2.metric("Juros implícitos no plano", _pct(ind.tir_plano_aa),
              help="Mesma conta sobre o valor contratado. Denuncia taxa anunciada que não "
                   "reproduz o próprio plano de pagamento.")
    # Divergência desprezível não é notícia: mostra em cinza em vez de vermelho.
    divergente = ind.divergencia_cet is not None and abs(ind.divergencia_cet) > 0.0005
    c3.metric("CET informado", _pct(ind.cet_informado_aa) if ind.cet_informado_aa else "—",
              delta=_pp(ind.divergencia_cet) if ind.divergencia_cet is not None else None,
              delta_color="inverse" if divergente else "off")
    st.caption(f"Equivalente mensal: {_pct(ind.tir_real_am, 4)} a.m.")

    _alertas(proposta, ind)

    st.divider()
    st.subheader("O que entra e o que sai")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Líquido no caixa", _fmt(ind.liquido_recebido))
    c2.metric("Total pago", _fmt(ind.total_pago))
    c3.metric("Custo total", _fmt(ind.custo_total))
    c4.metric("Custo por R$ 1,00 que entra", f"{ind.custo_por_real:.4f}".replace(".", ","))

    if proposta.descontado_na_liberacao:
        st.caption(f"Descontado na liberação: {_fmt(proposta.descontado_na_liberacao)} "
                   "(despesas não financiadas saem do que entra no caixa).")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("1ª parcela", _fmt(ind.primeira_parcela))
    c2.metric("Maior parcela", _fmt(ind.maior_parcela),
              help="É este valor que o caixa precisa suportar no pior mês.")
    c3.metric("Menor parcela", _fmt(ind.menor_parcela))
    c4.metric("Desembolso em 12 meses", _fmt(ind.desembolso_12m))

    _graficos(proposta, ind)

    with st.expander("Ver o fluxo que gerou a TIR"):
        st.caption("A primeira linha é a liberação (negativa); as demais são as parcelas.")
        df = pd.DataFrame({
            "Data": [d.strftime("%d/%m/%Y") for d, _ in ind.fluxo_real],
            "Fluxo real (líquido recebido)": [_fmt(v) for _, v in ind.fluxo_real],
            "Fluxo do plano (valor contratado)": [_fmt(v) for _, v in ind.fluxo_plano],
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Ver a conferência linha a linha"):
        for c in conf.checagens:
            if c.impresso is None:
                continue
            marca = "OK" if c.ok else "DIVERGE"
            rotulo = c.nome if c.bloqueante else f"{c.nome} (informativo)"
            st.write(f"**{marca}** · {rotulo} — documento {c.impresso:,.4f} · "
                     f"calculado {c.calculado:,.4f}")
            if c.observacao:
                st.caption(c.observacao)

    _salvar(proposta, cliente_id)


def _alertas(proposta: Proposta, ind):
    if proposta.pos_fixada:
        texto = (f"**Proposta pós-fixada em {proposta.perc_pos:.0f}% do {proposta.indice_pos}.** "
                 "A taxa nominal impressa é apenas o spread; o plano de pagamento é uma "
                 "projeção, não um compromisso. Se o índice subir, as parcelas sobem.")
        if ind.indexador_implicito is not None:
            texto += (f" O plano projeta {proposta.indice_pos} de aproximadamente "
                      f"{_pct(ind.indexador_implicito)} a.a. — vale conferir contra o "
                      "índice vigente na data da contratação.")
        st.warning(texto)

    if ind.divergencia_cet is not None and abs(ind.divergencia_cet) > 0.0005:
        st.warning(
            f"**O CET informado não reproduz o plano de pagamento.** O documento anuncia "
            f"{_pct(ind.cet_informado_aa)} a.a., e o fluxo real devolve {_pct(ind.tir_real_aa)} a.a. "
            f"— diferença de {_pp(ind.divergencia_cet)} Um CET assim não é "
            "comparável ao de outra proposta calculada pelo critério cheio; para decidir, use o "
            "custo em reais, que não depende de convenção de taxa."
        )


def _graficos(proposta: Proposta, ind):
    tab1, tab2 = st.tabs(["Parcelas", "Desembolso por ano"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[p.numero for p in proposta.parcelas],
            y=[p.valor_parcela for p in proposta.parcelas],
            mode="lines+markers", name="Parcela", line=dict(color=AZUL),
        ))
        fig.update_layout(title="Valor da parcela por período", xaxis_title="Parcela",
                          yaxis_title="R$", height=380, legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        anos = list(ind.desembolso_por_ano.keys())
        fig2 = go.Figure(go.Bar(
            x=anos, y=[ind.desembolso_por_ano[a] for a in anos], marker_color=AZUL_CLARO,
        ))
        fig2.update_layout(title="Parcelas vencendo por ano", xaxis_title="Ano",
                           yaxis_title="R$", height=380)
        st.plotly_chart(fig2, use_container_width=True)


def _salvar(proposta: Proposta, cliente_id):
    st.divider()
    clientes = db.listar_clientes()
    if not clientes:
        st.info("Cadastre um cliente para poder salvar a análise.")
        return

    st.subheader("Salvar esta análise")
    opcoes = {c.nome: c.id for c in clientes}
    c1, c2 = st.columns([1, 2])
    indice = list(opcoes.values()).index(cliente_id) if cliente_id in opcoes.values() else 0
    nome = c1.selectbox("Cliente", list(opcoes.keys()), index=indice, key="ap_cliente")
    sugestao = " ".join(x for x in (proposta.banco, proposta.sistema,
                                    f"{proposta.num_parcelas}x") if x).strip()
    apelido = c2.text_input("Identificação", value=sugestao, key="ap_apelido",
                            placeholder="Ex: Sicoob FGI 42x")

    if st.button("Salvar análise", type="primary"):
        if not apelido.strip():
            st.error("Dê um nome à proposta para conseguir reconhecê-la depois.")
        else:
            persistencia.salvar(proposta, opcoes[nome], apelido.strip())
            st.success(f"Análise salva para {nome}.")


# ── Propostas salvas e comparação ─────────────────────────────────────────────

def _salvas(cliente_id):
    clientes = db.listar_clientes()
    if not clientes:
        st.info("Nenhum cliente cadastrado.")
        return

    opcoes = {c.nome: c.id for c in clientes}
    indice = list(opcoes.values()).index(cliente_id) if cliente_id in opcoes.values() else 0
    nome = st.selectbox("Cliente", list(opcoes.keys()), index=indice, key="sv_cliente")
    salvas = db.listar_propostas(opcoes[nome])

    if not salvas:
        st.info("Nenhuma proposta salva para este cliente.")
        return

    linhas = []
    for s in salvas:
        p = persistencia.carregar(s.id)
        i = calcular(p)
        linhas.append({
            "Proposta": s.apelido,
            "Banco": s.banco or "—",
            "Parcelas": p.num_parcelas,
            "Líquido": _fmt(i.liquido_recebido),
            "Custo total": _fmt(i.custo_total),
            "TIR (a.a.)": _pct(i.tir_real_aa),
            "Salva em": s.criado_em or "",
        })
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    if len(salvas) >= 2:
        st.subheader("Comparar duas propostas")
        rotulos = {f"{s.apelido} (#{s.id})": s.id for s in salvas}
        c1, c2 = st.columns(2)
        a = c1.selectbox("Proposta A", list(rotulos.keys()), index=0, key="cmp_a")
        b = c2.selectbox("Proposta B", list(rotulos.keys()), index=1, key="cmp_b")
        if rotulos[a] != rotulos[b]:
            _comparar(rotulos[a], rotulos[b])

    st.divider()
    alvo = st.selectbox("Excluir análise", ["(nenhuma)"] + [f"{s.apelido} (#{s.id})" for s in salvas],
                        key="sv_excluir")
    if alvo != "(nenhuma)" and st.button("Excluir"):
        db.excluir_proposta(int(alvo.rsplit("#", 1)[1].rstrip(")")))
        st.success("Análise excluída.")
        st.rerun()


def _comparar(id_a: int, id_b: int):
    pa, pb = persistencia.carregar(id_a), persistencia.carregar(id_b)
    dif = comparar(pa, pb)

    rotulos = {
        "liquido_recebido": ("Líquido no caixa", _fmt),
        "total_pago": ("Total pago", _fmt),
        "custo_total": ("Custo total", _fmt),
        "custo_por_real": ("Custo por R$ 1,00 que entra", lambda v: f"{v:.4f}".replace(".", ",")),
        "tir_real_aa": ("TIR sobre o líquido (a.a.)", _pct),
        "maior_parcela": ("Maior parcela", _fmt),
        "desembolso_12m": ("Desembolso em 12 meses", _fmt),
    }
    linhas = [
        # A diferença entre duas taxas é em pontos percentuais, não em porcentagem
        {"Indicador": rot, "A": f(va), "B": f(vb),
         "B − A": _pp(d) if chave == "tir_real_aa" else f(d)}
        for chave, (rot, f) in rotulos.items()
        for va, vb, d in [dif[chave]]
    ]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
    st.caption(
        "O custo em reais é o critério que não depende de convenção de taxa — é o que "
        "vale quando os CETs das duas propostas foram calculados por critérios diferentes."
    )
