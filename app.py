# yt_music_keyword_app.py
"""
Streamlit app: YouTube music keyword explorer
Updated 2025‑05‑05
• Removes digits from A‑Z sweep (letters only)
• More robust Google Trends fetch: fills missing keywords with 0, retry logic to avoid empty dataframe error
• Optional request delay slider
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

def fetch_suggestions(seed: str, delay: float = 0.2) -> list[str]:
    """Return unique YouTube autocomplete suggestions for `seed` + [a‑z]."""
    suggestions = set()
    alphabet = string.ascii_lowercase  # digits removed per user request

    for ch in alphabet:
        query = f"{seed} {ch}"
        url = (
            "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q="
            + requests.utils.quote(query)
        )
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            suggestions.update(data[1])
        except (requests.RequestException, ValueError):
            continue
        time.sleep(delay)  # throttle to reduce blocking risk

    filtered = [s for s in suggestions if s.lower().startswith(seed.lower())]
    return sorted(filtered)


def fetch_trends(keywords: list[str], timeframe: str, geo: str = "", retries: int = 2) -> dict[str, float]:
    """Return average YouTube‑search interest index from Google Trends for each keyword.
    Missing or empty results are filled with 0 to avoid hard failure.
    """
    pytrends = TrendReq(hl="en-US", tz=0)
    interest: dict[str, float] = {}

    for i in range(0, len(keywords), 5):
        chunk = keywords[i : i + 5]
        attempt = 0
        while attempt <= retries:
            try:
                pytrends.build_payload(chunk, timeframe=timeframe, geo=geo, gprop="youtube")
                df = pytrends.interest_over_time()
                if not df.empty:
                    interest.update(df[chunk].mean().to_dict())
                else:
                    # empty dataframe — treat all chunk keywords as zero interest
                    interest.update({kw: 0 for kw in chunk})
                break  # success or handled empty; exit retry loop
            except Exception:
                attempt += 1
                time.sleep(1 + attempt)  # linear back‑off
        else:
            # after retries still no data; set zeros
            interest.update({kw: 0 for kw in chunk})

    return interest

# -------------------------------------
# Streamlit UI
# -------------------------------------

st.set_page_config(page_title="YouTube Music Keyword Explorer", layout="centered")
st.title("🎵 YouTube Music Keyword Explorer")

# Seed input
seed = st.text_input("Enter base keyword (seed)", value="music")

# Optional delay setting
delay = st.slider("Delay between YouTube suggest requests (seconds)", 0.1, 1.0, 0.2, 0.05)

# Google Trends settings
with st.expander("Google Trends settings"):
    col1, col2 = st.columns(2)
    with col1:
        timeframe_label = st.selectbox(
            "Select timeframe",
            [
                "Past 7 days",
                "Past 30 days",
                "Past 90 days",
                "Past 12 months",
                "Past 5 years",
            ],
            index=2,
        )
    with col2:
        geo_input = st.text_input("Geo (ISO‑2 code, blank = Worldwide)", value="")

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
            suggestions = fetch_suggestions(seed, delay)
        if suggestions:
            df = pd.DataFrame({"keyword": suggestions})
            st.session_state["keywords_df"] = df
            st.success(f"Collected {len(df)} suggestions.")
        else:
            st.error("No suggestions found; try another seed word.")

# Display table if exists
if "keywords_df" in st.session_state:
    df = st.session_state["keywords_df"]
    st.subheader("Suggestions table")
    st.dataframe(df, use_container_width=True)

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_data, "yt_suggestions.csv", "text/csv")

    if st.button("📈 Append Google Trends index"):
        with st.spinner("Fetching Google Trends data …"):
            interest = fetch_trends(df["keyword"].tolist(), timeframe, geo)
        # Always add interest col (zeros if not found)
        df["interest"] = df["keyword"].map(lambda x: round(interest.get(x, 0), 2))
        st.session_state["keywords_df"] = df
        st.success("Google Trends data added.")
        st.dataframe(df, use_container_width=True)
        csv_trend = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV with Trends", csv_trend, "yt_keywords_trends.csv", "text/csv")
