import sqlite3
import os
from datetime import date
from typing import List, Optional
from models import Cliente, Emprestimo, PropostaSalva, ParcelaSalva

DB_PATH = os.path.join(os.path.dirname(__file__), "dados.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT NOT NULL,
                cnpj_cpf  TEXT,
                contato   TEXT,
                criado_em TEXT DEFAULT (date('now'))
            )
        """)
        # Migração: adiciona email e telefone se ainda não existirem
        colunas = {r[1] for r in con.execute("PRAGMA table_info(clientes)").fetchall()}
        if "email" not in colunas:
            con.execute("ALTER TABLE clientes ADD COLUMN email TEXT DEFAULT ''")
        if "telefone" not in colunas:
            con.execute("ALTER TABLE clientes ADD COLUMN telefone TEXT DEFAULT ''")
        con.execute("""
            CREATE TABLE IF NOT EXISTS emprestimos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id       INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                credor           TEXT NOT NULL,
                produto          TEXT,
                tabela           TEXT NOT NULL,
                valor_liquido    REAL NOT NULL,
                taxa_mensal      REAL NOT NULL,
                num_parcelas     INTEGER NOT NULL,
                primeira_parcela TEXT NOT NULL,
                parcelas_pagas   INTEGER DEFAULT 0,
                status           TEXT DEFAULT 'ativo',
                carencia         INTEGER DEFAULT 0
            )
        """)
        try:
            con.execute("ALTER TABLE emprestimos ADD COLUMN carencia INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE emprestimos ADD COLUMN carencia_tipo TEXT DEFAULT 'capitalizado'")
        except Exception:
            pass
        con.execute("""
            CREATE TABLE IF NOT EXISTS propostas (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id       INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                apelido          TEXT NOT NULL,
                banco            TEXT,
                linha            TEXT,
                sistema          TEXT,
                data_proposta    TEXT,
                valor_proposta   REAL,
                valor_contratado REAL,
                valor_liberado   REAL,
                iof              REAL,
                tac              REAL,
                seguro           REAL,
                financia_iof     INTEGER DEFAULT 0,
                financia_tac     INTEGER DEFAULT 0,
                financia_seguro  INTEGER DEFAULT 0,
                taxa_nominal_am  REAL,
                cet_aa_informado REAL,
                indice_pos       TEXT,
                perc_pos         REAL,
                origem           TEXT,
                arquivo          TEXT,
                criado_em        TEXT DEFAULT (date('now'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS parcelas_proposta (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id   INTEGER NOT NULL REFERENCES propostas(id) ON DELETE CASCADE,
                numero        INTEGER NOT NULL,
                vencimento    TEXT NOT NULL,
                valor_parcela REAL NOT NULL,
                amortizacao   REAL,
                juros         REAL,
                iof           REAL,
                saldo_devedor REAL
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_parcelas_proposta
            ON parcelas_proposta(proposta_id)
        """)


# ── Clientes ──────────────────────────────────────────────────────────────────

def inserir_cliente(c: Cliente) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO clientes (nome, cnpj_cpf, email, telefone) VALUES (?, ?, ?, ?)",
            (c.nome, c.cnpj_cpf, c.email, c.telefone),
        )
        return cur.lastrowid


def listar_clientes() -> List[Cliente]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, nome, cnpj_cpf, email, telefone, criado_em FROM clientes ORDER BY nome"
        ).fetchall()
    return [Cliente(id=r[0], nome=r[1], cnpj_cpf=r[2], email=r[3] or "", telefone=r[4] or "", criado_em=r[5]) for r in rows]


def buscar_cliente(cliente_id: int) -> Optional[Cliente]:
    with _conn() as con:
        r = con.execute(
            "SELECT id, nome, cnpj_cpf, email, telefone, criado_em FROM clientes WHERE id = ?",
            (cliente_id,),
        ).fetchone()
    if r:
        return Cliente(id=r[0], nome=r[1], cnpj_cpf=r[2], email=r[3] or "", telefone=r[4] or "", criado_em=r[5])
    return None


def atualizar_cliente(c: Cliente):
    with _conn() as con:
        con.execute(
            "UPDATE clientes SET nome=?, cnpj_cpf=?, email=?, telefone=? WHERE id=?",
            (c.nome, c.cnpj_cpf, c.email, c.telefone, c.id),
        )


def excluir_cliente(cliente_id: int):
    with _conn() as con:
        con.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))


# ── Empréstimos ───────────────────────────────────────────────────────────────

def inserir_emprestimo(e: Emprestimo) -> int:
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO emprestimos
               (cliente_id, credor, produto, tabela, valor_liquido, taxa_mensal,
                num_parcelas, primeira_parcela, parcelas_pagas, status, carencia, carencia_tipo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (e.cliente_id, e.credor, e.produto, e.tabela, e.valor_liquido,
             e.taxa_mensal, e.num_parcelas, e.primeira_parcela,
             e.parcelas_pagas, e.status, e.carencia, e.carencia_tipo),
        )
        return cur.lastrowid


def listar_emprestimos(cliente_id: int) -> List[Emprestimo]:
    with _conn() as con:
        rows = con.execute(
            """SELECT id, cliente_id, credor, produto, tabela, valor_liquido,
                      taxa_mensal, num_parcelas, primeira_parcela, parcelas_pagas, status, carencia, carencia_tipo
               FROM emprestimos WHERE cliente_id = ? ORDER BY primeira_parcela""",
            (cliente_id,),
        ).fetchall()
    return [_row_to_emprestimo(r) for r in rows]


def buscar_emprestimo(emprestimo_id: int) -> Optional[Emprestimo]:
    with _conn() as con:
        r = con.execute(
            """SELECT id, cliente_id, credor, produto, tabela, valor_liquido,
                      taxa_mensal, num_parcelas, primeira_parcela, parcelas_pagas, status, carencia, carencia_tipo
               FROM emprestimos WHERE id = ?""",
            (emprestimo_id,),
        ).fetchone()
    return _row_to_emprestimo(r) if r else None


def atualizar_emprestimo(e: Emprestimo):
    with _conn() as con:
        con.execute(
            """UPDATE emprestimos SET credor=?, produto=?, tabela=?, valor_liquido=?,
               taxa_mensal=?, num_parcelas=?, primeira_parcela=?, parcelas_pagas=?, status=?,
               carencia=?, carencia_tipo=?
               WHERE id=?""",
            (e.credor, e.produto, e.tabela, e.valor_liquido, e.taxa_mensal,
             e.num_parcelas, e.primeira_parcela, e.parcelas_pagas, e.status,
             e.carencia, e.carencia_tipo, e.id),
        )


def excluir_emprestimo(emprestimo_id: int):
    with _conn() as con:
        con.execute("DELETE FROM emprestimos WHERE id = ?", (emprestimo_id,))


# ── Propostas analisadas ──────────────────────────────────────────────────────

_CAMPOS_PROPOSTA = (
    "cliente_id, apelido, banco, linha, sistema, data_proposta, valor_proposta, "
    "valor_contratado, valor_liberado, iof, tac, seguro, financia_iof, financia_tac, "
    "financia_seguro, taxa_nominal_am, cet_aa_informado, indice_pos, perc_pos, origem, arquivo"
)


def inserir_proposta(p: PropostaSalva, parcelas: List[ParcelaSalva]) -> int:
    """Grava cabeçalho e parcelas numa transação só."""
    with _conn() as con:
        cur = con.execute(
            f"INSERT INTO propostas ({_CAMPOS_PROPOSTA}) VALUES ({', '.join('?' * 21)})",
            (p.cliente_id, p.apelido, p.banco, p.linha, p.sistema, p.data_proposta,
             p.valor_proposta, p.valor_contratado, p.valor_liberado, p.iof, p.tac, p.seguro,
             int(p.financia_iof), int(p.financia_tac), int(p.financia_seguro),
             p.taxa_nominal_am, p.cet_aa_informado, p.indice_pos, p.perc_pos,
             p.origem, p.arquivo),
        )
        proposta_id = cur.lastrowid
        con.executemany(
            """INSERT INTO parcelas_proposta
               (proposta_id, numero, vencimento, valor_parcela, amortizacao, juros, iof, saldo_devedor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(proposta_id, x.numero, x.vencimento, x.valor_parcela,
              x.amortizacao, x.juros, x.iof, x.saldo_devedor) for x in parcelas],
        )
        return proposta_id


def listar_propostas(cliente_id: int) -> List[PropostaSalva]:
    with _conn() as con:
        rows = con.execute(
            f"SELECT id, {_CAMPOS_PROPOSTA}, criado_em FROM propostas "
            "WHERE cliente_id = ? ORDER BY criado_em DESC, id DESC",
            (cliente_id,),
        ).fetchall()
    return [_row_to_proposta(r) for r in rows]


def buscar_proposta(proposta_id: int) -> Optional[PropostaSalva]:
    with _conn() as con:
        r = con.execute(
            f"SELECT id, {_CAMPOS_PROPOSTA}, criado_em FROM propostas WHERE id = ?",
            (proposta_id,),
        ).fetchone()
    return _row_to_proposta(r) if r else None


def listar_parcelas_proposta(proposta_id: int) -> List[ParcelaSalva]:
    with _conn() as con:
        rows = con.execute(
            """SELECT id, proposta_id, numero, vencimento, valor_parcela,
                      amortizacao, juros, iof, saldo_devedor
               FROM parcelas_proposta WHERE proposta_id = ? ORDER BY numero""",
            (proposta_id,),
        ).fetchall()
    return [ParcelaSalva(
        id=r[0], proposta_id=r[1], numero=r[2], vencimento=r[3], valor_parcela=r[4],
        amortizacao=r[5], juros=r[6], iof=r[7], saldo_devedor=r[8],
    ) for r in rows]


def excluir_proposta(proposta_id: int):
    with _conn() as con:
        con.execute("DELETE FROM parcelas_proposta WHERE proposta_id = ?", (proposta_id,))
        con.execute("DELETE FROM propostas WHERE id = ?", (proposta_id,))


def _row_to_proposta(r) -> PropostaSalva:
    return PropostaSalva(
        id=r[0], cliente_id=r[1], apelido=r[2], banco=r[3], linha=r[4], sistema=r[5],
        data_proposta=r[6], valor_proposta=r[7], valor_contratado=r[8], valor_liberado=r[9],
        iof=r[10], tac=r[11], seguro=r[12],
        financia_iof=bool(r[13]), financia_tac=bool(r[14]), financia_seguro=bool(r[15]),
        taxa_nominal_am=r[16], cet_aa_informado=r[17], indice_pos=r[18], perc_pos=r[19],
        origem=r[20], arquivo=r[21], criado_em=r[22],
    )


def _row_to_emprestimo(r) -> Emprestimo:
    return Emprestimo(
        id=r[0], cliente_id=r[1], credor=r[2], produto=r[3], tabela=r[4],
        valor_liquido=r[5], taxa_mensal=r[6], num_parcelas=r[7],
        primeira_parcela=r[8], parcelas_pagas=r[9], status=r[10],
        carencia=r[11] if len(r) > 11 and r[11] is not None else 0,
        carencia_tipo=r[12] if len(r) > 12 and r[12] is not None else "capitalizado",
    )
