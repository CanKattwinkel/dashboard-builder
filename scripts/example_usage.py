#!/usr/bin/env python3
"""Example usage of the dashboard creation functions."""

import json
import sys

sys.path.append("..")
from dashboard_builder import create_dashboard

# Example 1: Simple single-asset dashboard with metric paths
print("Example 1: Creating a simple BTC dashboard")
btc_dashboard = create_dashboard(
    name="BTC Key Metrics",
    asset="BTC",
    metrics=[
        "/market/mvrv_z_score",
        "/indicators/net_unrealized_profit_loss",
        "/market/price_usd_close",
        "/indicators/fear_greed",
    ],
)

# Save it
with open("example_btc_dashboard.json", "w") as f:
    json.dump(btc_dashboard.model_dump(exclude_none=True), f, indent=2)
print("Saved to: example_btc_dashboard.json\n")


# Example 2: Multi-asset dashboard with customizations
print("Example 2: Creating a multi-asset dashboard with customizations")
multi_dashboard = create_dashboard(
    name="BTC vs ETH Analysis",
    metrics=[
        # Simple metrics
        {"code": "/market/price_usd_close", "asset": "BTC"},
        {"code": "/market/price_usd_close", "asset": "ETH"},
        # With custom zoom
        {"code": "/market/mvrv_z_score", "asset": "BTC", "zoom": "2y"},
        {"code": "/market/mvrv_z_score", "asset": "ETH", "zoom": "2y"},
        # With chart style
        {"code": "/market/spot_volume_daily_sum", "asset": "BTC", "chartStyle": "column"},
        {"code": "/market/spot_volume_daily_sum", "asset": "ETH", "chartStyle": "column"},
    ],
)

# Save it
with open("example_multi_dashboard.json", "w") as f:
    json.dump(multi_dashboard.model_dump(exclude_none=True), f, indent=2)
print("Saved to: example_multi_dashboard.json\n")


# Example 3: Dashboard with common overrides for all metrics
print("Example 3: Dashboard with common overrides")
futures_dashboard = create_dashboard(
    name="SOL Futures Analysis",
    asset="SOL",
    metrics=[
        "/derivatives/futures_annualized_basis_3m",
        "/derivatives/futures_open_interest",
        "/derivatives/futures_volume_daily_sum",
        "/derivatives/futures_liquidations_long_daily_sum",
    ],
    common_overrides={"resolution": "1h", "exchange": "binance", "chartStyle": "line"},
)

# Save it
with open("example_futures_dashboard.json", "w") as f:
    json.dump(futures_dashboard.model_dump(exclude_none=True), f, indent=2)
print("Saved to: example_futures_dashboard.json\n")


# Example 4: Mix of simple strings and dict specs (showing backwards compatibility)
print("Example 4: Mixed format dashboard")
mixed_dashboard = create_dashboard(
    name="Mixed Format Example",
    asset="ETH",
    metrics=[
        # Path format (preferred)
        "/market/price_usd_close",
        "/market/market_cap_usd",
        # Dict with overrides
        {"code": "/indicators/sopr", "zoom": "3m", "scale": "log"},
        # Note: Dotted format still works for backwards compatibility
        "supply.IssuedUsd",  # This will be converted internally
    ],
)

# Save it
with open("example_mixed_dashboard.json", "w") as f:
    json.dump(mixed_dashboard.model_dump(exclude_none=True), f, indent=2)
print("Saved to: example_mixed_dashboard.json\n")

print("All examples completed!")
print("\nNote: Metric paths (e.g., '/market/price_usd_close') are the preferred format.")
print("The dotted format (e.g., 'market.PriceUsdClose') is supported for backwards compatibility.")
print("\nYou can now upload these JSON files to your dashboard application.")
