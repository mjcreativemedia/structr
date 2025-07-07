"""
Bundle Explorer page for Structr dashboard

Browse and inspect individual PDP bundles with preview capabilities.
"""

import streamlit as st
from pathlib import Path
import json
from bs4 import BeautifulSoup
import pandas as pd
import base64

from config import CONFIG


def show_bundle_explorer_page():
    """Display bundle explorer page"""
    
    st.header("📦 Bundle Explorer")
    st.markdown("Browse and inspect individual PDP bundles")
    
    # Load available bundles
    bundles = load_bundle_list()
    
    if not bundles:
        st.info("No bundles found. Generate some PDPs first.")
        return
    
    # Bundle selection and preview
    col1, col2 = st.columns([1, 2])
    
    with col1:
        show_bundle_list(bundles)
    
    with col2:
        selected_bundle = st.session_state.get('selected_bundle')
        if selected_bundle:
            show_bundle_details(selected_bundle)
        else:
            st.info("Select a bundle from the list to view details")


@st.cache_data(ttl=CONFIG.CACHE_TTL)
def load_bundle_list():
    """Load list of available bundles"""
    
    output_dir = CONFIG.get_output_dir()
    bundles_dir = CONFIG.get_bundles_dir()
    
    bundles = []
    
    if not bundles_dir.exists():
        return bundles
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            try:
                bundle_info = {
                    'id': bundle_dir.name,
                    'path': str(bundle_dir),
                    'score': None,
                    'status': 'unknown',
                    'title': 'Unknown Product',
                    'brand': 'Unknown',
                    'timestamp': None,
                    'files': []
                }
                
                # Check available files
                for file_name in [CONFIG.HTML_FILENAME, CONFIG.SYNC_FILENAME, CONFIG.AUDIT_FILENAME, CONFIG.FIX_LOG_FILENAME]:
                    file_path = bundle_dir / file_name
                    if file_path.exists():
                        bundle_info['files'].append(file_name)
                
                # Load basic info from audit
                audit_file = bundle_dir / CONFIG.AUDIT_FILENAME
                if audit_file.exists():
                    with open(audit_file, 'r') as f:
                        audit_data = json.load(f)
                    
                    bundle_info['score'] = audit_data.get('score', 0)
                    bundle_info['timestamp'] = audit_data.get('timestamp')
                    
                    # Determine status using config thresholds
                    score = bundle_info['score']
                    if score >= CONFIG.SCORE_THRESHOLDS['excellent']:
                        bundle_info['status'] = 'excellent'
                    elif score >= CONFIG.SCORE_THRESHOLDS['good']:
                        bundle_info['status'] = 'good'
                    elif score >= CONFIG.SCORE_THRESHOLDS['fair']:
                        bundle_info['status'] = 'fair'
                    else:
                        bundle_info['status'] = 'poor'
                
                # Load product info from sync
                sync_file = bundle_dir / CONFIG.SYNC_FILENAME
                if sync_file.exists():
                    with open(sync_file, 'r') as f:
                        sync_data = json.load(f)
                    
                    input_data = sync_data.get('input', {})
                    bundle_info['title'] = input_data.get('title', 'Unknown Product')
                    bundle_info['brand'] = input_data.get('brand', 'Unknown')
                
                bundles.append(bundle_info)
                
            except Exception as e:
                st.warning(f"Error loading bundle {bundle_dir.name}: {str(e)}")
    
    # Sort by score (descending)
    bundles.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return bundles


