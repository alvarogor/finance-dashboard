import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import io

st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💶",
    layout="wide"
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fb; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #eee;
    }
    h1 { font-weight: 600; color: #1a1a2e; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Category mapping ──────────────────────────────────────────────────────────
CATEGORIES = {
    # Groceries
    "albert heijn": "🛒 Groceries",
    "jumbo": "🛒 Groceries",
    "lidl": "🛒 Groceries",
    "aldi": "🛒 Groceries",
    "bakkerij": "🛒 Groceries",
    # Food & Dining
    "thuisbezorgd": "🍕 Food & Dining",
    "uber eats": "🍕 Food & Dining",
    "cafe": "🍕 Food & Dining",
    "restaurant": "🍕 Food & Dining",
    "dudok": "🍕 Food & Dining",
    "blaak": "🍕 Food & Dining",
    "de unie": "🍕 Food & Dining",
    "mcdonalds": "🍕 Food & Dining",
    # Transport
    "ns trein": "🚆 Transport",
    "shell": "🚆 Transport",
    "bp": "🚆 Transport",
    "uber": "🚆 Transport",
    "ov-chipkaart": "🚆 Transport",
    # Entertainment
    "netflix": "🎬 Entertainment",
    "spotify": "🎬 Entertainment",
    "kinepolis": "🎬 Entertainment",
    "disney": "🎬 Entertainment",
    "steam": "🎬 Entertainment",
    # Shopping
    "h&m": "👗 Shopping",
    "zalando": "👗 Shopping",
    "bol.com": "👗 Shopping",
    "coolblue": "👗 Shopping",
    "zara": "👗 Shopping",
    # Bills & Utilities
    "ziggo": "🏠 Bills & Utilities",
    "rent": "🏠 Bills & Utilities",
    "kpn": "🏠 Bills & Utilities",
    "vodafone": "🏠 Bills & Utilities",
    "eneco": "🏠 Bills & Utilities",
    "nuon": "🏠 Bills & Utilities",
    # Health & Fitness
    "gym": "💪 Health & Fitness",
    "apotheek": "💪 Health & Fitness",
    "huisarts": "💪 Health & Fitness",
    # Income
    "salary": "💰 Income",
    "freelance": "💰 Income",
    "deposit": "💰 Income",
}

def categorize(description: str) -> str:
    desc = description.lower()
    for keyword, category in CATEGORIES.items():
        if keyword in desc:
            return category
    return "❓ Other"

def load_data(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    # Try to find date, description, amount columns
    date_col = next((c for c in df.columns if "date" in c), None)
    desc_col = next((c for c in df.columns if any(k in c for k in ["desc", "name", "merchant", "payee"])), None)
    amt_col  = next((c for c in df.columns if any(k in c for k in ["amount", "amt", "value"])), None)

    if not all([date_col, desc_col, amt_col]):
        st.error("Couldn't detect columns. Make sure your CSV has Date, Description, and Amount columns.")
        st.stop()

    df = df.rename(columns={date_col: "date", desc_col: "description", amt_col: "amount"})
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["category"] = df["description"].apply(categorize)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df.dropna(subset=["amount"])

# ── Header ────────────────────────────────────────────────────────────────────
st.title("💶 Personal Finance Dashboard")
st.markdown("Upload your bank statement CSV to get started.")

# ── File upload ───────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")

if not uploaded:
    st.info("No file uploaded yet — try the sample file below to see the dashboard in action.")
    with open("sample_transactions.csv", "rb") as f:
        st.download_button("⬇️ Download sample CSV", f, "sample_transactions.csv", "text/csv")
    st.stop()

df = load_data(uploaded)
expenses = df[df["amount"] < 0].copy()
expenses["amount_abs"] = expenses["amount"].abs()
income   = df[df["amount"] > 0].copy()

months = sorted(df["month"].unique())
selected_month = st.selectbox("Month", ["All months"] + months, index=len(months))

if selected_month != "All months":
    df_view  = df[df["month"] == selected_month]
    exp_view = expenses[expenses["month"] == selected_month]
    inc_view = income[income["month"] == selected_month]
else:
    df_view  = df
    exp_view = expenses
    inc_view = income

# ── KPI cards ─────────────────────────────────────────────────────────────────
total_income   = inc_view["amount"].sum()
total_expenses = exp_view["amount_abs"].sum()
net_savings    = total_income - total_expenses
savings_rate   = (net_savings / total_income * 100) if total_income > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Income",    f"€{total_income:,.0f}")
col2.metric("💸 Expenses",  f"€{total_expenses:,.0f}")
col3.metric("🏦 Saved",     f"€{net_savings:,.0f}")
col4.metric("📈 Savings rate", f"{savings_rate:.0f}%")

st.divider()

# ── Charts row ────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Spending by category")
    cat_data = exp_view.groupby("category")["amount_abs"].sum().sort_values(ascending=True)
    fig_bar = px.bar(
        cat_data,
        orientation="h",
        color=cat_data.values,
        color_continuous_scale="Blues",
        labels={"value": "Amount (€)", "index": ""},
    )
    fig_bar.update_layout(
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white", paper_bgcolor="white",
        height=320
    )
    fig_bar.update_traces(hovertemplate="€%{x:,.0f}<extra></extra>")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("Spending breakdown")
    fig_pie = px.pie(
        exp_view, values="amount_abs", names="category",
        hole=0.45,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    fig_pie.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white",
        height=320,
        legend=dict(font=dict(size=11))
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}: €%{value:,.0f}<extra></extra>")
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Monthly trend (only useful for "All months" view) ─────────────────────────
if selected_month == "All months" and len(months) > 1:
    st.subheader("Monthly income vs. expenses")
    monthly = df.groupby("month").apply(
        lambda g: pd.Series({
            "Income":   g[g["amount"] > 0]["amount"].sum(),
            "Expenses": g[g["amount"] < 0]["amount"].abs().sum(),
        })
    ).reset_index()
    fig_trend = go.Figure()
    fig_trend.add_bar(x=monthly["month"], y=monthly["Income"],   name="Income",   marker_color="#2196F3")
    fig_trend.add_bar(x=monthly["month"], y=monthly["Expenses"], name="Expenses", marker_color="#90CAF9")
    fig_trend.update_layout(
        barmode="group", plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=0, b=0), height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    fig_trend.update_yaxes(tickprefix="€")
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Transaction table ─────────────────────────────────────────────────────────
st.subheader("Transactions")
search = st.text_input("Search transactions", placeholder="e.g. Netflix, Albert Heijn...")
table = df_view.copy()
if search:
    table = table[table["description"].str.contains(search, case=False, na=False)]

table_display = table[["date", "description", "category", "amount"]].copy()
table_display["date"] = table_display["date"].dt.strftime("%d %b %Y")
table_display["amount"] = table_display["amount"].apply(lambda x: f"€{x:+,.2f}")
table_display.columns = ["Date", "Description", "Category", "Amount"]
st.dataframe(table_display, use_container_width=True, hide_index=True, height=350)
