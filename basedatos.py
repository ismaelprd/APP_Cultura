"""Acceso a datos compartido por bot.py y recordatorio.py (misma base de datos que app.py)."""
import json
import os
import sqlite3
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # en GitHub Actions no hace falta
    pass

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
DB_PATH = "cultura.db"

# Mismo orden que las columnas de la tabla cards (ver app.py)
CARD_COLS = [
    "id", "tema", "area", "subarea", "tipo", "pregunta", "respuesta", "explicacion",
    "dificultad", "elementos", "conceptos", "verificar", "fsrs_state", "due", "creada",
    "mnemotecnia", "origen", "verificacion",
]


def ahora():
    return datetime.now(timezone.utc)


def conectar():
    if TURSO_URL:
        import libsql
        return libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)
    return sqlite3.connect(DB_PATH)


def _cerrar(conn):
    try:
        conn.close()
    except Exception:
        pass


def consultar(sql, params=(), cols=None):
    conn = conectar()
    try:
        filas = conn.execute(sql, params).fetchall()
    finally:
        _cerrar(conn)
    return [dict(zip(cols, f)) for f in filas] if cols else [tuple(f) for f in filas]


def escribir(sentencias):
    conn = conectar()
    try:
        for sql, params in sentencias:
            conn.execute(sql, params)
        conn.commit()
    finally:
        _cerrar(conn)


def contar_pendientes():
    pend = consultar("SELECT COUNT(*) FROM cards WHERE due <= ?", (ahora().isoformat(),))[0][0]
    total = consultar("SELECT COUNT(*) FROM cards")[0][0]
    return pend, total


def siguiente_tarjeta():
    filas = consultar("SELECT * FROM cards WHERE due <= ? ORDER BY due LIMIT 1",
                      (ahora().isoformat(),), cols=CARD_COLS)
    return filas[0] if filas else None


def repasar(card_id, rating):
    from fsrs import Card, Scheduler
    estado = consultar("SELECT fsrs_state FROM cards WHERE id=?", (card_id,))[0][0]
    card, _log = Scheduler().review_card(Card.from_dict(json.loads(estado)), rating)
    escribir([
        ("UPDATE cards SET fsrs_state=?, due=? WHERE id=?",
         (json.dumps(card.to_dict()), card.due.isoformat(), card_id)),
        ("INSERT INTO reviews (card_id, rating, ts) VALUES (?,?,?)",
         (card_id, int(rating), ahora().isoformat())),
    ])
