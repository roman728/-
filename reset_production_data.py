from database.connection import get_connection


def reset_production_data() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM frame_events")
        cursor.execute("DELETE FROM frames")
        cursor.execute("DELETE FROM work_sessions")

        # Обнуляем внутренние номера записей.
        cursor.execute(
            """
            DELETE FROM sqlite_sequence
            WHERE name IN (
                'frame_events',
                'frames',
                'work_sessions'
            )
            """
        )

        connection.commit()
        print("Готово: рамы, события и смены удалены.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    reset_production_data()
