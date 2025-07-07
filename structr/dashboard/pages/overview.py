"""
Overview page for Structr dashboard

Provides high-level analytics and quick actions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
from datetime import datetime, timedelta

# Import centralized configuration
from config import StructrConfig as CONFIG


def show_overview_page():
    """Display overview page"""
    
    st.header("📊 Overview")
    st.markdown("Dashboard analytics and system health")
    
    # Load and display overview data
    try:
        overview_data = load_overview_data()
        
        # Key metrics row
        display_key_metrics(overview_data)
        
        # Charts row
        col1, col2 = st.columns(2)
        
        with col1:
            display_score_distribution(overview_data)
            
        with col2:
            display_recent_activity(overview_data)
        
        # Status breakdown
        display_status_breakdown(overview_data)
        
        # Quick actions
        display_quick_actions()
        
    except Exception as e:
        st.error(f"Error loading overview data: {str(e)}")
        st.info("Make sure you have generated some PDP bundles first.")


@st.cache_data(ttl=CONFIG.CACHE_TTL)
def load_overview_data():
    """Load overview data from bundles"""
    
    bundles_dir = CONFIG.get_bundles_dir()
    
    data = {
        'bundles': [],
        'total_count': 0,
        'avg_score': 0,
        'score_distribution': {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0},
        'recent_activity': [],
        'fix_history': []
    }
    
    if not bundles_dir.exists():
        return data
    
    # Process each bundle
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            try:
                bundle_info = process_bundle(bundle_dir)
                if bundle_info:
                    data['bundles'].append(bundle_info)
                    
            except Exception as e:
                st.warning(f"Error processing bundle {bundle_dir.name}: {str(e)}")
    
    # Calculate aggregated metrics
    if data['bundles']:
        data['total_count'] = len(data['bundles'])
        scores = [b['score'] for b in data['bundles'] if b['score'] is not None]
        
        if scores:
            data['avg_score'] = sum(scores) / len(scores)
            
            # Score distribution
            for score in scores:
                if score >= 90:
                    data['score_distribution']['excellent'] += 1
                elif score >= 80:
                    data['score_distribution']['good'] += 1
                elif score >= 60:
                    data['score_distribution']['fair'] += 1
                else:
                    data['score_distribution']['poor'] += 1
        
        # Sort by timestamp for recent activity
        data['bundles'].sort(key=lambda x: x['timestamp'] or '', reverse=True)
        data['recent_activity'] = data['bundles'][:10]
    
    return data


def process_bundle(bundle_dir):
    """Process a single bundle directory"""
    
    bundle_info = {
        'id': bundle_dir.name,
        'path': str(bundle_dir),
        'score': None,
        'status': 'unknown',
        'issues': [],
        'timestamp': None,
        'generation_time': None,
        'fix_count': 0
    }
    
    # Load audit data
    audit_file = bundle_dir / CONFIG.AUDIT_FILENAME
    if audit_file.exists():
        with open(audit_file, 'r') as f:
            audit_data = json.load(f)
        
        bundle_info['score'] = audit_data.get('score', 0)
        bundle_info['issues'] = (
            audit_data.get('missing_fields', []) +
            audit_data.get('flagged_issues', []) +
            audit_data.get('schema_errors', [])
        )
        bundle_info['timestamp'] = audit_data.get('timestamp')
        
        # Determine status using centralized thresholds
        score = bundle_info['score']
        if score >= CONFIG.SCORE_THRESHOLDS['excellent']:
            bundle_info['status'] = 'excellent'
        elif score >= CONFIG.SCORE_THRESHOLDS['good']:
            bundle_info['status'] = 'good'
        elif score >= CONFIG.SCORE_THRESHOLDS['fair']:
            bundle_info['status'] = 'fair'
        else:
            bundle_info['status'] = 'poor'
    
    # Load sync data for generation info
    sync_file = bundle_dir / CONFIG.SYNC_FILENAME
    if sync_file.exists():
        with open(sync_file, 'r') as f:
            sync_data = json.load(f)
        
        output_data = sync_data.get('output', {})
        bundle_info['generation_time'] = output_data.get('generation_time')
        if not bundle_info['timestamp']:
            bundle_info['timestamp'] = output_data.get('timestamp')
    
    # Check fix history
    fix_log_file = bundle_dir / CONFIG.FIX_LOG_FILENAME
    if fix_log_file.exists():
        with open(fix_log_file, 'r') as f:
            fix_logs = json.load(f)
        
        bundle_info['fix_count'] = len(fix_logs) if isinstance(fix_logs, list) else 1
    
    return bundle_info


def display_key_metrics(data):
    """Display key metrics in columns"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Bundles",
            value=data['total_count'],
            help="Total number of generated PDP bundles"
        )
    
    with col2:
        st.metric(
            label="Average Score",
            value=f"{data['avg_score']:.1f}",
            help="Average audit score across all bundles"
        )
    
    with col3:
        flagged_count = data['score_distribution']['fair'] + data['score_distribution']['poor']
        st.metric(
            label="Flagged PDPs",
            value=flagged_count,
            delta=f"{(flagged_count/data['total_count']*100):.1f}%" if data['total_count'] > 0 else "0%",
            help="PDPs with scores below 80 (requiring attention)"
        )
    
    with col4:
        excellent_count = data['score_distribution']['excellent']
        st.metric(
            label="Excellent PDPs", 
            value=excellent_count,
            delta=f"{(excellent_count/data['total_count']*100):.1f}%" if data['total_count'] > 0 else "0%",
            help="PDPs with scores 90+ (production ready)"
        )


