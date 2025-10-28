#fashion_ai_rankings
# fashion_trends_app_free.py
# 100% free edition — Unsplash public endpoints (no API keys) + lightweight local aesthetic scoring
import streamlit as st
import requests
import random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageStat, ImageFilter
import numpy as np

st.set_page_config(page_title="Daily Fashion Trends (Free)", layout="wide")

# -------- CONFIG --------
FASHION_TOPICS = [
    "street style", "fashion outfit", "runway", "OOTD", "minimalist fashion",
    "vintage denim", "boho outfit", "athleisure", "streetwear", "high fashion"
]
MAX_LOOKS_PER_TOPIC = 8

# -------- HELPERS FOR IMAGES (Unsplash public featured endpoint) --------
def unsplash_featured_urls(query, limit=8):
    """
    Use source.unsplash.com featured endpoint which returns a redirect to a curated image.
    This does not require an API key. Note: URLs often redirect to a different content URL each request.
    We'll generate distinct seed queries to increase variety.
    """
    urls = []
    for i in range(limit):
        # add an index to increase chance of distinct images
        q = query.replace(" ", ",")
        url = f"https://source.unsplash.com/800x800/?{q},{i}"
        urls.append(url)
    return urls

def fetch_image_bytes(url, timeout=10):
    """Download image bytes — returns bytes or None."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None

# -------- LIGHTWEIGHT AESTHETIC SCORING (free, CPU-only) --------
def colorfulness_score(img: Image.Image):
    """
    Compute a colorfulness metric similar to Hasler & Süsstrunk (simple approximation).
    Returns 0..100
    """
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    (R, G, B) = arr[..., 0], arr[..., 1], arr[..., 2]
    rg = np.abs(R - G)
    yb = np.abs(0.5 * (R + G) - B)
    std_rg = np.std(rg)
    std_yb = np.std(yb)
    mean_rg = np.mean(rg)
    mean_yb = np.mean(yb)
    # colorfulness measure
    score = np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2)
    # normalize roughly to 0-100
    return float(np.clip((score / 60.0) * 100.0, 0, 100))

def saturation_score(img: Image.Image):
    """Estimate saturation: mean saturation in HSV space (0..100)."""
    hsv = np.asarray(img.convert("HSV")).astype(np.float32)
    s = hsv[..., 1]
    return float(np.clip((np.mean(s) / 255.0) * 100.0, 0, 100))

def contrast_score(img: Image.Image):
    """Contrast approximated by standard deviation of luminance (0..100)."""
    gray = np.asarray(img.convert("L")).astype(np.float32)
    std = np.std(gray)
    return float(np.clip((std / 80.0) * 100.0, 0, 100))

def edge_density_score(img: Image.Image):
    """Edge density approximated by Sobel-like filter via PIL's FIND_EDGES, then fraction > threshold."""
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges).astype(np.float32)
    # proportion of pixels above a threshold
    thresh = 30.0
    prop = np.mean(arr > thresh)
    return float(np.clip(prop * 100.0, 0, 100))

def compute_aesthetic_score(image_bytes):
    """
    Combine multiple simple metrics into a single 0..100 score.
    This is lightweight and deterministic — good as an optional free ranking.
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB").resize((400, 400))
    except Exception:
        return 0.0
    c = colorfulness_score(img)
    s = saturation_score(img)
    co = contrast_score(img)
    e = edge_density_score(img)
    # weights tuned for balanced behavior
    score = 0.35 * c + 0.25 * s + 0.25 * co + 0.15 * e
    return float(np.clip(score, 0, 100))

# -------- UI: user selects topics or enters custom keywords --------
st.title("👗 Daily Fashion Trends — 100% Free Edition")
st.markdown("No API keys required. Images come from Unsplash's public endpoint. Optional lightweight local aesthetic ranking included.")

st.markdown("### Choose topics")
predefined = st.multiselect("Pick some popular themes (or leave blank):", FASHION_TOPICS, default=random.sample(FASHION_TOPICS, k=3))
custom_text = st.text_input("Or enter custom keywords (comma-separated):", placeholder="e.g., Paris street style, vintage denim")
custom_topics = [t.strip() for t in custom_text.split(",") if t.strip()]
selected_topics = predefined + custom_topics
if len(selected_topics) == 0:
    st.info("Select or enter at least one topic to fetch images.")
    st.stop()

limit = st.slider("Max looks per topic", min_value=3, max_value=12, value=6)
enable_scoring = st.checkbox("Enable aesthetic scoring (lightweight local)", value=False)
refresh = st.button("🔄 Refresh images")

if refresh:
    # Force re-fetch by clearing session state
    if "cache_docs" in st.session_state:
        del st.session_state["cache_docs"]

st.markdown(f"**Showing up to {limit} looks per topic — updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
st.write("Tip: images are fetched live from Unsplash's public endpoints. Scoring runs locally in the app (if enabled).")

# -------- Fetch, compute optional scores, and show --------
all_display = []  # list of dicts: {topic, img_url, bytes, score}

for topic in selected_topics:
    st.subheader(f"📸 {topic.title()}")
    # If cached in session, reuse
    key = f"topic::{topic}::limit::{limit}"
    if key in st.session_state:
        images_info = st.session_state[key]
    else:
        urls = unsplash_featured_urls(topic, limit=limit)
        images_info = []
        for u in urls:
            b = fetch_image_bytes(u)
            # if fetch failed, skip or try a simple fallback variant
            if b is None:
                # try without index
                b = fetch_image_bytes(f"https://source.unsplash.com/800x800/?{topic.replace(' ', ',')}")
            if b:
                images_info.append({"url": u, "bytes": b})
            # small polite pause (avoid rapid repeated redirects)
        st.session_state[key] = images_info

    # compute scores (if enabled) and prepare display list
    display_list = []
    for idx, info in enumerate(images_info):
        b = info["bytes"]
        score = None
        if enable_scoring and b:
            score = compute_aesthetic_score(b)
        display_list.append({"topic": topic, "url": info["url"], "bytes": b, "score": score})

    # If scoring enabled: sort by score desc (put None last)
    if enable_scoring:
        display_list.sort(key=lambda x: (x["score"] is None, -(x["score"] or 0)))
    st.write("")  # spacing

    # Show images in a responsive grid (4 columns)
    cols = st.columns(4)
    for i, item in enumerate(display_list):
        col = cols[i % 4]
        with col:
            if item["bytes"]:
                try:
                    img = Image.open(BytesIO(item["bytes"]))
                    # show thumbnail
                    caption = f"{topic} #{i+1}"
                    if enable_scoring and item["score"] is not None:
                        caption += f" — score: {item['score']:.1f}"
                    st.image(img, caption=caption, use_container_width=True)
                except Exception as e:
                    st.write("(image error)")
            else:
                st.write("(no image)")

st.markdown("---")
st.caption("Notes: scoring is a simple free heuristic (colorfulness, saturation, contrast, edge density). "
           "If you want true semantic ranking (CLIP), I can add a CLIP-based optional module — it requires heavier packages and may be slower on CPU.")
