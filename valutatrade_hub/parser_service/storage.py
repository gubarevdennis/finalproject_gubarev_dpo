# valutatrade_hub/parser_service/storage.py
from datetime import datetime
from decimal import Decimal
from typing import Dict

from ..infra.database import database_manager  # Используем Singleton DB Manager


class RateStorage:
    def save_current_rates(self, rates_map: Dict[str, Decimal], source: str):
        # print(rates_map)
        """
        Обновляет rates.json (снимок) и добавляет запись в exchange_rates.json (история)
        """
        now_iso = datetime.utcnow().isoformat()

        # 1. Обновление rates.json (Снимок)
        current_rates_snapshot = database_manager.get_rates()

        # Убеждаемся, что структура соответствует ТЗ
        if 'pairs' not in current_rates_snapshot:
            current_rates_snapshot['pairs'] = {}

        for pair_key, rate in rates_map.items():
            # Обновляем запись в снимке
            current_rates_snapshot['pairs'][pair_key] = {
                "rate": str(rate),
                "updated_at": now_iso,
                "source": source
            }

        current_rates_snapshot["last_refresh"] = now_iso
        database_manager.save_rates(current_rates_snapshot)

        # 2. Обновление exchange_rates.json (История)
        history = database_manager.get_exchange_rates_history()
        if "history" not in history:
            history["history"] = {}

        for pair_key, rate in rates_map.items():
            from_currency, to_currency = pair_key.split('_')
            # Формирование ID: <FROM><TO><ISO-UTC timestamp>
            record_id = f"{from_currency}{to_currency}_{now_iso}"

            history["history"][record_id] = {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": str(rate),
                "timestamp": now_iso,
                "source": source,
                "meta": {}
            }

        database_manager.save_exchange_rates_history(history)
        return len(rates_map)


storage = RateStorage()
