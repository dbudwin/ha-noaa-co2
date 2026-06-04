"""NOAA Atmospheric CO2 sensor."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_DATA_FREQUENCY,
    OPTION_WEEKLY,
    OPTION_MONTHLY,
    DEFAULT_FREQUENCY,
    NOAA_WEEKLY_URL,
    NOAA_MONTHLY_URL,
    SCAN_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)

MISSING_DATA_SENTINEL = -999.99


def _parse_weekly(text: str) -> dict[str, Any] | None:
    """
    Parse the NOAA weekly CO2 text file.
    Columns: year  month  day  decimal  ppm  #days  1yr_ago  10yr_ago  increase
    Returns the most recent row with valid data.
    """
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        if len(cols) < 5:
            continue
        try:
            ppm = float(cols[4])
        except ValueError:
            continue
        if ppm == MISSING_DATA_SENTINEL:
            continue
        result = {
            "ppm": round(ppm, 2),
            "year": cols[0],
            "month": cols[1],
            "day": cols[2],
            "source": "NOAA GML Weekly (Mauna Loa)",
        }
        # Include year-ago comparison if available and valid
        if len(cols) >= 7:
            try:
                yr_ago = float(cols[6])
                if yr_ago != MISSING_DATA_SENTINEL:
                    result["ppm_1yr_ago"] = round(yr_ago, 2)
                    result["ppm_increase_vs_1yr_ago"] = round(ppm - yr_ago, 2)
            except ValueError:
                pass
        return result
    return None


def _parse_monthly(text: str) -> dict[str, Any] | None:
    """
    Parse the NOAA monthly CO2 text file.
    Columns: year  month  decimal_date  average  deseasonalized  #days  std_days  unc
    Returns the most recent row with valid data.
    Missing months are denoted by -99.99.
    """
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        if len(cols) < 4:
            continue
        try:
            ppm = float(cols[3])
        except ValueError:
            continue
        if ppm < 0:  # catches both -99.99 and -999.99
            continue
        result = {
            "ppm": round(ppm, 2),
            "year": cols[0],
            "month": cols[1],
            "source": "NOAA GML Monthly (Mauna Loa)",
        }
        # Deseasonalized value
        if len(cols) >= 5:
            try:
                deseas = float(cols[4])
                if deseas > 0:
                    result["ppm_deseasonalized"] = round(deseas, 2)
            except ValueError:
                pass
        return result
    return None


async def _fetch_noaa_data(frequency: str) -> dict[str, Any]:
    """Fetch and parse NOAA CO2 data."""
    url = NOAA_WEEKLY_URL if frequency == OPTION_WEEKLY else NOAA_MONTHLY_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "HomeAssistant/NOAA-CO2-Integration"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"NOAA server returned HTTP {resp.status} for {url}"
                    )
                text = await resp.text()
    except aiohttp.ClientError as err:
        raise UpdateFailed(f"Network error fetching NOAA data: {err}") from err

    if frequency == OPTION_WEEKLY:
        result = _parse_weekly(text)
    else:
        result = _parse_monthly(text)

    if result is None:
        raise UpdateFailed("Could not find valid CO2 data in NOAA response")

    return result


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NOAA CO2 sensor from a config entry."""
    frequency = config_entry.options.get(
        CONF_DATA_FREQUENCY,
        config_entry.data.get(CONF_DATA_FREQUENCY, DEFAULT_FREQUENCY),
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="NOAA CO2",
        update_method=lambda: _fetch_noaa_data(frequency),
        update_interval=timedelta(hours=SCAN_INTERVAL_HOURS),
    )

    # Fetch initial data so the sensor isn't "unavailable" on first load
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([NOAAco2Sensor(coordinator, config_entry)])


class NOAAco2Sensor(CoordinatorEntity, SensorEntity):
    """Sensor entity representing atmospheric CO2 from NOAA Mauna Loa."""

    _attr_name = "Atmospheric CO2"
    _attr_device_class = SensorDeviceClass.CO2
    _attr_native_unit_of_measurement = "ppm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:molecule-co2"
    _attr_attribution = (
        "Data provided by NOAA Global Monitoring Laboratory "
        "(gml.noaa.gov/ccgg/trends)"
    )

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_co2_mlo"
        self._config_entry = config_entry

    @property
    def native_value(self) -> float | None:
        """Return the current CO2 value in ppm."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("ppm")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes: measurement date, source, comparisons."""
        if self.coordinator.data is None:
            return {}
        # Return everything except the main ppm value
        return {k: v for k, v in self.coordinator.data.items() if k != "ppm"}
