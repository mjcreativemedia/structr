"""
Export Center page for Structr dashboard

Handle CSV exports, downloads, and catalog generation.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json
import subprocess
from datetime import datetime
import zipfile
import io

from config import CONFIG
# Import enhanced CSV functionality
from dashboard.enhanced_csv import (
    show_csv_export_options,
    create_shopify_export,
    create_generic_export,
    create_audit_export,
    create_custom_export,
    load_existing_bundles_for_export
)


def show_export_center_page():
    """Display export center page"""
    
    st.header("📤 Export Center")
    st.markdown("Export catalogs, reports, and bundle data")
    
    # Tabs for different export types
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Catalog Export", "📋 Audit Reports", "📦 Bundle Archives", "🔗 Integration", "📊 Enhanced CSV"])
    
    with tab1:
        show_catalog_export()
    
    with tab2:
        show_audit_reports()
    
    with tab3:
        show_bundle_archives()
    
    with tab4:
        show_integration_options()
    
    with tab5:
        show_csv_export_options()


def show_catalog_export():
    """Show catalog export options"""
    
    st.subheader("📊 Catalog Export")
    st.markdown("Export your PDP bundles as platform-ready catalogs")
    
    # Export format selection
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox(
            "Export Format",
            CONFIG.EXPORT_FORMATS,
            index=CONFIG.EXPORT_FORMATS.index(CONFIG.DEFAULT_EXPORT_FORMAT) if CONFIG.DEFAULT_EXPORT_FORMAT in CONFIG.EXPORT_FORMATS else 0,
            help="Choose the target platform format"
        )
    
    with col2:
        include_audit_data = st.checkbox(
            "Include Audit Data",
            value=CONFIG.INCLUDE_AUDIT_DATA_DEFAULT,
            help="Include audit scores and issue tracking"
        )
    
    # Additional options
    st.subheader("Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        include_html = st.checkbox(
            "Include HTML Content",
            value=True,
            help="Include generated HTML in body_html field"
        )
    
    with col2:
        include_metafields = st.checkbox(
            "Include Metafields",
            value=True,
            help="Include custom metafields as JSON columns"
        )
    
    with col3:
        filter_by_score = st.checkbox(
            "Filter by Score",
            value=False,
            help="Only export bundles above a certain score"
        )
    
    # Score filter
    if filter_by_score:
        min_score = st.slider(
            "Minimum Score",
            min_value=0,
            max_value=100,
            value=80,
            help="Only export bundles with scores above this threshold"
        )
    else:
        min_score = 0
    
    # Preview export data
    if st.button("🔍 Preview Export Data"):
        preview_export_data(export_format, include_audit_data, include_html, include_metafields, min_score)
    
    # Export buttons
    st.subheader("Export Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Catalog", type="primary", use_container_width=True):
            export_catalog(export_format, include_audit_data, include_html, include_metafields, min_score)
    
    with col2:
        if st.button("⚡ Quick Export (CLI)", use_container_width=True):
            run_cli_export()


def show_audit_reports():
    """Show audit report export options"""
    
    st.subheader("📋 Audit Reports")
    st.markdown("Generate detailed audit and compliance reports")
    
    # Report type selection
    report_type = st.selectbox(
        "Report Type",
        ["Compliance Summary", "Detailed Issues Report", "Score Analytics", "Fix History Report"],
        help="Choose the type of audit report to generate"
    )
    
    # Load audit data for preview
    audit_data = load_audit_data_for_reports()
    
    if not audit_data:
        st.warning("No audit data found. Generate and audit some PDPs first.")
        return
    
    # Report options based on type
    if report_type == "Compliance Summary":
        show_compliance_summary_options(audit_data)
    elif report_type == "Detailed Issues Report":
        show_detailed_issues_options(audit_data)
    elif report_type == "Score Analytics":
        show_score_analytics_options(audit_data)
    elif report_type == "Fix History Report":
        show_fix_history_options(audit_data)


def show_bundle_archives():
    """Show bundle archive export options"""
    
    st.subheader("📦 Bundle Archives")
    st.markdown("Create downloadable archives of your PDP bundles")
    
    # Archive options
    col1, col2 = st.columns(2)
    
    with col1:
        archive_scope = st.selectbox(
            "Archive Scope",
            ["All bundles", "Selected bundles", "Bundles by score", "Bundles by status"],
            help="Choose which bundles to include in the archive"
        )
    
    with col2:
        archive_format = st.selectbox(
            "Archive Format",
            ["ZIP", "TAR.GZ"],
            help="Choose the archive compression format"
        )
    
    # Scope-specific options
    if archive_scope == "Selected bundles":
        available_bundles = get_available_bundles()
        if available_bundles:
            selected_bundles = st.multiselect(
                "Select Bundles",
                available_bundles,
                help="Choose specific bundles to archive"
            )
        else:
            st.warning("No bundles available")
            return
    
    elif archive_scope == "Bundles by score":
        score_range = st.slider(
            "Score Range",
            min_value=0,
            max_value=100,
            value=(80, 100),
            help="Include bundles within this score range"
        )
    
    elif archive_scope == "Bundles by status":
        status_filter = st.multiselect(
            "Status Filter",
            ["Excellent (90+)", "Good (80-89)", "Fair (60-79)", "Poor (<60)"],
            default=["Excellent (90+)", "Good (80-89)"],
            help="Include bundles with these status levels"
        )
    
    # File inclusion options
    st.subheader("Include Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        include_html = st.checkbox("HTML Files", value=True)
        include_audit = st.checkbox("Audit Data", value=True)
    
    with col2:
        include_sync = st.checkbox("Sync Data", value=True)
        include_fix_logs = st.checkbox("Fix Logs", value=True)
    
    with col3:
        include_readme = st.checkbox("Generate README", value=True, help="Include a README file with bundle information")
    
    # Create archive
    if st.button("📦 Create Archive", type="primary", use_container_width=True):
        create_bundle_archive(
            archive_scope, archive_format, locals()
        )


def show_integration_options():
    """Show integration and API export options"""
    
    st.subheader("🔗 Integration Options")
    st.markdown("Connect Structr exports to external platforms")
    
    # Platform integrations
    integration_type = st.selectbox(
        "Integration Type",
        ["Shopify Admin API", "Generic Webhook", "CSV Upload", "API Endpoint"],
        help="Choose the integration method"
    )
    
    if integration_type == "Shopify Admin API":
        show_shopify_integration()
    elif integration_type == "Generic Webhook":
        show_webhook_integration()
    elif integration_type == "CSV Upload":
        show_csv_upload_integration()
    elif integration_type == "API Endpoint":
        show_api_integration()


def preview_export_data(export_format, include_audit_data, include_html, include_metafields, min_score):
    """Preview export data before actual export"""
    
    try:
        # Load bundle data
        export_data = generate_export_data(export_format, include_audit_data, include_html, include_metafields, min_score)
        
        if not export_data:
            st.warning("No data to export with current filters")
            return
        
        st.subheader("Export Preview")
        
        # Show summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Bundles", len(export_data))
        
        with col2:
            avg_score = sum(row.get('audit_score', 0) for row in export_data) / len(export_data)
            st.metric("Avg Score", f"{avg_score:.1f}")
        
        with col3:
            flagged = sum(1 for row in export_data if row.get('audit_score', 100) < 80)
            st.metric("Flagged", flagged)
        
        # Show preview table
        df = pd.DataFrame(export_data)
        
        # Select columns to display in preview
        preview_columns = ['handle', 'title', 'vendor', 'price']
        if include_audit_data:
            preview_columns.extend(['audit_score', 'audit_issues'])
        
        available_columns = [col for col in preview_columns if col in df.columns]
        
        st.dataframe(df[available_columns].head(10), use_container_width=True)
        
        if len(export_data) > 10:
            st.info(f"Showing first 10 of {len(export_data)} rows")
        
        # Show column information
        with st.expander("Column Information"):
            column_info = []
            for col in df.columns:
                non_null_count = df[col].notna().sum()
                column_info.append({
                    'Column': col,
                    'Type': str(df[col].dtype),
                    'Non-null Count': non_null_count,
                    'Completion': f"{(non_null_count/len(df)*100):.1f}%"
                })
            
            st.dataframe(pd.DataFrame(column_info), use_container_width=True)
    
    except Exception as e:
        st.error(f"Error generating preview: {str(e)}")


def export_catalog(export_format, include_audit_data, include_html, include_metafields, min_score):
    """Export catalog with specified options"""
    
    try:
        with st.spinner("Generating catalog export..."):
            export_data = generate_export_data(export_format, include_audit_data, include_html, include_metafields, min_score)
        
        if not export_data:
            st.warning("No data to export")
            return
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        format_name = export_format.lower().replace(" ", "_")
        filename = f"structr_catalog_{format_name}_{timestamp}.csv"
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Success message
        st.success(f"✅ Catalog exported successfully!")
        
        # Show summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Exported Bundles", len(export_data))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            st.metric("File Size", f"{len(csv_content)/1024:.1f} KB")
        
        # Download button
        st.download_button(
            label="📥 Download Catalog CSV",
            data=csv_content,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )
        
        # Also save locally
        output_path = Path("output") / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        st.info(f"📁 File also saved locally as: {output_path}")
    
    except Exception as e:
        st.error(f"Error exporting catalog: {str(e)}")


def run_cli_export():
    """Run CLI export command"""
    
    try:
        with st.spinner("Running CLI export..."):
            result = subprocess.run([
                'python', 'cli.py', 'export'
            ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            st.success("✅ CLI export completed")
            if result.stdout:
                st.text_area("Export Results", result.stdout, height=150)
            
            # Look for generated file
            output_files = list(Path("output").glob("catalog_structr_*.csv"))
            if output_files:
                latest_file = max(output_files, key=lambda x: x.stat().st_mtime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
                
                st.download_button(
                    label=f"📥 Download {latest_file.name}",
                    data=csv_content,
                    file_name=latest_file.name,
                    mime="text/csv"
                )
        else:
            st.error(f"❌ CLI export failed: {result.stderr}")
    
    except Exception as e:
        st.error(f"Error running CLI export: {str(e)}")


def show_compliance_summary_options(audit_data):
    """Show compliance summary report options"""
    
    st.subheader("Compliance Summary Report")
    
    # Calculate metrics
    df = pd.DataFrame(audit_data)
    total_bundles = len(df)
    avg_score = df['score'].mean()
    compliance_rate = (df['score'] >= 80).mean() * 100
    
    # Preview metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Bundles", total_bundles)
    with col2:
        st.metric("Average Score", f"{avg_score:.1f}")
    with col3:
        st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
    
    # Export options
    include_details = st.checkbox("Include Individual Bundle Details", value=False)
    group_by_brand = st.checkbox("Group by Brand", value=True)
    
    if st.button("📋 Generate Compliance Report", use_container_width=True):
        generate_compliance_report(audit_data, include_details, group_by_brand)


def show_detailed_issues_options(audit_data):
    """Show detailed issues report options"""
    
    st.subheader("Detailed Issues Report")
    
    # Issue filtering
    col1, col2 = st.columns(2)
    
    with col1:
        issue_types = st.multiselect(
            "Include Issue Types",
            ["Missing Fields", "Flagged Issues", "Schema Errors", "Metadata Issues"],
            default=["Missing Fields", "Schema Errors"],
            help="Choose which types of issues to include"
        )
    
    with col2:
        severity_filter = st.selectbox(
            "Severity Filter",
            ["All Severities", "Critical Only", "High & Critical", "Medium & Above"],
            help="Filter issues by severity level"
        )
    
    if st.button("📋 Generate Issues Report", use_container_width=True):
        generate_issues_report(audit_data, issue_types, severity_filter)


def show_score_analytics_options(audit_data):
    """Show score analytics report options"""
    
    st.subheader("Score Analytics Report")
    
    # Analytics options
    include_charts = st.checkbox("Include Charts", value=True)
    include_trends = st.checkbox("Include Trend Analysis", value=True)
    breakdown_by = st.selectbox(
        "Breakdown By",
        ["None", "Brand", "Category", "Model Used"],
        help="Group analytics by specific field"
    )
    
    if st.button("📊 Generate Analytics Report", use_container_width=True):
        generate_analytics_report(audit_data, include_charts, include_trends, breakdown_by)


def show_fix_history_options(audit_data):
    """Show fix history report options"""
    
    st.subheader("Fix History Report")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        fixed_only = st.checkbox("Fixed Bundles Only", value=True)
    
    with col2:
        include_improvements = st.checkbox("Include Score Improvements", value=True)
    
    if st.button("🔧 Generate Fix History Report", use_container_width=True):
        generate_fix_history_report(audit_data, fixed_only, include_improvements)


def show_shopify_integration():
    """Show Shopify integration options"""
    
    st.subheader("Shopify Admin API Integration")
    st.info("⚠️ This feature requires Shopify Admin API credentials")
    
    # API credentials (would need secure storage in production)
    shop_url = st.text_input("Shop URL", placeholder="your-shop.myshopify.com")
    access_token = st.text_input("Access Token", type="password", help="Private app access token")
    
    # Sync options
    sync_mode = st.selectbox(
        "Sync Mode",
        ["Preview Only", "Update Existing Products", "Create New Products", "Full Sync"],
        help="Choose how to sync data to Shopify"
    )
    
    if st.button("🔗 Test Connection", use_container_width=True):
        if shop_url and access_token:
            st.info("Connection test would go here (not implemented in demo)")
        else:
            st.error("Please provide shop URL and access token")


def show_webhook_integration():
    """Show webhook integration options"""
    
    st.subheader("Generic Webhook Integration")
    
    webhook_url = st.text_input("Webhook URL", placeholder="https://your-server.com/webhook")
    webhook_method = st.selectbox("HTTP Method", ["POST", "PUT", "PATCH"])
    
    # Headers
    st.subheader("Headers")
    headers = {}
    for i in range(3):
        col1, col2 = st.columns(2)
        with col1:
            key = st.text_input(f"Header {i+1} Key", key=f"header_key_{i}")
        with col2:
            value = st.text_input(f"Header {i+1} Value", key=f"header_value_{i}")
        
        if key and value:
            headers[key] = value
    
    # Payload format
    payload_format = st.selectbox("Payload Format", ["JSON", "CSV", "XML"])
    
    if st.button("📡 Test Webhook", use_container_width=True):
        if webhook_url:
            st.info("Webhook test would go here (not implemented in demo)")
        else:
            st.error("Please provide webhook URL")


def show_csv_upload_integration():
    """Show CSV upload integration"""
    
    st.subheader("CSV Upload Integration")
    st.markdown("Upload generated CSV files to various platforms")
    
    platform = st.selectbox(
        "Target Platform",
        ["Shopify", "WooCommerce", "BigCommerce", "Custom Platform"],
        help="Choose the target platform for CSV upload"
    )
    
    upload_method = st.selectbox(
        "Upload Method",
        ["Manual Download", "FTP Upload", "SFTP Upload", "Cloud Storage"],
        help="Choose how to deliver the CSV file"
    )
    
    if upload_method in ["FTP Upload", "SFTP Upload"]:
        st.subheader("Connection Details")
        host = st.text_input("Host")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        remote_path = st.text_input("Remote Path", placeholder="/uploads/")
    
    elif upload_method == "Cloud Storage":
        st.subheader("Cloud Storage")
        provider = st.selectbox("Provider", ["AWS S3", "Google Cloud Storage", "Azure Blob"])
        bucket = st.text_input("Bucket/Container Name")
        access_key = st.text_input("Access Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")


def show_api_integration():
    """Show API endpoint integration"""
    
    st.subheader("API Endpoint Integration")
    st.markdown("Expose Structr data via REST API endpoints")
    
    st.info("🚧 API endpoints would include:")
    st.markdown("""
    - `GET /api/bundles` - List all bundles
    - `GET /api/bundles/{id}` - Get specific bundle
    - `GET /api/audit/{id}` - Get audit data
    - `POST /api/export` - Trigger export
    - `GET /api/export/{id}/download` - Download export file
    """)
    
    # API configuration
    enable_auth = st.checkbox("Enable Authentication", value=True)
    if enable_auth:
        auth_method = st.selectbox("Auth Method", ["API Key", "Bearer Token", "Basic Auth"])
        if auth_method == "API Key":
            api_key = st.text_input("API Key", type="password")
    
    rate_limiting = st.checkbox("Enable Rate Limiting", value=True)
    if rate_limiting:
        requests_per_minute = st.number_input("Requests per Minute", min_value=1, value=60)


# Utility functions

@st.cache_data(ttl=60)
def load_audit_data_for_reports():
    """Load audit data for reports"""
    
    output_dir = Path(st.session_state.get('output_dir', 'output'))
    bundles_dir = output_dir / "bundles"
    
    audit_data = []
    
    if not bundles_dir.exists():
        return audit_data
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            audit_file = bundle_dir / "audit.json"
            if audit_file.exists():
                try:
                    with open(audit_file, 'r') as f:
                        audit = json.load(f)
                    audit['bundle_id'] = bundle_dir.name
                    audit_data.append(audit)
                except:
                    pass
    
    return audit_data


def get_available_bundles():
    """Get list of available bundle IDs"""
    
    output_dir = Path(st.session_state.get('output_dir', 'output'))
    bundles_dir = output_dir / "bundles"
    
    if not bundles_dir.exists():
        return []
    
    return [d.name for d in bundles_dir.iterdir() if d.is_dir()]


def generate_export_data(export_format, include_audit_data, include_html, include_metafields, min_score):
    """Generate export data based on options"""
    
    # This would use the existing CSV exporter
    from export.csv_exporter import StructrCatalogExporter
    
    exporter = StructrCatalogExporter(st.session_state.get('output_dir', 'output'))
    
    # Get bundle data
    # For now, return mock data structure
    # In real implementation, would call exporter methods
    
    return []  # Placeholder


def generate_compliance_report(audit_data, include_details, group_by_brand):
    """Generate compliance summary report"""
    
    try:
        df = pd.DataFrame(audit_data)
        
        # Create report data
        report_data = {
            'summary': {
                'total_bundles': len(df),
                'average_score': df['score'].mean(),
                'compliance_rate': (df['score'] >= 80).mean() * 100,
                'excellence_rate': (df['score'] >= 90).mean() * 100
            }
        }
        
        # Generate CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_report_{timestamp}.csv"
        
        df_export = df[['bundle_id', 'score']].copy()
        df_export['compliant'] = df_export['score'] >= 80
        df_export['excellent'] = df_export['score'] >= 90
        
        csv_content = df_export.to_csv(index=False)
        
        st.success("✅ Compliance report generated")
        st.download_button(
            label="📥 Download Compliance Report",
            data=csv_content,
            file_name=filename,
            mime="text/csv"
        )
    
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")


def generate_issues_report(audit_data, issue_types, severity_filter):
    """Generate detailed issues report"""
    
    st.success("✅ Issues report generated")
    st.info("Issues report generation would be implemented here")


def generate_analytics_report(audit_data, include_charts, include_trends, breakdown_by):
    """Generate score analytics report"""
    
    st.success("✅ Analytics report generated")
    st.info("Analytics report generation would be implemented here")


def generate_fix_history_report(audit_data, fixed_only, include_improvements):
    """Generate fix history report"""
    
    st.success("✅ Fix history report generated")
    st.info("Fix history report generation would be implemented here")


def create_bundle_archive(archive_scope, archive_format, options):
    """Create downloadable bundle archive"""
    
    try:
        with st.spinner("Creating bundle archive..."):
            # Collect bundles based on scope
            bundles_to_archive = []
            
            output_dir = Path(st.session_state.get('output_dir', 'output'))
            bundles_dir = output_dir / "bundles"
            
            if not bundles_dir.exists():
                st.error("No bundles directory found")
                return
            
            # Get bundles based on scope
            for bundle_dir in bundles_dir.iterdir():
                if bundle_dir.is_dir():
                    include_bundle = False
                    
                    if archive_scope == "All bundles":
                        include_bundle = True
                    elif archive_scope == "Selected bundles":
                        include_bundle = bundle_dir.name in options.get('selected_bundles', [])
                    # Add other scope logic here
                    
                    if include_bundle:
                        bundles_to_archive.append(bundle_dir)
            
            if not bundles_to_archive:
                st.warning("No bundles match the selected criteria")
                return
            
            # Create archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"structr_bundles_{timestamp}.zip"
            
            archive_buffer = io.BytesIO()
            
            with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for bundle_dir in bundles_to_archive:
                    # Add files based on inclusion options
                    if options.get('include_html', True):
                        html_file = bundle_dir / "index.html"
                        if html_file.exists():
                            zf.write(html_file, f"{bundle_dir.name}/index.html")
                    
                    if options.get('include_audit', True):
                        audit_file = bundle_dir / "audit.json"
                        if audit_file.exists():
                            zf.write(audit_file, f"{bundle_dir.name}/audit.json")
                    
                    # Add other files based on options
                
                # Add README if requested
                if options.get('include_readme', True):
                    readme_content = f"""# Structr Bundle Archive
                    
Generated: {datetime.now().isoformat()}
Bundles included: {len(bundles_to_archive)}
Archive scope: {archive_scope}

## Bundle Contents
"""
                    for bundle_dir in bundles_to_archive:
                        readme_content += f"- {bundle_dir.name}\n"
                    
                    zf.writestr("README.md", readme_content)
            
            archive_buffer.seek(0)
            
            st.success(f"✅ Archive created with {len(bundles_to_archive)} bundles")
            
            st.download_button(
                label="📥 Download Bundle Archive",
                data=archive_buffer.getvalue(),
                file_name=archive_name,
                mime="application/zip",
                use_container_width=True
            )
    
    except Exception as e:
        st.error(f"Error creating archive: {str(e)}")