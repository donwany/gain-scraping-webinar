import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from wordcloud import WordCloud
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"
FILE_PATH = "data/94f75ed1ca1e4ddb96454128d8e49988_2025-11-25.csv"

st.title("🧠 AI News Analysis Agent")
st.caption("LLM-powered function calling agent. I can analyze sentiment, topics, trends, categories, or generate a word cloud and more ...")

# -------------------------------------------------------------------
# Load Dataset
# -------------------------------------------------------------------
@st.cache_data
def load_news():
    """Load news dataset from CSV."""
    
    df = pd.read_csv(FILE_PATH)
    df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce").dt.date
    df["content"] = df["content"].astype(str)
    return df


# -------------------------------------------------------------------
# LLM Sentiment Tool
# -------------------------------------------------------------------
def compute_sentiment_llm(text):
    """Compute sentiment polarity using LLM function calling."""
    
    system_msg = {
        "role": "system",
        "content": "Return the sentiment of the text. Output numeric polarity between -1 and 1."
    }
    user_msg = {"role": "user", "content": text}

    sentiment_tool = {
        "name": "sentiment_score",
        "description": "Compute sentiment polarity of a text",
        "parameters": {
            "type": "object",
            "properties": {"score": {"type": "number", "description": "Sentiment polarity (-1 to 1)"}},
            "required": ["score"]
        }
    }

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[system_msg, user_msg],
        functions=[sentiment_tool],
        function_call="auto"
    )

    if completion.choices[0].finish_reason == "function_call":
        args = completion.choices[0].message.function_call.arguments
        parsed = json.loads(args)
        return parsed["score"]

    return 0.0

@st.cache_data
def compute_sentiment_for_all(df):
    """Compute sentiment for all articles in the dataframe."""
    
    df["sentiment"] = df["content"].apply(compute_sentiment_llm)
    return df


def topic_model(df, n_topics=5):
    """Extract topics using NMF."""
    
    vectorizer = TfidfVectorizer(stop_words="english") # Term Frequency-Inverse Document Frequency
    X = vectorizer.fit_transform(df["content"])
    nmf = NMF(n_components=n_topics, random_state=42)  # Non-Negative Matrix Factorization
    nmf.fit(X)
    H = nmf.components_
    vocab = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(H):
        top_words = [vocab[i] for i in topic.argsort()[-10:]]
        topics.append(top_words)
    return topics


def generate_wordcloud(df):
    """Generate a word cloud from the content."""
    
    text = " ".join(df["content"])
    return WordCloud(width=1200, height=800).generate(text)


def positive_negative_tables(df, threshold=0.5):
    """Return positive and negative news articles based on sentiment threshold."""
    
    positive = df[df["sentiment"] > threshold][["published_date", "category", "content", "sentiment"]]
    negative = df[df["sentiment"] < -threshold][["published_date", "category", "content", "sentiment"]]
    return positive, negative


TOOLS = [
    {"name": "plot_sentiment_over_time", "description": "Plot sentiment over time.", "parameters": {"type": "object", "properties": {}}},
    {"name": "get_topics", "description": "Return trending topic words.", "parameters": {"type": "object", "properties": {}}},
    {"name": "show_wordcloud", "description": "Return a word cloud image.", "parameters": {"type": "object", "properties": {}}},
    {"name": "positive_negative_news",
     "description": "Return positive and negative news articles.",
     "parameters": {"type": "object", "properties": {"threshold": {"type": "number"}}, "required": ["threshold"]}}
]


def news_agent(query):
    """AI Agent to decide which tool to call based on user query."""
    
    system_prompt = """
    You are a News Analysis AI Agent. 
    You decide which tool to call based on the user's request.

    Tools available:
    1. plot_sentiment_over_time
    2. get_topics
    3. show_wordcloud
    4. positive_negative_news

    ALWAYS respond with a function call.
    """
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
        functions=TOOLS,
        function_call="auto"
    )
    return completion.choices[0].message


# -------------------------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------------------------
st.subheader("📦 Loaded Dataset")
# Show all columns
pd.set_option("display.max_columns", None)
df = load_news()
st.dataframe(df.head(10))

with st.spinner("Computing please wait!..."):
    df = compute_sentiment_for_all(df)
st.success("Sentiment computed!")


# ================= SIDEBAR FILTERS ================= #
# categories = df["category"].unique().tolist()
categories = sorted(df["category"].dropna().unique().tolist())
category_filter = st.sidebar.multiselect(
    "Filter by Category",
    categories,
    default=categories,
    key="category_filter"
)

# category_filter = st.sidebar.multiselect("Filter by Category", categories, default=categories)
filtered = df[df["category"].isin(category_filter)]


# ================= METRICS ================= #
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Articles", len(filtered))
col2.metric("Avg Sentiment Score", round(filtered["sentiment"].mean(), 3))
col3.metric("Positive %", round((filtered["sentiment"] > 0).mean() * 100, 1))
col4.metric("Negative %", round((filtered["sentiment"] < 0).mean() * 100, 1))

# ================= PLOT: ARTICLES PER CATEGORY ================= #
st.subheader("📌 Number of Articles per Category")
cat_counts = filtered["category"].value_counts()
fig1, ax1 = plt.subplots()
ax1.grid(True, linestyle='--', alpha=0.5)
ax1.set_ylabel("Number of Articles", fontsize=12)
ax1.legend()
plt.xticks(rotation=45)


