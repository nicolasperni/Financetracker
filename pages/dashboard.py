import streamlit as st
from analysis.registry import auto_discover, get_all_analyses

# Trigger auto-discovery of all analysis modules
auto_discover()


def run():
    st.title("Analysis Dashboard")

    analyses = get_all_analyses()
    if not analyses:
        st.warning("No analyses registered.")
        return

    # Let user select which analyses to show
    all_names = [a.name for a in analyses]
    selected = st.multiselect(
        "Select analyses to display",
        options=all_names,
        default=all_names,
    )

    for analysis in analyses:
        if analysis.name in selected:
            with st.expander(f"**{analysis.name}**", expanded=True):
                if analysis.description:
                    st.caption(analysis.description)
                try:
                    analysis.func()
                except Exception as e:
                    st.error(f"Error rendering analysis: {e}")


run()
