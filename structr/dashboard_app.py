#!/usr/bin/env python3
"""
Structr Dashboard - Main Streamlit Application

Visual PDP management and batch processing interface.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import dashboard modules
from dashboard.utils.session_state import init_session_state
from dashboard.utils.navigation import create_sidebar
from dashboard.config import DashboardConfig


def main():
    """Main dashboard application"""
    
    # Configure Streamlit page
    st.set_page_config(
        page_title="Structr Dashboard",
        page_icon="🧱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
    }
    
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2E86AB 0%, #A23B72 100%);
    }
    
    /* Terminal-style theme */
    .terminal-theme {
        background-color: #1a1a1a;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #333;
    }
    
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-error { color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Create sidebar navigation
    page = create_sidebar()
    
    # Main header
    st.markdown('<div class="main-header">🧱 Structr PDP Dashboard</div>', unsafe_allow_html=True)
    
    # Route to appropriate page based on selection
    if page == "Overview":
        from dashboard.pages.overview import show_overview_page
        show_overview_page()
        
    elif page == "Batch Processor":
        from dashboard.pages.batch_processor import show_batch_processor_page
        show_batch_processor_page()
        
    elif page == "Audit Manager":
        from dashboard.pages.audit_manager import show_audit_manager_page
        show_audit_manager_page()
        
    elif page == "Bundle Explorer":
        from dashboard.pages.bundle_explorer import show_bundle_explorer_page
        show_bundle_explorer_page()
        
    elif page == "Export Center":
        from dashboard.pages.export_center import show_export_center_page
        show_export_center_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8rem;'>"
        "🧱 Structr PDP Optimization Engine - Built with ❤️ and Streamlit"
        "</div>", 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()