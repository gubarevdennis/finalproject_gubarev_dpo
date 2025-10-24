import argparse
import sys
from prettytable import PrettyTable
from decimal import Decimal

from ..core import usecases
from ..core.models import ValidationError
from ..core.usecases import UserNotFoundError, InvalidCredentialsError, InsufficientFundsError, CurrencyNotFoundError, ApiRequestError

class CLIInterface:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="ValutaTrade Hub CLI")
        self.subparsers = self.parser.add_subparsers(dest="command", required=True)
        self.user_id = None  # Состояние сессии
        self.username = None # Состояние имени пользователя

        self._setup_parsers()

    def _setup_parsers(self):
        # Парсеры для каждой команды
        register_parser = self.subparsers.add_parser("register", help="Создать нового пользователя")
        register_parser.add_argument("--username", required=True, help="Имя пользователя")
        register_parser.add_argument("--password", required=True, help="Пароль")
        register_parser.set_defaults(func=self.handle_register)

        login_parser = self.subparsers.add_parser("login", help="Войти в систему")
        login_parser.add_argument("--username", required=True, help="Имя пользователя")
        login_parser.add_argument("--password", required=True, help="Пароль")
        login_parser.set_defaults(func=self.handle_login)

        show_portfolio_parser = self.subparsers.add_parser("show-portfolio", help="Показать портфель пользователя")
        show_portfolio_parser.add_argument("--base", default="USD", help="Базовая валюта для расчета общей стоимости (по умолчанию USD)")
        show_portfolio_parser.set_defaults(func=self.handle_show_portfolio)

        buy_parser = self.subparsers.add_parser("buy", help="Купить валюту")
        buy_parser.add_argument("--currency", required=True, help="Валюта для покупки (например, BTC)")
        buy_parser.add_argument("--amount", required=True, type=float, help="Количество для покупки")
        buy_parser.set_defaults(func=self.handle_buy)

        sell_parser = self.subparsers.add_parser("sell", help="Продать валюту")
        sell_parser.add_argument("--currency", required=True, help="Валюта для продажи (например, BTC)")
        sell_parser.add_argument("--amount", required=True, type=float, help="Количество для продажи")
        sell_parser.set_defaults(func=self.handle_sell)

        get_rate_parser = self.subparsers.add_parser("get-rate", help="Получить курс валюты")
        get_rate_parser.add_argument("--from", required=True, dest="from_currency", help="Исходная валюта")
        get_rate_parser.add_argument("--to", required=True, dest="to_currency", help="Целевая валюта")
        get_rate_parser.set_defaults(func=self.handle_get_rate)

    def handle_register(self, args):
        try:
            user_id = usecases.register_user(args.username, args.password)
            print(f"Пользователь '{args.username}' зарегистрирован (id={user_id}). Войдите: login --username {args.username} --password ****")
        except (ValidationError, UserNotFoundError) as e:
            print(f"Ошибка: {e}")

    def handle_login(self, args):
        try:
            user_id = usecases.login_user(args.username, args.password)
            self.user_id = user_id  # Фиксация сессии
            self.username = args.username
            print(f"Вы вошли как '{args.username}'")
        except (UserNotFoundError, InvalidCredentialsError) as e:
            if isinstance(e, UserNotFoundError):
                 print("Ошибка: Пользователь 'alice' не найден")
            else:
                 print("Ошибка: Неверный пароль")
            self.user_id = None
            self.username = None
        except ValidationError as e:
            print(f"Ошибка: {e}")
            self.user_id = None
            self.username = None

    def handle_show_portfolio(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            portfolio_data, total_value = usecases.show_portfolio(self.user_id, args.base.upper())
            
            table = PrettyTable()
            table.field_names = ["Валюта", "Баланс", f"Стоимость ({args.base.upper()})"]
            table.align["Валюта"] = "l"
            table.align["Баланс"] = "r"
            table.align[f"Стоимость ({args.base.upper()})"] = "r"
            
            if not portfolio_data:
                 table.add_row(["", "", ""])
            else:
                 for currency, data in portfolio_data.items():
                     table.add_row([currency, f"{data['balance']:.4f}", f"{data['value_in_base']:.2f}"])

            print(f"Портфель пользователя '{self.username}' (база: {args.base.upper()}):")
            print(table)
            print("-" * 40)
            print(f"ИТОГО: {total_value:.2f} {args.base.upper()}")

        except (ValidationError, UserNotFoundError) as e:
            print(f"Ошибка: {e}")

    def handle_buy(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            amount = Decimal(str(args.amount))
            result = usecases.buy_currency(self.user_id, args.currency.upper(), amount)
            print(result)
        except (ValidationError, InsufficientFundsError, ApiRequestError) as e:
             if isinstance(e, ApiRequestError):
                print(f"Ошибка: Не удалось получить курс для {args.currency.upper()}→USD")
             elif isinstance(e, InsufficientFundsError):
                 print("Ошибка: Недостаточно USD для совершения покупки.")
             else:
                print(f"Ошибка: {e}")
        except ValueError:
            print("Ошибка: 'amount' должен быть положительным числом")

    def handle_sell(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            amount = Decimal(str(args.amount))
            result = usecases.sell_currency(self.user_id, args.currency.upper(), amount)
            print(result)
        except (ValidationError, CurrencyNotFoundError, InsufficientFundsError, ApiRequestError) as e:
            if isinstance(e, CurrencyNotFoundError):
                print(f"У вас нет кошелька '{args.currency.upper()}'. Добавьте валюту: она создаётся автоматически при первой покупке.")
            elif isinstance(e, InsufficientFundsError):
                print(f"Недостаточно средств: доступно {e.available:.4f} {e.currency}, требуется {e.required:.4f} {e.currency}")
            elif isinstance(e, ApiRequestError):
                print(f"Ошибка: Не удалось получить курс для {args.currency.upper()}→USD")
            else:
                print(f"Ошибка: {e}")
        except ValueError:
            print("Ошибка: 'amount' должен быть положительным числом")

    def handle_get_rate(self, args):
        try:
            result = usecases.get_rate(args.from_currency.upper(), args.to_currency.upper())
            print(result)
        except (ValidationError, ApiRequestError) as e:
            print(f"Курс {args.from_currency.upper()}→{args.to_currency.upper()} недоступен. Повторите попытку позже.")

    def run(self):
        if len(sys.argv) == 1:
            print("--- ValutaTrade Hub CLI (Интерактивный режим) ---")
            print("Введите команды или 'exit' для выхода.")
            while True:
                try:
                    user_input = input(f"VTH ({'Logged' if self.user_id else 'Guest'})> ")
                    if not user_input.strip():
                        continue

                    if user_input.lower() == 'exit':
                        print("Завершение работы.")
                        break

                    args_list = user_input.split()
                    if not args_list:
                        continue

                    command = args_list[0]
                    args_list = args_list[1:]

                    if command == "register":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--username", required=True)
                        parser.add_argument("--password", required=True)
                        args = parser.parse_args(args_list)
                        self.handle_register(args)
                    elif command == "login":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--username", required=True)
                        parser.add_argument("--password", required=True)
                        args = parser.parse_args(args_list)
                        self.handle_login(args)
                    elif command == "show-portfolio":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--base", default="USD")
                        args = parser.parse_args(args_list)
                        self.handle_show_portfolio(args)
                    elif command == "buy":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--currency", required=True)
                        parser.add_argument("--amount", required=True, type=float)
                        args = parser.parse_args(args_list)
                        self.handle_buy(args)
                    elif command == "sell":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--currency", required=True)
                        parser.add_argument("--amount", required=True, type=float)
                        args = parser.parse_args(args_list)
                        self.handle_sell(args)
                    elif command == "get-rate":
                        parser = argparse.ArgumentParser()
                        parser.add_argument("--from", required=True, dest="from_currency")
                        parser.add_argument("--to", required=True, dest="to_currency")
                        args = parser.parse_args(args_list)
                        self.handle_get_rate(args)
                    else:
                        print("Ошибка: Неизвестная команда")

                except SystemExit:
                    pass
                except Exception as e:
                    print(f"Непредвиденная ошибка: {e}")

def main():
    cli = CLIInterface()
    cli.run()