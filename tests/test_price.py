"""Tests for price extraction helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.energy_advisor.price import PriceExtractionError, extract_price_points


def _build_raw(start: datetime, price: float) -> dict[str, str | float]:
    end = start + timedelta(minutes=15)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "value": price,
    }


async def test_extract_price_points(hass) -> None:
    now = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    hass.states.async_set(
        "sensor.nordpool",
        "0.10",
        {
            "currency": "SEK",
            "raw_today": [_build_raw(now, 0.10), _build_raw(now + timedelta(minutes=15), 0.20)],
        },
    )

    points = extract_price_points(hass, "sensor.nordpool")

    assert len(points) == 2
    assert float(points[0].price) == pytest.approx(0.10)
    assert points[0].currency == "SEK"


async def test_extract_price_points_without_raw(hass) -> None:
    hass.states.async_set("sensor.nordpool", "0.10", {})

    with pytest.raises(PriceExtractionError):
        extract_price_points(hass, "sensor.nordpool")
