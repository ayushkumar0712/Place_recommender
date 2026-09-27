import streamlit as st
import pandas as pd
import time
import re

from commute import geocode_address, get_commute
from scoring import score_localities, DEFAULT_AMENITY_WEIGHTS, DEFAULT_CATEGORY_WEIGHTS

 
# ------------------------------------------------------------------
# Data loading (cached — runs once per app session, not per user click)
# ------------------------------------------------------------------
 
def clean_rent_data(value):
    if pd.isna(value) or value=="":
        return None
    if isinstance(value,(int, float)):
        return float(value)
    cleaned= re.sub(r"[^\d.]", str[value])
    return float(cleaned) if cleaned else None

@st.cache_data

def load_data():
    df=pd.read_csv("locality_data_final.csv")
    rent_columns=[col for col in df.columns if col.startswith("rent_")]
    for col in rent_columns:
        df[col]=df[col].apply(clean_rent_data)
    return df

@st.cache_data(show_spinner=False)

def compute_commute_df(office_address, localities_tuple):
    office_lat, office_lng= geocode_address(office_address, country="India")
    if office_lat=="":
        return None, None, None

    rows=[]
    for locality, lat, lng in localities_tuple:
        km, mins= get_commute(office_lat,office_lng, lat, lng)
        rows.append({"locality": locality,"commute_km": km, "commute_min": mins})
        time.sleep(0.3)
    return pd.DataFrame(rows), office_lat, office_lng


 #------------------------------------------------------------------
# App layout
# ------------------------------------------------------------------
 
 
st.set_page_config(page_title="Bangalore Locality Recommender", layout="wide")
st.title("🏠 Bangalore Locality Recommender")
st.caption(
    "Ranks Bangalore localities based on your office location, budget, and priorities. "
    "Commute times are free-flow driving estimates (no live traffic) — treat them as a "
    "relative signal between localities, not an exact prediction."
)
 
df = load_data()
 
with st.sidebar:
    st.header("Your preferences")
 
    office_address = st.text_input(
        "Office location",
        placeholder="e.g. Manyata Tech Park, Bangalore",
    )
 
    budget = st.number_input("Monthly rent budget (₹)", min_value=5000, max_value=200000, value=25000, step=1000)
 
    bhk = st.selectbox("Residence type", ["1bhk", "2bhk", "3bhk"], index=1)
 
    furnishing = st.selectbox(
        "Furnishing preference",
        ["unfurnished", "semi_furnished", "fully_furnished"],
        index=1,
    )
 
    st.subheader("How much does each factor matter?")
    commute_weight = st.slider("Commute", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["commute"])
    rent_weight = st.slider("Rent", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["rent"])
    amenity_weight = st.slider("Amenities", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["amenities"])
 
    with st.expander("Amenity priorities (optional)"):
        amenity_weights = {}
        for amenity in DEFAULT_AMENITY_WEIGHTS:
            label = amenity.replace("_", " ").title()
            amenity_weights[amenity] = st.slider(label, 0.0, 2.0, 1.0, key=f"amenity_{amenity}")
 
    submitted = st.button("Find my localities", type="primary", use_container_width=True)
 
if submitted:
    if not office_address.strip():
        st.warning("Please enter an office location.")
        st.stop()
 
    with st.spinner("Resolving office location and computing commute times..."):
        localities_tuple = tuple(df[["locality", "lat", "lng"]].itertuples(index=False, name=None))
        commute_df, office_lat, office_lng = compute_commute_df(office_address, localities_tuple)
 
    if commute_df is None:
        st.error("Could not find that office location. Try being more specific, e.g. add 'Bangalore'.")
        st.stop()
 
    category_weights = {"commute": commute_weight, "rent": rent_weight, "amenities": amenity_weight}
 
    result, filtered_out = score_localities(
        df, commute_df,
        budget=budget, bhk=bhk, furnishing=furnishing,
        amenity_weights=amenity_weights,
        category_weights=category_weights,
    )
 
    if result.empty:
        st.warning(
            f"No localities matched your budget of ₹{budget:,} for a {bhk} "
            f"({furnishing.replace('_', ' ')}). Try increasing your budget."
        )
        st.stop()
 
    if filtered_out > 0:
        st.caption(f"{filtered_out} locality(ies) excluded — over budget or no rent data available.")
 
    st.subheader("Top matches")
 
    display_df = result[[
        "rank", "locality", "score", "effective_rent", "furnishing_used",
        "commute_min", "commute_km", "amenity_score",
    ]].copy()
    display_df["score"] = (display_df["score"] * 100).round(1)
    display_df["amenity_score"] = (display_df["amenity_score"] * 100).round(1)
    display_df.columns = [
        "Rank", "Locality", "Fit Score (%)", "Rent (₹)", "Furnishing Used",
        "Commute (min)", "Commute (km)", "Amenity Score (%)",
    ]
 
    st.dataframe(display_df, use_container_width=True, hide_index=True)
 
    st.subheader("Map")
    map_df = result[["lat", "lng"]].rename(columns={"lat": "latitude", "lng": "longitude"})
    st.map(map_df)
 
    with st.expander("Why these rankings? (score breakdown)"):
        st.write(
            "Each locality is scored on three weighted factors — commute time, rent "
            "(vs. your budget), and amenities (vs. your priorities) — each normalized "
            "0-100% relative to the other localities shown, then combined using the "
            "weights you set in the sidebar."
        )
        if result["furnishing_fallback"].any():
            st.caption(
                "Note: some localities didn't have your exact furnishing preference on "
                "record — the closest available furnishing type was used instead "
                "(see 'Furnishing Used' column)."
            )
else:
    st.info("Enter your office location and preferences in the sidebar, then click **Find my localities**.")