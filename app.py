# app.py
import streamlit as st
from pytrends.request import TrendReq
import pandas as pd


def main():
    st.title("Google Trends Popularity Index")

    # Ввод ключевого слова
    keyword = st.text_input("Enter keyword", "")
    # Параметры запроса
    timeframe = st.text_input("Timeframe (e.g., 'today 30-d')", "today 30-d")
    geo = st.text_input("Region code (leave empty for worldwide)", "")
    platform = st.selectbox(
        "Platform",
        ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"]
    )

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
        with st.spinner("Fetching data from Google Trends..."):
            pytrends = TrendReq(hl='en-US', tz=0)
            try:
                pytrends.build_payload([keyword], timeframe=timeframe, geo=geo, gprop=gprop)
                data = pytrends.interest_over_time()
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                return

            if data.empty:
                st.warning("No data found for this query.")
            else:
                # Убираем колонку isPartial
                if 'isPartial' in data.columns:
                    data = data.drop(labels=['isPartial'], axis=1)

                st.subheader("Interest Over Time")
                st.line_chart(data[keyword])

                st.subheader("Raw Data")
                st.dataframe(data)


if __name__ == "__main__":
    main()
