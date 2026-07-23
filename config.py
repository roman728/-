import os

from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_TELEGRAM_ID = int(
    os.getenv("ADMIN_TELEGRAM_ID", "0")
)

ENGINEER_TELEGRAM_ID = int(
    os.getenv("ENGINEER_TELEGRAM_ID", "0")
)

OPERATOR_EGOR_ID = int(
    os.getenv("OPERATOR_EGOR_ID", "0")
)

OPERATOR_YAROSLAV_ID = int(
    os.getenv("OPERATOR_YAROSLAV_ID", "0")
)

OPERATOR_IGOR_ID = int(
    os.getenv("OPERATOR_IGOR_ID", "0")
)
