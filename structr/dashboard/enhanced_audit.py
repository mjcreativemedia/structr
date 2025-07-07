"""
Enhanced interactive audit functionality for Structr dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

from config import CONFIG

def show_enhanced_audit_analytics(audit_data):
    """Enhanced interactive audit analytics"""
    
    if not audit_data:
        st.info("No audit data available")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(audit_data)
    
    # Interactive filters
    st.subheader("🔍 Interactive Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score_range = st.slider(
            "Score Range",
            min_value=CONFIG.MIN_SCORE,
            max_value=CONFIG.MAX_SCORE,
            value=(CONFIG.MIN_SCORE, CONFIG.MAX_SCORE),
            help="Filter by audit score range"
        )
    
    with col2:
        brands = ['All'] + list(df['product_brand'].unique()) if 'product_brand' in df.columns else ['All']
        selected_brand = st.selectbox("Brand Filter", brands)
    
    with col3:
        categories = ['All'] + list(df['product_category'].unique()) if 'product_category' in df.columns else ['All']
        selected_category = st.selectbox("Category Filter", categories)
    
    with col4:
        fix_filter = st.selectbox("Fix Status", ["All", "Fixed", "Not Fixed"])
    
    # Apply filters
    filtered_df = apply_audit_filters(df, score_range, selected_brand, selected_category, fix_filter)
    
    # Display filtered results count
    st.info(f"📊 Showing {len(filtered_df)} of {len(df)} bundles")
    
    # Key metrics with deltas
    show_enhanced_metrics(filtered_df, df)
    
    # Interactive charts
    show_interactive_charts(filtered_df)
    
    # Detailed analysis
    show_detailed_analysis(filtered_df)
    
    # Action buttons
    show_audit_action_buttons(filtered_df)


def apply_audit_filters(df, score_range, brand, category, fix_filter):
    """Apply interactive filters to audit data"""
    
    filtered = df.copy()
    
    # Score range filter
    filtered = filtered[
        (filtered['score'] >= score_range[0]) & 
        (filtered['score'] <= score_range[1])
    ]
    
    # Brand filter
    if brand != 'All' and 'product_brand' in filtered.columns:
        filtered = filtered[filtered['product_brand'] == brand]
    
    # Category filter
    if category != 'All' and 'product_category' in filtered.columns:
        filtered = filtered[filtered['product_category'] == category]
    
    # Fix filter
    if fix_filter == 'Fixed':
        filtered = filtered[filtered['fix_count'] > 0]
    elif fix_filter == 'Not Fixed':
        filtered = filtered[filtered['fix_count'] == 0]
    
    return filtered


def show_enhanced_metrics(filtered_df, full_df):
    """Show enhanced metrics with comparisons"""
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        avg_score = filtered_df['score'].mean()
        full_avg = full_df['score'].mean()
        delta = avg_score - full_avg
        st.metric(
            "Average Score",
            f"{avg_score:.1f}",
            delta=f"{delta:+.1f}" if abs(delta) > 0.1 else None
        )
    
    with col2:
        excellent_count = (filtered_df['score'] >= 90).sum()
        excellent_pct = (excellent_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric(
            "Excellent (90+)",
            excellent_count,
            delta=f"{excellent_pct:.1f}%"
        )
    
    with col3:
        flagged_count = (filtered_df['score'] < 80).sum()
        flagged_pct = (flagged_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric(
            "Flagged (<80)",
            flagged_count,
            delta=f"{flagged_pct:.1f}%"
        )
    
    with col4:
        fixed_count = (filtered_df['fix_count'] > 0).sum()
        fixed_pct = (fixed_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric(
            "Fixed",
            fixed_count,
            delta=f"{fixed_pct:.1f}%"
        )
    
    with col5:
        total_issues = sum([
            filtered_df['missing_fields'].apply(len).sum(),
            filtered_df['flagged_issues'].apply(len).sum(),
            filtered_df['schema_errors'].apply(len).sum(),
            filtered_df['metadata_issues'].apply(len).sum()
        ])
        avg_issues = total_issues / len(filtered_df) if len(filtered_df) > 0 else 0
        st.metric(
            "Avg Issues/Bundle",
            f"{avg_issues:.1f}",
            delta=f"Total: {total_issues}"
        )


def show_interactive_charts(df):
    """Show interactive charts and visualizations"""
    
    # Chart selection
    chart_type = st.selectbox(
        "Select Chart Type",
        ["Score Distribution", "Issues Breakdown", "Performance Analysis", "Trend Analysis", "Comparative Analysis"]
    )
    
    if chart_type == "Score Distribution":
        show_score_distribution_chart(df)
    elif chart_type == "Issues Breakdown":
        show_issues_breakdown_chart(df)
    elif chart_type == "Performance Analysis":
        show_performance_analysis_chart(df)
    elif chart_type == "Trend Analysis":
        show_trend_analysis_chart(df)
    elif chart_type == "Comparative Analysis":
        show_comparative_analysis_chart(df)


def show_score_distribution_chart(df):
    """Interactive score distribution chart"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram with color coding
        fig = px.histogram(
            df,
            x='score',
            bins=20,
            title="Score Distribution",
            color_discrete_sequence=['#1f77b4'],
            marginal="box"  # Add box plot on top
        )
        
        # Add vertical lines for thresholds
        fig.add_vline(x=60, line_dash="dash", line_color="orange", annotation_text="Fair Threshold")
        fig.add_vline(x=80, line_dash="dash", line_color="red", annotation_text="Good Threshold")
        fig.add_vline(x=90, line_dash="dash", line_color="green", annotation_text="Excellent Threshold")
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Score categories pie chart
        score_categories = pd.cut(
            df['score'],
            bins=[0, 60, 80, 90, 100],
            labels=['Poor (<60)', 'Fair (60-79)', 'Good (80-89)', 'Excellent (90+)'],
            include_lowest=True
        )
        
        category_counts = score_categories.value_counts()
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=category_counts.index,
            values=category_counts.values,
            marker_colors=['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4'],
            hole=0.3
        )])
        
        fig_pie.update_layout(
            title="Score Categories",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)


