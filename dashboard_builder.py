import uuid
import re
from typing import Dict, Any, List, Tuple, Optional, Union
import json
from pathlib import Path
import fnmatch
from functools import lru_cache
from models import (
    Dashboard,
    MetricConfig,
    MetricMeta,
    MetricExtra,
    LayoutItem,
    DashboardMeta,
)


@lru_cache(maxsize=1)
def _load_defaults() -> Tuple[Dict, Dict, Dict]:
    """Load default configurations from JSON files. Cached for performance."""
    defaults_dir = Path(__file__).parent / "defaults"

    # Load asset defaults
    with open(defaults_dir / "assets.json") as f:
        asset_defaults = json.load(f)

    # Load metric defaults
    with open(defaults_dir / "metrics.json") as f:
        metric_defaults = json.load(f)

    # Load overrides
    with open(defaults_dir / "overrides.json") as f:
        overrides = json.load(f)

    return asset_defaults, metric_defaults, overrides


def _get_defaults_for_metric(metric_code: str, asset: str) -> Dict[str, Any]:
    """
    Get all applicable defaults for a metric-asset combination.
    Returns merged defaults following the priority order.
    """
    asset_defaults, metric_defaults, overrides = _load_defaults()

    # Start with empty defaults
    defaults = {}

    # 1. Apply asset defaults
    if asset in asset_defaults:
        defaults.update(asset_defaults[asset])

    # 2. Apply metric defaults (exact match or pattern)
    for pattern, values in metric_defaults.items():
        if pattern == metric_code or fnmatch.fnmatch(metric_code, pattern):
            defaults.update(values)

    # 3. Apply asset-metric overrides
    if asset in overrides:
        for pattern, values in overrides[asset].items():
            if pattern == metric_code or fnmatch.fnmatch(metric_code, pattern):
                defaults.update(values)

    return defaults





def _generate_metric_name(metric_code: str) -> str:
    """Generates a display name from the metric code (e.g., 'market.MarketCapUsd' -> 'Market Cap Usd')."""
    parts = metric_code.split(".")
    name_part = parts[1]
    # Insert space before uppercase letters (handles CamelCase like MarketCapUsd -> Market Cap Usd)
    # Does not insert space if sequence of capitals like MVRV -> MVRV
    name_with_spaces = re.sub(r"(?<!^)(?<![A-Z])(?=[A-Z])", " ", name_part)
    # Capitalize the first letter just in case (e.g. if input was market.marketCap -> Market Cap)
    return name_with_spaces.title()


def _find_next_layout_position(
    layouts: List[Dict[str, Any]],
    item_height: int = 6,
    item_width: int = 6,
    columns: int = 2,
) -> Tuple[int, int]:
    """Finds the next available (x, y) position in a grid layout."""
    occupied = set()
    max_y = -item_height  # Start checking from y=0

    for item in layouts:
        occupied.add((item["x"], item["y"]))
        max_y = max(max_y, item["y"])

    target_y = 0
    while True:
        for col_index in range(columns):
            target_x = col_index * item_width
            if (target_x, target_y) not in occupied:
                return target_x, target_y
        target_y += item_height


