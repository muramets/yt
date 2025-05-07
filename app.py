# app.py
import streamlit as st
from pytrends.request import TrendReq
import pandas as pd


def main():
    st.title("Google Trends Popularity Index")

    # Ввод ключевого слова
    keyword = st.text_input("Enter keyword", "lofi study music")

    # Параметры запроса с пояснениями
    timeframe = st.text_input(
        "Timeframe (e.g., 'today 7-d' for last 7 days, 'today 30-d' for last 30 days, or 'YYYY-MM-DD YYYY-MM-DD')",
        "today 7-d"
    )
    geo = st.text_input(
        "Region code (leave empty for worldwide, e.g. 'US' or 'RU')",
        "US"
    )
    platform = st.selectbox(
        "Platform",
        ["Web Search", "YouTube", "Image Search", "News Search", "Google Shopping", "Top Charts"],
        index=1
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
        st.write("**Payload for debugging:**")
        st.json({
            "kw_list": [keyword],
            "timeframe": timeframe,
            "geo": geo,
            "gprop": gprop
        })

        with st.spinner("Fetching data from Google Trends..."):
            pytrends = TrendReq(hl='en-US', tz=0)
            try:
                # Попытка создания payload и запроса
                pytrends.build_payload(
                    kw_list=[keyword],
                    timeframe=timeframe,
                    geo=geo,
                    gprop=gprop
                )
                data = pytrends.interest_over_time()

            except Exception as e:
                # Вывод подробностей ошибки для диагностики
                st.error(f"Ошибка запроса: {e}")
                st.exception(e)
                return

            if data.empty:
                st.warning("No data found for this query. Попробуйте изменить параметры.")
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

# requirements.txt
streamlit
pytrends
pandas
