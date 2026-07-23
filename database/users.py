from typing import Optional

from database.connection import get_connection


ALLOWED_ROLES = {
    "operator",
    "engineer",
    "admin",
}


def add_user(
    telegram_id: int,
    full_name: str,
    role: str,
) -> int:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Недопустимая роль: {role}")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            telegram_id,
            full_name,
            role
        )
        VALUES (?, ?, ?)
        """,
        (
            telegram_id,
            full_name.strip(),
            role,
        ),
    )

    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    return user_id


def get_user_by_telegram_id(
    telegram_id: int,
) -> Optional[dict]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            full_name,
            role,
            is_active,
            created_at
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def user_exists(telegram_id: int) -> bool:
    return get_user_by_telegram_id(telegram_id) is not None


def update_user(
    telegram_id: int,
    full_name: str,
    role: str,
    is_active: bool = True,
) -> bool:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Недопустимая роль: {role}")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET
            full_name = ?,
            role = ?,
            is_active = ?
        WHERE telegram_id = ?
        """,
        (
            full_name.strip(),
            role,
            int(is_active),
            telegram_id,
        ),
    )

    connection.commit()
    updated = cursor.rowcount > 0
    connection.close()

    return updated


def add_or_update_user(
    telegram_id: int,
    full_name: str,
    role: str,
) -> int:
    existing_user = get_user_by_telegram_id(telegram_id)

    if existing_user is None:
        return add_user(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
        )

    update_user(
        telegram_id=telegram_id,
        full_name=full_name,
        role=role,
        is_active=True,
    )

    return existing_user["id"]

def get_active_users_by_role(role: str) -> list[dict]:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Недопустимая роль: {role}")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            full_name,
            role,
            is_active,
            created_at
        FROM users
        WHERE role = ?
          AND is_active = 1
        ORDER BY full_name
        """,
        (role,),
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]
