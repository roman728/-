from database.connection import get_connection


def get_shift_report_data(session_id: int) -> dict:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            ws.id,
            ws.started_at,
            ws.finished_at,
            ws.status,
            u.full_name AS operator_name
        FROM work_sessions AS ws
        JOIN users AS u ON u.id = ws.operator_id
        WHERE ws.id = ?
        """,
        (session_id,),
    )

    session = cursor.fetchone()

    if session is None:
        connection.close()
        raise ValueError("Рабочая смена не найдена.")

    cursor.execute(
        """
        SELECT
            event_type,
            COUNT(*) AS event_count
        FROM frame_events
        WHERE session_id = ?
        GROUP BY event_type
        """,
        (session_id,),
    )

    event_counts = {
        row["event_type"]: row["event_count"]
        for row in cursor.fetchall()
    }

    # Рамы, выгруженные во время этой смены.
    cursor.execute(
        """
        SELECT DISTINCT
            f.id,
            f.frame_number,
            f.station_number,
            f.status,
            f.loaded_at,
            f.welding_started_at,
            f.welding_finished_at,
            f.unloaded_at
        FROM frames AS f
        JOIN frame_events AS e
            ON e.frame_id = f.id
        WHERE e.session_id = ?
          AND e.event_type = 'unloaded'
        ORDER BY f.unloaded_at
        """,
        (session_id,),
    )

    completed_frames = [
        dict(row)
        for row in cursor.fetchall()
    ]

    # Рамы, снятые незавершёнными во время этой смены.
    cursor.execute(
        """
        SELECT DISTINCT
            f.id,
            f.frame_number,
            f.station_number,
            f.status,
            f.loaded_at,
            f.welding_started_at,
            f.removed_incomplete_at
        FROM frames AS f
        JOIN frame_events AS e
            ON e.frame_id = f.id
        WHERE e.session_id = ?
          AND e.event_type = 'removed_incomplete'
        ORDER BY f.removed_incomplete_at
        """,
        (session_id,),
    )

    removed_frames = [
        dict(row)
        for row in cursor.fetchall()
    ]

    # Все рамы, которые остаются на станциях после передачи смены.
    cursor.execute(
        """
        SELECT
            id,
            frame_number,
            station_number,
            status,
            loaded_at,
            welding_started_at,
            welding_finished_at
        FROM frames
        WHERE status IN (
            'loaded',
            'welding',
            'waiting_unload'
        )
        ORDER BY station_number
        """
    )

    active_frames = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return {
        "session": dict(session),
        "event_counts": event_counts,
        "completed_frames": completed_frames,
        "removed_frames": removed_frames,
        "active_frames": active_frames,
    }

def get_frame_report_data(
    frame_number: str,
) -> dict | None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            f.id,
            f.frame_number,
            f.station_number,
            f.status,

            f.loaded_at,
            f.welding_started_at,
            f.welding_finished_at,
            f.unloaded_at,
            f.removed_incomplete_at,

            loaded_user.full_name AS loaded_by_name,
            start_user.full_name AS welding_started_by_name,
            finish_user.full_name AS welding_finished_by_name,
            unload_user.full_name AS unloaded_by_name,
            removed_user.full_name AS removed_incomplete_by_name

        FROM frames AS f

        LEFT JOIN users AS loaded_user
            ON loaded_user.id = f.loaded_by

        LEFT JOIN users AS start_user
            ON start_user.id = f.welding_started_by

        LEFT JOIN users AS finish_user
            ON finish_user.id = f.welding_finished_by

        LEFT JOIN users AS unload_user
            ON unload_user.id = f.unloaded_by

        LEFT JOIN users AS removed_user
            ON removed_user.id = f.removed_incomplete_by

        WHERE f.frame_number = ?

        ORDER BY f.id DESC
        LIMIT 1
        """,
        (frame_number.strip(),),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)
