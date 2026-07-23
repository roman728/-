from typing import Optional

from database.connection import get_connection


ACTIVE_STATUSES = (
    "loaded",
    "welding",
    "waiting_unload",
)


def _validate_station(station_number: int) -> None:
    if station_number not in (1, 2, 3):
        raise ValueError("Номер станции должен быть от 1 до 3.")


def get_active_frame_by_station(
    station_number: int,
) -> Optional[dict]:
    _validate_station(station_number)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM frames
        WHERE station_number = ?
          AND status IN (
              'loaded',
              'welding',
              'waiting_unload'
          )
        ORDER BY id DESC
        LIMIT 1
        """,
        (station_number,),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def load_frame(
    frame_number: str,
    station_number: int,
    operator_id: int,
    session_id: int,
) -> int:
    _validate_station(station_number)

    frame_number = frame_number.strip()

    if not frame_number:
        raise ValueError("Номер рамы не может быть пустым.")

    if len(frame_number) > 30:
        raise ValueError("Номер рамы слишком длинный.")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM frames
            WHERE station_number = ?
              AND status IN (
                  'loaded',
                  'welding',
                  'waiting_unload'
              )
            LIMIT 1
            """,
            (station_number,),
        )

        if cursor.fetchone() is not None:
            raise ValueError(
                f"На станции {station_number} уже находится рама."
            )

        cursor.execute(
            """
            SELECT id
            FROM frames
            WHERE frame_number = ?
              AND status IN (
                  'loaded',
                  'welding',
                  'waiting_unload'
              )
            LIMIT 1
            """,
            (frame_number,),
        )

        if cursor.fetchone() is not None:
            raise ValueError(
                f"Рама №{frame_number} уже находится на участке."
            )

        cursor.execute(
            """
            INSERT INTO frames (
                frame_number,
                station_number,
                status,
                loaded_by
            )
            VALUES (?, ?, 'loaded', ?)
            """,
            (
                frame_number,
                station_number,
                operator_id,
            ),
        )

        frame_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO frame_events (
                frame_id,
                operator_id,
                session_id,
                event_type
            )
            VALUES (?, ?, ?, 'loaded')
            """,
            (
                frame_id,
                operator_id,
                session_id,
            ),
        )

        connection.commit()
        return frame_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def _change_frame_status(
    station_number: int,
    expected_status: str,
    new_status: str,
    time_field: str,
    operator_field: str,
    event_type: str,
    operator_id: int,
    session_id: int,
) -> int:
    _validate_station(station_number)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM frames
            WHERE station_number = ?
              AND status = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                station_number,
                expected_status,
            ),
        )

        frame = cursor.fetchone()

        if frame is None:
            raise ValueError(
                "Действие недоступно для текущего состояния станции."
            )

        frame_id = frame["id"]

        cursor.execute(
            f"""
            UPDATE frames
            SET
                status = ?,
                {time_field} = CURRENT_TIMESTAMP,
                {operator_field} = ?
            WHERE id = ?
              AND status = ?
            """,
            (
                new_status,
                operator_id,
                frame_id,
                expected_status,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Не удалось изменить состояние рамы.")

        cursor.execute(
            """
            INSERT INTO frame_events (
                frame_id,
                operator_id,
                session_id,
                event_type
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                frame_id,
                operator_id,
                session_id,
                event_type,
            ),
        )

        connection.commit()
        return frame_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def start_welding(
    station_number: int,
    operator_id: int,
    session_id: int,
) -> int:
    return _change_frame_status(
        station_number=station_number,
        expected_status="loaded",
        new_status="welding",
        time_field="welding_started_at",
        operator_field="welding_started_by",
        event_type="welding_started",
        operator_id=operator_id,
        session_id=session_id,
    )


def finish_welding(
    station_number: int,
    operator_id: int,
    session_id: int,
) -> int:
    return _change_frame_status(
        station_number=station_number,
        expected_status="welding",
        new_status="waiting_unload",
        time_field="welding_finished_at",
        operator_field="welding_finished_by",
        event_type="welding_finished",
        operator_id=operator_id,
        session_id=session_id,
    )


def unload_frame(
    station_number: int,
    operator_id: int,
    session_id: int,
) -> int:
    return _change_frame_status(
        station_number=station_number,
        expected_status="waiting_unload",
        new_status="completed",
        time_field="unloaded_at",
        operator_field="unloaded_by",
        event_type="unloaded",
        operator_id=operator_id,
        session_id=session_id,
    )


def remove_incomplete_frame(
    station_number: int,
    operator_id: int,
    session_id: int,
) -> int:
    return _change_frame_status(
        station_number=station_number,
        expected_status="welding",
        new_status="manual_welding",
        time_field="removed_incomplete_at",
        operator_field="removed_incomplete_by",
        event_type="removed_incomplete",
        operator_id=operator_id,
        session_id=session_id,
    )