def show_bundle_list(bundles):
    """Display bundle list with filtering"""
    
    st.subheader("Available Bundles")
    
    # Filters
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Excellent (90+)", "Good (80-89)", "Fair (60-79)", "Poor (<60)"]
    )
    
    search_term = st.text_input(
        "Search bundles",
        placeholder="Search by bundle ID or product name..."
    )
    
    # Apply filters
    filtered_bundles = bundles.copy()
    
    if status_filter != "All":
        status_map = {
            "Excellent (90+)": "excellent",
            "Good (80-89)": "good", 
            "Fair (60-79)": "fair",
            "Poor (<60)": "poor"
        }
        target_status = status_map[status_filter]
        filtered_bundles = [b for b in filtered_bundles if b['status'] == target_status]
    
    if search_term:
        search_lower = search_term.lower()
        filtered_bundles = [
            b for b in filtered_bundles
            if search_lower in b['id'].lower() or search_lower in b['title'].lower()
        ]
    
    st.markdown(f"**{len(filtered_bundles)} bundles found**")
    
    # Display bundle cards
    for bundle in filtered_bundles:
        show_bundle_card(bundle)


def show_bundle_card(bundle):
    """Display a compact bundle card"""
    
    # Status styling
    status_colors = {
        'excellent': '#28a745',
        'good': '#17a2b8',
        'fair': '#ffc107',
        'poor': '#dc3545'
    }
    
    status_color = status_colors.get(bundle['status'], '#6c757d')
    
    # Create card
    with st.container():
        if st.button(
            f"📦 {bundle['id']}", 
            key=f"select_{bundle['id']}",
            use_container_width=True
        ):
            st.session_state.selected_bundle = bundle['id']
            st.rerun()
        
        # Bundle info
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(
                f"**{bundle['title'][:40]}{'...' if len(bundle['title']) > 40 else ''}**<br/>"
                f"<small>{bundle['brand']}</small>",
                unsafe_allow_html=True
            )
        
        with col2:
            if bundle['score'] is not None:
                st.markdown(
                    f"<div style='text-align: right; color: {status_color}; font-weight: bold;'>"
                    f"{bundle['score']:.1f}/100</div>",
                    unsafe_allow_html=True
                )
        
        # File indicators
        file_indicators = []
        for file_name in ['index.html', 'sync.json', 'audit.json', 'fix_log.json']:
            if file_name in bundle['files']:
                file_indicators.append(f"✅ {file_name}")
            else:
                file_indicators.append(f"❌ {file_name}")
        
        st.markdown(f"<small>{' | '.join(file_indicators)}</small>", unsafe_allow_html=True)
        
        st.markdown("---")


def show_bundle_details(bundle_id):
    """Display detailed view of selected bundle"""
    
    st.subheader(f"Bundle Details: {bundle_id}")
    
    # Load bundle data
    bundle_data = load_bundle_details(bundle_id)
    
    if not bundle_data:
        st.error(f"Could not load bundle: {bundle_id}")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 HTML Preview", "🔍 Audit Details", "⚙️ Config & Sync", "🛠️ Fix History", "📁 Raw Files"])
    
    with tab1:
        show_html_preview(bundle_data)
    
    with tab2:
        show_audit_details(bundle_data)
    
    with tab3:
        show_config_sync(bundle_data)
    
    with tab4:
        show_fix_history(bundle_data)
    
    with tab5:
        show_raw_files(bundle_data)


@st.cache_data(ttl=60)
def load_bundle_details(bundle_id):
    """Load detailed bundle data"""
    
    output_dir = Path(st.session_state.get('output_dir', 'output'))
    bundle_dir = output_dir / "bundles" / bundle_id
    
    if not bundle_dir.exists():
        return None
    
    bundle_data = {
        'id': bundle_id,
        'path': str(bundle_dir),
        'html_content': None,
        'audit_data': None,
        'sync_data': None,
        'fix_history': None
    }
    
    # Load HTML content
    html_file = bundle_dir / "index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            bundle_data['html_content'] = f.read()
    
    # Load audit data
    audit_file = bundle_dir / "audit.json"
    if audit_file.exists():
        with open(audit_file, 'r') as f:
            bundle_data['audit_data'] = json.load(f)
    
    # Load sync data
    sync_file = bundle_dir / "sync.json"
    if sync_file.exists():
        with open(sync_file, 'r') as f:
            bundle_data['sync_data'] = json.load(f)
    
    # Load fix history
    fix_log_file = bundle_dir / "fix_log.json"
    if fix_log_file.exists():
        with open(fix_log_file, 'r') as f:
            bundle_data['fix_history'] = json.load(f)
    
    return bundle_data


