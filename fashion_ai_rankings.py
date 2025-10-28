import streamlit as st
import requests
import random
import time

# --- CONFIG ---
st.set_page_config(page_title="Daily Fashion Trends", layout="wide")

# --- STYLES ---
st.markdown("""
    <style>
        .stImage img {
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        }
        .topic-header {
            font-size: 1.2rem;
            font-weight: 600;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- UNSPLASH SETTINGS ---
UNSPLASH_ACCESS_KEY = st.secrets.get("UNSPLASH_ACCESS_KEY")

FASHION_TOPICS = [
    "street style", "runway fashion", "outfit of the day",
    "minimalist fashion", "vintage style", "haute couture",
    "sustainable fashion", "summer looks", "winter outfits", "editorial fashion"
]

# --- FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_unsplash_images(query, count=10):
    if not UNSPLASH_ACCESS_KEY:
        st.error("Missing Unsplash API key. Please add UNSPLASH_ACCESS_KEY to your Streamlit Secrets.")
        return []

    url = f"https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": count,
        "client_id": UNSPLASH_ACCESS_KEY,
        "orientation": "portrait"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.warning(f"Unsplash error for '{query}': {response.status_code}")
        return []

    data = response.json()
    results = []
    for r in data.get("results", []):
        results.append({
            "title": r["alt_description"] or "Untitled",
            "image_url": r["urls"]["regular"],
            "author": r["user"]["name"],
            "link": r["links"]["html"]
        })
    return results

# --- HEADER ---
st.title("👗 Daily Fashion Trends")
st.caption(f"Showing 10 looks — updated {time.strftime('%Y-%m-%d %H:%M:%S')}")

# --- USER INPUT ---
st.markdown("### 🎨 Choose your fashion inspirations")

# Predefined topics
predefined = st.multiselect(
    "Select up to 3 predefined styles:",
    FASHION_TOPICS,
    default=random.sample(FASHION_TOPICS, k=3)
)

# Custom keywords
custom_text = st.text_input(
    "Or enter your own keywords (comma-separated):",
    placeholder="e.g., Paris street style, vintage denim, boho outfit"
)

# Parse custom keywords
custom_topics = [t.strip() for t in custom_text.split(",") if t.strip()]

# Combine all topics
selected_topics = predefined + custom_topics

if not selected_topics:
    st.info("👆 Choose at least one theme or enter your own keywords to begin.")
    st.stop()

st.success(f"Fetching trends for {', '.join(selected_topics)}")

# --- DISPLAY ---
cols = st.columns(2)
for i, topic in enumerate(selected_topics):
    with cols[i % 2]:
        st.markdown(f"<div class='topic-header'>{topic.title()}</div>", unsafe_allow_html=True)
        images = fetch_unsplash_images(topic, count=5)
        if not images:
            st.warning(f"No images found for {topic}.")
        else:
            for img in images:
                st.image(img["image_url"], use_container_width=True)
                st.caption(f"📸 {img['author']} — [View on Unsplash]({img['link']})")

st.info("✅ Data from Unsplash (free tier). Updated hourly.")
