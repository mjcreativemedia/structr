"""
Audit Manager page for Structr dashboard

Provides detailed audit analysis, filtering, and reporting capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import subprocess
from datetime import datetime

from config import CONFIG
# Import enhanced audit functionality
from dashboard.enhanced_audit import (
    show_enhanced_audit_analytics,
    show_audit_action_buttons,
    run_bulk_reaudit,
    run_bulk_fix,
    export_audit_report
)
# Import schema validation functionality
from dashboard.schema_validation_ui import show_schema_validation_tab


def show_audit_manager_page():
    """Display audit manager page"""
    
    st.header("🔍 Audit Manager")
    st.markdown("Detailed audit analysis and compliance reporting")
    
    # Load audit data
    audit_data = load_audit_data()
    
    if not audit_data:
        st.info("No audit data found. Generate some PDPs first.")
        return
    
    # Tabs for different audit views - added Schema Validation tab
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Enhanced Analytics", "🔍 Schema Validation", "🔍 Detailed View", "📋 Compliance Report", "⚙️ Run Audit"])
    
    with tab1:
        show_enhanced_audit_analytics(audit_data)
    
    with tab2:
        show_schema_validation_tab()
    
    with tab3:
        show_detailed_audit_view(audit_data)
    
    with tab4:
        show_compliance_report(audit_data)
    
    with tab5:
        show_run_audit()


@st.cache_data(ttl=CONFIG.CACHE_TTL)
def load_audit_data():
    """Load all audit data from bundles"""
    
    output_dir = CONFIG.get_output_dir()
    bundles_dir = CONFIG.get_bundles_dir()
    
    audit_data = []
    
    if not bundles_dir.exists():
        return audit_data
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            audit_file = bundle_dir / CONFIG.AUDIT_FILENAME
            if audit_file.exists():
                try:
                    with open(audit_file, 'r') as f:
                        audit = json.load(f)
                    
                    # Enhance with bundle info
                    audit['bundle_id'] = bundle_dir.name
                    audit['bundle_path'] = str(bundle_dir)
                    
                    # Load sync data for additional context
                    sync_file = bundle_dir / CONFIG.SYNC_FILENAME
                    if sync_file.exists():
                        with open(sync_file, 'r') as f:
                            sync_data = json.load(f)
                        
                        input_data = sync_data.get('input', {})
                        audit['product_title'] = input_data.get('title', 'Unknown')
                        audit['product_brand'] = input_data.get('brand', 'Unknown')
                        audit['product_category'] = input_data.get('category', 'Unknown')
                        
                        output_data = sync_data.get('output', {})
                        audit['generation_time'] = output_data.get('generation_time', 0)
                        audit['model_used'] = output_data.get('model_used', 'Unknown')
                    
                    # Check for fix history
                    fix_log_file = bundle_dir / CONFIG.FIX_LOG_FILENAME
                    if fix_log_file.exists():
                        with open(fix_log_file, 'r') as f:
                            fix_logs = json.load(f)
                        
                        audit['fix_count'] = len(fix_logs) if isinstance(fix_logs, list) else 1
                        audit['last_fix'] = fix_logs[-1] if isinstance(fix_logs, list) and fix_logs else fix_logs
                    else:
                        audit['fix_count'] = 0
                        audit['last_fix'] = None
                    
                    audit_data.append(audit)
                    
                except Exception as e:
                    st.warning(f"Error loading audit for {bundle_dir.name}: {str(e)}")
    
    return audit_data


def show_audit_analytics(audit_data):
    """Show audit analytics and charts"""
    
    st.subheader("Audit Analytics")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(audit_data)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_score = df['score'].mean()
        st.metric("Average Score", f"{avg_score:.1f}")
    
    with col2:
        excellent_count = (df['score'] >= 90).sum()
        st.metric("Excellent (90+)", excellent_count)
    
    with col3:
        flagged_count = (df['score'] < 80).sum()
        st.metric("Flagged (<80)", flagged_count)
    
    with col4:
        fixed_count = (df['fix_count'] > 0).sum()
        st.metric("Fixed Bundles", fixed_count)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Score distribution histogram
        st.subheader("Score Distribution")
        fig_hist = px.histogram(
            df, 
            x='score', 
            bins=20,
            title="Distribution of Audit Scores",
            color_discrete_sequence=['#1f77b4']
        )
        fig_hist.update_layout(height=350)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Issues breakdown
        st.subheader("Issues Breakdown")
        
        # Count all types of issues
        issue_counts = {
            'Missing Fields': df['missing_fields'].apply(len).sum(),
            'Flagged Issues': df['flagged_issues'].apply(len).sum(),
            'Schema Errors': df['schema_errors'].apply(len).sum(),
            'Metadata Issues': df['metadata_issues'].apply(len).sum()
        }
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(issue_counts.keys()),
            values=list(issue_counts.values()),
            marker_colors=['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        )])
        fig_pie.update_layout(height=350, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Score vs Generation Time scatter
    if 'generation_time' in df.columns:
        st.subheader("Score vs Generation Time")
        fig_scatter = px.scatter(
            df,
            x='generation_time',
            y='score',
            color='fix_count',
            size='score',
            hover_data=['bundle_id', 'product_title'],
            title="Relationship between Generation Time and Quality"
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Brand/Category analysis
    if 'product_brand' in df.columns and 'product_category' in df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Average Score by Brand")
            brand_scores = df.groupby('product_brand')['score'].mean().sort_values(ascending=False)
            if len(brand_scores) > 0:
                fig_brand = px.bar(
                    x=brand_scores.values,
                    y=brand_scores.index,
                    orientation='h',
                    title="Brand Performance"
                )
                fig_brand.update_layout(height=300)
                st.plotly_chart(fig_brand, use_container_width=True)
        
        with col2:
            st.subheader("Score Distribution by Category")
            if len(df['product_category'].unique()) > 1:
                fig_cat = px.box(
                    df,
                    x='product_category',
                    y='score',
                    title="Category Performance"
                )
                fig_cat.update_layout(height=300)
                fig_cat.update_xaxes(tickangle=45)
                st.plotly_chart(fig_cat, use_container_width=True)


def show_detailed_audit_view(audit_data):
    """Show detailed audit view with filtering"""
    
    st.subheader("Detailed Audit View")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score_range = st.slider(
            "Score Range",
            min_value=0,
            max_value=100,
            value=(0, 100),
            help="Filter by audit score range"
        )
    
    with col2:
        has_issues = st.selectbox(
            "Issue Status",
            ["All", "Has Issues", "No Issues"],
            help="Filter by presence of issues"
        )
    
    with col3:
        fix_status = st.selectbox(
            "Fix Status", 
            ["All", "Fixed", "Not Fixed"],
            help="Filter by fix application status"
        )
    
    with col4:
        sort_by = st.selectbox(
            "Sort By",
            ["Score (Low to High)", "Score (High to Low)", "Bundle ID", "Last Updated"],
            help="Choose sorting order"
        )
    
    # Apply filters
    filtered_data = filter_audit_data(audit_data, score_range, has_issues, fix_status)
    
    if not filtered_data:
        st.info("No data matches the current filters")
        return
    
    # Sort data
    filtered_data = sort_audit_data(filtered_data, sort_by)
    
    st.markdown(f"**Showing {len(filtered_data)} of {len(audit_data)} bundles**")
    
    # Display detailed cards
    for audit in filtered_data[:20]:  # Show first 20
        show_audit_card(audit)
    
    if len(filtered_data) > 20:
        st.info(f"... and {len(filtered_data) - 20} more. Use filters to narrow down.")
    
    # Add enhanced action buttons for filtered data
    st.markdown("---")
    show_audit_action_buttons(pd.DataFrame(filtered_data))


def show_audit_card(audit):
    """Display a detailed audit card"""
    
    score = audit.get('score', 0)
    
    # Determine status color
    if score >= 90:
        status_color = "#28a745"
        status_text = "Excellent"
    elif score >= 80:
        status_color = "#17a2b8"
        status_text = "Good"
    elif score >= 60:
        status_color = "#ffc107"
        status_text = "Fair"
    else:
        status_color = "#dc3545"
        status_text = "Poor"
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(
                f"**{audit.get('bundle_id', 'Unknown')}** - "
                f"{audit.get('product_title', 'Unknown Product')}"
            )
            
            if audit.get('product_brand'):
                st.markdown(f"*Brand: {audit['product_brand']}*")
        
        with col2:
            st.markdown(
                f"<div style='text-align: center; color: {status_color}; font-weight: bold; font-size: 1.2em;'>"
                f"{score:.1f}/100<br/><small>{status_text}</small></div>",
                unsafe_allow_html=True
            )
        
        with col3:
            if audit.get('fix_count', 0) > 0:
                st.markdown("🔧 **Fixed**")
            
            # Quick fix button
            if score < 80:
                if st.button(f"Fix {audit['bundle_id']}", key=f"fix_{audit['bundle_id']}"):
                    run_single_fix(audit['bundle_id'])
        
        # Issue details
        issues = []
        issues.extend(audit.get('missing_fields', []))
        issues.extend(audit.get('flagged_issues', []))
        issues.extend(audit.get('schema_errors', []))
        issues.extend(audit.get('metadata_issues', []))
        
        if issues:
            with st.expander(f"View Issues ({len(issues)})"):
                for issue in issues:
                    st.markdown(f"• {issue}")
        
        # Additional info
        if audit.get('generation_time'):
            st.markdown(f"*Generated in {audit['generation_time']:.2f}s*")
        
        st.markdown("---")


def show_compliance_report(audit_data):
    """Show compliance report"""
    
    st.subheader("📋 Compliance Report")
    
    # Overall compliance metrics
    df = pd.DataFrame(audit_data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        compliance_rate = (df['score'] >= 80).mean() * 100
        st.metric("Compliance Rate", f"{compliance_rate:.1f}%", help="Percentage with score ≥ 80")
    
    with col2:
        excellence_rate = (df['score'] >= 90).mean() * 100
        st.metric("Excellence Rate", f"{excellence_rate:.1f}%", help="Percentage with score ≥ 90")
    
    with col3:
        avg_issues = df[['missing_fields', 'flagged_issues', 'schema_errors', 'metadata_issues']].apply(len).sum(axis=1).mean()
        st.metric("Avg Issues per PDP", f"{avg_issues:.1f}")
    
    # Most common issues
    st.subheader("Most Common Issues")
    
    all_issues = []
    for audit in audit_data:
        all_issues.extend(audit.get('missing_fields', []))
        all_issues.extend(audit.get('flagged_issues', []))
        all_issues.extend(audit.get('schema_errors', []))
        all_issues.extend(audit.get('metadata_issues', []))
    
    if all_issues:
        # Count issue frequency
        issue_counts = pd.Series(all_issues).value_counts().head(10)
        
        fig_issues = px.bar(
            x=issue_counts.values,
            y=issue_counts.index,
            orientation='h',
            title="Top 10 Most Common Issues"
        )
        fig_issues.update_layout(height=400)
        st.plotly_chart(fig_issues, use_container_width=True)
    else:
        st.success("🎉 No common issues found!")
    
    # Compliance by category/brand
    if 'product_brand' in df.columns:
        st.subheader("Compliance by Brand")
        
        brand_compliance = df.groupby('product_brand').agg({
            'score': ['mean', 'count'],
            'bundle_id': 'count'
        }).round(2)
        
        brand_compliance.columns = ['Avg Score', 'Bundle Count', 'Total']
        brand_compliance['Compliance Rate'] = ((df.groupby('product_brand')['score'] >= 80).mean() * 100).round(1)
        
        st.dataframe(brand_compliance, use_container_width=True)
    
    # Export compliance report
    if st.button("📥 Export Compliance Report", use_container_width=True):
        export_compliance_report(audit_data)


def show_run_audit():
    """Interface for running new audits"""
    
    st.subheader("⚙️ Run Audit")
    
    # Audit options
    col1, col2 = st.columns(2)
    
    with col1:
        audit_scope = st.radio(
            "Audit Scope",
            ["All bundles", "Specific bundle", "Bundles below score threshold"]
        )
    
    with col2:
        export_results = st.checkbox(
            "Export results to CSV",
            value=True,
            help="Save audit results to CSV file"
        )
    
    # Scope-specific options
    if audit_scope == "Specific bundle":
        # Load available bundles
        output_dir = Path(st.session_state.get('output_dir', 'output'))
        bundles_dir = output_dir / "bundles"
        
        if bundles_dir.exists():
            available_bundles = [d.name for d in bundles_dir.iterdir() if d.is_dir()]
            
            if available_bundles:
                selected_bundle = st.selectbox(
                    "Select Bundle",
                    available_bundles
                )
            else:
                st.warning("No bundles found")
                return
        else:
            st.warning("Bundles directory not found")
            return
    
    elif audit_scope == "Bundles below score threshold":
        score_threshold = st.slider(
            "Score Threshold",
            min_value=0,
            max_value=100,
            value=80,
            help="Audit bundles with scores below this threshold"
        )
    
    # Run audit button
    if st.button("🔍 Run Audit", type="primary", use_container_width=True):
        run_audit_operation(audit_scope, export_results, locals())


def filter_audit_data(audit_data, score_range, has_issues, fix_status):
    """Filter audit data based on criteria"""
    
    filtered = audit_data.copy()
    
    # Score range filter
    filtered = [
        a for a in filtered 
        if score_range[0] <= a.get('score', 0) <= score_range[1]
    ]
    
    # Issues filter
    if has_issues == "Has Issues":
        filtered = [
            a for a in filtered
            if (len(a.get('missing_fields', [])) + 
                len(a.get('flagged_issues', [])) + 
                len(a.get('schema_errors', [])) + 
                len(a.get('metadata_issues', []))) > 0
        ]
    elif has_issues == "No Issues":
        filtered = [
            a for a in filtered
            if (len(a.get('missing_fields', [])) + 
                len(a.get('flagged_issues', [])) + 
                len(a.get('schema_errors', [])) + 
                len(a.get('metadata_issues', []))) == 0
        ]
    
    # Fix status filter
    if fix_status == "Fixed":
        filtered = [a for a in filtered if a.get('fix_count', 0) > 0]
    elif fix_status == "Not Fixed":
        filtered = [a for a in filtered if a.get('fix_count', 0) == 0]
    
    return filtered


def sort_audit_data(audit_data, sort_by):
    """Sort audit data"""
    
    if sort_by == "Score (Low to High)":
        return sorted(audit_data, key=lambda x: x.get('score', 0))
    elif sort_by == "Score (High to Low)":
        return sorted(audit_data, key=lambda x: x.get('score', 0), reverse=True)
    elif sort_by == "Bundle ID":
        return sorted(audit_data, key=lambda x: x.get('bundle_id', ''))
    elif sort_by == "Last Updated":
        return sorted(audit_data, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return audit_data


def run_single_fix(bundle_id):
    """Run fix for a single bundle"""
    
    try:
        with st.spinner(f"Fixing {bundle_id}..."):
            result = subprocess.run([
                'python', 'cli.py', 'fix', bundle_id
            ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            st.success(f"✅ Fixed {bundle_id}")
            # Clear cache to refresh data
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"❌ Failed to fix {bundle_id}: {result.stderr}")
    
    except Exception as e:
        st.error(f"Error fixing {bundle_id}: {str(e)}")


def run_audit_operation(audit_scope, export_results, scope_vars):
    """Run audit operation based on scope"""
    
    try:
        cmd = ['python', 'cli.py', 'audit']
        
        if audit_scope == "All bundles":
            cmd.append('--all')
        elif audit_scope == "Specific bundle":
            cmd.append(scope_vars['selected_bundle'])
        elif audit_scope == "Bundles below score threshold":
            cmd.extend(['--all', '--min-score', str(scope_vars['score_threshold'])])
        
        if export_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"audit_report_{timestamp}.csv"
            cmd.extend(['--export', export_file])
        
        with st.spinner("Running audit..."):
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            st.success("✅ Audit completed successfully")
            
            # Show results
            if result.stdout:
                st.text_area("Audit Results", result.stdout, height=200)
            
            # Clear cache to refresh data
            st.cache_data.clear()
            
            if export_results:
                st.info(f"📁 Results exported to {export_file}")
        else:
            st.error(f"❌ Audit failed: {result.stderr}")
    
    except Exception as e:
        st.error(f"Error running audit: {str(e)}")


def export_compliance_report(audit_data):
    """Export compliance report to CSV"""
    
    try:
        df = pd.DataFrame(audit_data)
        
        # Prepare export data
        export_data = []
        for audit in audit_data:
            issues_count = (
                len(audit.get('missing_fields', [])) +
                len(audit.get('flagged_issues', [])) +
                len(audit.get('schema_errors', [])) +
                len(audit.get('metadata_issues', []))
            )
            
            export_data.append({
                'Bundle ID': audit.get('bundle_id', ''),
                'Product Title': audit.get('product_title', ''),
                'Brand': audit.get('product_brand', ''),
                'Category': audit.get('product_category', ''),
                'Audit Score': audit.get('score', 0),
                'Total Issues': issues_count,
                'Missing Fields': len(audit.get('missing_fields', [])),
                'Flagged Issues': len(audit.get('flagged_issues', [])),
                'Schema Errors': len(audit.get('schema_errors', [])),
                'Metadata Issues': len(audit.get('metadata_issues', [])),
                'Fix Count': audit.get('fix_count', 0),
                'Compliant (≥80)': 'Yes' if audit.get('score', 0) >= 80 else 'No',
                'Excellent (≥90)': 'Yes' if audit.get('score', 0) >= 90 else 'No',
                'Last Audit': audit.get('timestamp', '')
            })
        
        export_df = pd.DataFrame(export_data)
        
        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_report_{timestamp}.csv"
        export_df.to_csv(filename, index=False)
        
        st.success(f"📁 Compliance report exported to {filename}")
        
        # Show download button
        with open(filename, 'rb') as f:
            st.download_button(
                label="📥 Download Report",
                data=f.read(),
                file_name=filename,
                mime='text/csv'
            )
    
    except Exception as e:
        st.error(f"Error exporting report: {str(e)}")