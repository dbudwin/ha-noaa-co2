# NOAA Atmospheric CO2 — Home Assistant Integration

A Home Assistant custom integration that pulls real atmospheric CO2 data directly from [NOAA's Global Monitoring Laboratory](https://gml.noaa.gov/ccgg/trends/) (Mauna Loa Observatory, Hawaii) — the longest-running CO2 record on Earth.

## Features

- **No API key required** — data is fetched directly from NOAA's public data files
- **UI setup** — configure entirely through Settings → Integrations, no YAML needed
- **Weekly or monthly data** — choose weekly (more current) or monthly (official averaged record)
- **Rich attributes** — measurement date, year-ago comparison, and ppm increase exposed as sensor attributes
- **Proper HA sensor** — uses `SensorDeviceClass.CO2`, works with history graphs, statistics, and automations

## Installation via HACS

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Add this repository URL, category: **Integration**
3. Click **Download**
4. Restart Home Assistant

## Manual Installation

1. Copy the `custom_components/noaa_co2/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup

After installation and restart:

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **NOAA Atmospheric CO2**
3. Choose **Weekly** or **Monthly** data frequency
4. Click **Submit**

The sensor `sensor.atmospheric_co2` will appear, updating once per day.

## Sensor Attributes

| Attribute | Description |
|---|---|
| `year` / `month` / `day` | Date of the measurement |
| `source` | Which NOAA data file was used |
| `ppm_1yr_ago` | CO2 level exactly one year prior (weekly only) |
| `ppm_increase_vs_1yr_ago` | Year-over-year increase in ppm (weekly only) |
| `ppm_deseasonalized` | Seasonally adjusted value (monthly only) |

## Data Source

Data is sourced from:
- **Weekly:** `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_weekly_mlo.txt`
- **Monthly:** `https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt`

> Xin Lan, NOAA/GML (gml.noaa.gov/ccgg/trends/) and Ralph Keeling, Scripps Institution of Oceanography.
