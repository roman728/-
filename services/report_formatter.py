from datetime import datetime, timezone
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Asia/Almaty")


def parse_database_time(value: str | None) -> datetime | None:
    if not value:
        return None

    parsed = datetime.fromisoformat(value)

    # SQLite CURRENT_TIMESTAMP сохраняет время в UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(LOCAL_TIMEZONE)


def format_datetime(value: str | None) -> str:
    parsed = parse_database_time(value)

    if parsed is None:
        return "не отмечено"

    return parsed.strftime("%d.%m.%Y %H:%M")


def format_duration(
    start_value: str | None,
    finish_value: str | None,
) -> str:
    start = parse_database_time(start_value)
    finish = parse_database_time(finish_value)

    if start is None or finish is None:
        return "не рассчитано"

    total_seconds = max(
        0,
        int((finish - start).total_seconds()),
    )

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours} ч {minutes} мин"

    if minutes > 0:
        return f"{minutes} мин {seconds} сек"

    return f"{seconds} сек"


def build_shift_report(data: dict) -> str:
    session = data["session"]
    counts = data["event_counts"]
    completed_frames = data["completed_frames"]
    removed_frames = data["removed_frames"]
    active_frames = data["active_frames"]

    lines = [
        "📋 ОТЧЁТ ЗА СМЕНУ",
        "",
        f"👤 Оператор: {session['operator_name']}",
        f"🕒 Начало: {format_datetime(session['started_at'])}",
        f"🕒 Окончание: {format_datetime(session['finished_at'])}",
        "⏱ Продолжительность: "
        f"{format_duration(session['started_at'], session['finished_at'])}",
        "",
        f"📦 Загружено рам: {counts.get('loaded', 0)}",
        f"▶️ Начато сварок: {counts.get('welding_started', 0)}",
        f"⏹ Закончено сварок: {counts.get('welding_finished', 0)}",
        f"✅ Выгружено готовых рам: {len(completed_frames)}",
        f"⚠️ Снято незавершённых: {len(removed_frames)}",
        f"🔄 Переходящих рам: {len(active_frames)}",
    ]

    if completed_frames:
        lines.extend([
            "",
            "✅ ЗАВЕРШЁННЫЕ РАМЫ",
        ])

        for frame in completed_frames:
            lines.extend([
                "",
                f"Рама №{frame['frame_number']}",
                f"🏭 Станция {frame['station_number']}",
                f"📦 Загрузка: {format_datetime(frame['loaded_at'])}",
                "▶️ Начало сварки: "
                f"{format_datetime(frame['welding_started_at'])}",
                "⏹ Окончание сварки: "
                f"{format_datetime(frame['welding_finished_at'])}",
                f"📤 Выгрузка: {format_datetime(frame['unloaded_at'])}",
                "",
                "⏱ Загрузка → сварка: "
                f"{format_duration(frame['loaded_at'], frame['welding_started_at'])}",
                "🔥 Время сварки: "
                f"{format_duration(frame['welding_started_at'], frame['welding_finished_at'])}",
                "⏱ Ожидание выгрузки: "
                f"{format_duration(frame['welding_finished_at'], frame['unloaded_at'])}",
                "⏱ Полный цикл: "
                f"{format_duration(frame['loaded_at'], frame['unloaded_at'])}",
            ])

    if removed_frames:
        lines.extend([
            "",
            "⚠️ СНЯТЫЕ НЕЗАВЕРШЁННЫЕ РАМЫ",
        ])

        for frame in removed_frames:
            lines.extend([
                "",
                f"Рама №{frame['frame_number']}",
                f"🏭 Станция {frame['station_number']}",
                "▶️ Начало сварки: "
                f"{format_datetime(frame['welding_started_at'])}",
                "⚠️ Снята со станции: "
                f"{format_datetime(frame['removed_incomplete_at'])}",
                "⏱ Работа на станции: "
                f"{format_duration(frame['loaded_at'], frame['removed_incomplete_at'])}",
                "Статус: передана на ручную доварку",
            ])

    if active_frames:
        status_names = {
            "loaded": "📦 загружена",
            "welding": "🔥 идёт сварка",
            "waiting_unload": "⏳ ожидает выгрузку",
        }

        lines.extend([
            "",
            "🔄 ПЕРЕХОДЯЩИЕ РАМЫ",
        ])

        for frame in active_frames:
            lines.extend([
                "",
                f"🏭 Станция {frame['station_number']}",
                f"Рама №{frame['frame_number']}",
                f"Статус: {status_names.get(frame['status'], frame['status'])}",
            ])

    return "\n".join(lines)

