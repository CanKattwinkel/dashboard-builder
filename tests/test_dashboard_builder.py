"""Tests for dashboard_builder.py - focusing on core dashboard building functionality"""

import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard_builder import build_dashboard, build_dashboard_from_file, build_metric_config, generate_layout, build_dashboards_from_directory


def test_build_metric_config():
    """Test building individual metric configurations"""
    # Expected use - basic metric
    config = build_metric_config(metric_code="/market/price_usd", asset="BTC")
    assert config.meta.asset == "BTC"
    assert config.configType == "metric"
    assert hasattr(config, "uuid")
    assert config.uuid is not None

    # Expected use - with custom values
    config = build_metric_config(
        metric_code="/market/volume",
        asset="ETH",
        name="Custom Volume",
        resolution="1h",
        chartStyle="column",
        lineColor="#ff0000",
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
        chartStyle="line",  # Override default column
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
    except Exception:
        assert False, "Empty string should be allowed"


def test_generate_layout():
    """Test dashboard layout generation"""
    # Expected use - standard 2x2 grid
    configs = []
    for i in range(4):
        config = type("Config", (), {"uuid": f"uuid-{i}"})()
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
    configs = [type("Config", (), {"uuid": "single-uuid"})()]
    layouts = generate_layout(configs)
    assert len(layouts) == 1
    assert layouts[0].x == 0 and layouts[0].y == 0
    assert layouts[0].w == 6 and layouts[0].h == 6

    # Edge case - odd number of metrics (5)
    configs = [type("Config", (), {"uuid": f"uuid-{i}"})() for i in range(5)]
    layouts = generate_layout(configs)
    assert len(layouts) == 5
    # Third row starts at y=12
    assert layouts[4].x == 0 and layouts[4].y == 12

    # Edge case - many metrics (10)
    configs = [type("Config", (), {"uuid": f"uuid-{i}"})() for i in range(10)]
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
        name="BTC Dashboard", asset="BTC", metrics=["/market/price", "/market/volume", "/market/market_cap"]
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
            {"code": "/market/price", "asset": "SOL"},
        ],
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
            {"code": "/indicators/nvt", "resolution": "4h"},  # Custom resolution
        ],
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
        dashboard_overrides={"resolution": "4h", "currency": "EUR", "chartStyle": "column"},
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
            {"code": "/market/volume", "resolution": "1h"},  # Overrides common
        ],
        dashboard_overrides={"resolution": "24h"},
    )
    assert dashboard.configs[0].meta.resolution == "24h"  # Common
    assert dashboard.configs[1].meta.resolution == "1h"  # Specific wins

    # Edge case - empty metrics list
    dashboard = build_dashboard(name="Empty", metrics=[])
    assert dashboard.meta.name == "Empty"
    assert len(dashboard.configs) == 0
    assert len(dashboard.layouts) == 0

    # Failing case - metric dict without code/metricCode
    try:
        build_dashboard(
            name="Invalid",
            metrics=[{"asset": "BTC", "resolution": "1h"}],  # No code!
        )
        assert False, "Should require code or metricCode"
    except ValueError as e:
        assert "must include 'code' or 'metricCode'" in str(e)

    # Failing case - no asset anywhere
    try:
        build_dashboard(
            name="No Asset",
            metrics=["/market/price"],  # No default asset, no asset in metric
        )
        assert False, "Should require asset"
    except ValueError as e:
        assert "No asset specified" in str(e)


