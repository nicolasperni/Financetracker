import streamlit as st
from db.database import init_db

# Initialize database
init_db()

# Page config
st.set_page_config(
    page_title="Investment Tracker",
    page_icon="chart_with_upwards_trend",
    layout="wide",
)

# Navigation
pages = [
    st.Page("pages/portfolio.py", title="Portfolio", icon=":material/account_balance:", default=True),
    st.Page("pages/transactions.py", title="Transactions", icon=":material/receipt_long:"),
    st.Page("pages/dashboard.py", title="Analysis", icon=":material/analytics:"),
    st.Page("pages/projections.py", title="Projections", icon=":material/trending_up:"),
]

pg = st.navigation(pages)
pg.run()
