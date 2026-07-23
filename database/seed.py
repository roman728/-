from database.users import add_or_update_user


def seed_initial_users(
    admin_telegram_id: int,
    engineer_telegram_id: int,
    operator_egor_id: int = 0,
    operator_yaroslav_id: int = 0,
    operator_igor_id: int = 0,
) -> None:
    users = [
        (
            admin_telegram_id,
            "Роман",
            "admin",
        ),
        (
            engineer_telegram_id,
            "Игорь — инженер",
            "engineer",
        ),
        (
            operator_egor_id,
            "Егор",
            "operator",
        ),
        (
            operator_yaroslav_id,
            "Ярослав",
            "operator",
        ),
        (
            operator_igor_id,
            "Игорь — оператор",
            "operator",
        ),
    ]

    for telegram_id, full_name, role in users:
        if telegram_id <= 0:
            continue

        add_or_update_user(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
        )
