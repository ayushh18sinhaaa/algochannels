import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from data.channels import CHANNELS

APP_NAME = "AlgoChannels"
APP_TAGLINE = "Find the best YouTube channels for AI & ML, faster."
APP_OWNER = "Ayush"
SUBMISSIONS_PATH = Path(__file__).parent / "data" / "submissions.json"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_submissions() -> list[dict]:
    if not SUBMISSIONS_PATH.exists():
        return []
    try:
        return json.loads(SUBMISSIONS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_submission(entry: dict) -> None:
    submissions = load_submissions()
    submissions.append(entry)
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_PATH.write_text(json.dumps(submissions, indent=2), encoding="utf-8")


@st.cache_data
def base_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(CHANNELS)
    df["topics_str"] = df["topics"].apply(lambda ts: ", ".join(ts))
    df["source"] = "curated"
    return df


def merged_dataframe() -> pd.DataFrame:
    df = base_dataframe().copy()
    submissions = load_submissions()
    if submissions:
        sub_df = pd.DataFrame(submissions)
        sub_df["topics_str"] = sub_df["topics"].apply(lambda ts: ", ".join(ts))
        sub_df["source"] = "community"
        df = pd.concat([df, sub_df], ignore_index=True)
    return df


def all_topics(df: pd.DataFrame) -> list[str]:
    topics: set[str] = set()
    for ts in df["topics"]:
        topics.update(ts)
    return sorted(topics)


if "favorites" not in st.session_state:
    st.session_state.favorites = set()
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "All"


def toggle_favorite(name: str) -> None:
    favs = st.session_state.favorites
    if name in favs:
        favs.remove(name)
    else:
        favs.add(name)


df = merged_dataframe()

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 50%, #3B82F6 100%);
        padding: 28px 32px;
        border-radius: 18px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 10px 40px rgba(139, 92, 246, 0.25);
    ">
        <div style="font-size: 14px; letter-spacing: 4px; opacity: 0.85; text-transform: uppercase;">
            ⚡ {APP_OWNER}'s curated AI/ML library
        </div>
        <div style="font-size: 44px; font-weight: 800; line-height: 1.1; margin-top: 6px;">
            {APP_NAME}
        </div>
        <div style="font-size: 18px; opacity: 0.92; margin-top: 8px;">
            {APP_TAGLINE}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(f"### ⚡ {APP_NAME}")
    st.caption(f"Curated by {APP_OWNER}")
    st.divider()

    st.subheader("Filters")
    search = st.text_input(
        "Search",
        placeholder="e.g. PyTorch, Karpathy, NLP",
        label_visibility="collapsed",
    )

    levels = st.multiselect(
        "Skill level",
        options=["Beginner", "Intermediate", "Advanced", "All Levels"],
    )

    topic_options = all_topics(df)
    topics = st.multiselect("Topics", options=topic_options)

    min_subs = st.slider(
        "Minimum subscribers (millions)",
        min_value=0.0,
        max_value=12.0,
        value=0.0,
        step=0.1,
    )

    sort_by = st.selectbox(
        "Sort by",
        options=["Recommended", "Subscribers (high to low)", "Name (A-Z)"],
    )

    show_only = st.radio(
        "Show",
        options=["All", "Favorites only", "Community submissions"],
        key="view_mode",
    )

    st.divider()
    st.caption(
        f"⭐ {len(st.session_state.favorites)} favorites  ·  "
        f"📺 {len(df)} channels in total"
    )

filtered = df.copy()

if show_only == "Favorites only":
    filtered = filtered[filtered["name"].isin(st.session_state.favorites)]
elif show_only == "Community submissions":
    filtered = filtered[filtered["source"] == "community"]

if search:
    s = search.lower().strip()
    mask = (
        filtered["name"].str.lower().str.contains(s)
        | filtered["creator"].str.lower().str.contains(s)
        | filtered["topics_str"].str.lower().str.contains(s)
        | filtered["description"].str.lower().str.contains(s)
    )
    filtered = filtered[mask]

if levels:
    filtered = filtered[filtered["level"].isin(levels)]

if topics:
    filtered = filtered[
        filtered["topics"].apply(lambda ts: any(t in ts for t in topics))
    ]

filtered = filtered[filtered["subscribers_millions"] >= min_subs]

if sort_by == "Subscribers (high to low)":
    filtered = filtered.sort_values("subscribers_millions", ascending=False)
elif sort_by == "Name (A-Z)":
    filtered = filtered.sort_values("name", key=lambda s: s.str.lower())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Library", len(df))
c2.metric("Showing", len(filtered))
c3.metric("Favorites", len(st.session_state.favorites))
c4.metric(
    "Total subs",
    f"{filtered['subscribers_millions'].sum():.1f}M",
)

st.divider()

tab_browse, tab_paths, tab_submit, tab_about = st.tabs(
    ["🎯 Browse", "🗺️ Learning paths", "➕ Suggest a channel", "ℹ️ About"]
)

with tab_browse:
    if len(filtered) == 0:
        if show_only == "Favorites only":
            st.info("You haven't favorited any channels yet. Tap the ☆ on a channel to save it.")
        else:
            st.info("No channels match your filters yet. Try loosening them on the left.")
    else:
        cols = st.columns(2)
        for i, (_, row) in enumerate(filtered.iterrows()):
            with cols[i % 2]:
                with st.container(border=True):
                    is_fav = row["name"] in st.session_state.favorites
                    star = "★" if is_fav else "☆"
                    head_l, head_r = st.columns([0.85, 0.15])
                    with head_l:
                        st.subheader(row["name"])
                        st.caption(
                            f"by {row['creator']}  ·  {row['level']}  ·  "
                            f"{row['subscribers_millions']:.2f}M subs"
                            + ("  ·  🌱 community" if row.get("source") == "community" else "")
                        )
                    with head_r:
                        st.button(
                            star,
                            key=f"fav-{row['name']}",
                            help="Favorite",
                            on_click=toggle_favorite,
                            args=(row["name"],),
                            use_container_width=True,
                        )

                    st.markdown(f"**Best for:** {row['best_for']}")
                    st.write(row["description"])
                    st.markdown(" ".join(f"`{t}`" for t in row["topics"]))
                    st.link_button(
                        "Open on YouTube",
                        row["url"],
                        use_container_width=True,
                    )

with tab_paths:
    st.markdown("### Hand-picked learning paths")
    p1, p2 = st.columns(2)
    with p1:
        with st.container(border=True):
            st.markdown("#### 🌱 Total beginner → solid foundation")
            st.markdown(
                "1. **StatQuest with Josh Starmer** — stats and ML algorithm intuitions.\n"
                "2. **3Blue1Brown** — Neural Networks playlist for the math.\n"
                "3. **CodeBasics** or **Daniel Bourke** — write Python and your first models."
            )
        with st.container(border=True):
            st.markdown("#### 🛠️ Building real projects")
            st.markdown(
                "1. **Sentdex** and **Nicholas Renotte** — practical end-to-end builds.\n"
                "2. **Aladdin Persson** — re-implement well-known papers in PyTorch.\n"
                "3. **Hugging Face** — modern open-source LLMs and transformers."
            )
    with p2:
        with st.container(border=True):
            st.markdown("#### 🧠 Go deep on neural networks")
            st.markdown(
                "1. **Andrej Karpathy** — Neural Networks: Zero to Hero (build GPT).\n"
                "2. **Stanford Online** — CS231N (Vision) and CS224N (NLP).\n"
                "3. **Yannic Kilcher** — start reading and reviewing modern papers."
            )
        with st.container(border=True):
            st.markdown("#### 💼 Career and interview prep")
            st.markdown(
                "1. **Krish Naik** — full data science roadmap and mock interviews.\n"
                "2. **DeepLearningAI** — short courses on production ML and LLM apps.\n"
                "3. **Lex Fridman** — long-form context on where the field is going."
            )

with tab_submit:
    st.markdown("### Know a great channel I missed?")
    st.caption("Submit it below — it'll show up under 'Community submissions' for everyone.")

    with st.form("submit_channel", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            in_name = st.text_input("Channel name *")
            in_creator = st.text_input("Creator")
            in_url = st.text_input("YouTube URL *", placeholder="https://www.youtube.com/@...")
            in_subs = st.number_input(
                "Subscribers (in millions)",
                min_value=0.0,
                max_value=200.0,
                value=0.1,
                step=0.1,
            )
        with col_b:
            in_level = st.selectbox(
                "Skill level",
                options=["Beginner", "Intermediate", "Advanced", "All Levels"],
            )
            in_topics = st.text_input(
                "Topics (comma-separated)",
                placeholder="e.g. PyTorch, NLP, Transformers",
            )
            in_best_for = st.text_input("Best for (one line)")
            in_description = st.text_area("Short description", height=110)

        submitter = st.text_input("Your name (optional)")
        submitted = st.form_submit_button("Submit channel", type="primary")

        if submitted:
            if not in_name or not in_url:
                st.error("Channel name and URL are required.")
            elif not in_url.startswith(("http://", "https://")):
                st.error("URL must start with http:// or https://")
            else:
                entry = {
                    "name": in_name.strip(),
                    "creator": (in_creator or "Unknown").strip(),
                    "url": in_url.strip(),
                    "subscribers_millions": float(in_subs),
                    "level": in_level,
                    "topics": [t.strip() for t in in_topics.split(",") if t.strip()] or ["General"],
                    "best_for": in_best_for.strip() or "Community-submitted channel",
                    "description": in_description.strip() or "Submitted by the community.",
                    "submitted_by": (submitter or "Anonymous").strip(),
                    "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                }
                save_submission(entry)
                st.success(f"Thanks! '{entry['name']}' has been added.")
                st.balloons()
                st.cache_data.clear()

with tab_about:
    st.markdown(f"### About {APP_NAME}")
    st.markdown(
        f"""
        **{APP_NAME}** is a hand-picked directory of the best YouTube channels for
        learning Artificial Intelligence and Machine Learning, curated by **{APP_OWNER}**.

        - 🎯 **Filter** by skill level, topic, or subscriber size
        - ⭐ **Favorite** channels you want to come back to
        - 🗺️ Follow a **learning path** based on your goal
        - ➕ **Suggest** a channel and it shows up for everyone

        Built with Python and Streamlit. The channel list lives in
        `data/channels.py` and community submissions in `data/submissions.json` —
        edit those files to customize your own copy.
        """
    )
    st.caption("⚡ AlgoChannels · Made with care for AI/ML learners.")
