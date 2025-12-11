import streamlit as st

from .logs import print_logs
from thread_manager import stop_all_threads


def shutdown_app():
    stop_all_threads()

    print_logs("Shutting down Streamlit...")
    st.session_state["shutdown"] = True
    st.rerun()