"""
Navigation sidebar for Structr dashboard
"""

import streamlit as st
from pathlib import Path
import json


def create_sidebar():
    """Create sidebar with navigation and quick stats"""
    
    with st.sidebar:
        st.markdown("## 🧱 Structr")
        st.markdown("*Local-first PDP optimization*")
        
        # Navigation
        st.markdown("### Navigation")
        
        pages = {
            "📊 Overview": "Overview",
            "⚡ Batch Processor": "Batch Processor", 
            "🔍 Audit Manager": "Audit Manager",
            "📦 Bundle Explorer": "Bundle Explorer",
            "📤 Export Center": "Export Center"
        }
        
        selected_page = st.radio(
            "Go to:",
            options=list(pages.keys()),
            label_visibility="collapsed"
        )
        
        # Quick stats
        st.markdown("### Quick Stats")
        
        try:
            stats = get_quick_stats()
            
            st.metric(
                label="Total Bundles",
                value=stats['total_bundles'],
                delta=f"+{stats.get('new_today', 0)} today" if stats.get('new_today', 0) > 0 else None
            )
            
            st.metric(
                label="Avg. Score",
                value=f"{stats['avg_score']:.1f}",
                delta=f"{stats.get('score_trend', 0):+.1f}" if stats.get('score_trend') else None
            )
            
            st.metric(
                label="Flagged",
                value=stats['flagged_count'],
                delta=f"{stats.get('flagged_trend', 0):+d}" if stats.get('flagged_trend') else None
            )
            
        except Exception as e:
            st.warning(f"Could not load stats: {str(e)}")
        
        # Settings
        st.markdown("### Settings")
        
        # Output directory
        new_output_dir = st.text_input(
            "Output Directory",
            value=st.session_state.get('output_dir', 'output'),
            help="Directory containing PDP bundles"
        )
        
        if new_output_dir != st.session_state.get('output_dir'):
            st.session_state.output_dir = new_output_dir
            st.rerun()
        
        # Auto-refresh
        auto_refresh = st.checkbox(
            "Auto-refresh data",
            value=False,
            help="Automatically refresh dashboard data every 30 seconds"
        )
        
        if auto_refresh:
            st.info("Auto-refresh enabled")
        
        # Manual refresh
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Version info
        st.markdown("---")
        st.markdown(
            "<small>**Sprint 2** - Dashboard Interface<br/>"
            "Local-first • CLI-native • Google-compliant</small>",
            unsafe_allow_html=True
        )
    
    return pages[selected_page]


@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_quick_stats():
    """Get quick statistics for sidebar"""
    
    output_dir = Path(st.session_state.get('output_dir', 'output'))
    bundles_dir = output_dir / "bundles"
    
    stats = {
        'total_bundles': 0,
        'avg_score': 0,
        'flagged_count': 0,
        'new_today': 0,
        'score_trend': 0,
        'flagged_trend': 0
    }
    
    if not bundles_dir.exists():
        return stats
    
    # Count bundles and collect scores
    scores = []
    flagged = 0
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            stats['total_bundles'] += 1
            
            # Check audit file
            audit_file = bundle_dir / "audit.json"
            if audit_file.exists():
                try:
                    with open(audit_file, 'r') as f:
                        audit_data = json.load(f)
                    
                    score = audit_data.get('score', 0)
                    scores.append(score)
                    
                    if score < 80:
                        flagged += 1
                        
                except:
                    pass
    
    # Calculate averages
    if scores:
        stats['avg_score'] = sum(scores) / len(scores)
    
    stats['flagged_count'] = flagged
    
    return stats