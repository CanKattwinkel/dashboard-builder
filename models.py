from typing import List, Optional, Literal
from pydantic import BaseModel


class DashboardMeta(BaseModel):
    name: str


class MetricMeta(BaseModel):
    metricCode: str
    asset: str
    date: Optional[int] = 0
    since: Optional[int] = 0
    until: Optional[int] = 0
    currency: Optional[str] = "usd"
    chartType: Optional[str] = None
    resolution: Optional[str] = "24h"
    exchange: Optional[str] = None
    movingMedian: Optional[int] = None
    movingAverage: Optional[str] = None
    expMovingAverage: Optional[int] = None


class MetricExtra(BaseModel):
    name: str
    zoom: str = "All"
    scale: str = "lin"
    lineColor: str = "#f7931a"
    price: bool = True
    chartStyle: Literal["line", "column"] = "line"
    logTickInterval: Optional[int] = None


class MetricConfig(BaseModel):
    uuid: str
    meta: MetricMeta
    extra: MetricExtra
    configType: Literal["metric"]


class LayoutItem(BaseModel):
    i: str
    x: int
    y: int
    h: Optional[int] = 6
    w: Optional[int] = 6
    minH: Optional[int] = 1
    minW: Optional[int] = 3
    moved: Optional[bool] = False
    static: Optional[bool] = False


class Dashboard(BaseModel):
    meta: DashboardMeta
    configs: List[MetricConfig]
    layouts: List[LayoutItem]

    model_config = {"exclude_defaults": True}
