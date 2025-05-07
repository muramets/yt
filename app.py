# app.py
import streamlit as st
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import re
import time


# Helper: fetch data with retry/backoff for 429 errors
def fetch_interest(keyword: str, tf: str, geo: str, gprop: str, max_attempts: int = 4):
    """Return interest_over_time DataFrame or raise last exception."""
    # TrendReq with built‑in retry/backoff
    pytrends = TrendReq(
        hl="en-US",
        tz=0,
        retries=0,  # we handle retries manually for more control
        backoff_factor=0,
        timeout=(10, 25),
    )
    attempt = 0
    while True:
        try:
            pytrends.build_payload([keyword], timeframe=tf, geo=geo, gprop=gprop)
            return pytrends.interest_over_time()
        except ResponseError as err:
            status = getattr(err.response, "status_code", None)
            if status == 429 and attempt < max_attempts - 1:
                sleep_time = 2 ** attempt  # exponential backoff: 1,2,4,8 sec
                time.sleep(sleep_time)
                attempt += 1
            else:
                raise
        except Exception:
            raise


def main():
    st.title("Google Trends Popularity Index")

    # INPUTS --------------------------------------------------------------
    keyword = st.text_input("Keyword", "lofi study music")

    timeframe_option = st.selectbox(
        "Timeframe",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1,
    )

    if timeframe_option == "Custom":
        st.info(
            "**Custom timeframe format:**\n"
            "• Recent periods: `now 7-d` (last 7 days) or `now 30-d` (last 30 days).\n"
            "• Exact date range: `YYYY-MM-DD YYYY-MM-DD`, e.g. `2025-01-01 2025-05-01`."
        )
        custom_tf = st.text_input(
            "Custom timeframe",
            "",
            placeholder="now 7-d or 2025-01-01 2025-05-01",
            key="custom_tf",
        )
        tf = custom_tf.strip()
    else:
        tf = {
            "Last 7 days": "now 7-d",
            "Last 30 days": "now 30-d",
            "Last 90 days": "now 90-d",
        }[timeframe_option]

    geo = st.text_input(
        "Region code (optional)",
        "",
        help="ISO country code, e.g. 'US', 'RU'; leave blank for worldwide",
    )

    platform = st.selectbox(
        "Platform",
        ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
        index=1,
    )

    submit = st.button("Submit")
    if not submit:
        return

    # VALIDATE -----------------------------------------------------------
    if timeframe_option == "Custom" and not tf:
        st.error("Please enter a custom timeframe.")
        return

    # Convert 'today X-d' → 'now X-d' if user typed it
    m_today = re.match(r"today (\d+)-d", tf)
    if m_today:
        tf = f"now {m_today.group(1)}-d"
        st.info(f"Timeframe adjusted to '{tf}' for API compatibility.")

    gprop_map = {
        "Web Search": "",
        "YouTube": "youtube",
        "Image Search": "images",
        "News Search": "news",
        "Google Shopping": "froogle",
        "Top Charts": "topsites",
    }
    gprop = gprop_map[platform]

    # DEBUG PAYLOAD -------------------------------------------------------
    with st.expander("Debug Payload", expanded=False):
        st.json({"kw_list": [keyword], "timeframe": tf, "geo": geo, "gprop": gprop})

    # FETCH DATA ----------------------------------------------------------
    with st.spinner("Fetching data from Google Trends..."):
        try:
            data = fetch_interest(keyword, tf, geo, gprop)
        except ResponseError as err:
            code = getattr(err.response, "status_code", "unknown")
            if code == 429:
                st.error(
                    "Google returned **429 Too Many Requests**. This usually means the shared IP "
                    "address on Streamlit Cloud hit a temporary rate limit or needs a CAPTCHA. "
                    "Please wait a few minutes and try again, or switch to 'Web Search' platform, "
                    "which is less strict than YouTube."
                )
            else:
                st.error(f"Google Trends API returned status code {code}.")
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

    # DISPLAY -------------------------------------------------------------
    if data.empty:
        st.warning("No data found. Try different parameters.")
        return

    if "isPartial" in data.columns:
        data = data.drop(columns=["isPartial"])

    st.subheader("Interest Over Time")
    st.line_chart(data[keyword])

    st.subheader("Raw Data")
    st.dataframe(data)


if __name__ == "__main__":
    main()
