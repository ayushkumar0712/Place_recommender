"""
Bangalore Locality Recommender — Commute Module
---------------------------------------------------
This is the query-time piece: given a user's office location (resolved
fresh each time, since it's different per user) and the static
locality_features.csv, computes commute distance/time from that office
to every candidate locality.

Import this from your Streamlit app, or run standalone as a CLI tool.

Standalone run: python commute.py --office "Manyata Tech Park, Bangalore"
"""

import requests
import pandas as pd
import time
import argparse

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
HEADERS = {"User-Agent": "bangalore-locality-recommender-project (personal use)"}


def geocode_address(address, city="", country="India"):
    """Return (lat, lng) for a free-text address using Nominatim."""
    query_parts = [p for p in [address, city, country] if p]
    params = {"q": ", ".join(query_parts), "format": "json", "limit": 1}
    r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    results = r.json()
    if not results:
        return None, None
    return float(results[0]["lat"]), float(results[0]["lon"])


def resolve_office_location(office_arg=None, office_lat_arg=None, office_lng_arg=None, interactive=True):
    """
    Resolve an office location from an address string, explicit lat/lng,
    or (if interactive=True) a prompt. Call this fresh for each user/query
    — never cache it across different users.
    """
    if office_lat_arg is not None and office_lng_arg is not None:
        return office_lat_arg, office_lng_arg

    if office_arg:
        lat, lng = geocode_address(office_arg, city="", country="India")
        if lat is not None:
            return lat, lng
        if not interactive:
            raise ValueError(f"Could not geocode office address: {office_arg}")

    if not interactive:
        raise ValueError("No office location provided and interactive mode is off.")

    while True:
        user_input = input(
            "\nEnter your office location.\n"
            "  - Type an address/area (e.g. 'MG Road, Bangalore'), OR\n"
            "  - Type lat,lng directly (e.g. '12.9758,77.6045')\n> "
        ).strip()

        if "," in user_input and all(
            part.strip().replace(".", "").replace("-", "").isdigit()
            for part in user_input.split(",")
        ):
            lat_str, lng_str = user_input.split(",")
            return float(lat_str.strip()), float(lng_str.strip())

        lat, lng = geocode_address(user_input, city="Bangalore", country="India")
        if lat is not None:
            return lat, lng
        print("Could not find that location — try being more specific (e.g. add 'Bangalore').")


def get_commute(office_lat, office_lng, dest_lat, dest_lng):
    """Return (distance_km, duration_min) driving from office to a single destination."""
    url = f"{OSRM_URL}/{office_lng},{office_lat};{dest_lng},{dest_lat}"
    try:
        r = requests.get(url, params={"overview": "false"}, timeout=15)
        r.raise_for_status()
        route = r.json()["routes"][0]
        return round(route["distance"] / 1000, 2), round(route["duration"] / 60, 1)
    except Exception as e:
        print(f"  [WARN] OSRM query failed: {e}")
        return None, None


def add_commute_column(locality_df, office_lat, office_lng, sleep_between=0.3):
    """
    Given the static locality_features.csv (as a DataFrame) and a resolved
    office location, return a copy with commute_km / commute_min columns
    computed fresh for that office location.
    """
    df = locality_df.copy()
    commute_km, commute_min = [], []

    for _, row in df.iterrows():
        km, mins = get_commute(office_lat, office_lng, row["lat"], row["lng"])
        commute_km.append(km)
        commute_min.append(mins)
        time.sleep(sleep_between)  # light politeness delay to the public OSRM server

    df["commute_km"] = commute_km
    df["commute_min"] = commute_min
    return df


# ------------------------------------------------------------------
# Standalone CLI usage
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compute commute times from an office to all localities")
    parser.add_argument("--office", type=str, default=None, help="Office address")
    parser.add_argument("--office-lat", type=float, default=None)
    parser.add_argument("--office-lng", type=float, default=None)
    parser.add_argument("--features", type=str, default="locality_features.csv",
                         help="Path to the static locality_features.csv")
    args = parser.parse_args()

    office_lat, office_lng = resolve_office_location(args.office, args.office_lat, args.office_lng)
    print(f"\nUsing office location: {office_lat}, {office_lng}\n")

    locality_df = pd.read_csv(args.features)
    result_df = add_commute_column(locality_df, office_lat, office_lng)

    result_df.to_csv("locality_features_with_commute.csv", index=False)
    print("\nSaved locality_features_with_commute.csv")
    print(result_df[["locality", "commute_km", "commute_min"]])


if __name__ == "__main__":
    main()