def show_html_preview(bundle_data):
    """Show HTML preview and metadata extraction"""
    
    if not bundle_data['html_content']:
        st.warning("No HTML content found")
        return
    
    html_content = bundle_data['html_content']
    
    # Display options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("HTML Preview")
    
    with col2:
        view_mode = st.selectbox(
            "View Mode",
            ["Rendered", "Source Code", "Metadata Only"]
        )
    
    if view_mode == "Rendered":
        # Render HTML (with safety warning)
        st.warning("⚠️ Rendering HTML content (external links disabled)")
        
        try:
            # Create safe HTML for display
            safe_html = html_content.replace('href="http', 'href="#disabled-http')
            safe_html = safe_html.replace('src="http', 'src="#disabled-http')
            safe_html = safe_html.replace('href="https', 'href="#disabled-https')
            safe_html = safe_html.replace('src="https', 'src="#disabled-https')
            
            # Use iframe with custom CSS for better rendering
            iframe_content = f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 10px; 
                        background: white;
                    }}
                    img {{ max-width: 100%; height: auto; }}
                    * {{ box-sizing: border-box; }}
                </style>
            </head>
            <body>
                {safe_html}
            </body>
            </html>
            """
            
            # Use components to render HTML
            st.components.v1.html(iframe_content, height=600, scrolling=True)
            
        except Exception as e:
            st.error(f"Error rendering HTML: {str(e)}")
            st.info("Falling back to source code view:")
            st.code(html_content, language='html')
    
    elif view_mode == "Source Code":
        # Show source code with syntax highlighting
        st.code(html_content, language='html')
    
    elif view_mode == "Metadata Only":
        # Extract and display metadata
        show_extracted_metadata(html_content)
    
    # Quick actions
    st.subheader("Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Copy HTML", use_container_width=True):
            st.code(html_content, language='html')
    
    with col2:
        if st.button("💾 Download HTML", use_container_width=True):
            st.download_button(
                label="Download",
                data=html_content,
                file_name=f"{bundle_data['id']}.html",
                mime="text/html"
            )
    
    with col3:
        if st.button("🔍 Validate HTML", use_container_width=True):
            validate_html_content(html_content)


def show_extracted_metadata(html_content):
    """Extract and display metadata from HTML"""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        if title:
            st.markdown(f"**Title:** {title.text.strip()}")
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            st.markdown(f"**Meta Description:** {meta_desc.get('content', '')}")
        
        # Extract Open Graph tags
        st.subheader("Open Graph Tags")
        og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
        if og_tags:
            for tag in og_tags:
                prop = tag.get('property')
                content = tag.get('content', '')
                st.markdown(f"**{prop}:** {content}")
        else:
            st.info("No Open Graph tags found")
        
        # Extract JSON-LD schema
        st.subheader("JSON-LD Schema")
        schema_script = soup.find('script', attrs={'type': 'application/ld+json'})
        if schema_script and schema_script.string:
            try:
                schema_data = json.loads(schema_script.string)
                st.json(schema_data)
            except json.JSONDecodeError:
                st.error("Invalid JSON-LD schema format")
        else:
            st.info("No JSON-LD schema found")
        
        # Extract other metadata
        st.subheader("Other Meta Tags")
        meta_tags = soup.find_all('meta')
        other_meta = []
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content', '')
            if name and not name.startswith('og:') and name != 'description':
                other_meta.append({'Name': name, 'Content': content})
        
        if other_meta:
            st.dataframe(pd.DataFrame(other_meta), use_container_width=True)
        else:
            st.info("No additional meta tags found")
    
    except Exception as e:
        st.error(f"Error extracting metadata: {str(e)}")


def show_audit_details(bundle_data):
    """Show detailed audit information"""
    
    if not bundle_data['audit_data']:
        st.warning("No audit data found")
        return
    
    audit = bundle_data['audit_data']
    
    # Audit summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        score = audit.get('score', 0)
        status = "Excellent" if score >= 90 else "Good" if score >= 80 else "Fair" if score >= 60 else "Poor"
        st.metric("Audit Score", f"{score:.1f}/100", help=f"Status: {status}")
    
    with col2:
        total_issues = (
            len(audit.get('missing_fields', [])) +
            len(audit.get('flagged_issues', [])) +
            len(audit.get('schema_errors', [])) +
            len(audit.get('metadata_issues', []))
        )
        st.metric("Total Issues", total_issues)
    
    with col3:
        timestamp = audit.get('timestamp')
        if timestamp:
            st.metric("Last Audited", timestamp[:10] if len(timestamp) > 10 else timestamp)
    
    # Issue breakdown
    st.subheader("Issue Breakdown")
    
    issue_categories = [
        ('Missing Fields', audit.get('missing_fields', [])),
        ('Flagged Issues', audit.get('flagged_issues', [])),
        ('Schema Errors', audit.get('schema_errors', [])),
        ('Metadata Issues', audit.get('metadata_issues', []))
    ]
    
    for category, issues in issue_categories:
        if issues:
            with st.expander(f"{category} ({len(issues)})"):
                for issue in issues:
                    st.markdown(f"• {issue}")
        else:
            st.success(f"✅ {category}: No issues")
    
    # Re-audit button
    st.subheader("Actions")
    if st.button("🔍 Re-run Audit", use_container_width=True):
        run_bundle_audit(bundle_data['id'])


def show_config_sync(bundle_data):
    """Show configuration and sync data"""
    
    if not bundle_data['sync_data']:
        st.warning("No sync data found")
        return
    
    sync_data = bundle_data['sync_data']
    
    # Input data
    st.subheader("Input Configuration")
    input_data = sync_data.get('input', {})
    if input_data:
        st.json(input_data)
    else:
        st.info("No input data found")
    
    # Output metadata
    st.subheader("Generation Metadata")
    output_data = sync_data.get('output', {})
    if output_data:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Generation Time", f"{output_data.get('generation_time', 0):.2f}s")
            st.metric("Model Used", output_data.get('model_used', 'Unknown'))
        
        with col2:
            st.metric("Bundle Path", output_data.get('bundle_path', 'Unknown'))
            timestamp = output_data.get('timestamp', '')
            if timestamp:
                st.metric("Generated", timestamp[:19] if len(timestamp) > 19 else timestamp)
    else:
        st.info("No output metadata found")
    
    # Raw sync data
    with st.expander("Raw Sync Data"):
        st.json(sync_data)


def show_fix_history(bundle_data):
    """Show fix history if available"""
    
    if not bundle_data['fix_history']:
        st.info("No fix history found - this bundle has not been fixed")
        return
    
    fix_history = bundle_data['fix_history']
    
    # Handle both single fix and array of fixes
    if isinstance(fix_history, dict):
        fix_history = [fix_history]
    
    st.subheader(f"Fix History ({len(fix_history)} fixes)")
    
    for i, fix in enumerate(fix_history, 1):
        with st.expander(f"Fix #{i} - {fix.get('timestamp', 'Unknown time')[:19]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Original Score", f"{fix.get('original_score', 0):.1f}")
                st.metric("New Score", f"{fix.get('new_score', 0):.1f}")
                improvement = fix.get('new_score', 0) - fix.get('original_score', 0)
                st.metric("Improvement", f"+{improvement:.1f}" if improvement > 0 else f"{improvement:.1f}")
            
            with col2:
                st.metric("Fix Time", f"{fix.get('fix_time', 0):.2f}s")
                st.metric("Model Used", fix.get('model_used', 'Unknown'))
            
            # Issues fixed
            issues_fixed = fix.get('issues_fixed', {})
            if issues_fixed:
                st.markdown("**Issues Fixed:**")
                for category, issues in issues_fixed.items():
                    if issues:
                        st.markdown(f"• **{category}:** {', '.join(issues) if isinstance(issues, list) else issues}")


def show_raw_files(bundle_data):
    """Show raw file contents"""
    
    st.subheader("Raw Bundle Files")
    
    bundle_dir = Path(bundle_data['path'])
    
    # List all files in bundle
    all_files = list(bundle_dir.glob('*'))
    
    if not all_files:
        st.warning("No files found in bundle directory")
        return
    
    # File selector
    selected_file = st.selectbox(
        "Select file to view",
        [f.name for f in all_files if f.is_file()]
    )
    
    if selected_file:
        file_path = bundle_dir / selected_file
        
        try:
            # Determine file type and display appropriately
            if selected_file.endswith('.json'):
                with open(file_path, 'r') as f:
                    content = json.load(f)
                st.json(content)
            
            elif selected_file.endswith('.html'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.code(content, language='html')
            
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.text_area("File Content", content, height=400)
            
            # Download button
            with open(file_path, 'rb') as f:
                st.download_button(
                    label=f"📥 Download {selected_file}",
                    data=f.read(),
                    file_name=selected_file,
                    mime="application/octet-stream"
                )
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")


def validate_html_content(html_content):
    """Validate HTML content and show results"""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        validation_results = []
        
        # Check for title
        title = soup.find('title')
        if title and title.text.strip():
            validation_results.append({"Check": "Title Tag", "Status": "✅ Pass", "Details": f"'{title.text.strip()[:50]}...'"})
        else:
            validation_results.append({"Check": "Title Tag", "Status": "❌ Fail", "Details": "Missing or empty title"})
        
        # Check for meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            validation_results.append({"Check": "Meta Description", "Status": "✅ Pass", "Details": f"Length: {len(meta_desc.get('content'))}"})
        else:
            validation_results.append({"Check": "Meta Description", "Status": "❌ Fail", "Details": "Missing meta description"})
        
        # Check for JSON-LD schema
        schema_script = soup.find('script', attrs={'type': 'application/ld+json'})
        if schema_script and schema_script.string:
            try:
                json.loads(schema_script.string)
                validation_results.append({"Check": "JSON-LD Schema", "Status": "✅ Pass", "Details": "Valid JSON-LD found"})
            except json.JSONDecodeError:
                validation_results.append({"Check": "JSON-LD Schema", "Status": "❌ Fail", "Details": "Invalid JSON-LD format"})
        else:
            validation_results.append({"Check": "JSON-LD Schema", "Status": "❌ Fail", "Details": "No JSON-LD schema found"})
        
        # Check for Open Graph tags
        og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
        if og_tags:
            validation_results.append({"Check": "Open Graph Tags", "Status": "✅ Pass", "Details": f"{len(og_tags)} OG tags found"})
        else:
            validation_results.append({"Check": "Open Graph Tags", "Status": "⚠️ Warning", "Details": "No Open Graph tags found"})
        
        # Display validation results
        st.subheader("HTML Validation Results")
        validation_df = pd.DataFrame(validation_results)
        st.dataframe(validation_df, use_container_width=True)
        
        # Summary
        passed = sum(1 for r in validation_results if "✅" in r["Status"])
        total = len(validation_results)
        st.metric("Validation Score", f"{passed}/{total}", f"{(passed/total*100):.1f}%")
    
    except Exception as e:
        st.error(f"Error validating HTML: {str(e)}")


def run_bundle_audit(bundle_id):
    """Run audit for specific bundle"""
    
    try:
        import subprocess
        
        with st.spinner(f"Running audit for {bundle_id}..."):
            result = subprocess.run([
                'python', 'cli.py', 'audit', bundle_id
            ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            st.success(f"✅ Audit completed for {bundle_id}")
            if result.stdout:
                st.text_area("Audit Results", result.stdout, height=200)
            
            # Clear cache to refresh data
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"❌ Audit failed: {result.stderr}")
    
    except Exception as e:
        st.error(f"Error running audit: {str(e)}")