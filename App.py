# import streamlit as st
# import pandas as pd
# import time
# import re

# from commute import geocode_address, get_commute
# from scoring import score_localities, DEFAULT_AMENITY_WEIGHTS, DEFAULT_CATEGORY_WEIGHTS

 
# # ------------------------------------------------------------------
# # Data loading (cached — runs once per app session, not per user click)
# # ------------------------------------------------------------------
 
# def clean_rent_data(value):
#     if pd.isna(value) or value == "":
#         return None
#     if isinstance(value, (int, float)):
#         return float(value)
#     cleaned = re.sub(r"[^\d.]", "", str(value))
#     return float(cleaned) if cleaned else None

# @st.cache_data

# def load_data():
#     df=pd.read_csv("locality_data_final.csv")
#     rent_columns=[col for col in df.columns if col.startswith("rent_")]
#     for col in rent_columns:
#         df[col]=df[col].apply(clean_rent_data)
#     return df

# @st.cache_data(show_spinner=False)

# def compute_commute_df(office_address, localities_tuple):
#     office_lat, office_lng= geocode_address(office_address, country="India")
#     if office_lat=="":
#         return None, None, None

#     rows=[]
#     for locality, lat, lng in localities_tuple:
#         km, mins= get_commute(office_lat,office_lng, lat, lng)
#         rows.append({"locality": locality,"commute_km": km, "commute_min": mins})
#         time.sleep(0.3)
#     return pd.DataFrame(rows), office_lat, office_lng


#  #------------------------------------------------------------------
# # App layout
# # ------------------------------------------------------------------
 
 
# st.set_page_config(page_title="Bangalore Locality Recommender", layout="wide")
# st.title("🏠 Bangalore Locality Recommender")
# st.caption(
#     "Ranks Bangalore localities based on your office location, budget, and priorities. "
#     "Commute times are free-flow driving estimates (no live traffic) — treat them as a "
#     "relative signal between localities, not an exact prediction."
# )
 
# df = load_data()
 
# with st.sidebar:
#     st.header("Your preferences")
 
#     office_address = st.text_input(
#         "Office location",
#         placeholder="e.g. Manyata Tech Park, Bangalore",
#     )
 
#     budget = st.number_input("Monthly rent budget (₹)", min_value=5000, max_value=200000, value=25000, step=1000)
 
#     bhk = st.selectbox("Residence type", ["1bhk", "2bhk", "3bhk"], index=1)
 
#     furnishing = st.selectbox(
#         "Furnishing preference",
#         ["unfurnished", "semi_furnished", "fully_furnished"],
#         index=1,
#     )
 
#     st.subheader("How much does each factor matter?")
#     commute_weight = st.slider("Commute", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["commute"])
#     rent_weight = st.slider("Rent", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["rent"])
#     amenity_weight = st.slider("Amenities", 0.0, 1.0, DEFAULT_CATEGORY_WEIGHTS["amenities"])
 
#     with st.expander("Amenity priorities (optional)"):
#         amenity_weights = {}
#         for amenity in DEFAULT_AMENITY_WEIGHTS:
#             label = amenity.replace("_", " ").title()
#             amenity_weights[amenity] = st.slider(label, 0.0, 2.0, 1.0, key=f"amenity_{amenity}")
 
#     submitted = st.button("Find my localities", type="primary", use_container_width=True)
 
# if submitted:
#     if not office_address.strip():
#         st.warning("Please enter an office location.")
#         st.stop()
 
#     with st.spinner("Resolving office location and computing commute times..."):
#         localities_tuple = tuple(df[["locality", "lat", "lng"]].itertuples(index=False, name=None))
#         commute_df, office_lat, office_lng = compute_commute_df(office_address, localities_tuple)
 
#     if commute_df is None:
#         st.error("Could not find that office location. Try being more specific, e.g. add 'Bangalore'.")
#         st.stop()
 
#     category_weights = {"commute": commute_weight, "rent": rent_weight, "amenities": amenity_weight}
 
#     result, filtered_out = score_localities(
#         df, commute_df,
#         budget=budget, bhk=bhk, furnishing=furnishing,
#         amenity_weights=amenity_weights,
#         category_weights=category_weights,
#     )
 
#     if result.empty:
#         st.warning(
#             f"No localities matched your budget of ₹{budget:,} for a {bhk} "
#             f"({furnishing.replace('_', ' ')}). Try increasing your budget."
#         )
#         st.stop()
 
