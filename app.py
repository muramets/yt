import streamlit as st
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import re

def main():
    st.title("Google Trends Popularity Index")

    # Input keyword
    keyword = st.text_input("Enter keyword", "lofi study music")

    # Parameters
    timeframe_input = st.text_input(
        "Timeframe (e.g., 'now 7-d' for last 7 days, 'today 1-m' for last month, or 'YYYY-MM-DD YYYY-MM-DD')",
        "now 7-d"
    )
    geo = st.text_input("Region code (leave empty for worldwide, e.g. 'US' or 'RU')", "US")
    platform = st.selectbox(
        "Platform",
        ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
        index=1
    )

    # gprop mapping
    gprop_map = {
        "Web Search": "",
        "YouTube": "youtube",
        "Image Search": "images",
        "News Search": "news",
        "Google Shopping": "froogle",
        "Top Charts": "topsites"
    }
    gprop = gprop_map[platform]

    if keyword:
        # timeframe autocorrection: today X-d -> now X-d
        tf = timeframe_input.strip()
        m = re.match(r"^today (\d+)-d$", tf)
        if m:
            days = m.group(1)
            tf = f"now {days}-d"
            st.info(f"Timeframe autocorrected to '{tf}' for compatibility with the API")

        # Show payload
        st.write("**Payload for debugging:**")
        st.json({
            "kw_list": [keyword],
            "timeframe": tf,
            "geo": geo,
            "gprop": gprop
        })

        with st.spinner("Fetching data from Google Trends..."):
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
                st.error(f"Google Trends API returned status code {status}")
                if hasattr(re_err, 'response'):
                    st.subheader("Response Text")
                    st.code(re_err.response.text or "(empty)")
                return

            except Exception as e:
                st.error(f"Unexpected error: {e}")
                return

            if data.empty:
                st.warning("No data found for this query. Try changing the parameters.")
            else:
                if 'isPartial' in data.columns:
                    data = data.drop(labels=['isPartial'], axis=1)

                st.subheader("Interest Over Time")
                st.line_chart(data[keyword])

                st.subheader("Raw Data")
                st.dataframe(data)

if __name__ == "__main__":
    main()
