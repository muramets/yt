import streamlit as st
import requests
import pandas as pd
import string
import time
from typing import List, Set


def get_suggestions(base: str, lang: str = "en", country: str = "US", pause: float = 0.1) -> List[str]:
    """Return a sorted list of unique YouTube search suggestions that start with the
    supplied *base* word followed by a space and a‐z characters.

    Parameters
    ----------
    base : str
        Seed phrase (e.g. "music").
    lang : str, optional
        Interface language code passed as *hl* param to Google suggest endpoint.
    country : str, optional
        Region code passed as *gl* param to Google suggest endpoint.
    pause : float, optional
        Delay between outbound requests to avoid 429 errors.
    """
    suggestions: Set[str] = set()
    for ch in string.ascii_lowercase:
        query = f"{base} {ch}"
        url = (
            "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt"
            f"&hl={lang}&gl={country}&q={query}"
        )
        try:
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                # Google returns list; second element holds suggestions
                suggestions.update(data[1])
        except Exception as exc:
            # We silently continue but surface the error to the user later
            st.warning(f"Failed to fetch suggestions for '{query}': {exc}")
        time.sleep(pause)
    return sorted(suggestions)


def main() -> None:
    st.set_page_config(page_title="YouTube Suggest Explorer", page_icon="🎵", layout="wide")

    st.title("🎵 YouTube Suggest Explorer")
    st.markdown(
        "Discover what people are *actually* typing on YouTube. Enter a seed keyword "
        "and we'll scrape YouTube's autocomplete suggestions A‑Z, then show them in "
        "an interactive table you can download as CSV." 
    )

    with st.sidebar:
        st.header("Parameters")
        base = st.text_input("Seed keyword", value="music")
        col1, col2 = st.columns(2)
        with col1:
            lang = st.text_input("Language (hl)", value="en")
        with col2:
            country = st.text_input("Country (gl)", value="US")
        pause = st.slider("Pause between requests (sec)", 0.0, 1.0, 0.1, 0.05)
        submitted = st.button("Fetch suggestions 🚀")

    if submitted:
        if not base.strip():
            st.error("Seed keyword cannot be empty.")
            st.stop()

        with st.spinner("Contacting YouTube autocomplete API …"):
            suggestions = get_suggestions(base.strip(), lang.strip(), country.strip(), pause)

        if suggestions:
            df = pd.DataFrame({"Suggested Query": suggestions})
            st.success(f"Fetched {len(df)} unique suggestions for '{base}'.")
            st.dataframe(df, use_container_width=True)

            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Download CSV",
                data=csv_bytes,
                file_name=f"{base.replace(' ', '_')}_yt_suggestions.csv",
                mime="text/csv",
            )
        else:
            st.info("No suggestions returned. Try a different keyword or region.")


if __name__ == "__main__":
    main()
