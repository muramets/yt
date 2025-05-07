# app.py
import streamlit as st
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import re


def main():
    st.title("Google Trends Popularity Index")

    # --- INPUT WIDGETS ---
    keyword = st.text_input("Keyword", "lofi study music")

    timeframe_option = st.selectbox(
        "Timeframe",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1,
    )

    # Show custom timeframe field only when "Custom" is selected
    if timeframe_option == "Custom":
        st.info(
            "**Custom timeframe format:**\n"
            "• Recent periods: `now 7-d` (last 7 days), `now 30-d` (last 30 days).\n"
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
        preset_map = {
            "Last 7 days": "now 7-d",
            "Last 30 days": "now 30-d",
            "Last 90 days": "now 90-d",
        }
        tf = preset_map[timeframe_option]

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

    # Stop if user hasn't clicked Submit yet
    if not submit:
        return

    # --- PROCESS INPUTS ---
    if timeframe_option != "Custom":
        st.info(f"Selected timeframe: **{tf}**")
    else:
        if not tf:
            st.error("Please enter a custom timeframe.")
            return

    # Convert 'today X-d' → 'now X-d' if needed
    if tf.startswith("today "):
        m = re.match(r"today (\d+)-d", tf)
        if m:
            tf = f"now {m.group(1)}-d"
            st.info(f"Timeframe adjusted to '{tf}' for API compatibility.")

    # Map platform to gprop
    gprop_map = {
        "Web Search": "",
        "YouTube": "youtube",
        "Image Search": "images",
        "News Search": "news",
        "Google Shopping": "froogle",
        "Top Charts": "topsites",
    }
    gprop = gprop_map[platform]

    # --- DEBUG PAYLOAD ---
    with st.expander("Debug Payload", expanded=False):
        st.json({"kw_list": [keyword], "timeframe": tf, "geo": geo, "gprop": gprop})

    # --- FETCH DATA ---
    with st.spinner("Fetching data from Google Trends..."):
        pytrends = TrendReq(hl="en-US", tz=0)
        try:
            pytrends.build_payload(
                kw_list=[keyword],
                timeframe=tf,
                geo=geo,
                gprop=gprop,
            )
            data = pytrends.interest_over_time()
        except ResponseError as err:
            code = getattr(err.response, "status_code", "unknown")
            st.error(f"Google Trends API returned status code {code}.")
            if hasattr(err, "response") and err.response is not None:
                st.code(err.response.text or "(empty)")
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

    # --- DISPLAY RESULTS ---
    if data.empty:
        st.warning("No data found for this query. Try adjusting your parameters.")
        return

    if "isPartial" in data.columns:
        data = data.drop(columns=["isPartial"])

    st.subheader("Interest Over Time")
    st.line_chart(data[keyword])

    st.subheader("Raw Data")
    st.dataframe(data)


if __name__ == "__main__":
    main()
