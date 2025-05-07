# app.py
import streamlit as st
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import re


def main():
    st.title("Google Trends Popularity Index")

    # Query form
    with st.form("query_form"):
        keyword = st.text_input("Keyword", "lofi study music")

        # Timeframe selection
        timeframe_option = st.selectbox(
            "Timeframe",
            ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
            index=1
        )

        # If custom timeframe is selected, show instructions and input
        if timeframe_option == "Custom":
            st.info(
                "**How to enter a custom timeframe:**\n"
                "- For recent periods, type `now 7-d` (last 7 days) or `now 30-d` (last 30 days).\n"
                "- For a specific date range, type two dates in `YYYY-MM-DD YYYY-MM-DD` format, e.g. `2025-01-01 2025-05-01` (Jan 1 to May 1, 2025)."
            )
            custom_tf = st.text_input(
                "Custom timeframe",
                "",
                placeholder="now 7-d or 2025-01-01 2025-05-01"
            )
            tf = custom_tf.strip()
        else:
            # Map presets to API format
            preset_map = {
                "Last 7 days": "now 7-d",
                "Last 30 days": "now 30-d",
                "Last 90 days": "now 90-d"
            }
            tf = preset_map[timeframe_option]

        # Region code input
        geo = st.text_input(
            "Region code",
            "",
            help="Enter a country code (e.g., 'US', 'RU') or leave empty for Worldwide"
        )

        # Platform selection
        platform = st.selectbox(
            "Platform",
            ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
            index=1
        )

        submit = st.form_submit_button("Submit")

    if not submit:
        return

    # Auto-correct 'today X-d' to 'now X-d'
    if tf.startswith("today "):
        days_match = re.match(r"today (\d+)-d", tf)
        if days_match:
            tf = f"now {days_match.group(1)}-d"
            st.info(f"Timeframe adjusted to '{tf}' for API compatibility.")

    # Map platform to gprop
    gprop_map = {
        "Web Search": "",
        "YouTube": "youtube",
        "Image Search": "images",
        "News Search": "news",
        "Google Shopping": "froogle",
        "Top Charts": "topsites"
    }
    gprop = gprop_map[platform]

    # Debug payload expander
    with st.expander("Debug Payload", expanded=False):
        st.json({
            "kw_list": [keyword],
            "timeframe": tf,
            "geo": geo,
            "gprop": gprop
        })

    # Fetch data
    with st.spinner("Fetching data..."):
        pytrends = TrendReq(hl='en-US', tz=0)
        try:
            pytrends.build_payload(kw_list=[keyword], timeframe=tf, geo=geo, gprop=gprop)
            data = pytrends.interest_over_time()
        except ResponseError as err:
            status = getattr(err.response, 'status_code', 'unknown')
            st.error(f"Google Trends API returned status code {status}.")
            if hasattr(err, 'response'):
                st.subheader("API Response Text")
                st.code(err.response.text or "(empty)")
            return
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

    # Display results
    if data.empty:
        st.warning("No data found. Try adjusting your parameters.")
    else:
        if 'isPartial' in data.columns:
            data = data.drop(columns=['isPartial'])

        st.subheader("Interest Over Time")
        st.line_chart(data[keyword])

        st.subheader("Raw Data")
        st.dataframe(data)


if __name__ == "__main__":
    main()
