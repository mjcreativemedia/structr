"""
Compliance Monitoring Dashboard UI for Structr

Provides real-time monitoring, trends, alerts, and configuration
for schema compliance tracking.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

from config import CONFIG
from monitoring.compliance_monitor import (
    get_compliance_monitor, ComplianceRecord, Alert, AlertRule, 
    AlertSeverity, ComplianceStatus
)


def show_compliance_monitoring_page():
    """Display the main compliance monitoring page"""
    
    st.header("📊 Schema Compliance Monitoring")
    st.markdown("Real-time monitoring and alerting for Product Schema compliance")
    
    # Get monitor instance
    monitor = get_compliance_monitor()
    
    # Control tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Dashboard", 
        "🔔 Alerts", 
        "📊 Trends", 
        "⚙️ Configuration", 
        "📋 History"
    ])
    
    with tab1:
        show_monitoring_dashboard(monitor)
    
    with tab2:
        show_alerts_management(monitor)
    
    with tab3:
        show_compliance_trends(monitor)
    
    with tab4:
        show_monitoring_configuration(monitor)
    
    with tab5:
        show_compliance_history(monitor)


def show_monitoring_dashboard(monitor):
    """Show the main monitoring dashboard"""
    
    st.subheader("📊 Real-time Compliance Dashboard")
    
    # Summary metrics
    summary = monitor.get_compliance_summary(days=1)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Products",
            summary["total_bundles"],
            help="Total number of monitored products"
        )
    
    with col2:
        eligible_rate = summary.get("google_eligible_rate", 0)
        st.metric(
            "Google Eligible",
            f"{summary['google_eligible']}/{summary['total_bundles']}",
            delta=f"{eligible_rate:.1f}%",
            help="Products eligible for Google Rich Results"
        )
    
    with col3:
        avg_score = summary.get("avg_compliance_score", 0)
        score_color = "normal"
        if avg_score >= CONFIG.SCORE_THRESHOLDS['excellent']:
            score_color = "normal"
        elif avg_score >= CONFIG.SCORE_THRESHOLDS['good']:
            score_color = "normal"
        else:
            score_color = "inverse"
        
        st.metric(
            "Avg Compliance",
            f"{avg_score:.1f}%",
            help="Average compliance score across all products"
        )
    
    with col4:
        schema_rate = summary.get("schema_found_rate", 0)
        st.metric(
            "Schema Found",
            f"{summary['schema_found']}/{summary['total_bundles']}",
            delta=f"{schema_rate:.1f}%",
            help="Products with detectable schema"
        )
    
    with col5:
        critical_alerts = summary.get("critical_alerts", 0)
        total_alerts = summary.get("total_active_alerts", 0)
        alert_delta = f"+{total_alerts - critical_alerts} other" if total_alerts > critical_alerts else None
        
        st.metric(
            "Critical Alerts",
            critical_alerts,
            delta=alert_delta,
            delta_color="inverse" if critical_alerts > 0 else "normal",
            help="Active critical alerts requiring attention"
        )
    
    # Status distribution chart
    st.markdown("### 📊 Compliance Status Distribution")
    
    status_dist = summary.get("status_distribution", {})
    if status_dist:
        
        # Create status chart with proper colors
        status_labels = []
        status_values = []
        status_colors = []
        
        for status, count in status_dist.items():
            status_labels.append(status.replace('_', ' ').title())
            status_values.append(count)
            
            # Map status to colors
            if status in ['excellent']:
                status_colors.append(CONFIG.COLORS['success'])
            elif status in ['good']:
                status_colors.append(CONFIG.COLORS['info'])
            elif status in ['fair']:
                status_colors.append(CONFIG.COLORS['warning'])
            elif status in ['poor', 'critical']:
                status_colors.append(CONFIG.COLORS['danger'])
            else:
                status_colors.append(CONFIG.COLORS['secondary'])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.pie(
                values=status_values,
                names=status_labels,
                title="Product Compliance Status",
                color_discrete_sequence=status_colors
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Status Breakdown:**")
            for status, count in status_dist.items():
                percentage = (count / summary["total_bundles"]) * 100
                st.markdown(f"• **{status.replace('_', ' ').title()}**: {count} ({percentage:.1f}%)")
    else:
        st.info("No compliance data available")
    
    # Recent alerts
    st.markdown("### 🔔 Recent Alerts")
    
    recent_alerts = [alert for alert in monitor.active_alerts if not alert.resolved][-5:]
    
    if recent_alerts:
        for alert in reversed(recent_alerts):  # Show newest first
            severity_color = {
                AlertSeverity.CRITICAL: "error",
                AlertSeverity.HIGH: "warning", 
                AlertSeverity.MEDIUM: "info",
                AlertSeverity.LOW: "success"
            }.get(alert.severity, "info")
            
            time_ago = datetime.now() - alert.timestamp
            time_str = f"{int(time_ago.total_seconds() // 3600)}h ago" if time_ago.total_seconds() > 3600 else f"{int(time_ago.total_seconds() // 60)}m ago"
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if severity_color == "error":
                        st.error(f"🚨 **{alert.title}**")
                    elif severity_color == "warning":
                        st.warning(f"⚠️ **{alert.title}**")
                    else:
                        st.info(f"💡 **{alert.title}**")
                    
                    st.caption(alert.message)
                
                with col2:
                    st.text(f"{alert.severity.value.upper()}")
                    st.caption(time_str)
                
                with col3:
                    if not alert.acknowledged:
                        if st.button("✓ Ack", key=f"ack_{alert.id}"):
                            monitor.acknowledge_alert(alert.id)
                            st.rerun()
                    else:
                        st.text("✓ Ack'd")
    else:
        st.success("🎉 No active alerts")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Run Check Now", type="primary", use_container_width=True):
            with st.spinner("Running compliance check..."):
                from validators.schema_validator import validate_all_bundles
                results = validate_all_bundles()
                monitor.record_compliance(results)
                st.success(f"✅ Checked {len(results)} products")
                st.rerun()
    
    with col2:
        if st.button("📊 View Trends", use_container_width=True):
            st.session_state.monitoring_tab = "trends"
            st.rerun()
    
    with col3:
        if st.button("🔔 Manage Alerts", use_container_width=True):
            st.session_state.monitoring_tab = "alerts"  
            st.rerun()
    
    with col4:
        monitoring_status = "Running" if monitor.config.get("monitoring_enabled", False) else "Stopped"
        status_color = "success" if monitoring_status == "Running" else "error"
        
        if monitoring_status == "Running":
            if st.button("⏸️ Stop Monitor", use_container_width=True):
                monitor.config["monitoring_enabled"] = False
                monitor._save_monitor_config()
                monitor.stop_monitoring()
                st.rerun()
        else:
            if st.button("▶️ Start Monitor", use_container_width=True):
                monitor.config["monitoring_enabled"] = True
                monitor._save_monitor_config()
                monitor.start_monitoring()
                st.rerun()


def show_alerts_management(monitor):
    """Show alerts management interface"""
    
    st.subheader("🔔 Alert Management")
    
    # Alert summary
    active_alerts = [alert for alert in monitor.active_alerts if not alert.resolved]
    resolved_alerts = [alert for alert in monitor.active_alerts if alert.resolved]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Alerts", len(active_alerts))
    
    with col2:
        critical_count = sum(1 for a in active_alerts if a.severity == AlertSeverity.CRITICAL)
        st.metric("Critical", critical_count, delta_color="inverse" if critical_count > 0 else "normal")
    
    with col3:
        unacknowledged = sum(1 for a in active_alerts if not a.acknowledged)
        st.metric("Unacknowledged", unacknowledged)
    
    with col4:
        st.metric("Resolved (30d)", len(resolved_alerts))
    
    # Active alerts table
    st.markdown("### 🚨 Active Alerts")
    
    if active_alerts:
        alert_data = []
        
        for alert in sorted(active_alerts, key=lambda x: x.timestamp, reverse=True):
            time_ago = datetime.now() - alert.timestamp
            time_str = f"{int(time_ago.total_seconds() // 3600)}h" if time_ago.total_seconds() > 3600 else f"{int(time_ago.total_seconds() // 60)}m"
            
            alert_data.append({
                "Product": alert.bundle_id,
                "Severity": alert.severity.value.upper(),
                "Title": alert.title,
                "Age": time_str,
                "Acknowledged": "✓" if alert.acknowledged else "❌",
                "Alert ID": alert.id
            })
        
        df = pd.DataFrame(alert_data)
        
        # Display table with actions
        for idx, row in df.iterrows():
            alert_id = row["Alert ID"]
            alert = next(a for a in active_alerts if a.id == alert_id)
            
            with st.expander(f"{row['Severity']} - {row['Title']} ({row['Age']} ago)"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Product:** {alert.bundle_id}")
                    st.markdown(f"**Message:** {alert.message}")
                    st.markdown(f"**Rule:** {alert.rule_id}")
                    st.markdown(f"**Timestamp:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    if not alert.acknowledged:
                        if st.button("✓ Acknowledge", key=f"ack_detail_{alert_id}"):
                            monitor.acknowledge_alert(alert_id)
                            st.rerun()
                    
                    if st.button("🔧 Resolve", key=f"resolve_{alert_id}"):
                        monitor.resolve_alert(alert_id)
                        st.rerun()
                    
                    if st.button("🔍 View Product", key=f"view_{alert_id}"):
                        st.info(f"Navigate to Bundle Explorer for {alert.bundle_id}")
    else:
        st.success("🎉 No active alerts")
    
    # Alert rules configuration
    st.markdown("### ⚙️ Alert Rules")
    
    for rule in monitor.alert_rules:
        with st.expander(f"{'✅' if rule.enabled else '❌'} {rule.name}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Description:** {rule.description}")
                st.markdown(f"**Severity:** {rule.severity.value.upper()}")
                st.markdown(f"**Conditions:** {json.dumps(rule.conditions, indent=2)}")
                st.markdown(f"**Cooldown:** {rule.cooldown_minutes} minutes")
            
            with col2:
                new_enabled = st.checkbox(
                    "Enabled",
                    value=rule.enabled,
                    key=f"rule_enabled_{rule.id}"
                )
                
                if new_enabled != rule.enabled:
                    rule.enabled = new_enabled
                    monitor._save_alert_rules()
                    st.rerun()
                
                if st.button("📝 Edit", key=f"edit_rule_{rule.id}"):
                    st.info("Rule editing interface would open here")


def show_compliance_trends(monitor):
    """Show compliance trends and analytics"""
    
    st.subheader("📈 Compliance Trends & Analytics")
    
    # Time range selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        days = st.selectbox(
            "Time Range",
            [7, 14, 30, 60, 90],
            index=2,  # Default to 30 days
            help="Select time range for trend analysis"
        )
    
    # Get historical data
    history = monitor.get_compliance_history(days=days)
    
    if not history:
        st.warning(f"No compliance data available for the last {days} days")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([
        {
            "timestamp": record.timestamp,
            "bundle_id": record.bundle_id,
            "compliance_score": record.compliance_score,
            "google_eligible": record.google_eligible,
            "schema_found": record.schema_found,
            "status": record.status,
            "total_issues": record.total_issues,
            "critical_issues": record.critical_issues
        }
        for record in history
    ])
    
    # Overall compliance trend
    st.markdown("### 📊 Overall Compliance Trends")
    
    # Daily aggregated scores
    daily_stats = df.groupby(df['timestamp'].dt.date).agg({
        'compliance_score': 'mean',
        'google_eligible': 'mean',
        'schema_found': 'mean',
        'bundle_id': 'nunique'
    }).reset_index()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Average Compliance Score",
            "Google Eligibility Rate", 
            "Schema Detection Rate",
            "Products Monitored"
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Compliance score trend
    fig.add_trace(
        go.Scatter(
            x=daily_stats['timestamp'],
            y=daily_stats['compliance_score'],
            mode='lines+markers',
            name='Compliance Score',
            line=dict(color=CONFIG.COLORS['primary'])
        ),
        row=1, col=1
    )
    
    # Google eligibility trend
    fig.add_trace(
        go.Scatter(
            x=daily_stats['timestamp'],
            y=daily_stats['google_eligible'] * 100,
            mode='lines+markers',
            name='Google Eligible %',
            line=dict(color=CONFIG.COLORS['success'])
        ),
        row=1, col=2
    )
    
    # Schema detection trend
    fig.add_trace(
        go.Scatter(
            x=daily_stats['timestamp'],
            y=daily_stats['schema_found'] * 100,
            mode='lines+markers',
            name='Schema Found %',
            line=dict(color=CONFIG.COLORS['info'])
        ),
        row=2, col=1
    )
    
    # Products monitored
    fig.add_trace(
        go.Scatter(
            x=daily_stats['timestamp'],
            y=daily_stats['bundle_id'],
            mode='lines+markers',
            name='Products',
            line=dict(color=CONFIG.COLORS['secondary'])
        ),
        row=2, col=2
    )
    
    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Product-specific trends
    st.markdown("### 🔍 Product-Specific Analysis")
    
    # Get products with most data points
    product_counts = df['bundle_id'].value_counts()
    top_products = product_counts.head(10).index.tolist()
    
    selected_products = st.multiselect(
        "Select products to analyze",
        options=top_products,
        default=top_products[:3] if len(top_products) >= 3 else top_products,
        help="Choose products for detailed trend analysis"
    )
    
    if selected_products:
        product_df = df[df['bundle_id'].isin(selected_products)]
        
        # Compliance score trends by product
        fig = px.line(
            product_df,
            x='timestamp',
            y='compliance_score',
            color='bundle_id',
            title="Compliance Score Trends by Product",
            labels={'compliance_score': 'Compliance Score (%)', 'timestamp': 'Date'}
        )
        
        # Add threshold lines
        fig.add_hline(
            y=CONFIG.SCORE_THRESHOLDS['excellent'],
            line_dash="dash",
            line_color=CONFIG.COLORS['success'],
            annotation_text="Excellent"
        )
        
        fig.add_hline(
            y=CONFIG.SCORE_THRESHOLDS['good'],
            line_dash="dash", 
            line_color=CONFIG.COLORS['warning'],
            annotation_text="Good"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Issues trend
        fig2 = px.line(
            product_df,
            x='timestamp',
            y='total_issues',
            color='bundle_id',
            title="Total Issues Trends by Product",
            labels={'total_issues': 'Total Issues', 'timestamp': 'Date'}
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Trend analysis insights
    st.markdown("### 💡 Trend Insights")
    
    # Calculate trend metrics
    if len(daily_stats) >= 2:
        first_score = daily_stats['compliance_score'].iloc[0]
        last_score = daily_stats['compliance_score'].iloc[-1]
        score_change = last_score - first_score
        
        first_eligible = daily_stats['google_eligible'].iloc[0]
        last_eligible = daily_stats['google_eligible'].iloc[-1]
        eligible_change = last_eligible - first_eligible
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_icon = "📈" if score_change > 0 else "📉" if score_change < 0 else "➡️"
            st.metric(
                "Compliance Trend",
                f"{last_score:.1f}%",
                delta=f"{score_change:+.1f}%",
                delta_color="normal" if score_change >= 0 else "inverse"
            )
        
        with col2:
            eligible_icon = "📈" if eligible_change > 0 else "📉" if eligible_change < 0 else "➡️"
            st.metric(
                "Eligibility Trend", 
                f"{last_eligible:.1%}",
                delta=f"{eligible_change:+.1%}",
                delta_color="normal" if eligible_change >= 0 else "inverse"
            )
        
        with col3:
            # Calculate volatility
            score_std = daily_stats['compliance_score'].std()
            volatility = "High" if score_std > 10 else "Medium" if score_std > 5 else "Low"
            st.metric("Score Volatility", volatility)
        
        # Trend recommendations
        recommendations = []
        
        if score_change < -5:
            recommendations.append("🚨 **Declining compliance** - Review recent changes and run diagnostics")
        
        if eligible_change < -0.1:
            recommendations.append("⚠️ **Google eligibility dropping** - Focus on required field compliance")
        
        if score_std > 15:
            recommendations.append("📊 **High volatility detected** - Consider implementing more consistent validation")
        
        if last_score < CONFIG.SCORE_THRESHOLDS['good']:
            recommendations.append("🎯 **Below good threshold** - Prioritize schema improvements")
        
        if not recommendations:
            recommendations.append("✅ **Trends look stable** - Continue current monitoring practices")
        
        st.markdown("**Recommendations:**")
        for rec in recommendations:
            st.markdown(f"• {rec}")


def show_monitoring_configuration(monitor):
    """Show monitoring configuration interface"""
    
    st.subheader("⚙️ Monitoring Configuration")
    
    # General monitoring settings
    st.markdown("### 🔧 General Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        monitoring_enabled = st.checkbox(
            "Enable Monitoring",
            value=monitor.config.get("monitoring_enabled", True),
            help="Enable/disable automatic compliance monitoring"
        )
        
        check_interval = st.number_input(
            "Check Interval (minutes)",
            min_value=5,
            max_value=1440,
            value=monitor.config.get("check_interval_minutes", 60),
            help="How often to run compliance checks"
        )
    
    with col2:
        retention_days = st.number_input(
            "Data Retention (days)",
            min_value=7,
            max_value=365,
            value=monitor.config.get("retention_days", 90),
            help="How long to keep historical data"
        )
    
    # Alert thresholds
    st.markdown("### 🚨 Alert Thresholds")
    
    thresholds = monitor.config.get("alert_thresholds", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        critical_score = st.number_input(
            "Critical Score Threshold",
            min_value=0,
            max_value=100,
            value=thresholds.get("compliance_score_critical", 40),
            help="Compliance score threshold for critical alerts"
        )
        
        warning_score = st.number_input(
            "Warning Score Threshold",
            min_value=0,
            max_value=100,
            value=thresholds.get("compliance_score_warning", CONFIG.SCORE_THRESHOLDS['good']),
            help="Compliance score threshold for warning alerts"
        )
    
    with col2:
        max_critical_issues = st.number_input(
            "Max Critical Issues",
            min_value=0,
            max_value=20,
            value=thresholds.get("max_critical_issues", 3),
            help="Maximum critical issues before alert"
        )
        
        max_total_issues = st.number_input(
            "Max Total Issues",
            min_value=0,
            max_value=50,
            value=thresholds.get("max_total_issues", 10),
            help="Maximum total issues before alert"
        )
    
    # Email notifications
    st.markdown("### 📧 Email Notifications")
    
    email_config = monitor.config.get("email_notifications", {})
    
    email_enabled = st.checkbox(
        "Enable Email Notifications",
        value=email_config.get("enabled", False)
    )
    
    if email_enabled:
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input(
                "SMTP Server",
                value=email_config.get("smtp_server", ""),
                placeholder="smtp.gmail.com"
            )
            
            smtp_port = st.number_input(
                "SMTP Port", 
                value=email_config.get("smtp_port", 587)
            )
            
            from_email = st.text_input(
                "From Email",
                value=email_config.get("from_email", ""),
                placeholder="alerts@company.com"
            )
        
        with col2:
            username = st.text_input(
                "Username",
                value=email_config.get("username", ""),
                placeholder="your-email@gmail.com"
            )
            
            password = st.text_input(
                "Password",
                value=email_config.get("password", ""),
                type="password",
                placeholder="your-app-password"
            )
            
            to_emails = st.text_area(
                "To Emails (one per line)",
                value="\n".join(email_config.get("to_emails", [])),
                placeholder="admin@company.com\ndevops@company.com"
            )
    
    # Webhook notifications
    st.markdown("### 🔗 Webhook Notifications")
    
    webhook_config = monitor.config.get("webhook_notifications", {})
    
    webhook_enabled = st.checkbox(
        "Enable Webhook Notifications",
        value=webhook_config.get("enabled", False)
    )
    
    if webhook_enabled:
        webhook_urls = st.text_area(
            "Webhook URLs (one per line)",
            value="\n".join(webhook_config.get("urls", [])),
            placeholder="https://hooks.slack.com/services/...\nhttps://discord.com/api/webhooks/..."
        )
    
    # Save configuration
    if st.button("💾 Save Configuration", type="primary"):
        # Update configuration
        monitor.config.update({
            "monitoring_enabled": monitoring_enabled,
            "check_interval_minutes": check_interval,
            "retention_days": retention_days,
            "alert_thresholds": {
                "compliance_score_critical": critical_score,
                "compliance_score_warning": warning_score,
                "max_critical_issues": max_critical_issues,
                "max_total_issues": max_total_issues
            },
            "email_notifications": {
                "enabled": email_enabled,
                "smtp_server": smtp_server if email_enabled else "",
                "smtp_port": smtp_port if email_enabled else 587,
                "username": username if email_enabled else "",
                "password": password if email_enabled else "",
                "from_email": from_email if email_enabled else "",
                "to_emails": [email.strip() for email in to_emails.split('\n') if email.strip()] if email_enabled else []
            },
            "webhook_notifications": {
                "enabled": webhook_enabled,
                "urls": [url.strip() for url in webhook_urls.split('\n') if url.strip()] if webhook_enabled else []
            }
        })
        
        monitor._save_monitor_config()
        
        # Restart monitoring if needed
        if monitoring_enabled:
            monitor.start_monitoring()
        else:
            monitor.stop_monitoring()
        
        st.success("✅ Configuration saved successfully!")
        st.rerun()
    
    # Monitoring status
    st.markdown("### 📊 Monitoring Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = "🟢 Running" if monitor.config.get("monitoring_enabled", False) else "🔴 Stopped"
        st.metric("Status", status)
    
    with col2:
        interval = monitor.config.get("check_interval_minutes", 60)
        st.metric("Check Interval", f"{interval}m")
    
    with col3:
        last_check = "Never"  # TODO: Track last check time
        st.metric("Last Check", last_check)


def show_compliance_history(monitor):
    """Show detailed compliance history"""
    
    st.subheader("📋 Compliance History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days = st.selectbox(
            "Time Range",
            [7, 14, 30, 60, 90],
            index=1,  # Default to 14 days
            key="history_days"
        )
    
    with col2:
        # Get available products
        history = monitor.get_compliance_history(days=days)
        product_ids = sorted(list(set(record.bundle_id for record in history)))
        
        selected_product = st.selectbox(
            "Product Filter",
            ["All Products"] + product_ids,
            key="history_product"
        )
    
    with col3:
        min_score = st.slider(
            "Min Compliance Score",
            0, 100, 0,
            key="history_score"
        )
    
    # Get filtered history
    if selected_product == "All Products":
        filtered_history = monitor.get_compliance_history(days=days)
    else:
        filtered_history = monitor.get_compliance_history(bundle_id=selected_product, days=days)
    
    # Apply score filter
    filtered_history = [r for r in filtered_history if r.compliance_score >= min_score]
    
    if not filtered_history:
        st.warning("No compliance history found for the selected filters")
        return
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", len(filtered_history))
    
    with col2:
        avg_score = sum(r.compliance_score for r in filtered_history) / len(filtered_history)
        st.metric("Average Score", f"{avg_score:.1f}%")
    
    with col3:
        google_eligible = sum(1 for r in filtered_history if r.google_eligible)
        eligible_rate = google_eligible / len(filtered_history) * 100
        st.metric("Google Eligible", f"{eligible_rate:.1f}%")
    
    with col4:
        unique_products = len(set(r.bundle_id for r in filtered_history))
        st.metric("Products", unique_products)
    
    # History table
    st.markdown("### 📊 Detailed Records")
    
    # Convert to DataFrame for display
    df_data = []
    for record in filtered_history[-100:]:  # Show last 100 records
        df_data.append({
            "Timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M"),
            "Product": record.bundle_id,
            "Score": f"{record.compliance_score:.1f}%",
            "Google": "✅" if record.google_eligible else "❌",
            "Schema": "✅" if record.schema_found else "❌",
            "Status": record.status.replace('_', ' ').title(),
            "Issues": record.total_issues,
            "Critical": record.critical_issues
        })
    
    df = pd.DataFrame(df_data)
    
    # Style the dataframe
    def style_status(val):
        if "✅" in str(val):
            return 'background-color: #d4edda; color: #155724;'
        elif "❌" in str(val):
            return 'background-color: #f8d7da; color: #721c24;'
        return ''
    
    def style_score(val):
        if isinstance(val, str) and val.endswith('%'):
            score = float(val.replace('%', ''))
            if score >= CONFIG.SCORE_THRESHOLDS['excellent']:
                return 'background-color: #d4edda; color: #155724;'
            elif score >= CONFIG.SCORE_THRESHOLDS['good']:
                return 'background-color: #fff3cd; color: #856404;'
            else:
                return 'background-color: #f8d7da; color: #721c24;'
        return ''
    
    styled_df = df.style.applymap(style_status, subset=['Google', 'Schema'])
    styled_df = styled_df.applymap(style_score, subset=['Score'])
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Export history
    if st.button("📥 Export History as CSV"):
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"compliance_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Data cleanup
    st.markdown("### 🧹 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Cleanup Old Data"):
            with st.spinner("Cleaning up old data..."):
                deleted_count = monitor.cleanup_old_data()
                st.success(f"✅ Deleted {deleted_count} old records")
    
    with col2:
        if st.button("📊 Recalculate Stats"):
            st.info("Statistics recalculation would run here")


def show_monitoring_tab():
    """Main entry point for monitoring tab"""
    show_compliance_monitoring_page()