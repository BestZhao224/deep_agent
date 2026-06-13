from __future__ import annotations

import httpx

from personalops_agent.config import Settings
from personalops_agent.tools.models import ExchangeRateResult


class ExchangeRateTool:
    """ExchangeRate-API-compatible currency converter."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def convert_currency(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRateResult:
        from_code = from_currency.upper()
        to_code = to_currency.upper()
        if not self.settings.exchange_rate_api_key:
            return ExchangeRateResult(
                ok=False,
                amount=amount,
                from_currency=from_code,
                to_currency=to_code,
                error=(
                    "EXCHANGE_RATE_API_KEY is required for real currency conversion; "
                    "no fake results returned."
                ),
            )

        url = (
            f"{self.settings.exchange_rate_api_base_url.rstrip('/')}/v6/"
            f"{self.settings.exchange_rate_api_key}/pair/{from_code}/{to_code}/{amount}"
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        rate = data.get("conversion_rate")
        converted = data.get("conversion_result")
        return ExchangeRateResult(
            ok=True,
            amount=amount,
            from_currency=from_code,
            to_currency=to_code,
            converted_amount=converted,
            rate=rate,
        )