def build_metric_config(
    metric_code: str,
    asset: str,
    name: Optional[str] = None,
    uuid_str: Optional[str] = None,
    # Meta overrides
    date: Optional[int] = None,
    since: Optional[int] = None,
    until: Optional[int] = None,
    currency: Optional[str] = None,
    chartType: Optional[str] = None,
    resolution: Optional[str] = None,
    exchange: Optional[str] = None,
    period: Optional[str] = None,
    # Extra overrides
    zoom: Optional[str] = None,
    scale: Optional[str] = None,
    lineColor: Optional[str] = None,
    price: Optional[bool] = None,
    chartStyle: Optional[str] = None,
    logTickInterval: Optional[int] = None,
) -> MetricConfig:
    """
    Creates a single metric configuration with sensible defaults.

    Args:
        metric_code: The metric code in dot notation (e.g., "market.MvrvZScore", "indicators.FearGreed")
        asset: The asset code (e.g., "BTC", "ETH")
        name: Display name for the metric (auto-generated if not provided)
        uuid_str: UUID for the metric (auto-generated if not provided)
        **kwargs: Any overrides for meta or extra fields

    Returns:
        MetricConfig object
    """
    # Get all applicable defaults for this metric-asset combination
    defaults = _get_defaults_for_metric(metric_code, asset.upper())

    # Generate UUID and name if not provided
    if uuid_str is None:
        uuid_str = str(uuid.uuid4())

    if name is None:
        name = _generate_metric_name(metric_code)

    # Define which fields belong to meta vs extra
    meta_fields = {
        "date",
        "since",
        "until",
        "currency",
        "chartType",
        "resolution",
        "exchange",
        "period",
        "movingMedian",
        "movingAverage",
        "expMovingAverage",
    }
    extra_fields = {"zoom", "scale", "lineColor", "price", "chartStyle", "logTickInterval"}

    # Build meta kwargs
    meta_kwargs = {
        "metricCode": metric_code,
        "asset": asset.upper(),
    }

    # Apply defaults for meta fields
    for field, value in defaults.items():
        if field in meta_fields:
            meta_kwargs[field] = value

    # Apply explicit overrides for all meta fields
    if date is not None:
        meta_kwargs["date"] = date
    if since is not None:
        meta_kwargs["since"] = since
    if until is not None:
        meta_kwargs["until"] = until
    if currency is not None:
        meta_kwargs["currency"] = currency
    if chartType is not None:
        meta_kwargs["chartType"] = chartType
    if resolution is not None:
        meta_kwargs["resolution"] = resolution
    if exchange is not None:
        meta_kwargs["exchange"] = exchange
    if period is not None:
        meta_kwargs["period"] = period

    meta = MetricMeta(**meta_kwargs)

    # Build extra kwargs
    extra_kwargs = {"name": name}

    # Apply defaults for extra fields
    for field, value in defaults.items():
        if field in extra_fields:
            extra_kwargs[field] = value

    # Apply explicit overrides for all extra fields
    if zoom is not None:
        extra_kwargs["zoom"] = zoom
    if scale is not None:
        extra_kwargs["scale"] = scale
    if lineColor is not None:
        extra_kwargs["lineColor"] = lineColor
    if price is not None:
        extra_kwargs["price"] = price
    if chartStyle is not None:
        extra_kwargs["chartStyle"] = chartStyle
    if logTickInterval is not None:
        extra_kwargs["logTickInterval"] = logTickInterval

    extra = MetricExtra(**extra_kwargs)

    return MetricConfig(uuid=uuid_str, meta=meta, extra=extra, configType="metric")


def generate_layout(metric_configs: List[MetricConfig]) -> List[LayoutItem]:
    """
    Generates layout items for a list of metric configurations.

    Args:
        metric_configs: List of MetricConfig objects

    Returns:
        List of LayoutItem objects
    """
    layouts = []

    for i, config in enumerate(metric_configs):
        if i == 0:
            x, y = 0, 0
        else:
            # Convert LayoutItem objects to dicts for the existing function
            layout_dicts = [{"x": layout.x, "y": layout.y, "h": layout.h, "w": layout.w} for layout in layouts]
            x, y = _find_next_layout_position(layout_dicts)

        layout = LayoutItem(
            i=config.uuid,
            x=x,
            y=y,
            h=6,  # Use defaults from LayoutItem model
            w=6,
            minH=1,
            minW=3,
            moved=False,
            static=False,
        )
        layouts.append(layout)

    return layouts