ax1.bar(cat_counts.index, cat_counts.values)
plt.xticks(rotation=45)
st.pyplot(fig1)



# ================= RADIO FILTER ================= #
st.sidebar.markdown("### 🔍 Quick Filters")

radio_filter = st.sidebar.radio(
    "Choose a filter:",
    [
        # "Show All Articles",
        "Economic-Related Articles",
        "Most Positive Article",
        "Most Negative Article"
    ],
    key="radio_filter"
)

# ================= APPLY RADIO FILTER ================= #
st.subheader(" 🎯 Filtered Results")

display_df = filtered.copy()

# ---- Economic Related ----
if radio_filter == "Economic-Related Articles":
    ECON_KEYWORDS = {
        "Inflation": ["inflation", "cost of living", "price hikes", "cpi", "inflation rate"],
        "Fuel": ["fuel", "petrol", "diesel", "gas price", "fuel prices"],
        "Jobs": ["jobs", "employment", "unemployment", "recruitment", "hiring", "labour"],
        "Stock Market": ["stock", "shares", "market", "bourse", "investors", "equity", "exchange"]
    }

    def keyword_match(df, keywords):
        pattern = "|".join([fr"\b{kw}\b" for kw in keywords])
        return df[df["content"].str.contains(pattern, case=False, regex=True)]

    frames = []
    for topic, words in ECON_KEYWORDS.items():
        frames.append(keyword_match(display_df, words))

    econ_df = pd.concat(frames).drop_duplicates()
    
    st.write(f"**Found {len(econ_df)} Economic-Related Articles**")
    st.dataframe(econ_df)

# ---- MOST POSITIVE ----
elif radio_filter == "Most Positive Article":
    if len(display_df) > 0:
        top = display_df.loc[display_df["sentiment"].idxmax()]
        st.markdown("### 😊 Most Positive Article")
        st.write(f"**Date:** {top['published_date']}  |  **Category:** {top['category']}  |  **Score:** {top['sentiment']:.3f}")
        st.info(top["content"])
    else:
        st.warning("No articles available.")

# ---- MOST NEGATIVE ----
elif radio_filter == "Most Negative Article":
    if len(display_df) > 0:
        bottom = display_df.loc[display_df["sentiment"].idxmin()]
        st.markdown("### 😡 Most Negative Article")
        st.write(f"**Date:** {bottom['published_date']}  |  **Category:** {bottom['category']}  |  **Score:** {bottom['sentiment']:.3f}")
        st.error(bottom["content"])
    else:
        st.warning("No articles available.")

# ---- SHOW ALL ----
else:
    st.dataframe(display_df)


# -------------------------------------------------------------------
# Optional Agent Query
# -------------------------------------------------------------------
st.subheader("🤖 AI Agent")

query = st.text_input(
    "Ask the agent (optional): e.g., 'show positive and negative news', "
    "'trending topics', 'sentiment trends', 'category', 'topics', 'wordcloud', 'trends'"
)

if query.strip() != "":
    agent_response = news_agent(query)

    st.write("🧠 **Agent Decision (Function Called):**")
    st.code(agent_response.function_call.name)

    if agent_response.function_call:
        fn_name = agent_response.function_call.name

        # SENTIMENT OVER TIME
        if fn_name == "plot_sentiment_over_time":
            import matplotlib.dates as mdates
            st.subheader("📈 Sentiment Over Time")
            series = filtered.groupby("published_date")["sentiment"].mean()
            fig, ax = plt.subplots()
            series.plot(ax=ax, marker='o', linestyle='-', color='#1f77b4')
            ax.axhline(0, color='gray', linestyle='--', linewidth=1)
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
            ax.set_ylabel("Sentiment Score", fontsize=12)
            ax.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig)

        # TOPICS
        elif fn_name == "get_topics":
            st.subheader("🔥 Trending Topics")
            topics = topic_model(filtered)
            for i, words in enumerate(topics):
                st.write(f"**Topic {i + 1}:** {', '.join(words)}")

        # WORD CLOUD
        elif fn_name == "show_wordcloud":
            st.subheader("☁ Word Cloud")
            wc = generate_wordcloud(filtered)
            fig, ax = plt.subplots(figsize=(10, 10))
            ax.imshow(wc)
            ax.axis("off")
            st.pyplot(fig)

        # POSITIVE & NEGATIVE NEWS TABLES
        elif fn_name == "positive_negative_news":
            args = json.loads(agent_response.function_call.arguments)
            threshold = args.get("threshold", 0.5)
            st.subheader("😊 Positive News")
            pos, neg = positive_negative_tables(filtered, threshold=threshold)
            st.dataframe(pos)
            st.subheader("😡 Negative News")
            st.dataframe(neg)


# --------------------------
# Footer / Author
# --------------------------
st.markdown(
    """
    <hr>
    <p style='text-align: center; font-size:12px; color:gray;'>
        Developed by Theophilus Siameh —
        LinkedIn: <a href="https://www.linkedin.com/in/theophilus-siameh-793a8626" target="_blank">Profile</a>
    </p>
    """,
    unsafe_allow_html=True
)
