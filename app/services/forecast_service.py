"""
Forecast Service — Production Demand Forecasting

Algorithm (v2):
  1. Load historical daily quantities per product+route.
  2. Filter out zero-quantity days (days with no orders ≠ days with low demand).
  3. Build a weighted weekly signature using exponential weighted mean (ewm)
     so recent weeks contribute more than older ones.
  4. Compute a recent trend factor (last 2 weeks vs previous 2 weeks), clipped [0.5, 2.0].
  5. Project the next N days: predicted = ewm_mean[dow] * trend_factor
  6. recommended = ceil(predicted * 1.10)  — 10% safety buffer, rounded up.
  7. last_week_actual = actual units sold on the same weekday 7 days ago.
  8. is_no_delivery_day = weekday where >80% of historical records are zero.
"""

from __future__ import annotations

import math
from datetime import datetime, date, timedelta, timezone
from typing import List

import numpy as np
import pandas as pd

from ..schemas.forecast import (
    ForecastPoint,
    ForecastResponse,
    ProductForecast,
    RouteBreakdown,
)


_CONFIDENCE_THRESHOLDS = {"alta": 45, "media": 20}
_BUFFER = 1.10          # 10% safety buffer
_TREND_STABLE_PCT = 5   # ±5% is considered stable


def _confidence(data_points: int) -> str:
    if data_points >= _CONFIDENCE_THRESHOLDS["alta"]:
        return "alta"
    if data_points >= _CONFIDENCE_THRESHOLDS["media"]:
        return "media"
    return "baja"


def _trend_direction(pct: float) -> str:
    if pct > _TREND_STABLE_PCT:
        return "up"
    if pct < -_TREND_STABLE_PCT:
        return "down"
    return "stable"


def _trend_factor(series: pd.Series) -> float:
    """Ratio of last-2-weeks total vs previous-2-weeks, clipped [0.5, 2.0]."""
    if len(series) < 14:
        return 1.0
    recent = series.iloc[-14:].sum()
    previous = series.iloc[-28:-14].sum() if len(series) >= 28 else series.iloc[:-14].sum()
    if previous == 0:
        return 1.0
    return float(np.clip(recent / previous, 0.5, 2.0))


def _recommended(predicted: float) -> int:
    """Apply safety buffer and round up to a whole unit."""
    return math.ceil(predicted * _BUFFER)


def _no_delivery_rate(dow: int, full_df: pd.DataFrame) -> bool:
    """True when >80% of records for this weekday have zero quantity."""
    dow_data = full_df[full_df["dow"] == dow]["total_quantity"]
    if len(dow_data) == 0:
        return True
    zero_rate = (dow_data == 0).sum() / len(dow_data)
    return zero_rate > 0.80