def build_dashboard(
    name: str,
    metrics: List[Union[str, Dict[str, Any]]],
    asset: Optional[str] = None,
    dashboard_overrides: Optional[Dict[str, Any]] = None,
) -> Dashboard:
    """
    Creates a dashboard from a list of metrics specifications.

    Args:
        name: Dashboard name
        metrics: List of metric paths (strings) or metric specifications (dicts)
        asset: Global asset to use if not specified per metric
        dashboard_overrides: Dashboard-specific overrides to apply to all metrics

    Returns:
        Dashboard object

    Examples:
        # Simple single asset with metric codes
        dashboard = build_dashboard(
            name="BTC Metrics",
            asset="BTC",
            metrics=["market.MvrvZScore", "indicators.FearGreed"]
        )

        # Multi-asset with overrides
        dashboard = create_dashboard(
            name="Multi Asset",
            metrics=[
                {"code": "market.MvrvZScore", "asset": "BTC"},
                {"code": "market.MvrvZScore", "asset": "ETH", "zoom": "1y"},
                {"code": "indicators.FearGreed", "asset": "BTC", "chartStyle": "column"}
            ]
        )

        # Common overrides for all metrics
        dashboard = create_dashboard(
            name="ETH Futures",
            asset="ETH",
            metrics=["derivatives.FuturesAnnualizedBasis3m", "derivatives.FuturesOpenInterest"],
            common_overrides={"resolution": "1h", "exchange": "binance"}
        )
    """
    if dashboard_overrides is None:
        dashboard_overrides = {}

    metric_configs = []

    for metric_spec in metrics:
        # Parse metric specification
        if isinstance(metric_spec, str):
            # Simple string format
            metric_code = metric_spec
            metric_asset = asset
            metric_overrides = {}
        elif isinstance(metric_spec, dict):
            # Dict format with overrides
            metric_code = metric_spec.get("code") or metric_spec.get("metricCode")
            if not metric_code:
                raise ValueError("Metric specification must include 'code' or 'metricCode'")

            metric_asset = metric_spec.get("asset", asset)

            # Extract overrides (everything except 'code' and 'asset')
            metric_overrides = {k: v for k, v in metric_spec.items() if k not in ["code", "metricCode", "asset"]}
        else:
            raise ValueError(f"Invalid metric specification: {metric_spec}")

        if not metric_asset:
            raise ValueError(f"No asset specified for metric: {metric_code}")

        # Merge dashboard overrides with metric-specific overrides
        all_overrides = {**dashboard_overrides, **metric_overrides}

        # Create metric config
        config = build_metric_config(metric_code=metric_code, asset=metric_asset, **all_overrides)
        metric_configs.append(config)

    # Generate layouts
    layouts = generate_layout(metric_configs)

    # Create dashboard
    return Dashboard(meta=DashboardMeta(name=name), configs=metric_configs, layouts=layouts)


def build_dashboard_from_file(file_path: Union[str, Path]) -> Dashboard:
    """
    Creates a dashboard from a JSON specification file.

    Args:
        file_path: Path to the JSON specification file

    Returns:
        Dashboard object

    File format:
        {
            "name": "My Dashboard",
            "asset": "BTC",  // optional global asset
            "dashboardOverrides": {  // optional
                "resolution": "1h"
            },
            "metrics": [
                "market.PriceUsdClose",
                "market.MvrvZScore",
                {
                    "code": "indicators.FearGreed",
                    "chartStyle": "column"
                },
                {
                    "code": "derivatives.FuturesOpenInterest",
                    "asset": "ETH",
                    "exchange": "binance"
                }
            ]
        }
    """
    file_path = Path(file_path)

    with open(file_path, "r") as f:
        spec = json.load(f)

    return build_dashboard(
        name=spec["name"],
        metrics=spec["metrics"],
        asset=spec.get("asset"),
        dashboard_overrides=spec.get("dashboardOverrides", spec.get("common_overrides")),
    )


def build_dashboards_from_directory(
    directory_path: Union[str, Path], pattern: str = "*.json"
) -> Dict[Path, Dashboard]:
    """
    Creates dashboards from all JSON specification files in a directory and its subdirectories.

    Args:
        directory_path: Path to the directory containing JSON specification files
        pattern: Glob pattern for finding JSON files (default: "*.json")

    Returns:
        Dictionary mapping file paths to Dashboard objects

    Example:
        dashboards = build_dashboards_from_directory("configs/examples")
        for file_path, dashboard in dashboards.items():
            print(f"Built {dashboard.meta.name} from {file_path}")
    """
    directory_path = Path(directory_path)

    if not directory_path.is_dir():
        raise ValueError(f"Not a directory: {directory_path}")

    dashboards = {}
    
    # Use rglob for recursive search
    json_files = list(directory_path.rglob(pattern))

    if not json_files:
        raise ValueError(f"No JSON files found recursively in {directory_path} matching pattern '{pattern}'")

    for json_file in json_files:
        try:
            dashboard = build_dashboard_from_file(json_file)
            dashboards[json_file] = dashboard
        except Exception as e:
            # Log error but continue with other files
            print(f"Error building dashboard from {json_file}: {e}")
            continue

    return dashboards
