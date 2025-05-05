# yt_music_keyword_app.py
"""
Streamlit app: YouTube music keyword explorer
1. Fetch YouTube search suggestions for a seed word (music‑related)
2. Display them in an interactive table with CSV download
3. On demand, append Google Trends (YouTube Search) popularity index

Dependencies: streamlit, pandas, requests, pytrends
Run: streamlit run yt_music_keyword_app.py
"""

import streamlit as st
import pandas as pd
import string
import requests
import time
from pytrends.request import TrendReq

# -------------------------------------
# Helper functions
# -------------------------------------

def fetch_suggestions(seed: str, delay: float = 0.15) -> list[str]:
    """Return unique YouTube autocomplete suggestions for `seed` + [a‑z0‑9]."""
    suggestions = set()
    alphabet = string.ascii_lowercase + "0123456789"
    for ch in alphabet:
        query = f"{seed} {ch}"
        url = (
            "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q="
            + requests.utils.quote(query)
        )
        try:
            resp = requests.get(url, timeout=4)
            resp.raise_for_status()
            data = resp.json()
            # data[1] is the list of suggestions
            suggestions.update(data[1])
        except (requests.RequestException, ValueError):
            continue
        time.sleep(delay)  # be polite to the service
    # keep only phrases that start with the seed token (case‑insensitive)
    filtered = [s for s in suggestions if s.lower().startswith(seed.lower())]
    return sorted(filtered)


def fetch_trends(keywords: list[str], timeframe: str, geo: str = "") -> dict[str, float]:
    """Return average interest index from Google Trends (YouTube Search) for each keyword."""
    pytrends = TrendReq(hl="en-US", tz=0)
    interest: dict[str, float] = {}

    # Google Trends allows ≤5 keywords per payload
    for i in range(0, len(keywords), 5):
        chunk = keywords[i : i + 5]
        try:
            pytrends.build_payload(
                kw_list=chunk, timeframe=timeframe, geo=geo, gprop="youtube"
            )
            df = pytrends.interest_over_time()
            if not df.empty:
                interest.update(df[chunk].mean().to_dict())
        except Exception:
            continue
    return interest


# -------------------------------------
# Streamlit UI
# -------------------------------------

st.set_page_config(page_title="YouTube Music Keyword Explorer", layout="centered")
st.title("🎵 YouTube Music Keyword Explorer")

# Seed term input
seed = st.text_input(
    "Enter base keyword (seed)",
    value="music",
    help="The script will combine this word with A‑Z & 0‑9 to fetch YouTube autocomplete suggestions.",
)

# Google Trends settings
with st.expander("Google Trends settings", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        timeframe_label = st.selectbox(
            "Select timeframe", [
                "Past 7 days",
                "Past 30 days",
                "Past 90 days",
                "Past 12 months",
                "Past 5 years",
            ],
            index=2,
        )
    with col2:
        geo_input = st.text_input(
            "Geo (ISO‑2 country code, leave blank for Worldwide)", value=""
        )

# Mapping label -> Trends timeframe shorthand
TIMEFRAME_MAP = {
    "Past 7 days": "now 7-d",
    "Past 30 days": "today 1-m",
    "Past 90 days": "today 3-m",
    "Past 12 months": "today 12-m",
    "Past 5 years": "today 5-y",
}

timeframe = TIMEFRAME_MAP[timeframe_label]
geo = geo_input.strip().upper()

st.divider()

if st.button("🔍 Get YouTube suggestions"):
    if not seed:
        st.warning("Please enter a seed keyword.")
    else:
        with st.spinner("Fetching suggestions …"):
            suggestions = fetch_suggestions(seed)
        if suggestions:
            df = pd.DataFrame({"keyword": suggestions})
            st.session_state["keywords_df"] = df
            st.success(f"Collected {len(df)} unique suggestions.")
        else:
            st.error("No suggestions found. Try a different seed word.")

# Display table if present
if "keywords_df" in st.session_state:
    st.subheader("Suggestions table")
    df = st.session_state["keywords_df"]
    st.dataframe(df, use_container_width=True)

    # Download button
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", data=csv_data, file_name="yt_suggestions.csv", mime="text/csv"
    )

    if st.button("📈 Fetch Google Trends info"):
        with st.spinner("Fetching Google Trends data …"):
            interest = fetch_trends(df["keyword"].tolist(), timeframe=timeframe, geo=geo)
        if interest:
            df["interest"] = df["keyword"].map(lambda x: round(interest.get(x, 0), 2))
            st.session_state["keywords_df"] = df  # update session data
            st.success("Trends data appended.")
            st.dataframe(df, use_container_width=True)

            # Updated download button
            csv_trend = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV with Trends", data=csv_trend, file_name="yt_keywords_trends.csv", mime="text/csv"
            )
        else:
            st.error("Failed to retrieve Trends data. Try again later.")
