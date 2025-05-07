# app.py
import streamlit as st
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import re
import time
import random


@st.cache_data(show_spinner=False, ttl=60 * 60)
def cached_interest(keyword: str, tf: str, geo: str, gprop: str, proxy: str | None):
    """Cached wrapper around fetch_interest (1 hour cache)."""
    return fetch_interest(keyword, tf, geo, gprop, proxy)


def fetch_interest(keyword: str, tf: str, geo: str, gprop: str, proxy: str | None, max_attempts: int = 5):
    """Fetch interest_over_time with retries / backoff / optional proxy."""
    # Pass proxy to requests
    requests_args = None
    if proxy:
        requests_args = {
            "proxies": {
                "https": proxy,
                "http": proxy,
            },
            "headers": {
                "User-Agent": f"Mozilla/5.0 (compatible; PyTrends/5.0; +https://github.com/)",
            },
        }

    attempt = 0
    while True:
        try:
            pytrends = TrendReq(
                hl="en-US",
                tz=0,
                timeout=(10, 30),
                retries=0,
                backoff_factor=0,
                requests_args=requests_args,
            )
            # Random small sleep before request to avoid bursts
            time.sleep(random.uniform(0.5, 1.2))
            pytrends.build_payload([keyword], timeframe=tf, geo=geo, gprop=gprop)
            return pytrends.interest_over_time()
        except ResponseError as err:
            status = getattr(err.response, "status_code", None)
            if status == 429 and attempt < max_attempts - 1:
                sleep_time = 2 ** attempt + random.uniform(0.2, 0.8)
                attempt += 1
                time.sleep(sleep_time)
            else:
                raise
        except Exception:
            raise


def main():
    st.title("Google Trends Popularity Index")

    # --- INPUTS --------------------------------------------------------------
    keyword = st.text_input("Keyword", "lofi study music")

    timeframe_option = st.selectbox(
        "Timeframe",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1,
    )

    if timeframe_option == "Custom":
        st.info(
            "**Custom timeframe format:**\n"
            "• Recent period: `now 7-d`, `now 30-d`, ...\n"
            "• Date range: `YYYY-MM-DD YYYY-MM-DD` (two dates separated by a space)."
        )
        custom_tf = st.text_input(
            "Custom timeframe",
            placeholder="now 7-d or 2025-01-01 2025-05-01",
        )
        tf = custom_tf.strip()
    else:
        tf = {
            "Last 7 days": "now 7-d",
            "Last 30 days": "now 30-d",
            "Last 90 days": "now 90-d",
        }[timeframe_option]

    geo = st.text_input("Region code (optional)", "", help="Country code like 'US'; leave blank for worldwide")

    platform = st.selectbox(
        "Platform",
        ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
        index=0,
    )

    st.markdown("---")
    with st.expander("Advanced settings"):
        proxy = st.text_input(
            "Proxy (optional)",
            placeholder="http://user:pass@host:port",
            help="Set an HTTPS proxy to bypass Google rate‑limit (optional)"
        )
        clear_cache = st.button("⇧ Clear cached results")
        if clear_cache:
            st.cache_data.clear()
            st.success("Cache cleared.")

    submit = st.button("Submit")
    if not submit:
        return

    if timeframe_option == "Custom" and not tf:
        st.error("Please enter a custom timeframe.")
        return

    # Convert 'today X-d' to 'now X-d'
    m_today = re.match(r"today (\d+)-d", tf)
    if m_today:
        tf = f"now {m_today.group(1)}-d"
        st.info(f"Timeframe adjusted to '{tf}'.")

    gprop = {
        "Web Search": "",
        "YouTube": "youtube",
        "Image Search": "images",
        "News Search": "news",
        "Google Shopping": "froogle",
        "Top Charts": "topsites",
    }[platform]

    with st.expander("Debug Payload", expanded=False):
        st.json({"kw_list": [keyword], "timeframe": tf, "geo": geo, "gprop": gprop, "proxy": proxy or "none"})

    # --- FETCH DATA (cached) ----------------------------------------------
    with st.spinner("Fetching data from Google Trends (cached)…"):
        try:
            data = cached_interest(keyword, tf, geo, gprop, proxy)
        except ResponseError as err:
            code = getattr(err.response, "status_code", "unknown")
            if code == 429:
                st.error(
                    "Google returned **429 Too Many Requests** even after retries.\n\n"
                    "• Wait a few minutes and press **Submit** again.\n"
                    "• Try another platform (Web Search vs YouTube) or shorter date range.\n"
                    "• Optionally provide a proxy in *Advanced settings*."
                )
            else:
                st.error(f"Google Trends API returned status {code}.")
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

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
