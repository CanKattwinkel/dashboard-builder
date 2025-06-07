"""Tests for dashboard_builder.py - focusing on core dashboard building functionality"""
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard_builder import build_dashboard, build_dashboard_from_file, build_metric_config, generate_layout


def test_build_metric_config():
    """Test building individual metric configurations"""
    # Expected use - basic metric
    config = build_metric_config(
        metric_code="/market/price_usd",
        asset="BTC"
    )
    assert config.meta.asset == "BTC"
    assert config.configType == "metric"
    assert hasattr(config, 'uuid')
    assert config.uuid is not None
    
    # Expected use - with custom values
    config = build_metric_config(
        metric_code="/market/volume",
        asset="ETH",
        name="Custom Volume",
        resolution="1h",
        chartStyle="column",
        lineColor="#ff0000"
    )
    assert config.meta.asset == "ETH"
    assert config.meta.resolution == "1h"
    assert config.extra.name == "Custom Volume"
    assert config.extra.chartStyle == "column"
    assert config.extra.lineColor == "#ff0000"
    
    # Edge case - override defaults from config files
    config = build_metric_config(
        metric_code="/derivatives/futures_open_interest",
        asset="SOL",
        currency="EUR",  # Override default USD
        chartStyle="line"  # Override default column
    )
    assert config.meta.currency == "EUR"
    assert config.extra.chartStyle == "line"
    
    # Failing case - missing required asset
    try:
        build_metric_config(metric_code="/market/price", asset=None)
        assert False, "Should require asset"
    except AttributeError:
        pass  # Expected - tries to call .upper() on None
    
    # Failing case - empty asset
    try:
        build_metric_config(metric_code="/market/price", asset="")
        # Empty string is actually allowed, just becomes empty
        pass
    except:
        assert False, "Empty string should be allowed"


def test_generate_layout():
    """Test dashboard layout generation"""
    # Expected use - standard 2x2 grid
    configs = []
    for i in range(4):
        config = type('Config', (), {'uuid': f'uuid-{i}'})()
        configs.append(config)
    
    layouts = generate_layout(configs)
    assert len(layouts) == 4
    # Row 1
    assert layouts[0].i == "uuid-0"
    assert layouts[0].x == 0 and layouts[0].y == 0
    assert layouts[1].i == "uuid-1"
    assert layouts[1].x == 6 and layouts[1].y == 0
    # Row 2
    assert layouts[2].i == "uuid-2"
    assert layouts[2].x == 0 and layouts[2].y == 6
    assert layouts[3].i == "uuid-3"
    assert layouts[3].x == 6 and layouts[3].y == 6
    
    # Edge case - single metric
    configs = [type('Config', (), {'uuid': 'single-uuid'})()]
    layouts = generate_layout(configs)
    assert len(layouts) == 1
    assert layouts[0].x == 0 and layouts[0].y == 0
    assert layouts[0].w == 6 and layouts[0].h == 6
    
    # Edge case - odd number of metrics (5)
    configs = [type('Config', (), {'uuid': f'uuid-{i}'})() for i in range(5)]
    layouts = generate_layout(configs)
    assert len(layouts) == 5
    # Third row starts at y=12
    assert layouts[4].x == 0 and layouts[4].y == 12
    
    # Edge case - many metrics (10)
    configs = [type('Config', (), {'uuid': f'uuid-{i}'})() for i in range(10)]
    layouts = generate_layout(configs)
    assert len(layouts) == 10
    # Should have 5 rows
    assert layouts[8].y == 24  # 5th row
    assert layouts[9].y == 24
    
    # Edge case - empty list
    layouts = generate_layout([])
    assert layouts == []


