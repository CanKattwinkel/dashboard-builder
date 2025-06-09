# Dashboard Builder

A command-line tool for generating Glassnode dashboards from JSON configurations.

## Installation

Requires Python 3.12+:

```bash
pip install -e .
```

Set your Glassnode API key via environment variable or `.env` file:
```bash
export GLASSNODE_API_KEY=your_api_key_here
```

Or create a `.env` file:
```
GLASSNODE_API_KEY=your_api_key_here
```

## Usage

### Build a dashboard from configuration

```bash
./dash build configs/my_dashboard.json
```

This generates a complete dashboard specification in `dashboards/my_dashboard_dashboard.json`.

Build all dashboards in a directory:
```bash
./dash build configs/examples/
```

Directory structure is preserved: `configs/examples/sub/` → `dashboards/examples/sub/`

### Create dashboard on Glassnode

```bash
./dash create dashboards/my_dashboard_dashboard.json
```

Creates the dashboard via API and saves the UUID mapping for future updates. If a dashboard already exists for the corresponding config file, it will update the existing dashboard instead of creating a duplicate.

Create all dashboards in a directory:
```bash
./dash create dashboards/examples/
```

### Update existing dashboard

Using config path (recommended):
```bash
./dash update configs/my_dashboard.json
```

Using UUID directly:
```bash
./dash update 123e4567-e89b-12d3-a456-426614174000 dashboards/my_dashboard_dashboard.json
```

Update all dashboards in a directory:
```bash
./dash update configs/examples/
./dash update dashboards/examples/
```

## Configuration Format

### Simple metric list

```json
{
  "name": "BTC Overview",
  "metrics": [
    "/market/price_usd_close",
    "/market/volume_sum",
    "/network/active_addresses_count"
  ]
}
```

### Detailed configuration

```json
{
  "name": "Multi-Asset Dashboard",
  "dashboardOverrides": {
    "zoom": "3m",
    "resolution": "1h"
  },
  "metrics": [
    {
      "code": "/market/price_usd_close",
      "asset": "BTC",
      "chartStyle": "line"
    },
    {
      "code": "/market/price_usd_close", 
      "asset": "ETH",
      "chartStyle": "column",
      "zoom": "1y"
    },
    "/derivatives/futures_open_interest_sum"
  ]
}
```

## Configuration Hierarchy

Settings are applied in priority order:
1. Metric-specific overrides (highest)
2. Dashboard overrides
3. Asset-metric combination defaults (`defaults/overrides.json`)
4. Metric pattern defaults (`defaults/metrics.json`)
5. Asset defaults (`defaults/assets.json`)
6. Model defaults (lowest)

## Metric Formats

Both formats are supported:
- `/market/price_usd_close` (preferred)
- `market.PriceUsdClose` (caution: will not use default files)

## Default Files

- `defaults/assets.json` - Per-asset
- `defaults/metrics.json` - Per-metric
- `defaults/overrides.json` - Specific Asset-metric overrides

### Pattern matching in metrics.json

```json
{
  "/derivatives/futures_*": {
    "chartStyle": "column",
    "resolution": "1h"
  }
}
```

## UUID Mapping

Dashboard UUIDs are stored in `.dashboard_mappings.json`:

```json
{
  "configs/my_dashboard.json": "123e4567-e89b-12d3-a456-426614174000"
}
```

This enables updating dashboards using just the config path.

## Python API

```python
from dashboard_builder import build_dashboard
from dashboard_client import create_dashboard, update_dashboard

# Build dashboard
dashboard = build_dashboard("My Dashboard", ["/market/price_usd_close"])

# Create on Glassnode
uuid = create_dashboard(dashboard.model_dump())

# Update existing
update_dashboard(uuid, dashboard.model_dump())
```