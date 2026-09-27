"""
Bangalore Locality Recommender — Scoring & Ranking
------------------------------------------------------
Takes the static locality dataset (locality_data_final.csv), live commute
data (computed per user's office address), and user preferences (budget,
BHK, furnishing, amenity priorities) and produces a ranked list of
localities.

This is a weighted multi-criteria scoring system, NOT collaborative
filtering — there's no user-item interaction history to learn from, so
a transparent weighted-sum approach is both the honest choice given the
data available, and easier to explain/justify to anyone reviewing the
project.
"""

import pandas as pd
import numpy as np


# ------------------------------------------------------------------
# 1. RENT LOOKUP WITH FALLBACK
# ------------------------------------------------------------------

# Order to try furnishing types if the user's exact preference isn't
# available for a given locality/BHK. Falls back to "closest" option
# rather than dropping the locality.
FURNISHING_FALLBACK_ORDER = {
    "unfurnished": ["unfurnished", "semi_furnished", "fully_furnished"],
    "semi_furnished": ["semi_furnished", "unfurnished", "fully_furnished"],
    "fully_furnished": ["fully_furnished", "semi_furnished", "unfurnished"],
}


def get_rent(row, bhk, furnishing):
    """
    Return the rent for a given BHK/furnishing combo, falling back to the
    closest available furnishing type if the exact one is missing.
    Returns (rent_value, used_furnishing, was_fallback).
    """
    for candidate in FURNISHING_FALLBACK_ORDER[furnishing]:
        col = f"rent_{bhk}_{candidate}"
        if col in row and pd.notna(row[col]) and row[col] != "":
            return float(row[col]), candidate, (candidate != furnishing)
    return None, None, None


# ------------------------------------------------------------------
# 2. NORMALIZATION
# ------------------------------------------------------------------

def normalize(series, higher_is_better=True):
    """Min-max normalize a pandas Series to 0-1. Missing values become NaN
    (handled later, not silently treated as 0 or filled)."""
    s = series.astype(float)
    if s.max() == s.min():
        return pd.Series(1.0, index=s.index)  # all equal -> no differentiation
    norm = (s - s.min()) / (s.max() - s.min())
    return norm if higher_is_better else 1 - norm


# ------------------------------------------------------------------
# 3. MAIN SCORING FUNCTION
# ------------------------------------------------------------------

DEFAULT_AMENITY_WEIGHTS = {
    "hospitals": 1.0,
    "schools": 1.0,
    "gyms": 1.0,
    "supermarkets": 1.0,
    "restaurants": 1.0,
    "metro_stations": 1.0,
}

# Overall category weights — how much commute vs rent vs amenities matter.
# These should sum to 1.0 but don't have to; they get normalized anyway.
DEFAULT_CATEGORY_WEIGHTS = {
    "commute": 0.4,
    "rent": 0.35,
    "amenities": 0.25,
}


def score_localities(
    df,
    commute_df,          # DataFrame with ['locality', 'commute_km', 'commute_min'] — computed live
    budget,              # max monthly rent the user will pay
    bhk,                 # "1bhk", "2bhk", or "3bhk"
    furnishing,          # "unfurnished", "semi_furnished", or "fully_furnished"
    amenity_weights=None,
    category_weights=None,
):
    """
    Returns a DataFrame ranked best-to-worst, with a 'score' column and
    supporting columns showing why each locality scored the way it did.
    """
    amenity_weights = amenity_weights or DEFAULT_AMENITY_WEIGHTS
    category_weights = category_weights or DEFAULT_CATEGORY_WEIGHTS

    data = df.merge(commute_df[["locality", "commute_km", "commute_min"]], on="locality", how="left")

    # --- rent lookup with fallback ---
    rent_values, used_furnishing, was_fallback = [], [], []
    for _, row in data.iterrows():
        rent, used, fallback = get_rent(row, bhk, furnishing)
        rent_values.append(rent)
        used_furnishing.append(used)
        was_fallback.append(fallback)

    data["effective_rent"] = rent_values
    data["furnishing_used"] = used_furnishing
    data["furnishing_fallback"] = was_fallback

    # --- filter out localities with no rent data at all, or over budget ---
    before_count = len(data)
    data = data[data["effective_rent"].notna()]
    data = data[data["effective_rent"] <= budget]
    filtered_count = before_count - len(data)

    if data.empty:
        return data, filtered_count  # nothing fits — caller should handle this

    # --- normalize each criterion (0-1, higher = better) ---
    data["commute_score"] = normalize(data["commute_min"], higher_is_better=False)
    data["rent_score"] = normalize(data["effective_rent"], higher_is_better=False)

    # amenity score = weighted average of normalized individual amenity counts
    amenity_norms = []
    total_amenity_weight = sum(amenity_weights.values())
    for amenity, weight in amenity_weights.items():
        if amenity in data.columns:
            norm_col = normalize(data[amenity].fillna(0), higher_is_better=True)
            amenity_norms.append(norm_col * weight)
    data["amenity_score"] = sum(amenity_norms) / total_amenity_weight if amenity_norms else 0.5

    # --- combine into final weighted score ---
    total_cat_weight = sum(category_weights.values())
    data["score"] = (
        data["commute_score"] * category_weights["commute"] +
        data["rent_score"] * category_weights["rent"] +
        data["amenity_score"] * category_weights["amenities"]
    ) / total_cat_weight

    data = data.sort_values("score", ascending=False).reset_index(drop=True)
    data["rank"] = data.index + 1

    return data, filtered_count


# ------------------------------------------------------------------
# 4. DEMO / MANUAL TEST
# ------------------------------------------------------------------

if __name__ == "__main__":
    # Minimal fake data to sanity-check the logic without needing real files
    df = pd.DataFrame({
        "locality": ["A", "B", "C"],
        "lat": [12.9, 12.95, 13.0],
        "lng": [77.6, 77.65, 77.7],
        "hospitals": [3, 1, 5],
        "schools": [2, 4, 1],
        "gyms": [1, 1, 2],
        "supermarkets": [2, 3, 1],
        "restaurants": [10, 5, 8],
        "metro_stations": [1, 0, 2],
        "rent_2bhk_semi_furnished": [25000, 22000, np.nan],
        "rent_2bhk_unfurnished": [20000, 19000, 30000],
        "rent_2bhk_fully_furnished": [30000, 27000, 35000],
    })

    commute_df = pd.DataFrame({
        "locality": ["A", "B", "C"],
        "commute_km": [5, 12, 3],
        "commute_min": [20, 40, 10],
    })

    result, filtered_out = score_localities(
        df, commute_df,
        budget=28000, bhk="2bhk", furnishing="semi_furnished",
    )
    print(f"Filtered out {filtered_out} localities (over budget or no rent data)\n")
    print(result[["rank", "locality", "score", "effective_rent", "furnishing_used",
                   "furnishing_fallback", "commute_min", "amenity_score"]])
