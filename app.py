import streamlit as st
from db.database import init_db

# Initialize database
init_db()

# Page config
st.set_page_config(
    page_title="Investment Tracker",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Check authentication
if "user_id" not in st.session_state:
    # Not logged in — show auth page only
    pg = st.navigation([st.Page("pages/auth.py", title="Login", icon=":material/login:")])
    pg.run()
else:
    # Logged in — show app with logout in sidebar
    with st.sidebar:
        st.write(f"Signed in as **{st.session_state['username']}**")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    pages = [
        st.Page("pages/portfolio.py", title="Portfolio", icon=":material/account_balance:", default=True),
        st.Page("pages/transactions.py", title="Transactions", icon=":material/receipt_long:"),
        st.Page("pages/dashboard.py", title="Analysis", icon=":material/analytics:"),
        st.Page("pages/projections.py", title="Projections", icon=":material/trending_up:"),
    ]

    pg = st.navigation(pages)
    pg.run()