def test_build_dashboard():
    """Test building complete dashboards"""
    # Expected use - single asset dashboard
    dashboard = build_dashboard(
        name="BTC Dashboard",
        asset="BTC",
        metrics=["/market/price", "/market/volume", "/market/market_cap"]
    )
    assert dashboard.meta.name == "BTC Dashboard"
    assert len(dashboard.configs) == 3
    assert len(dashboard.layouts) == 3
    assert all(c.meta.asset == "BTC" for c in dashboard.configs)
    
    # Expected use - multi-asset dashboard
    dashboard = build_dashboard(
        name="Multi Asset",
        metrics=[
            {"code": "/market/price", "asset": "BTC"},
            {"code": "/market/price", "asset": "ETH"},
            {"code": "/market/price", "asset": "SOL"}
        ]
    )
    assert len(dashboard.configs) == 3
    assert dashboard.configs[0].meta.asset == "BTC"
    assert dashboard.configs[1].meta.asset == "ETH"
    assert dashboard.configs[2].meta.asset == "SOL"
    
    # Edge case - mixed metric formats
    dashboard = build_dashboard(
        name="Mixed Formats",
        asset="BTC",  # Default asset
        metrics=[
            "/market/price",  # Uses default asset
            {"code": "/market/volume", "asset": "ETH"},  # Override asset
            {"metricCode": "market.MarketCap", "asset": "SOL"},  # Dotted format
            {"code": "/indicators/nvt", "resolution": "4h"}  # Custom resolution
        ]
    )
    assert len(dashboard.configs) == 4
    assert dashboard.configs[0].meta.asset == "BTC"
    assert dashboard.configs[1].meta.asset == "ETH"
    assert dashboard.configs[2].meta.asset == "SOL"
    assert dashboard.configs[3].meta.asset == "BTC"
    assert dashboard.configs[3].meta.resolution == "4h"
    
    # Edge case - common overrides apply to all metrics
    dashboard = build_dashboard(
        name="Common Overrides",
        asset="BTC",
        metrics=["/market/price", "/market/volume"],
        common_overrides={
            "resolution": "4h",
            "currency": "EUR",
            "chartStyle": "column"
        }
    )
    assert all(c.meta.resolution == "4h" for c in dashboard.configs)
    assert all(c.meta.currency == "EUR" for c in dashboard.configs)
    assert all(c.extra.chartStyle == "column" for c in dashboard.configs)
    
    # Edge case - metric-specific override beats common override
    dashboard = build_dashboard(
        name="Override Priority",
        asset="BTC",
        metrics=[
            "/market/price",
            {"code": "/market/volume", "resolution": "1h"}  # Overrides common
        ],
        common_overrides={"resolution": "24h"}
    )
    assert dashboard.configs[0].meta.resolution == "24h"  # Common
    assert dashboard.configs[1].meta.resolution == "1h"   # Specific wins
    
    # Edge case - empty metrics list
    dashboard = build_dashboard(name="Empty", metrics=[])
    assert dashboard.meta.name == "Empty"
    assert len(dashboard.configs) == 0
    assert len(dashboard.layouts) == 0
    
    # Failing case - metric dict without code/metricCode
    try:
        build_dashboard(
            name="Invalid",
            metrics=[{"asset": "BTC", "resolution": "1h"}]  # No code!
        )
        assert False, "Should require code or metricCode"
    except ValueError as e:
        assert "must include 'code' or 'metricCode'" in str(e)
    
    # Failing case - no asset anywhere
    try:
        build_dashboard(
            name="No Asset",
            metrics=["/market/price"]  # No default asset, no asset in metric
        )
        assert False, "Should require asset"
    except ValueError as e:
        assert "No asset specified" in str(e)


def test_build_dashboard_from_file():
    """Test building dashboards from JSON files"""
    # Expected use - basic config file
    config = {
        "name": "Test Dashboard",
        "asset": "BTC",
        "metrics": [
            "/market/price",
            "/market/volume"
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        dashboard = build_dashboard_from_file(temp_path)
        assert dashboard.meta.name == "Test Dashboard"
        assert len(dashboard.configs) == 2
        assert all(c.meta.asset == "BTC" for c in dashboard.configs)
    finally:
        Path(temp_path).unlink()
    
    # Expected use - with common overrides
    config_with_overrides = {
        "name": "Override Dashboard",
        "asset": "ETH",
        "metrics": ["/market/price"],
        "common_overrides": {
            "resolution": "1h",
            "currency": "EUR"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_with_overrides, f)
        temp_path = f.name
    
    try:
        dashboard = build_dashboard_from_file(temp_path)
        assert dashboard.configs[0].meta.resolution == "1h"
        assert dashboard.configs[0].meta.currency == "EUR"
    finally:
        Path(temp_path).unlink()
    
    # Edge case - complex multi-asset config
    complex_config = {
        "name": "Complex Dashboard",
        "metrics": [
            {"code": "/market/price", "asset": "BTC"},
            {"code": "/market/price", "asset": "ETH", "resolution": "1h"},
            {"metricCode": "derivatives.FuturesVolume", "asset": "SOL"}
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(complex_config, f)
        temp_path = f.name
    
    try:
        dashboard = build_dashboard_from_file(temp_path)
        assert len(dashboard.configs) == 3
        assert dashboard.configs[0].meta.asset == "BTC"
        assert dashboard.configs[1].meta.asset == "ETH"
        assert dashboard.configs[1].meta.resolution == "1h"
        assert dashboard.configs[2].meta.asset == "SOL"
    finally:
        Path(temp_path).unlink()
    
    # Edge case - minimal config
    minimal_config = {
        "name": "Minimal",
        "asset": "BTC",
        "metrics": []
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(minimal_config, f)
        temp_path = f.name
    
    try:
        dashboard = build_dashboard_from_file(temp_path)
        assert dashboard.meta.name == "Minimal"
        assert len(dashboard.configs) == 0
    finally:
        Path(temp_path).unlink()
    
    # Failing case - file not found
    try:
        build_dashboard_from_file("nonexistent.json")
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass
    
    # Failing case - invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{'invalid': json, }")
        temp_path = f.name
    
    try:
        build_dashboard_from_file(temp_path)
        assert False, "Should raise JSONDecodeError"
    except json.JSONDecodeError:
        pass
    finally:
        Path(temp_path).unlink()
    
    # Failing case - missing required fields
    invalid_config = {
        "asset": "BTC",
        "metrics": ["/market/price"]
        # Missing 'name'!
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_config, f)
        temp_path = f.name
    
    try:
        build_dashboard_from_file(temp_path)
        assert False, "Should require name field"
    except (KeyError, TypeError):
        pass
    finally:
        Path(temp_path).unlink()


if __name__ == "__main__":
    test_build_metric_config()
    test_generate_layout()
    test_build_dashboard()
    test_build_dashboard_from_file()
    print("All dashboard_builder tests passed!")