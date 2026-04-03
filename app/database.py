import sqlite3
import os
from datetime import date
from typing import List, Optional
from models import Cliente, Emprestimo

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


def _row_to_emprestimo(r) -> Emprestimo:
    return Emprestimo(
        id=r[0], cliente_id=r[1], credor=r[2], produto=r[3], tabela=r[4],
        valor_liquido=r[5], taxa_mensal=r[6], num_parcelas=r[7],
        primeira_parcela=r[8], parcelas_pagas=r[9], status=r[10],
        carencia=r[11] if len(r) > 11 and r[11] is not None else 0,
        carencia_tipo=r[12] if len(r) > 12 and r[12] is not None else "capitalizado",
    )
