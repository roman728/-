from typing import Optional

from database.connection import get_connection


def start_session(operator_id: int) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM work_sessions
        WHERE operator_id = ?
          AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (operator_id,),
    )

    active_session = cursor.fetchone()

    if active_session is not None:
        connection.close()
        return active_session["id"]

    cursor.execute(
        """
        INSERT INTO work_sessions (
            operator_id,
            status
        )
        VALUES (?, 'active')
        """,
        (operator_id,),
    )

    connection.commit()
    session_id = cursor.lastrowid
    connection.close()

    return session_id


def get_active_session(operator_id: int) -> Optional[dict]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            operator_id,
            started_at,
            finished_at,
            status
        FROM work_sessions
        WHERE operator_id = ?
          AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (operator_id,),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def finish_session(operator_id: int) -> Optional[dict]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM work_sessions
        WHERE operator_id = ?
          AND status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """,
        (operator_id,),
    )

    session = cursor.fetchone()

    if session is None:
        connection.close()
        return None

    session_id = session["id"]

    cursor.execute(
        """
        UPDATE work_sessions
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = 'finished'
        WHERE id = ?
          AND status = 'active'
        """,
        (session_id,),
    )

    connection.commit()

    cursor.execute(
        """
        SELECT
            id,
            operator_id,
            started_at,
            finished_at,
            status
        FROM work_sessions
        WHERE id = ?
        """,
        (session_id,),
    )

    finished_session = cursor.fetchone()
    connection.close()

    if finished_session is None:
        return None

    return dict(finished_session)