#     if filtered_out > 0:
#         st.caption(f"{filtered_out} locality(ies) excluded — over budget or no rent data available.")
 
#     st.subheader("Top matches")
 
#     display_df = result[[
#         "rank", "locality", "score", "effective_rent", "furnishing_used",
#         "commute_min", "commute_km", "amenity_score",
#     ]].copy()
#     display_df["score"] = (display_df["score"] * 100).round(1)
#     display_df["amenity_score"] = (display_df["amenity_score"] * 100).round(1)
#     display_df.columns = [
#         "Rank", "Locality", "Fit Score (%)", "Rent (₹)", "Furnishing Used",
#         "Commute (min)", "Commute (km)", "Amenity Score (%)",
#     ]
 
#     st.dataframe(display_df, use_container_width=True, hide_index=True)
 
#     st.subheader("Map")
#     map_df = result[["lat", "lng"]].rename(columns={"lat": "latitude", "lng": "longitude"})
#     st.map(map_df)
 
#     with st.expander("Why these rankings? (score breakdown)"):
#         st.write(
#             "Each locality is scored on three weighted factors — commute time, rent "
#             "(vs. your budget), and amenities (vs. your priorities) — each normalized "
#             "0-100% relative to the other localities shown, then combined using the "
#             "weights you set in the sidebar."
#         )
#         if result["furnishing_fallback"].any():
#             st.caption(
#                 "Note: some localities didn't have your exact furnishing preference on "
#                 "record — the closest available furnishing type was used instead "
#                 "(see 'Furnishing Used' column)."
#             )
# else:
#     st.info("Enter your office location and preferences in the sidebar, then click **Find my localities**.")


import streamlit as st
import pandas as pd
import time
import re

from commute import geocode_address, get_commute
from scoring import score_localities, DEFAULT_AMENITY_WEIGHTS, DEFAULT_CATEGORY_WEIGHTS


# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Bangalore Locality Recommender",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# CUSTOM CSS — VISUAL ONLY
# ------------------------------------------------------------------