def show_issues_breakdown_chart(df):
    """Interactive issues breakdown analysis"""
    
    # Calculate issue counts
    issue_data = []
    
    for _, row in df.iterrows():
        bundle_issues = {
            'Bundle': row['bundle_id'],
            'Product': row.get('product_title', 'Unknown')[:30],
            'Score': row['score'],
            'Missing Fields': len(row.get('missing_fields', [])),
            'Flagged Issues': len(row.get('flagged_issues', [])),
            'Schema Errors': len(row.get('schema_errors', [])),
            'Metadata Issues': len(row.get('metadata_issues', []))
        }
        issue_data.append(bundle_issues)
    
    issues_df = pd.DataFrame(issue_data)
    
    # Chart type selection
    chart_view = st.radio(
        "Issues View",
        ["Stacked Bar", "Heatmap", "Scatter Plot", "Individual Analysis"],
        horizontal=True
    )
    
    if chart_view == "Stacked Bar":
        # Stacked bar chart of issues by bundle
        fig = go.Figure()
        
        issue_types = ['Missing Fields', 'Flagged Issues', 'Schema Errors', 'Metadata Issues']
        colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, issue_type in enumerate(issue_types):
            fig.add_trace(go.Bar(
                x=issues_df['Product'],
                y=issues_df[issue_type],
                name=issue_type,
                marker_color=colors[i]
            ))
        
        fig.update_layout(
            title="Issues Breakdown by Bundle",
            barmode='stack',
            height=500,
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_view == "Heatmap":
        # Heatmap of issues
        heatmap_data = issues_df[issue_types].T
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=issues_df['Product'],
            y=issue_types,
            colorscale='Reds',
            hoverongaps=False
        ))
        
        fig.update_layout(
            title="Issues Heatmap",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_view == "Scatter Plot":
        # Scatter plot: Total issues vs Score
        issues_df['Total Issues'] = issues_df[issue_types].sum(axis=1)
        
        fig = px.scatter(
            issues_df,
            x='Total Issues',
            y='Score',
            size='Total Issues',
            color='Score',
            hover_data=['Product'],
            title="Score vs Total Issues",
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_view == "Individual Analysis":
        # Detailed view for selected bundle
        selected_bundle = st.selectbox(
            "Select Bundle for Detailed Analysis",
            issues_df['Bundle'].tolist(),
            format_func=lambda x: f"{x} - {issues_df[issues_df['Bundle']==x]['Product'].iloc[0]}"
        )
        
        if selected_bundle:
            show_individual_bundle_analysis(df, selected_bundle)


def show_performance_analysis_chart(df):
    """Performance analysis charts"""
    
    if 'generation_time' not in df.columns:
        st.info("Generation time data not available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Score vs Generation Time
        fig = px.scatter(
            df,
            x='generation_time',
            y='score',
            color='fix_count',
            size='score',
            hover_data=['bundle_id', 'product_title'],
            title="Score vs Generation Time",
            labels={'generation_time': 'Generation Time (s)', 'score': 'Audit Score'}
        )
        
        # Add trend line
        fig.add_scatter(
            x=df['generation_time'],
            y=df['generation_time'].rolling(window=5).mean(),
            mode='lines',
            name='Trend',
            line=dict(color='red', dash='dash')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Performance distribution
        performance_df = df.copy()
        performance_df['Performance'] = pd.cut(
            performance_df['score'] / performance_df['generation_time'],
            bins=3,
            labels=['Low', 'Medium', 'High']
        )
        
        perf_counts = performance_df['Performance'].value_counts()
        
        fig_perf = px.pie(
            values=perf_counts.values,
            names=perf_counts.index,
            title="Performance Distribution<br>(Score/Time Ratio)"
        )
        
        st.plotly_chart(fig_perf, use_container_width=True)


def show_trend_analysis_chart(df):
    """Trend analysis over time"""
    
    if 'timestamp' not in df.columns:
        st.info("Timestamp data not available for trend analysis")
        return
    
    # Convert timestamps and create time-based analysis
    df_time = df.copy()
    df_time['timestamp'] = pd.to_datetime(df_time['timestamp'], errors='coerce')
    df_time = df_time.dropna(subset=['timestamp'])
    
    if df_time.empty:
        st.info("No valid timestamp data available")
        return
    
    # Group by time periods
    time_period = st.selectbox("Time Period", ["Hour", "Day", "Week"])
    
    if time_period == "Hour":
        df_time['period'] = df_time['timestamp'].dt.floor('H')
    elif time_period == "Day":
        df_time['period'] = df_time['timestamp'].dt.floor('D')
    else:  # Week
        df_time['period'] = df_time['timestamp'].dt.floor('W')
    
    # Aggregate metrics
    trend_data = df_time.groupby('period').agg({
        'score': ['mean', 'count'],
        'fix_count': 'sum'
    }).reset_index()
    
    trend_data.columns = ['Period', 'Avg Score', 'Bundle Count', 'Total Fixes']
    
    # Create subplot
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Average Score Over Time', 'Bundle Generation Over Time'),
        vertical_spacing=0.1
    )
    
    # Average score trend
    fig.add_trace(
        go.Scatter(
            x=trend_data['Period'],
            y=trend_data['Avg Score'],
            mode='lines+markers',
            name='Avg Score',
            line=dict(color='blue')
        ),
        row=1, col=1
    )
    
    # Bundle count trend
    fig.add_trace(
        go.Bar(
            x=trend_data['Period'],
            y=trend_data['Bundle Count'],
            name='Bundle Count',
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    fig.update_layout(height=600, title_text="Trends Analysis")
    st.plotly_chart(fig, use_container_width=True)


def show_comparative_analysis_chart(df):
    """Comparative analysis between different segments"""
    
    comparison_by = st.selectbox(
        "Compare By",
        ["Brand", "Category", "Fix Status", "Score Range"]
    )
    
    if comparison_by == "Brand" and 'product_brand' in df.columns:
        compare_by_brand(df)
    elif comparison_by == "Category" and 'product_category' in df.columns:
        compare_by_category(df)
    elif comparison_by == "Fix Status":
        compare_by_fix_status(df)
    elif comparison_by == "Score Range":
        compare_by_score_range(df)


def compare_by_brand(df):
    """Compare metrics by brand"""
    
    brand_metrics = df.groupby('product_brand').agg({
        'score': ['mean', 'count', 'std'],
        'fix_count': 'sum'
    }).round(2)
    
    brand_metrics.columns = ['Avg Score', 'Bundle Count', 'Score StdDev', 'Total Fixes']
    brand_metrics = brand_metrics.reset_index()
    
    # Create comparison chart
    fig = px.bar(
        brand_metrics,
        x='product_brand',
        y='Avg Score',
        color='Bundle Count',
        title="Brand Performance Comparison",
        hover_data=['Score StdDev', 'Total Fixes']
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Show detailed table
    st.subheader("Brand Metrics Table")
    st.dataframe(brand_metrics, use_container_width=True)


def compare_by_category(df):
    """Compare metrics by category"""
    
    category_metrics = df.groupby('product_category').agg({
        'score': ['mean', 'count'],
        'generation_time': 'mean' if 'generation_time' in df.columns else lambda x: 0
    }).round(2)
    
    category_metrics.columns = ['Avg Score', 'Bundle Count', 'Avg Generation Time']
    category_metrics = category_metrics.reset_index()
    
    # Radar chart for category comparison
    categories = category_metrics['product_category'].tolist()
    
    fig = go.Figure()
    
    for i, category in enumerate(categories):
        row = category_metrics[category_metrics['product_category'] == category].iloc[0]
        
        fig.add_trace(go.Scatterpolar(
            r=[row['Avg Score'], row['Bundle Count']*10, 100-row['Avg Generation Time'] if row['Avg Generation Time'] else 50],
            theta=['Quality', 'Volume', 'Speed'],
            fill='toself',
            name=category
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="Category Performance Radar"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def compare_by_fix_status(df):
    """Compare fixed vs unfixed bundles"""
    
    df['Fix Status'] = df['fix_count'].apply(lambda x: 'Fixed' if x > 0 else 'Not Fixed')
    
    fix_comparison = df.groupby('Fix Status').agg({
        'score': ['mean', 'count'],
        'missing_fields': lambda x: sum(len(fields) for fields in x),
        'flagged_issues': lambda x: sum(len(issues) for issues in x)
    }).round(2)
    
    fix_comparison.columns = ['Avg Score', 'Count', 'Total Missing Fields', 'Total Flagged Issues']
    fix_comparison = fix_comparison.reset_index()
    
    # Before/after comparison
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Average Score', 'Issue Counts'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Score comparison
    fig.add_trace(
        go.Bar(
            x=fix_comparison['Fix Status'],
            y=fix_comparison['Avg Score'],
            name='Avg Score',
            marker_color=['red', 'green']
        ),
        row=1, col=1
    )
    
    # Issues comparison
    fig.add_trace(
        go.Bar(
            x=fix_comparison['Fix Status'],
            y=fix_comparison['Total Missing Fields'],
            name='Missing Fields',
            marker_color='orange'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=400, title_text="Fixed vs Not Fixed Comparison")
    st.plotly_chart(fig, use_container_width=True)


def show_individual_bundle_analysis(df, bundle_id):
    """Show detailed analysis for individual bundle"""
    
    bundle_data = df[df['bundle_id'] == bundle_id].iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Bundle Metrics")
        st.metric("Audit Score", f"{bundle_data['score']:.1f}/100")
        st.metric("Fix Count", bundle_data.get('fix_count', 0))
        st.metric("Product", bundle_data.get('product_title', 'Unknown'))
        st.metric("Brand", bundle_data.get('product_brand', 'Unknown'))
    
    with col2:
        st.subheader("🔍 Issue Details")
        
        issue_categories = [
            ('Missing Fields', bundle_data.get('missing_fields', [])),
            ('Flagged Issues', bundle_data.get('flagged_issues', [])),
            ('Schema Errors', bundle_data.get('schema_errors', [])),
            ('Metadata Issues', bundle_data.get('metadata_issues', []))
        ]
        
        for category, issues in issue_categories:
            if issues:
                st.markdown(f"**{category} ({len(issues)}):**")
                for issue in issues[:3]:  # Show first 3
                    st.markdown(f"• {issue}")
                if len(issues) > 3:
                    st.markdown(f"... and {len(issues) - 3} more")
            else:
                st.markdown(f"**{category}:** ✅ No issues")


def show_audit_action_buttons(filtered_df):
    """Show action buttons for audit operations"""
    
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Re-audit All", use_container_width=True):
            run_bulk_reaudit(filtered_df['bundle_id'].tolist())
    
    with col2:
        if st.button("🔧 Fix Flagged", use_container_width=True):
            flagged_bundles = filtered_df[filtered_df['score'] < 80]['bundle_id'].tolist()
            run_bulk_fix(flagged_bundles)
    
    with col3:
        if st.button("📊 Export Report", use_container_width=True):
            export_audit_report(filtered_df)
    
    with col4:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


def run_bulk_reaudit(bundle_ids):
    """Run bulk re-audit operation"""
    
    if not bundle_ids:
        st.warning("No bundles selected for re-audit")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    for i, bundle_id in enumerate(bundle_ids):
        status_text.text(f"Re-auditing {bundle_id}...")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'audit', bundle_id
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                results.append({"Bundle": bundle_id, "Status": "✅ Success"})
            else:
                results.append({"Bundle": bundle_id, "Status": "❌ Failed"})
        
        except Exception as e:
            results.append({"Bundle": bundle_id, "Status": f"❌ Error: {str(e)}"})
        
        progress_bar.progress((i + 1) / len(bundle_ids))
    
    # Show results
    st.subheader("Re-audit Results")
    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True)
    
    # Clear cache to refresh data
    st.cache_data.clear()


def run_bulk_fix(bundle_ids):
    """Run bulk fix operation"""
    
    if not bundle_ids:
        st.warning("No bundles selected for fixing")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    for i, bundle_id in enumerate(bundle_ids):
        status_text.text(f"Fixing {bundle_id}...")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'fix', bundle_id
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                results.append({"Bundle": bundle_id, "Status": "✅ Fixed"})
            else:
                results.append({"Bundle": bundle_id, "Status": "❌ Failed"})
        
        except Exception as e:
            results.append({"Bundle": bundle_id, "Status": f"❌ Error: {str(e)}"})
        
        progress_bar.progress((i + 1) / len(bundle_ids))
    
    # Show results
    st.subheader("Fix Results")
    results_df = pd.DataFrame(results)
    st.dataframe(results_df, use_container_width=True)
    
    # Clear cache to refresh data
    st.cache_data.clear()


def export_audit_report(filtered_df):
    """Export filtered audit data as report"""
    
    # Create detailed report
    report_data = []
    
    for _, row in filtered_df.iterrows():
        report_row = {
            'Bundle ID': row['bundle_id'],
            'Product Title': row.get('product_title', 'Unknown'),
            'Brand': row.get('product_brand', 'Unknown'),
            'Category': row.get('product_category', 'Unknown'),
            'Audit Score': row['score'],
            'Missing Fields': len(row.get('missing_fields', [])),
            'Flagged Issues': len(row.get('flagged_issues', [])),
            'Schema Errors': len(row.get('schema_errors', [])),
            'Metadata Issues': len(row.get('metadata_issues', [])),
            'Total Issues': (
                len(row.get('missing_fields', [])) +
                len(row.get('flagged_issues', [])) +
                len(row.get('schema_errors', [])) +
                len(row.get('metadata_issues', []))
            ),
            'Fix Count': row.get('fix_count', 0),
            'Last Audit': row.get('timestamp', ''),
            'Generation Time': row.get('generation_time', 0)
        }
        report_data.append(report_row)
    
    report_df = pd.DataFrame(report_data)
    
    # Convert to CSV
    csv_content = report_df.to_csv(index=False)
    
    # Create download
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"structr_audit_report_{timestamp}.csv"
    
    st.download_button(
        label="📥 Download Audit Report",
        data=csv_content,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )