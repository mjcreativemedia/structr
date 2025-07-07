"""
Session state management for Structr dashboard
"""

import streamlit as st
from pathlib import Path


def init_session_state():
    """Initialize session state variables"""
    
    # Dashboard state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Overview'
    
    # Data refresh tracking
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None
    
    # Batch processing state
    if 'batch_processing' not in st.session_state:
        st.session_state.batch_processing = False
    
    if 'batch_progress' not in st.session_state:
        st.session_state.batch_progress = 0
    
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = []
    
    # File upload state
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    
    # Filter state
    if 'score_filter' not in st.session_state:
        st.session_state.score_filter = (0, 100)
    
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = 'All'
    
    # Selected bundles for bulk operations
    if 'selected_bundles' not in st.session_state:
        st.session_state.selected_bundles = []
    
    # Output directory
    if 'output_dir' not in st.session_state:
        st.session_state.output_dir = str(Path("output").absolute())


def clear_batch_state():
    """Clear batch processing state"""
    st.session_state.batch_processing = False
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []


def add_batch_result(result):
    """Add result to batch processing results"""
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = []
    
    st.session_state.batch_results.append(result)


def update_batch_progress(progress):
    """Update batch processing progress"""
    st.session_state.batch_progress = progress