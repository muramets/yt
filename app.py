import streamlit as st
import pandas as pd
import requests
import string
import time
from io import StringIO
from pytrends.request import TrendReq

st.set_page_config(page_title="YouTube Suggestion & Google Trends Explorer", layout="wide")

# App title and description
st.title("YouTube Suggestion & Google Trends Explorer")
st.markdown("""
Explore YouTube search suggestions and get popularity data from Google Trends for your keywords.
Perfect for researching niches for YouTube channels!
""")

# Function to get YouTube search suggestions
def get_youtube_suggestions(keyword, prefix=""):
    suggestions = []
    
    if prefix:
        query = f"{keyword} {prefix}"
    else:
        query = keyword
        
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=youtube&ds=yt&q={query}"
        response = requests.get(url)
        data = response.json()
        
        if data and len(data) > 1:
            suggestions = data[1]
    except Exception as e:
        st.error(f"Ошибка при получении подсказок: {e}")
    
    return suggestions

# Function to get all suggestions for a keyword with all letter/number prefixes
def get_all_suggestions(keyword):
    all_suggestions = []
    
    # Create progress bar
    progress = st.progress(0)
    
    # Define prefixes to check (letters and numbers)
    prefixes = list(string.ascii_lowercase) + list(string.digits)
    total_prefixes = len(prefixes)
    
    # Get suggestions for the base keyword without prefix
    base_suggestions = get_youtube_suggestions(keyword)
    for suggestion in base_suggestions:
        if suggestion not in all_suggestions:
            all_suggestions.append(suggestion)
    
    # Get suggestions for each prefix
    for i, prefix in enumerate(prefixes):
        suggestions = get_youtube_suggestions(keyword, prefix)
        for suggestion in suggestions:
            if suggestion not in all_suggestions:
                all_suggestions.append(suggestion)
        
        # Update progress bar
        progress.progress((i + 1) / total_prefixes)
        
        # Show progress in text as well
        st.text(f"Processing prefix '{prefix}' ({i+1}/{total_prefixes})...")
        
        # Slow down requests to avoid rate limiting
        time.sleep(0.2)
    
    progress.empty()
    return all_suggestions

# Function to get Google Trends data
def get_google_trends_data(keywords, timeframe='today 3-m', geo=''):
    pytrends = TrendReq(hl='en-US', tz=0)  # English language, UTC timezone
    
    trends_data = []
    # Process in batches of 5 (Google Trends API limitation)
    progress = st.progress(0)
    total_keywords = len(keywords)
    
    for i in range(0, total_keywords, 5):
        batch = keywords[i:i+5]
        try:
            pytrends.build_payload(batch, cat=0, timeframe=timeframe, geo=geo, gprop='youtube')
            data = pytrends.interest_over_time()
            
            # If we have data
            if not data.empty:
                for keyword in batch:
                    if keyword in data.columns:
                        # Get average interest over time
                        avg_interest = data[keyword].mean()
                        trends_data.append({
                            'Keyword': keyword,
                            'Google Trends Index': round(avg_interest, 2)
                        })
                    else:
                        trends_data.append({
                            'Keyword': keyword,
                            'Google Trends Index': 0
                        })
            else:
                # If no data returned, set to 0
                for keyword in batch:
                    trends_data.append({
                        'Keyword': keyword,
                        'Google Trends Index': 0
                    })
                    
            # Update progress
            progress.progress(min(1.0, (i + len(batch)) / total_keywords))
            
            # Avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            st.warning(f"Error retrieving Google Trends data for batch {i//5 + 1}: {e}")
            # Add entries with 0 for failed batch
            for keyword in batch:
                trends_data.append({
                    'Keyword': keyword,
                    'Google Trends Index': 0
                })
    
    progress.empty()
    return pd.DataFrame(trends_data)

# Main app interface
st.sidebar.header("Settings")
keyword = st.sidebar.text_input("Enter keyword to research:", value="music")

# Time period settings
st.sidebar.subheader("Google Trends Settings")
time_period_options = {
    "Past 7 days": "now 7-d",
    "Past 30 days": "today 1-m",
    "Past 90 days": "today 3-m", 
    "Past 12 months": "today 12-m",
    "Past 5 years": "today 5-y"
}
selected_time_period = st.sidebar.selectbox(
    "Time Period:",
    options=list(time_period_options.keys()),
    index=2  # Default to 90 days
)
timeframe = time_period_options[selected_time_period]

# Region settings
region_options = {
    "Worldwide": "",
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "India": "IN",
    "Germany": "DE",
    "France": "FR",
    "Japan": "JP",
    "Russia": "RU"
}
selected_region = st.sidebar.selectbox(
    "Region:",
    options=list(region_options.keys()),
    index=0  # Default to Worldwide
)
geo = region_options[selected_region]

# Button to get suggestions
if st.sidebar.button("Get YouTube Suggestions"):
    with st.spinner("Fetching YouTube suggestions..."):
        suggestions = get_all_suggestions(keyword)
        
        if suggestions:
            # Create dataframe
            df = pd.DataFrame({
                'Keyword': suggestions,
                'Google Trends Index': [None] * len(suggestions)
            })
            
            # Store in session state
            st.session_state.suggestions_df = df
            st.success(f"Found {len(suggestions)} suggestions!")
        else:
            st.error("Failed to get suggestions. Please try a different keyword.")

# Button to get Google Trends data
if 'suggestions_df' in st.session_state and st.sidebar.button("Get Google Trends Index"):
    with st.spinner("Fetching Google Trends data..."):
        keywords = st.session_state.suggestions_df['Keyword'].tolist()
        trends_df = get_google_trends_data(keywords, timeframe=timeframe, geo=geo)
        
        # Merge with existing dataframe
        st.session_state.suggestions_df = trends_df
        st.success("Google Trends data retrieved!")

# Display results
if 'suggestions_df' in st.session_state:
    st.header("Results")
    
    # Display dataframe
    st.dataframe(st.session_state.suggestions_df)
    
    # Download button
    csv = st.session_state.suggestions_df.to_csv(index=False)
    st.download_button(
        label="Download Data (CSV)",
        data=csv,
        file_name=f"{keyword}_youtube_suggestions.csv",
        mime="text/csv",
    )
    
    # Sort by Google Trends Index if available
    if st.session_state.suggestions_df['Google Trends Index'].notna().any():
        st.subheader("Top 10 Keywords by Popularity")
        top_df = st.session_state.suggestions_df.sort_values(by='Google Trends Index', ascending=False).head(10)
        st.dataframe(top_df)

# Instructions
st.sidebar.markdown("""
## Instructions:
1. Enter a keyword (e.g., "music")
2. Click "Get YouTube Suggestions" to find auto-suggestions
3. Click "Get Google Trends Index" to get popularity data
4. Download the results in CSV format

Note: This application requires the following libraries:
- streamlit
- pandas
- requests
- pytrends

You can install them with:
```
pip install streamlit pandas requests pytrends
```
""")
