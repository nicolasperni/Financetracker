import streamlit as st
from db.auth import create_user, authenticate


def run():
    st.title("Welcome to Investment Tracker")

    tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

    with tab_signin:
        with st.form("signin_form"):
            username = st.text_input("Username", key="signin_user")
            password = st.text_input("Password", type="password", key="signin_pass")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate(username, password)
                    if user:
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

    with tab_signup:
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_user")
            new_password = st.text_input("Password", type="password", key="signup_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if submitted:
                if not new_username or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user_id = create_user(new_username, new_password)
                        st.session_state["user_id"] = user_id
                        st.session_state["username"] = new_username.strip()
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


run()
