"""Создание учётной записи для локального запуска и Config Vars."""

import argparse
import json
from getpass import getpass
from secrets import token_hex

from werkzeug.security import generate_password_hash

from . import INSTANCE_DIR


def main() -> None:
    """Запросить данные через терминал, не показывая пароль."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--heroku", action="store_true",
        help="вывести значения для Heroku Config Vars вместо записи файла",
    )
    args = parser.parse_args()
    path = INSTANCE_DIR / "config.json"
    if not args.heroku and path.exists():
        parser.exit(1, f"Настройки уже существуют: {path}\n")

    username = input("Имя пользователя: ").strip()
    if not 1 <= len(username) <= 64:
        parser.error("Имя должно содержать от 1 до 64 символов.")
    password = getpass("Пароль (12–128 символов): ")
    if not 12 <= len(password) <= 128:
        parser.error("Пароль должен содержать от 12 до 128 символов.")
    if password != getpass("Повторите пароль: "):
        parser.error("Пароли не совпадают.")

    values = {
        "LAB6_USERNAME": username,
        "LAB6_PASSWORD_HASH": generate_password_hash(password),
        "LAB6_SECRET_KEY": token_hex(32),
    }
    if args.heroku:
        for key, value in values.items():
            print(f"{key}={value}")
        return

    path.parent.mkdir(exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(values, stream, ensure_ascii=False, indent=2)
    except FileExistsError:
        parser.exit(1, f"Настройки уже существуют: {path}\n")
    print(f"Локальные настройки записаны: {path}")


if __name__ == "__main__":
    main()