def test_build_dashboard_from_file():
    """Test building dashboards from JSON files"""
    # Expected use - basic config file
    config = {"name": "Test Dashboard", "asset": "BTC", "metrics": ["/market/price", "/market/volume"]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        "dashboardOverrides": {"resolution": "1h", "currency": "EUR"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
            {"metricCode": "derivatives.FuturesVolume", "asset": "SOL"},
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
    minimal_config = {"name": "Minimal", "asset": "BTC", "metrics": []}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
        "metrics": ["/market/price"],
        # Missing 'name'!
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(invalid_config, f)
        temp_path = f.name

    try:
        build_dashboard_from_file(temp_path)
        assert False, "Should require name field"
    except (KeyError, TypeError):
        pass
    finally:
        Path(temp_path).unlink()


def test_build_dashboards_from_directory():
    """Test building multiple dashboards from a directory"""
    # Expected use - directory with multiple JSON files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test JSON files
        config1 = {"name": "Dashboard 1", "asset": "BTC", "metrics": ["/market/price"]}
        config2 = {"name": "Dashboard 2", "asset": "ETH", "metrics": ["/market/volume", "/market/cap"]}
        config3 = {"name": "Dashboard 3", "asset": "SOL", "metrics": []}
        
        (temp_path / "dash1.json").write_text(json.dumps(config1))
        (temp_path / "dash2.json").write_text(json.dumps(config2))
        (temp_path / "dash3.json").write_text(json.dumps(config3))
        
        # Also create a non-JSON file to ensure it's ignored
        (temp_path / "readme.txt").write_text("This should be ignored")
        
        dashboards = build_dashboards_from_directory(temp_path)
        
        assert len(dashboards) == 3
        
        # Check each dashboard
        paths = sorted(dashboards.keys(), key=lambda p: p.name)
        assert paths[0].name == "dash1.json"
        assert dashboards[paths[0]].meta.name == "Dashboard 1"
        assert len(dashboards[paths[0]].configs) == 1
        
        assert paths[1].name == "dash2.json"
        assert dashboards[paths[1]].meta.name == "Dashboard 2"
        assert len(dashboards[paths[1]].configs) == 2
        
        assert paths[2].name == "dash3.json"
        assert dashboards[paths[2]].meta.name == "Dashboard 3"
        assert len(dashboards[paths[2]].configs) == 0
    
    # Expected use - custom pattern
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files with different patterns
        config_prod = {"name": "Prod Dashboard", "asset": "BTC", "metrics": ["/market/price"]}
        config_test = {"name": "Test Dashboard", "asset": "ETH", "metrics": ["/market/volume"]}
        
        (temp_path / "prod_dashboard.json").write_text(json.dumps(config_prod))
        (temp_path / "test_dashboard.json").write_text(json.dumps(config_test))
        
        # Only get prod dashboards
        dashboards = build_dashboards_from_directory(temp_path, pattern="prod_*.json")
        
        assert len(dashboards) == 1
        assert list(dashboards.values())[0].meta.name == "Prod Dashboard"
    
    # Edge case - directory with one file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = {"name": "Single Dashboard", "asset": "BTC", "metrics": ["/market/price"]}
        (temp_path / "single.json").write_text(json.dumps(config))
        
        dashboards = build_dashboards_from_directory(temp_path)
        
        assert len(dashboards) == 1
        assert list(dashboards.values())[0].meta.name == "Single Dashboard"
    
    # Edge case - some files have errors but others succeed
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Valid config
        valid_config = {"name": "Valid Dashboard", "asset": "BTC", "metrics": ["/market/price"]}
        (temp_path / "valid.json").write_text(json.dumps(valid_config))
        
        # Invalid JSON
        (temp_path / "invalid.json").write_text("{'bad': json, }")
        
        # Missing required field
        missing_name = {"asset": "ETH", "metrics": []}
        (temp_path / "missing_name.json").write_text(json.dumps(missing_name))
        
        dashboards = build_dashboards_from_directory(temp_path)
        
        # Should only have the valid dashboard
        assert len(dashboards) == 1
        assert list(dashboards.values())[0].meta.name == "Valid Dashboard"
    
    # Failing case - directory doesn't exist
    try:
        build_dashboards_from_directory("/nonexistent/directory")
        assert False, "Should raise ValueError for non-existent directory"
    except ValueError as e:
        assert "Not a directory" in str(e)
    
    # Failing case - not a directory (file instead)
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        try:
            build_dashboards_from_directory(f.name)
            assert False, "Should raise ValueError for file instead of directory"
        except ValueError as e:
            assert "Not a directory" in str(e)
    
    # Failing case - empty directory (no JSON files)
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            build_dashboards_from_directory(temp_dir)
            assert False, "Should raise ValueError for empty directory"
        except ValueError as e:
            assert "No JSON files found" in str(e)
    
    # Failing case - directory with only non-matching files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "data.yaml").write_text("yaml: content")
        (temp_path / "config.toml").write_text("[config]")
        
        try:
            build_dashboards_from_directory(temp_dir)
            assert False, "Should raise ValueError when no JSON files found"
        except ValueError as e:
            assert "No JSON files found" in str(e)


if __name__ == "__main__":
    test_build_metric_config()
    test_generate_layout()
    test_build_dashboard()
    test_build_dashboard_from_file()
    test_build_dashboards_from_directory()
    print("All dashboard_builder tests passed!")
