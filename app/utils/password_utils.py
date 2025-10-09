import getpass
import sys

import bcrypt


def generate_password_hash(password: str) -> str:
    """
    Создает хеш пароля с использованием bcrypt

    :param password: Исходный пароль
    :return: Хеш пароля в виде строки
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def check_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли пароль хешу

    :param plain_password: Пароль в открытом виде
    :param hashed_password: Хеш для сравнения
    :return: True, если пароль верный, иначе False
    """
    plain_password_bytes = plain_password.encode("utf-8")
    hashed_password_bytes = hashed_password.encode("utf-8")

    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)


def interactive_password_hash() -> None:
    """
    Запускает интерактивный режим для создания хеша пароля
    """
    try:
        password = getpass.getpass("Введите пароль для хеширования: ")
        if not password:
            print("Пароль не может быть пустым")
            sys.exit(1)

        password_confirm = getpass.getpass("Повторите пароль: ")
        if password != password_confirm:
            print("Пароли не совпадают")
            sys.exit(1)

        hashed = generate_password_hash(password)
        print("\nХеш пароля:")
        print(hashed)
    except KeyboardInterrupt:
        print("\nОперация отменена пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    interactive_password_hash()