class ForecastService:

    def generate_production_forecast(
        self,
        daily_data: List[dict],
        days_ahead: int = 3,
        history_days: int = 90,
    ) -> ForecastResponse:
        """Build a production forecast from raw daily quantity rows."""

        if not daily_data:
            return ForecastResponse(
                products=[],
                days_ahead=days_ahead,
                history_days_used=history_days,
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_recommended_tomorrow=0,
            )

        df = pd.DataFrame(daily_data)
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["dow"] = df["order_date"].dt.dayofweek   # 0=Mon … 6=Sun

        today = date.today()
        last_week = today - timedelta(days=7)
        forecast_dates = [today + timedelta(days=i + 1) for i in range(days_ahead)]

        # Build last_week_actual lookup: product_id → actual quantity sold 7 days ago
        last_week_df = df[df["order_date"].dt.date == last_week]
        last_week_by_product: dict[int, float] = (
            last_week_df.groupby("product_id")["total_quantity"]
            .sum()
            .to_dict()
        )

        products = self._build_product_forecasts(df, forecast_dates, last_week_by_product)

        total_tomorrow = sum(
            p.forecast[0].recommended for p in products
            if p.forecast and not p.forecast[0].is_no_delivery_day
        )

        return ForecastResponse(
            products=products,
            days_ahead=days_ahead,
            history_days_used=history_days,
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_recommended_tomorrow=total_tomorrow,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_product_forecasts(
        self,
        df: pd.DataFrame,
        forecast_dates: List[date],
        last_week_by_product: dict,
    ) -> List[ProductForecast]:
        results: List[ProductForecast] = []

        for product_id, pdf in df.groupby("product_id"):
            product_name = pdf["product_name"].iloc[0]

            # Daily totals including zeros (used for no-delivery detection)
            daily_totals_with_zeros = (
                pdf.groupby("order_date")["total_quantity"]
                .sum()
                .sort_index()
            )

            # Remove zero-quantity days before building the signature
            # (zeros mean no orders that day, not low demand)
            pdf_nonzero = pdf[pdf["total_quantity"] > 0]

            # Exponential weighted mean per day-of-week using recent data
            # ewm gives more weight to recent observations
            dow_ewm: dict[int, float] = {}
            dow_std: dict[int, float] = {}
            for dow_val, dow_group in pdf_nonzero.groupby("dow"):
                daily = dow_group.groupby("order_date")["total_quantity"].sum().sort_index()
                if len(daily) >= 2:
                    dow_ewm[dow_val] = float(daily.ewm(span=8).mean().iloc[-1])
                    dow_std[dow_val] = float(daily.std())
                elif len(daily) == 1:
                    dow_ewm[dow_val] = float(daily.iloc[0])
                    dow_std[dow_val] = 0.0

            trend = _trend_factor(daily_totals_with_zeros[daily_totals_with_zeros > 0])
            trend_pct = round((trend - 1) * 100, 1)
            data_points = int((daily_totals_with_zeros > 0).sum())

            last_week_actual = last_week_by_product.get(int(product_id))

            forecast_points = []
            for forecast_date in forecast_dates:
                dow = forecast_date.weekday()
                no_delivery = _no_delivery_rate(dow, pdf)

                if no_delivery or dow not in dow_ewm:
                    forecast_points.append(ForecastPoint(
                        date=forecast_date.isoformat(),
                        predicted=0.0,
                        recommended=0,
                        last_week_actual=last_week_actual if forecast_date == forecast_dates[0] else None,
                        is_no_delivery_day=True,
                    ))
                    continue

                predicted = round(dow_ewm[dow] * trend, 2)
                forecast_points.append(ForecastPoint(
                    date=forecast_date.isoformat(),
                    predicted=predicted,
                    recommended=_recommended(predicted),
                    last_week_actual=last_week_actual if forecast_date == forecast_dates[0] else None,
                    is_no_delivery_day=False,
                ))

            # Route breakdown for tomorrow
            by_route = self._route_breakdown(pdf_nonzero, forecast_dates[0], trend)

            results.append(ProductForecast(
                product_id=int(product_id),
                product_name=product_name,
                forecast=forecast_points,
                by_route=by_route,
                trend_direction=_trend_direction(trend_pct),
                trend_percentage=trend_pct,
                confidence=_confidence(data_points),
                history_days_available=data_points,
            ))

        # Sort by tomorrow's recommended (descending) — most critical first
        results.sort(
            key=lambda p: p.forecast[0].recommended if p.forecast and not p.forecast[0].is_no_delivery_day else 0,
            reverse=True,
        )
        return results

    def _route_breakdown(
        self,
        pdf: pd.DataFrame,
        target_date: date,
        trend: float,
    ) -> List[RouteBreakdown]:
        """Estimate each route's contribution for a given target day."""
        dow = target_date.weekday()

        route_dow = (
            pdf.groupby(["route_id", "route_name", "dow"])["total_quantity"]
            .mean()
            .reset_index()
        )
        route_dow = route_dow[route_dow["dow"] == dow]

        breakdown: List[RouteBreakdown] = []
        for _, row in route_dow.iterrows():
            predicted = round(float(row["total_quantity"]) * trend, 2)
            if predicted > 0:
                breakdown.append(RouteBreakdown(
                    route_id=int(row["route_id"]) if row["route_id"] and not math.isnan(float(row["route_id"])) else None,
                    route_name=str(row["route_name"]),
                    predicted=predicted,
                    recommended=_recommended(predicted),
                ))

        return sorted(breakdown, key=lambda r: r.predicted, reverse=True)