st.markdown(
    """
    <style>

    /* ==============================
       GLOBAL
       ============================== */

    .stApp {
        background-color: #f7f8fa;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Remove excessive top spacing */
    header[data-testid="stHeader"] {
        background-color: transparent;
    }


    /* ==============================
       HERO SECTION
       ============================== */

    .hero {
        background: linear-gradient(
            135deg,
            #111827 0%,
            #1f2937 55%,
            #374151 100%
        );

        padding: 2.2rem 2.5rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;

        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
    }

    .hero-title {
        color: white;
        font-size: 2.35rem;
        font-weight: 750;
        margin: 0;
        letter-spacing: -0.8px;
    }

    .hero-subtitle {
        color: #d1d5db;
        font-size: 1rem;
        margin-top: 0.65rem;
        max-width: 850px;
        line-height: 1.6;
    }

    .hero-tag {
        display: inline-block;
        margin-top: 1.1rem;
        padding: 0.35rem 0.8rem;
        border-radius: 20px;
        background-color: rgba(255,255,255,0.1);
        color: #e5e7eb;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }


    /* ==============================
       SIDEBAR
       ============================== */

    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #111827;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        color: #4b5563;
    }

    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 10px;
        font-weight: 650;
        padding: 0.65rem 1rem;
    }


    /* ==============================
       SECTION HEADERS
       ============================== */

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #111827;
        margin-top: 1.4rem;
        margin-bottom: 0.8rem;
    }

    .section-subtitle {
        color: #6b7280;
        font-size: 0.9rem;
        margin-top: -0.4rem;
        margin-bottom: 1rem;
    }


    /* ==============================
       KPI CARDS
       ============================== */

    .kpi-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.15rem 1.3rem;
        min-height: 110px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.035);
    }

    .kpi-label {
        color: #6b7280;
        font-size: 0.78rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .kpi-value {
        color: #111827;
        font-size: 1.65rem;
        font-weight: 750;
        margin-top: 0.35rem;
    }

    .kpi-description {
        color: #9ca3af;
        font-size: 0.75rem;
        margin-top: 0.15rem;
    }


    /* ==============================
       RESULT TABLE
       ============================== */

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.035);
    }


    /* ==============================
       INFO / EXPLANATION CARDS
       ============================== */

    .info-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.25rem 1.4rem;
        margin-top: 0.5rem;
        line-height: 1.65;
        color: #4b5563;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.025);
    }

    .info-card strong {
        color: #111827;
    }


    /* ==============================
       METHODOLOGY CARDS
       ============================== */

    .method-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        min-height: 125px;
    }

    .method-number {
        font-size: 0.75rem;
        font-weight: 700;
        color: #6b7280;
        letter-spacing: 0.6px;
    }

    .method-title {
        font-size: 1rem;
        font-weight: 700;
        color: #111827;
        margin-top: 0.35rem;
    }

    .method-text {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 0.35rem;
        line-height: 1.45;
    }


    /* ==============================
       FOOTER
       ============================== */

    .footer {
        margin-top: 3rem;
        padding-top: 1.2rem;
        border-top: 1px solid #e5e7eb;
        text-align: center;
        color: #9ca3af;
        font-size: 0.75rem;
    }


    /* ==============================
       BUTTON
       ============================== */

    .stButton > button {
        border-radius: 10px;
        font-weight: 650;
        min-height: 42px;
    }


    /* ==============================
       MOBILE
       ============================== */

    @media (max-width: 768px) {

        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .hero {
            padding: 1.5rem;
        }

        .hero-title {
            font-size: 1.8rem;
        }

        .hero-subtitle {
            font-size: 0.9rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# DATA LOADING
# ------------------------------------------------------------------

def clean_rent_data(value):
    if pd.isna(value) or value == "":
        return None

    if isinstance(value, (int, float)):
        return float(value)

    cleaned = re.sub(r"[^\d.]", "", str(value))

    return float(cleaned) if cleaned else None


@st.cache_data
def load_data():

    df = pd.read_csv("locality_data_final.csv")

    rent_columns = [
        col for col in df.columns
        if col.startswith("rent_")
    ]

    for col in rent_columns:
        df[col] = df[col].apply(clean_rent_data)

    return df


@st.cache_data(show_spinner=False)
def compute_commute_df(office_address, localities_tuple):

    office_lat, office_lng = geocode_address(
        office_address,
        country="India"
    )

    if office_lat == "":
        return None, None, None

    rows = []

    for locality, lat, lng in localities_tuple:

        km, mins = get_commute(
            office_lat,
            office_lng,
            lat,
            lng
        )

        rows.append(
            {
                "locality": locality,
                "commute_km": km,
                "commute_min": mins
            }
        )

        time.sleep(0.3)

    return pd.DataFrame(rows), office_lat, office_lng


# ------------------------------------------------------------------
# HERO
# ------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">

        <div class="hero-title">
            🏠 Bangalore Locality Recommender
        </div>

        <div class="hero-subtitle">
            A data-driven recommendation tool that helps you identify
            Bangalore localities based on your office location, rental
            budget, residence preferences, commute, and amenities.
        </div>

        <div class="hero-tag">
            DATA-DRIVEN LOCALITY RECOMMENDATION
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------

df = load_data()


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------

with st.sidebar:

    st.markdown("## ⚙️ Your Preferences")

    st.caption(
        "Tell us what matters to you and we'll rank suitable localities."
    )

    st.markdown("### 📍 Location")

    office_address = st.text_input(
        "Office location",
        placeholder="e.g. Manyata Tech Park, Bangalore",
    )

    st.markdown("### 🏠 Residence")

    budget = st.number_input(
        "Monthly rent budget (₹)",
        min_value=5000,
        max_value=200000,
        value=25000,
        step=1000
    )

    bhk = st.selectbox(
        "Residence type",
        ["1bhk", "2bhk", "3bhk"],
        index=1
    )

    furnishing = st.selectbox(
        "Furnishing preference",
        [
            "unfurnished",
            "semi_furnished",
            "fully_furnished"
        ],
        index=1,
    )

    st.markdown("### ⚖️ Recommendation Weights")

    st.caption(
        "Adjust how strongly each factor influences the final score."
    )

    commute_weight = st.slider(
        "🚗 Commute",
        0.0,
        1.0,
        DEFAULT_CATEGORY_WEIGHTS["commute"]
    )

    rent_weight = st.slider(
        "💰 Rent",
        0.0,
        1.0,
        DEFAULT_CATEGORY_WEIGHTS["rent"]
    )

    amenity_weight = st.slider(
        "🏪 Amenities",
        0.0,
        1.0,
        DEFAULT_CATEGORY_WEIGHTS["amenities"]
    )

    with st.expander("🔎 Amenity priorities"):

        amenity_weights = {}

        for amenity in DEFAULT_AMENITY_WEIGHTS:

            label = amenity.replace(
                "_", " "
            ).title()

            amenity_weights[amenity] = st.slider(
                label,
                0.0,
                2.0,
                1.0,
                key=f"amenity_{amenity}"
            )

    st.markdown("---")

    submitted = st.button(
        "Find My Localities →",
        type="primary",
        use_container_width=True
    )


# ------------------------------------------------------------------
# MAIN RESULTS
# ------------------------------------------------------------------

if submitted:

    if not office_address.strip():

        st.warning(
            "Please enter an office location."
        )

        st.stop()


    # --------------------------------------------------------------
    # COMPUTE COMMUTE
    # --------------------------------------------------------------

    with st.spinner(
        "Resolving office location and computing commute times..."
    ):

        localities_tuple = tuple(
            df[
                ["locality", "lat", "lng"]
            ].itertuples(
                index=False,
                name=None
            )
        )

        commute_df, office_lat, office_lng = compute_commute_df(
            office_address,
            localities_tuple
        )


    if commute_df is None:

        st.error(
            "Could not find that office location. "
            "Try being more specific, e.g. add 'Bangalore'."
        )

        st.stop()


    # --------------------------------------------------------------
    # SCORE LOCALITIES
    # --------------------------------------------------------------

    category_weights = {
        "commute": commute_weight,
        "rent": rent_weight,
        "amenities": amenity_weight
    }


    result, filtered_out = score_localities(
        df,
        commute_df,
        budget=budget,
        bhk=bhk,
        furnishing=furnishing,
        amenity_weights=amenity_weights,
        category_weights=category_weights,
    )


    if result.empty:

        st.warning(
            f"No localities matched your budget of ₹{budget:,} "
            f"for a {bhk} "
            f"({furnishing.replace('_', ' ')}). "
            f"Try increasing your budget."
        )

        st.stop()


    # --------------------------------------------------------------
    # RESULTS HEADER
    # --------------------------------------------------------------

    st.markdown(
        '<div class="section-title">✨ Your Recommended Localities</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-subtitle">'
        'Localities ranked according to your selected preferences.'
        '</div>',
        unsafe_allow_html=True
    )


    # --------------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------------

    top_locality = result.iloc[0]["locality"]

    avg_commute = result["commute_min"].mean()

    avg_rent = result["effective_rent"].mean()

    top_score = result.iloc[0]["score"] * 100


    kpi1, kpi2, kpi3, kpi4 = st.columns(4)


    with kpi1:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Top Match
                </div>

                <div class="kpi-value">
                    {top_locality}
                </div>

                <div class="kpi-description">
                    Highest overall fit
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with kpi2:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Fit Score
                </div>

                <div class="kpi-value">
                    {top_score:.1f}%
                </div>

                <div class="kpi-description">
                    Top locality score
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with kpi3:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Avg. Rent
                </div>

                <div class="kpi-value">
                    ₹{avg_rent:,.0f}
                </div>

                <div class="kpi-description">
                    Across matched localities
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with kpi4:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Avg. Commute
                </div>

                <div class="kpi-value">
                    {avg_commute:.0f} min
                </div>

                <div class="kpi-description">
                    Free-flow estimate
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    st.write("")


    # --------------------------------------------------------------
    # FILTER MESSAGE
    # --------------------------------------------------------------

    if filtered_out > 0:

        st.caption(
            f"ℹ️ {filtered_out} locality(ies) excluded — "
            "over budget or no rent data available."
        )


    # --------------------------------------------------------------
    # RESULTS TABLE
    # --------------------------------------------------------------

    display_df = result[
        [
            "rank",
            "locality",
            "score",
            "effective_rent",
            "furnishing_used",
            "commute_min",
            "commute_km",
            "amenity_score",
        ]
    ].copy()


    display_df["score"] = (
        display_df["score"] * 100
    ).round(1)


    display_df["amenity_score"] = (
        display_df["amenity_score"] * 100
    ).round(1)


    display_df["effective_rent"] = (
        display_df["effective_rent"]
        .round(0)
    )


    display_df["commute_min"] = (
        display_df["commute_min"]
        .round(0)
    )


    display_df["commute_km"] = (
        display_df["commute_km"]
        .round(1)
    )


    display_df.columns = [
        "Rank",
        "Locality",
        "Fit Score (%)",
        "Rent (₹)",
        "Furnishing Used",
        "Commute (min)",
        "Commute (km)",
        "Amenity Score (%)",
    ]


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=430,
    )


    # --------------------------------------------------------------
    # MAP
    # --------------------------------------------------------------

    st.markdown(
        '<div class="section-title">📍 Locality Map</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-subtitle">'
        'Geographic view of the recommended localities.'
        '</div>',
        unsafe_allow_html=True
    )


    map_df = result[
        ["lat", "lng"]
    ].rename(
        columns={
            "lat": "latitude",
            "lng": "longitude"
        }
    )


    st.map(map_df)


    # --------------------------------------------------------------
    # SCORE BREAKDOWN
    # --------------------------------------------------------------

    st.markdown("")


    with st.expander(
        "📊 Why these rankings?"
    ):

        st.markdown(
            """
            <div class="info-card">

            Each locality receives a composite score based on three
            major dimensions:

            <br><br>

            <strong>🚗 Commute</strong><br>
            Estimated driving distance and time from your office location.

            <br><br>

            <strong>💰 Rent</strong><br>
            Rental cost relative to your selected monthly budget and
            furnishing preference.

            <br><br>

            <strong>🏪 Amenities</strong><br>
            Availability of relevant amenities around each locality,
            adjusted according to your selected priorities.

            <br><br>

            The individual factors are normalized and combined using
            the weights selected in the sidebar.

            </div>
            """,
            unsafe_allow_html=True
        )


        if result["furnishing_fallback"].any():

            st.caption(
                "Note: some localities didn't have your exact "
                "furnishing preference on record — the closest "
                "available furnishing type was used instead "
                "(see 'Furnishing Used' column)."
            )


    # --------------------------------------------------------------
    # METHODOLOGY
    # --------------------------------------------------------------

    st.markdown(
        '<div class="section-title">🧠 How the recommender works</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-subtitle">'
        'A simple explainable scoring pipeline behind the recommendations.'
        '</div>',
        unsafe_allow_html=True
    )


    m1, m2, m3 = st.columns(3)


    with m1:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    STEP 01
                </div>

                <div class="method-title">
                    User Preferences
                </div>

                <div class="method-text">
                    Office location, budget, BHK,
                    furnishing and personal priorities
                    define the recommendation criteria.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with m2:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    STEP 02
                </div>

                <div class="method-title">
                    Data & Scoring
                </div>

                <div class="method-text">
                    Rental, commute and amenity signals
                    are normalized and combined using
                    user-selected weights.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with m3:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    STEP 03
                </div>

                <div class="method-title">
                    Ranked Recommendations
                </div>

                <div class="method-text">
                    Suitable localities are ranked by their
                    overall fit score and presented with
                    supporting metrics.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


else:

    # --------------------------------------------------------------
    # INITIAL LANDING STATE
    # --------------------------------------------------------------

    st.markdown(
        '<div class="section-title">🚀 Start your search</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-subtitle">'
        'Enter your preferences in the sidebar to generate personalized locality recommendations.'
        '</div>',
        unsafe_allow_html=True
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    01
                </div>

                <div class="method-title">
                    📍 Enter your office
                </div>

                <div class="method-text">
                    Provide your office location so the
                    recommender can estimate commute times.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c2:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    02
                </div>

                <div class="method-title">
                    💰 Set your preferences
                </div>

                <div class="method-text">
                    Define your rental budget, residence
                    type, furnishing and priorities.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c3:

        st.markdown(
            """
            <div class="method-card">

                <div class="method-number">
                    03
                </div>

                <div class="method-title">
                    ✨ Explore recommendations
                </div>

                <div class="method-text">
                    Get ranked localities with supporting
                    rent, commute and amenity metrics.
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("")


    st.markdown(
        """
        <div class="info-card">

        <strong>💡 What makes this recommendation data-driven?</strong>

        <br><br>

        Instead of simply listing popular Bangalore neighbourhoods,
        the application combines multiple signals — rental affordability,
        commute distance, commute time and local amenities — and allows
        the user to decide how important each factor should be.

        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------------

st.markdown(
    """
    <div class="footer">

        Bangalore Locality Recommender &nbsp;•&nbsp;
        Data-driven recommendation prototype

        <br>

        Commute estimates represent free-flow driving conditions
        and should be treated as relative signals rather than
        exact travel-time predictions.

    </div>
    """,
    unsafe_allow_html=True,
)