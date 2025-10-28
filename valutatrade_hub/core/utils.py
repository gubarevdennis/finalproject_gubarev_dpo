# valutatrade_hub/core/utils.py
from datetime import datetime
from decimal import Decimal

# Заменим на импорт синглтона
from ..infra.database import database_manager
from ..infra.settings import settings_loader


class RateManager:
    def __init__(self):
        # Мок курсов (пока RateManager их только отдает, но не обновляет сам)
        self.mock_exchange_rates = {
            "USD_USD": Decimal("1.0000"),
            "EUR_USD": Decimal("1.0786"),
            "USD_EUR": Decimal("0.9271"),
            "BTC_USD": Decimal("59337.21"),
            "USD_BTC": Decimal("0.00001685"),
            "ETH_USD": Decimal("3720.00"),
            "USD_ETH": Decimal("0.0002688"),
            "BTC_EUR": Decimal("55000.00"),
            "EUR_BTC": Decimal("0.00001818")
        }
        self.rate_ttl_seconds = settings_loader.get('rates_ttl_seconds', 300)

    def get_rates(self):
        rates_data = database_manager.get_rates()

        # Если rates_data пуст или нет last_refresh, вызываем refresh_rates
        last_refresh_str = rates_data.get("last_refresh")

        if (not last_refresh_str or
            (datetime.utcnow() - datetime.fromisoformat(last_refresh_str)).total_seconds() > self.rate_ttl_seconds):
            self.refresh_rates()
            rates_data = database_manager.get_rates()

        return rates_data

    def refresh_rates(self):
        """Симуляция обновления данных, которые должны были прийти из Parser Service."""
        rates_data = {
            "source": "Mocked_Parser_Service",
            "last_refresh": datetime.utcnow().isoformat(),
            "pairs": {}
        }

        for pair, rate in self.mock_exchange_rates.items():
            from_currency, to_currency = pair.split('_')
            # Сохраняем в формате, который ожидает Core (из rates.json)
            rates_data["pairs"][pair] = {"rate": str(rate), "updated_at": rates_data["last_refresh"]}

        database_manager.save_rates(rates_data)
        return rates_data


rate_manager = RateManager()