def format_elapsed(start_value: str | None) -> str:
    start = parse_database_time(start_value)

    if start is None:
        return "не рассчитано"

    current_time = datetime.now(LOCAL_TIMEZONE)

    total_seconds = max(
        0,
        int((current_time - start).total_seconds()),
    )

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours} ч {minutes} мин"

    if minutes > 0:
        return f"{minutes} мин {seconds} сек"

    return f"{seconds} сек"


def build_frame_report(frame: dict) -> str:
    status_names = {
        "loaded": "📦 загружена",
        "welding": "🔥 идёт сварка",
        "waiting_unload": "⏳ ожидает выгрузку",
        "completed": "✅ готова",
        "manual_welding": "⚠️ передана на ручную доварку",
    }

    lines = [
        f"📋 ОТЧЁТ ПО РАМЕ №{frame['frame_number']}",
        "",
        f"🏭 Станция: {frame['station_number']}",
        f"📌 Статус: {status_names.get(frame['status'], frame['status'])}",
        "",
        f"📦 Загрузка: {format_datetime(frame['loaded_at'])}",
        f"👤 Оператор: {frame['loaded_by_name'] or 'не указан'}",
    ]

    if frame["welding_started_at"]:
        lines.extend([
            "",
            "▶️ Начало сварки: "
            f"{format_datetime(frame['welding_started_at'])}",
            "👤 Оператор: "
            f"{frame['welding_started_by_name'] or 'не указан'}",
        ])

    if frame["welding_finished_at"]:
        lines.extend([
            "",
            "⏹ Окончание сварки: "
            f"{format_datetime(frame['welding_finished_at'])}",
            "👤 Оператор: "
            f"{frame['welding_finished_by_name'] or 'не указан'}",
        ])

    if frame["unloaded_at"]:
        lines.extend([
            "",
            f"📤 Выгрузка: {format_datetime(frame['unloaded_at'])}",
            f"👤 Оператор: {frame['unloaded_by_name'] or 'не указан'}",
        ])

    if frame["removed_incomplete_at"]:
        lines.extend([
            "",
            "⚠️ Снята незавершённой: "
            f"{format_datetime(frame['removed_incomplete_at'])}",
            "👤 Оператор: "
            f"{frame['removed_incomplete_by_name'] or 'не указан'}",
        ])

    lines.extend([
        "",
        "⏱ ВРЕМЯ ПО ЭТАПАМ",
    ])

    if frame["welding_started_at"]:
        lines.append(
            "Загрузка → начало сварки: "
            f"{format_duration(frame['loaded_at'], frame['welding_started_at'])}"
        )

    if frame["welding_finished_at"]:
        lines.append(
            "Время сварки: "
            f"{format_duration(frame['welding_started_at'], frame['welding_finished_at'])}"
        )
    elif frame["welding_started_at"]:
        lines.append(
            "Сварка продолжается: "
            f"{format_elapsed(frame['welding_started_at'])}"
        )

    if frame["unloaded_at"]:
        lines.append(
            "Ожидание выгрузки: "
            f"{format_duration(frame['welding_finished_at'], frame['unloaded_at'])}"
        )
    elif (
        frame["status"] == "waiting_unload"
        and frame["welding_finished_at"]
    ):
        lines.append(
            "Ожидание выгрузки продолжается: "
            f"{format_elapsed(frame['welding_finished_at'])}"
        )

    if frame["unloaded_at"]:
        lines.append(
            "Полный цикл: "
            f"{format_duration(frame['loaded_at'], frame['unloaded_at'])}"
        )
    elif frame["removed_incomplete_at"]:
        lines.append(
            "Время на роботизированной станции: "
            f"{format_duration(frame['loaded_at'], frame['removed_incomplete_at'])}"
        )
    else:
        lines.append(
            "На участке с момента загрузки: "
            f"{format_elapsed(frame['loaded_at'])}"
        )

    return "\n".join(lines)
