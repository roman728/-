from database.connection import get_connection


def create_tables() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    # Пользователи
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Рабочие сессии операторов
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS work_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'active',

            FOREIGN KEY (operator_id) REFERENCES users(id)
        )
        """
    )

    # Рамы
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            frame_number TEXT NOT NULL,
            station_number INTEGER NOT NULL,

            status TEXT NOT NULL DEFAULT 'loaded',

            loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            welding_started_at TIMESTAMP,
            welding_finished_at TIMESTAMP,
            unloaded_at TIMESTAMP,
            removed_incomplete_at TIMESTAMP,

            loaded_by INTEGER NOT NULL,
            welding_started_by INTEGER,
            welding_finished_by INTEGER,
            unloaded_by INTEGER,
            removed_incomplete_by INTEGER,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CHECK (station_number IN (1, 2, 3)),

            CHECK (
                status IN (
                    'loaded',
                    'welding',
                    'waiting_unload',
                    'completed',
                    'manual_welding'
                )
            ),

            FOREIGN KEY (loaded_by) REFERENCES users(id),
            FOREIGN KEY (welding_started_by) REFERENCES users(id),
            FOREIGN KEY (welding_finished_by) REFERENCES users(id),
            FOREIGN KEY (unloaded_by) REFERENCES users(id),
            FOREIGN KEY (removed_incomplete_by) REFERENCES users(id)
        )
        """
    )

    # История всех действий по раме
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS frame_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            frame_id INTEGER NOT NULL,
            operator_id INTEGER NOT NULL,
            session_id INTEGER,

            event_type TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CHECK (
                event_type IN (
                    'loaded',
                    'welding_started',
                    'welding_finished',
                    'unloaded',
                    'removed_incomplete'
                )
            ),

            FOREIGN KEY (frame_id) REFERENCES frames(id),
            FOREIGN KEY (operator_id) REFERENCES users(id),
            FOREIGN KEY (session_id) REFERENCES work_sessions(id)
        )
        """
    )

    # На одной станции может находиться только одна активная рама
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_one_active_frame_per_station
        ON frames(station_number)
        WHERE status IN (
            'loaded',
            'welding',
            'waiting_unload'
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_frames_number
        ON frames(frame_number)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_frame_events_frame_id
        ON frame_events(frame_id)
        """
    )

    connection.commit()
    connection.close()