def display_score_distribution(data):
    """Display score distribution chart"""
    
    st.subheader("Score Distribution")
    
    if data['total_count'] == 0:
        st.info("No bundles to display")
        return
    
    # Create pie chart
    labels = ['Excellent (90+)', 'Good (80-89)', 'Fair (60-79)', 'Poor (<60)']
    values = [
        data['score_distribution']['excellent'],
        data['score_distribution']['good'],
        data['score_distribution']['fair'],
        data['score_distribution']['poor']
    ]
    colors = ['#28a745', '#17a2b8', '#ffc107', '#dc3545']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker_colors=colors,
        hole=0.4
    )])
    
    fig.update_layout(
        showlegend=True,
        height=300,
        margin=dict(t=20, b=20, l=20, r=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_recent_activity(data):
    """Display recent activity timeline"""
    
    st.subheader("Recent Activity")
    
    if not data['recent_activity']:
        st.info("No recent activity")
        return
    
    # Create timeline chart
    df = pd.DataFrame(data['recent_activity'][:8])  # Last 8 items
    
    if 'timestamp' in df.columns and not df['timestamp'].isna().all():
        # Convert timestamps for plotting
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        
        if not df.empty:
            fig = px.scatter(
                df,
                x='timestamp',
                y='score',
                color='status',
                hover_data=['id'],
                color_discrete_map={
                    'excellent': '#28a745',
                    'good': '#17a2b8', 
                    'fair': '#ffc107',
                    'poor': '#dc3545'
                }
            )
            
            fig.update_layout(
                height=300,
                xaxis_title="Time",
                yaxis_title="Audit Score",
                margin=dict(t=20, b=20, l=20, r=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timestamped activity to display")
    else:
        # Fallback: show recent items as list
        for item in data['recent_activity'][:5]:
            status_color = {
                'excellent': 'status-excellent',
                'good': 'status-good',
                'fair': 'status-fair',
                'poor': 'status-poor'
            }.get(item['status'], '')
            
            st.markdown(
                f"<div class='bundle-card'>"
                f"<strong>{item['id']}</strong><br/>"
                f"<span class='audit-score {status_color}'>Score: {item['score']:.1f}</span><br/>"
                f"<small>Issues: {len(item['issues'])}</small>"
                f"</div>",
                unsafe_allow_html=True
            )


def display_status_breakdown(data):
    """Display detailed status breakdown"""
    
    st.subheader("Status Breakdown")
    
    if data['total_count'] == 0:
        st.info("No bundles to analyze")
        return
    
    # Create DataFrame for display
    status_data = []
    for bundle in data['bundles']:
        status_data.append({
            'Bundle ID': bundle['id'],
            'Score': bundle['score'],
            'Status': bundle['status'].title(),
            'Issues': len(bundle['issues']),
            'Fixes Applied': bundle['fix_count']
        })
    
    df = pd.DataFrame(status_data)
    
    # Apply styling
    def style_score(val):
        if pd.isna(val):
            return ''
        if val >= 90:
            return 'color: #28a745; font-weight: bold'
        elif val >= 80:
            return 'color: #17a2b8; font-weight: bold'
        elif val >= 60:
            return 'color: #ffc107; font-weight: bold'
        else:
            return 'color: #dc3545; font-weight: bold'
    
    styled_df = df.style.applymap(style_score, subset=['Score'])
    
    st.dataframe(styled_df, use_container_width=True, height=300)


def display_quick_actions():
    """Display quick action buttons"""
    
    st.subheader("Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Run Full Audit", use_container_width=True):
            st.switch_page("Audit Manager")
    
    with col2:
        if st.button("🔧 Fix All Flagged", use_container_width=True):
            st.info("Redirecting to Batch Processor...")
            st.switch_page("Batch Processor")
    
    with col3:
        if st.button("📤 Export Catalog", use_container_width=True):
            st.switch_page("Export Center")
    
    with col4:
        if st.button("📁 Browse Bundles", use_container_width=True):
            st.switch_page("Bundle Explorer")