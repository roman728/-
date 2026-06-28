import sqlite3
from datetime import datetime

DB_NAME = "robo_stock.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unit TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        min_quantity INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        action TEXT NOT NULL,
        amount INTEGER NOT NULL,
        before_qty INTEGER NOT NULL,
        after_qty INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]

    if count == 0:
        demo_items = [
            ("Сопла", "шт.", 17, 10),
            ("Наконечники", "шт.", 34, 15),
            ("Контактные трубки", "шт.", 8, 10),
            ("Проволока", "кат.", 6, 3),
            ("Спрей антипригарный", "шт.", 1, 3),
        ]

        cur.executemany(
            "INSERT INTO items (name, unit, quantity, min_quantity) VALUES (?, ?, ?, ?)",
            demo_items,
        )

    conn.commit()
    conn.close()


def get_all_items():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, unit, quantity, min_quantity FROM items ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_item(item_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, unit, quantity, min_quantity FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_low_items():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
    SELECT id, name, unit, quantity, min_quantity
    FROM items
    WHERE quantity <= min_quantity
    ORDER BY quantity ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def change_quantity(item_id: int, amount: int, action: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id, name, unit, quantity, min_quantity FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return False, "Расходник не найден."

    _, name, unit, before_qty, min_quantity = row
    after_qty = before_qty + amount

    if after_qty < 0:
        conn.close()
        return False, "Нельзя списать больше, чем есть в остатке."

    cur.execute("UPDATE items SET quantity = ? WHERE id = ?", (after_qty, item_id))

    cur.execute(
        """
        INSERT INTO history 
        (item_id, item_name, action, amount, before_qty, after_qty, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            name,
            action,
            abs(amount),
            before_qty,
            after_qty,
            datetime.now().strftime("%d.%m.%Y %H:%M"),
        ),
    )

    conn.commit()
    conn.close()

    return True, {
        "name": name,
        "unit": unit,
        "before": before_qty,
        "after": after_qty,
        "amount": abs(amount),
        "min_quantity": min_quantity,
    }


def get_history(limit: int = 10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT item_name, action, amount, before_qty, after_qty, created_at
        FROM history
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
