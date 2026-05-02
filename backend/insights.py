"""Generate simple rule-based analyst commentary from recent housing trends."""

import pandas as pd


def _trend_label(current: float, prior: float, higher_word: str, lower_word: str) -> str:
    """Describe whether a value increased or decreased."""
    if current > prior:
        return higher_word
    if current < prior:
        return lower_word
    return "flat"


def generate_insights(dataset: pd.DataFrame) -> list[dict]:
    """Return analyst-style observations based on the latest available data."""
    if len(dataset) < 13:
        return [
            {
                "title": "Not enough history yet",
                "message": "The dataset needs at least 13 monthly observations for trend commentary.",
                "tone": "neutral",
            }
        ]

    latest = dataset.iloc[-1]
    previous = dataset.iloc[-2]
    year_ago = dataset.iloc[-13]

    starts_yoy = ((latest["housing_starts"] / year_ago["housing_starts"]) - 1) * 100
    permits_yoy = ((latest["building_permits"] / year_ago["building_permits"]) - 1) * 100
    price_yoy = ((latest["home_price_index"] / year_ago["home_price_index"]) - 1) * 100
    mortgage_change_yoy = latest["mortgage_rate"] - year_ago["mortgage_rate"]

    supply_tone = "positive" if starts_yoy > 0 and permits_yoy > 0 else "cautious"
    affordability_tone = "cautious" if mortgage_change_yoy > 0.25 else "positive"
    price_tone = "positive" if price_yoy > 0 else "cautious"

    return [
        {
            "title": "Supply Momentum",
            "message": (
                f"Housing starts are {starts_yoy:.1f}% year over year and building permits are "
                f"{permits_yoy:.1f}% year over year. This points to a {supply_tone} near-term "
                "construction pipeline."
            ),
            "tone": supply_tone,
        },
        {
            "title": "Mortgage Rate Pressure",
            "message": (
                f"The 30-year mortgage rate is {latest['mortgage_rate']:.2f}%, "
                f"{mortgage_change_yoy:+.2f} percentage points versus a year ago. "
                "Higher rates can cool buyer demand, while lower rates can improve affordability."
            ),
            "tone": affordability_tone,
        },
        {
            "title": "Home Price Trend",
            "message": (
                f"The Case-Shiller index is {price_yoy:.1f}% year over year, and the latest monthly "
                f"change was {latest['home_price_change']:.2f}%. Price momentum looks {price_tone}."
            ),
            "tone": price_tone,
        },
        {
            "title": "Latest Monthly Movement",
            "message": (
                f"From the prior month, mortgage rates were "
                f"{_trend_label(latest['mortgage_rate'], previous['mortgage_rate'], 'higher', 'lower')}, "
                f"starts were {_trend_label(latest['housing_starts'], previous['housing_starts'], 'higher', 'lower')}, "
                f"and permits were {_trend_label(latest['building_permits'], previous['building_permits'], 'higher', 'lower')}."
            ),
            "tone": "neutral",
        },
    ]
