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

        # Timeframe selection with help
        timeframe_option = st.selectbox(
            "Timeframe",
            ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
            index=1,
            help="Select a preset range or choose 'Custom' to enter your own period"
        )
        if timeframe_option == "Custom":
            custom_tf = st.text_input(
                "Custom timeframe",
                "",
                placeholder="now 7-d or YYYY-MM-DD YYYY-MM-DD",
                help=(
                    "For recent periods: 'now 7-d' for last 7 days, 'now 30-d' for last 30 days\n"
                    "For exact dates: 'YYYY-MM-DD YYYY-MM-DD', e.g. '2025-01-01 2025-05-01', "
                    "which means from Jan 1, 2025 to May 1, 2025"
                )
            )
            tf = custom_tf.strip()
        else:
            tf_map = {
                "Last 7 days": "now 7-d",
                "Last 30 days": "now 30-d",
                "Last 90 days": "now 90-d"
            }
            tf = tf_map[timeframe_option]

        geo = st.text_input(
            "Region code",
            "",
            help="Enter a country code (e.g., 'US', 'RU') or leave empty for Worldwide"
        )

        platform = st.selectbox(
            "Platform",
            ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
            index=1
        )

        submit = st.form_submit_button("Submit")

    if not submit:
        return

    # Auto-correct 'today X-d' to 'now X-d'
    m = re.match(r"^today (\d+)-d$", tf)
    if m:
        days = m.group(1)
        tf = f"now {days}-d"
        st.info(f"Timeframe adjusted to '{tf}' for compatibility.")

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

    # Debug payload expander in main area
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
            pytrends.build_payload(
                kw_list=[keyword],
                timeframe=tf,
                geo=geo,
                gprop=gprop
            )
            data = pytrends.interest_over_time()
        except ResponseError as re_err:
            status = getattr(re_err.response, 'status_code', 'unknown')
            st.error(f"Google Trends API returned status code {status}.")
            if hasattr(re_err, 'response'):
                st.subheader("API Response Text")
                st.code(re_err.response.text or "(empty)")
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
