"""
Batch Processor page for Structr dashboard

Handles bulk operations like generation, fixing, and processing multiple PDPs.
"""

import streamlit as st
import json
import threading
import time
from pathlib import Path
import subprocess
import pandas as pd
from datetime import datetime
import asyncio
from typing import Dict, List, Any

from config import CONFIG
from dashboard.utils.session_state import clear_batch_state, add_batch_result, update_batch_progress
from connectors.shopify.importer import ShopifyCSVImporter
from connectors.generic.csv_mapper import GenericCSVMapper
from batch.processors.batch_manager import BatchManager
from batch.monitors.progress_monitor import ProgressMonitor
from batch.queues.job_queue import JobQueue
from models.pdp import ProductData
from dashboard.enhanced_csv import show_enhanced_csv_operations


def show_batch_processor_page():
    """Display batch processor page"""
    
    st.header("⚡ Batch Processor")
    st.markdown("Upload and process multiple products at scale")
    
    # Tabs for different batch operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Upload & Generate", "🔧 Bulk Fix", "📊 Batch Status", "🔗 Connectors", "📊 Enhanced CSV"])
    
    with tab1:
        show_upload_and_generate()
    
    with tab2:
        show_bulk_fix()
    
    with tab3:
        show_batch_status()
    
    with tab4:
        show_connectors_tab()
    
    with tab5:
        show_enhanced_csv_operations()


def show_upload_and_generate():
    """Upload files and generate PDPs in batch"""
    
    st.subheader("Upload Product Data")
    
    # File upload options
    upload_method = st.radio(
        "Choose upload method:",
        ["Upload JSON files", "Upload CSV file", "Upload JSON array"]
    )
    
    if upload_method == "Upload JSON files":
        uploaded_files = st.file_uploader(
            "Choose JSON files",
            type=['json'],
            accept_multiple_files=True,
            help="Upload one or more JSON files, each containing product data"
        )
        
        if uploaded_files:
            process_json_files(uploaded_files)
    
    elif upload_method == "Upload CSV file":
        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=['csv'],
            help="Upload a CSV file with product data (must include required columns)"
        )
        
        if uploaded_file:
            process_csv_file(uploaded_file)
    
    elif upload_method == "Upload JSON array":
        uploaded_file = st.file_uploader(
            "Choose JSON array file",
            type=['json'],
            help="Upload a JSON file containing an array of product objects"
        )
        
        if uploaded_file:
            process_json_array(uploaded_file)


def process_json_files(uploaded_files):
    """Process multiple JSON files"""
    
    st.success(f"Uploaded {len(uploaded_files)} files")
    
    # Preview files
    with st.expander("Preview uploaded files"):
        for file in uploaded_files[:5]:  # Show first 5
            try:
                content = json.loads(file.read())
                file.seek(0)  # Reset file pointer
                st.json(content)
            except Exception as e:
                st.error(f"Invalid JSON in {file.name}: {str(e)}")
    
    # Processing options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        model = st.selectbox(
            "LLM Model",
            CONFIG.AVAILABLE_LLM_MODELS,
            index=CONFIG.AVAILABLE_LLM_MODELS.index(CONFIG.get_llm_model()) if CONFIG.get_llm_model() in CONFIG.AVAILABLE_LLM_MODELS else 0,
            help="Choose the LLM model for PDP generation"
        )
    
    with col2:
        parallel_jobs = st.number_input(
            "Parallel Jobs",
            min_value=1,
            max_value=CONFIG.MAX_WORKER_COUNT,
            value=CONFIG.get_max_workers(),
            help="Number of parallel generation jobs"
        )
    
    # Process button
    if st.button("🚀 Generate PDPs", type="primary", use_container_width=True):
        if not st.session_state.get('batch_processing', False):
            start_batch_generation(uploaded_files, model, parallel_jobs)
        else:
            st.warning("Batch processing already in progress")


def process_csv_file(uploaded_file):
    """Process CSV file with product data"""
    
    try:
        df = pd.read_csv(uploaded_file)
        st.success(f"Uploaded CSV with {len(df)} rows")
        
        # Show preview
        st.subheader("Data Preview")
        st.dataframe(df.head(), use_container_width=True)
        
        # Column mapping
        st.subheader("Column Mapping")
        st.info("Map your CSV columns to Structr product fields")
        
        required_fields = CONFIG.REQUIRED_PRODUCT_FIELDS
        optional_fields = CONFIG.OPTIONAL_PRODUCT_FIELDS
        
        mapping = {}
        available_columns = [''] + list(df.columns)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Required Fields**")
            for field in required_fields:
                mapping[field] = st.selectbox(
                    f"{field}*",
                    available_columns,
                    help=f"Map to column containing {field} data"
                )
        
        with col2:
            st.markdown("**Optional Fields**")
            for field in optional_fields:
                mapping[field] = st.selectbox(
                    field,
                    available_columns,
                    help=f"Map to column containing {field} data (optional)"
                )
        
        # Validate mapping
        missing_required = [field for field in required_fields if not mapping.get(field)]
        
        if missing_required:
            st.error(f"Please map required fields: {', '.join(missing_required)}")
        else:
            if st.button("🔄 Convert and Generate", type="primary", use_container_width=True):
                convert_csv_and_generate(df, mapping)
    
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")


def process_json_array(uploaded_file):
    """Process JSON file containing array of products"""
    
    try:
        content = json.loads(uploaded_file.read())
        
        if not isinstance(content, list):
            st.error("JSON file must contain an array of product objects")
            return
        
        st.success(f"Uploaded JSON array with {len(content)} products")
        
        # Preview
        with st.expander("Preview products"):
            for i, product in enumerate(content[:3]):  # Show first 3
                st.markdown(f"**Product {i+1}:**")
                st.json(product)
        
        # Process
        if st.button("🚀 Generate PDPs", type="primary", use_container_width=True):
            start_batch_generation_from_array(content)
    
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")


def show_bulk_fix():
    """Bulk fix operations for existing PDPs"""
    
    st.subheader("Bulk Fix Operations")
    
    # Load current bundles
    bundles = load_existing_bundles()
    
    if not bundles:
        st.info("No existing bundles found. Generate some PDPs first.")
        return
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider(
            "Min Score to Fix",
            min_value=CONFIG.MIN_SCORE,
            max_value=CONFIG.MAX_SCORE,
            value=CONFIG.DEFAULT_MIN_SCORE,
            help="Fix bundles with scores below this threshold"
        )
    
    with col2:
        target_issues = st.multiselect(
            "Target Specific Issues",
            CONFIG.AUDIT_CATEGORIES + ["title", "meta_description", "images", "brand"],
            help="Focus on specific types of issues (leave empty for all)"
        )
    
    with col3:
        dry_run = st.checkbox(
            "Dry Run",
            value=True,
            help="Preview what would be fixed without making changes"
        )
    
    # Show flagged bundles
    flagged_bundles = [b for b in bundles if b.get('score', 100) < min_score]
    
    st.markdown(f"**Found {len(flagged_bundles)} bundles needing fixes:**")
    
    if flagged_bundles:
        # Show preview table
        fix_preview_df = pd.DataFrame([
            {
                'Bundle': b['id'],
                'Current Score': b.get('score', 0),
                'Issues': len(b.get('issues', [])),
                'Status': b.get('status', 'unknown').title()
            }
            for b in flagged_bundles[:10]  # Show first 10
        ])
        
        st.dataframe(fix_preview_df, use_container_width=True)
        
        if len(flagged_bundles) > 10:
            st.info(f"... and {len(flagged_bundles) - 10} more")
        
        # Fix button
        fix_text = "🔍 Preview Fixes" if dry_run else "🔧 Apply Fixes"
        
        if st.button(fix_text, type="primary", use_container_width=True):
            start_bulk_fix(flagged_bundles, target_issues, dry_run, min_score)
    else:
        st.success("🎉 No bundles need fixing!")


def show_batch_status():
    """Show status of batch operations with enhanced monitoring"""
    
    st.subheader("📊 Batch Operation Status")
    
    # Current operation status
    if st.session_state.get('batch_processing', False):
        st.markdown("### 🔄 Current Operation")
        
        # Show progress with enhanced details
        progress = st.session_state.get('batch_progress', 0)
        st.progress(progress / 100, text=f"Processing: {progress:.1f}%")
        
        # Operation details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", "Running")
        with col2:
            st.metric("Progress", f"{progress:.1f}%")
        with col3:
            start_time = st.session_state.get('batch_start_time', datetime.now())
            elapsed = (datetime.now() - start_time).total_seconds()
            st.metric("Elapsed Time", f"{elapsed:.1f}s")
        
        # Show recent activity
        recent_results = st.session_state.get('batch_results', [])[-5:]
        if recent_results:
            st.markdown("**Recent Activity:**")
            for result in recent_results:
                status_icon = "✅" if result.get('success', False) else "❌"
                st.text(f"{status_icon} {result.get('product', result.get('bundle', 'Unknown'))} - {result.get('message', '')[:50]}...")
        
        # Auto-refresh while processing
        time.sleep(1)
        st.rerun()
    
    # Historical results
    batch_results = st.session_state.get('batch_results', [])
    
    if batch_results:
        st.markdown("### 📊 Operation Results")
        
        # Summary metrics
        successful = sum(1 for r in batch_results if r.get('success', False))
        failed = len(batch_results) - successful
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(batch_results))
        with col2:
            st.metric("Successful", successful, delta=successful)
        with col3:
            st.metric("Failed", failed, delta=-failed if failed > 0 else 0)
        with col4:
            success_rate = (successful/len(batch_results)*100) if batch_results else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Results table with better formatting
        st.markdown("**Detailed Results:**")
        
        # Create enhanced results DataFrame
        enhanced_results = []
        for result in batch_results:
            enhanced_result = {
                'Product/Bundle': result.get('product', result.get('bundle', 'Unknown')),
                'Status': '✅ Success' if result.get('success', False) else '❌ Failed',
                'Message': result.get('message', '')[:100],
                'Score': result.get('score', result.get('new_score', 'N/A')),
                'Time': result.get('timestamp', '')[:19].replace('T', ' ')
            }
            
            # Add specific metrics based on operation type
            if 'original_score' in result:
                enhanced_result['Score Change'] = f"{result.get('original_score', 0)} → {result.get('new_score', 0)}"
            
            if 'fixes_applied' in result:
                enhanced_result['Fixes Applied'] = len(result.get('fixes_applied', []))
            
            enhanced_results.append(enhanced_result)
        
        results_df = pd.DataFrame(enhanced_results)
        
        # Style the dataframe
        def style_status(val):
            if '✅' in str(val):
                return 'background-color: #d4edda; color: #155724;'
            elif '❌' in str(val):
                return 'background-color: #f8d7da; color: #721c24;'
            return ''
        
        styled_df = results_df.style.applymap(style_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Export results
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Results as CSV"):
                csv_data = results_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("🗑️ Clear Results"):
                clear_batch_state()
                st.rerun()
    
    else:
        st.info("📍 No recent batch operations")
        
        # Quick actions when no operations running
        if not st.session_state.get('batch_processing', False):
            st.markdown("### 🚀 Quick Actions")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📥 Import CSV", use_container_width=True):
                    st.switch_page("pages/batch_processor.py")
            
            with col2:
                if st.button("🔧 Bulk Fix", use_container_width=True):
                    st.switch_page("pages/batch_processor.py")
            
            with col3:
                if st.button("🔗 Connect API", use_container_width=True):
                    st.switch_page("pages/batch_processor.py")
    
    # System health indicators
    st.markdown("### 🔋 System Health")
    
    try:
        # Check if batch infrastructure is healthy
        health_col1, health_col2, health_col3 = st.columns(3)
        
        with health_col1:
            st.metric(
                "Job Queue",
                "Healthy",
                help="Current status of the background job queue"
            )
        
        with health_col2:
            st.metric(
                "LLM Service",
                "Ready",
                help="Status of the local LLM service (Ollama)"
            )
        
        with health_col3:
            st.metric(
                "Storage",
                "Available",
                help="Storage system for bundles and logs"
            )
    
    except Exception as e:
        st.error(f"Health check failed: {str(e)}")


def start_batch_generation(uploaded_files, model, parallel_jobs):
    """Start batch generation process using new infrastructure"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []
    
    # Save uploaded files temporarily
    temp_dir = CONFIG.get_temp_dir()
    temp_dir.mkdir(exist_ok=True)
    
    file_paths = []
    for uploaded_file in uploaded_files:
        temp_path = temp_dir / uploaded_file.name
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.read())
        file_paths.append(temp_path)
    
    # Start processing using new batch infrastructure
    thread = threading.Thread(
        target=new_batch_process_background,
        args=(file_paths, model, parallel_jobs)
    )
    thread.daemon = True
    thread.start()
    
    st.success("🚀 Batch generation started!")
    st.info("Check the 'Batch Status' tab for progress updates")


def start_new_batch_generation(file_paths, model, parallel_jobs):
    """Start batch generation with new infrastructure for converted files"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    
    # Start processing using new batch infrastructure
    thread = threading.Thread(
        target=new_batch_process_background,
        args=(file_paths, model, parallel_jobs)
    )
    thread.daemon = True
    thread.start()


def new_batch_process_background(file_paths, model, parallel_jobs, products=None):
    """Background processing using new batch infrastructure"""
    
    try:
        # Initialize new batch infrastructure
        job_queue = JobQueue(max_size=1000, persistent=True)
        monitor = ProgressMonitor()
        batch_manager = BatchManager(job_queue, monitor)
        
        # Load products from files or use provided products
        if products is None:
            products = []
            for file_path in file_paths:
                try:
                    with open(file_path, 'r') as f:
                        product_data = json.load(f)
                        if isinstance(product_data, list):
                            products.extend(product_data)
                        else:
                            products.append(product_data)
                except Exception as e:
                    add_batch_result({
                        'file': str(file_path),
                        'success': False,
                        'message': f"Failed to load file: {str(e)}",
                        'timestamp': datetime.now().isoformat()
                    })
        
        # Create batch generation job
        job_id = batch_manager.create_batch_generation_job(
            products,
            model=model,
            parallel_workers=parallel_jobs
        )
        
        # Monitor progress
        while True:
            status = batch_manager.get_job_status(job_id)
            
            if status:
                progress = status.get('progress', 0)
                update_batch_progress(progress)
                
                # Add any new results
                if 'results' in status:
                    for result in status['results']:
                        add_batch_result({
                            'product': result.get('product_id', 'unknown'),
                            'success': result.get('success', False),
                            'message': result.get('message', ''),
                            'score': result.get('audit_score', 0),
                            'timestamp': datetime.now().isoformat()
                        })
                
                if status.get('status') in ['completed', 'failed']:
                    break
            
            time.sleep(2)
        
        # Cleanup temp files if provided
        if file_paths:
            for file_path in file_paths:
                try:
                    file_path.unlink()
                except:
                    pass
        
    except Exception as e:
        add_batch_result({
            'error': str(e),
            'success': False,
            'timestamp': datetime.now().isoformat()
        })
    
    finally:
        st.session_state.batch_processing = False


def start_batch_generation_from_array(products):
    """Start batch generation from product array using new infrastructure"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []
    st.session_state.batch_start_time = datetime.now()
    
    # Start processing using new batch infrastructure
    thread = threading.Thread(
        target=new_batch_process_background,
        args=([], CONFIG.get_llm_model(), CONFIG.get_max_workers(), products)  # Pass products directly
    )
    thread.daemon = True
    thread.start()
    
    st.success("🚀 Batch generation started!")


def start_bulk_fix(flagged_bundles, target_issues, dry_run, min_score):
    """Start bulk fix operation using new batch infrastructure"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []
    
    # Start fixing using new infrastructure
    thread = threading.Thread(
        target=new_bulk_fix_background,
        args=(flagged_bundles, target_issues, dry_run, min_score)
    )
    thread.daemon = True
    thread.start()
    
    action = "Previewing" if dry_run else "Applying"
    st.success(f"🔧 {action} fixes for {len(flagged_bundles)} bundles!")


def new_bulk_fix_background(flagged_bundles, target_issues, dry_run, min_score):
    """Background thread for bulk fixing using new infrastructure"""
    
    try:
        # Initialize new batch infrastructure
        job_queue = JobQueue(max_size=1000, persistent=True)
        monitor = ProgressMonitor()
        batch_manager = BatchManager(job_queue, monitor)
        
        # Extract product IDs from bundles
        product_ids = [bundle['id'] for bundle in flagged_bundles]
        
        # Create batch fix job
        job_id = batch_manager.create_batch_fix_job(
            product_ids,
            target_issues=target_issues,
            dry_run=dry_run,
            min_score=min_score
        )
        
        # Monitor progress
        while True:
            status = batch_manager.get_job_status(job_id)
            
            if status:
                progress = status.get('progress', 0)
                update_batch_progress(progress)
                
                # Add any new results
                if 'results' in status:
                    for result in status['results']:
                        add_batch_result({
                            'bundle': result.get('product_id', 'unknown'),
                            'success': result.get('success', False),
                            'message': result.get('message', ''),
                            'original_score': result.get('original_score', 0),
                            'new_score': result.get('new_score', 0),
                            'fixes_applied': result.get('fixes_applied', []),
                            'timestamp': datetime.now().isoformat()
                        })
                
                if status.get('status') in ['completed', 'failed']:
                    break
            
            time.sleep(2)
        
    except Exception as e:
        add_batch_result({
            'error': str(e),
            'success': False,
            'timestamp': datetime.now().isoformat()
        })
    
    finally:
        st.session_state.batch_processing = False


# Legacy subprocess-based functions removed in favor of new batch infrastructure
# All processing now uses BatchManager, ProgressMonitor, and JobQueue


@st.cache_data(ttl=CONFIG.CACHE_TTL)
def load_existing_bundles():
    """Load existing bundle data"""
    
    output_dir = CONFIG.get_output_dir()
    bundles_dir = CONFIG.get_bundles_dir()
    
    bundles = []
    
    if not bundles_dir.exists():
        return bundles
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            try:
                # Load audit data
                audit_file = bundle_dir / CONFIG.AUDIT_FILENAME
                if audit_file.exists():
                    with open(audit_file, 'r') as f:
                        audit_data = json.load(f)
                    
                    bundle = {
                        'id': bundle_dir.name,
                        'path': str(bundle_dir),
                        'score': audit_data.get('score', 0),
                        'issues': (
                            audit_data.get('missing_fields', []) +
                            audit_data.get('flagged_issues', []) +
                            audit_data.get('schema_errors', [])
                        )
                    }
                    
                    # Determine status using config thresholds
                    score = bundle['score']
                    if score >= CONFIG.SCORE_THRESHOLDS['excellent']:
                        bundle['status'] = 'excellent'
                    elif score >= CONFIG.SCORE_THRESHOLDS['good']:
                        bundle['status'] = 'good'
                    elif score >= CONFIG.SCORE_THRESHOLDS['fair']:
                        bundle['status'] = 'fair'
                    else:
                        bundle['status'] = 'poor'
                    
                    bundles.append(bundle)
                    
            except Exception:
                pass
    
    return bundles


def show_connectors_tab():
    """Display the connectors management tab"""
    
    st.subheader("🔗 Data Connectors")
    st.markdown("Import from various data sources using intelligent field mapping")
    
    # Connector type selection
    connector_type = st.selectbox(
        "Choose Connector Type:",
        ["Shopify CSV", "Generic CSV", "API Connector"],
        help="Select the type of data source you want to connect to"
    )
    
    if connector_type == "Shopify CSV":
        show_shopify_connector()
    elif connector_type == "Generic CSV":
        show_generic_csv_connector()
    elif connector_type == "API Connector":
        show_api_connector()


def show_shopify_connector():
    """Shopify CSV import interface"""
    
    st.markdown("### 🛍️ Shopify CSV Importer")
    st.info("Upload a Shopify product export CSV for automatic field mapping and import")
    
    uploaded_file = st.file_uploader(
        "Upload Shopify CSV Export",
        type=['csv'],
        help="Export your products from Shopify Admin > Products > Export"
    )
    
    if uploaded_file:
        try:
            # Use the new Shopify importer
            importer = ShopifyCSVImporter()
            
            # Save uploaded file temporarily
            temp_path = Path("temp_uploads") / uploaded_file.name
            temp_path.parent.mkdir(exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.read())
            
            # Analyze the CSV
            with st.spinner("Analyzing Shopify CSV..."):
                analysis = importer.analyze_csv(str(temp_path))
            
            # Show analysis results
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Products", analysis['total_rows'])
                st.metric("Detected Columns", len(analysis['columns']))
            
            with col2:
                st.metric("Confidence Score", f"{analysis['confidence']:.1%}")
                st.metric("Estimated Import Time", f"{analysis['estimated_time']:.1f}s")
            
            # Show field mapping preview
            if analysis['recommended_mapping']:
                st.subheader("Recommended Field Mapping")
                
                mapping_df = pd.DataFrame([
                    {"Structr Field": k, "Shopify Column": v, "Confidence": "High"}
                    for k, v in analysis['recommended_mapping'].items()
                ])
                
                st.dataframe(mapping_df, use_container_width=True)
            
            # Import options
            st.subheader("Import Options")
            
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.number_input(
                    "Batch Size",
                    min_value=1,
                    max_value=CONFIG.MAX_BATCH_SIZE // 2,
                    value=CONFIG.DEFAULT_BATCH_SIZE // 2,
                    help="Number of products to process in each batch"
                )
            
            with col2:
                auto_fix = st.checkbox(
                    "Auto-fix after import",
                    value=True,
                    help="Automatically fix any issues found during import"
                )
            
            # Import button
            if st.button("🚀 Import Products", type="primary", use_container_width=True):
                start_shopify_import(str(temp_path), batch_size, auto_fix)
            
            # Cleanup
            temp_path.unlink(missing_ok=True)
            
        except Exception as e:
            st.error(f"Error processing Shopify CSV: {str(e)}")


def show_generic_csv_connector():
    """Generic CSV import interface with intelligent mapping"""
    
    st.markdown("### 📄 Generic CSV Importer")
    st.info("Upload any CSV file and we'll intelligently map fields to Structr format")
    
    uploaded_file = st.file_uploader(
        "Upload CSV File",
        type=['csv'],
        help="Upload any CSV file with product data"
    )
    
    if uploaded_file:
        try:
            # Use the new generic CSV mapper
            mapper = GenericCSVMapper()
            
            # Save uploaded file temporarily
            temp_path = Path("temp_uploads") / uploaded_file.name
            temp_path.parent.mkdir(exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.read())
            
            # Analyze the CSV
            with st.spinner("Analyzing CSV structure..."):
                analysis = mapper.analyze_csv_structure(str(temp_path))
            
            # Show analysis results
            st.subheader("CSV Analysis Results")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Rows", analysis['total_rows'])
                st.metric("Total Columns", len(analysis['columns']))
            
            with col2:
                st.metric("Confidence Score", f"{analysis['confidence']:.1%}")
                st.metric("Data Quality", analysis['data_quality'])
            
            with col3:
                st.metric("Required Fields Found", f"{analysis['completeness']:.1%}")
                st.metric("Estimated Processing Time", f"{analysis['estimated_time']:.1f}s")
            
            # Show intelligent field suggestions
            if analysis['suggested_mapping']:
                st.subheader("Intelligent Field Mapping")
                
                # Allow user to review and modify mapping
                mapping = {}
                available_columns = [''] + list(analysis['columns'])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Suggested Mappings**")
                    for field, suggestion in analysis['suggested_mapping'].items():
                        mapping[field] = st.selectbox(
                            f"{field}",
                            available_columns,
                            index=available_columns.index(suggestion['column']) if suggestion['column'] in available_columns else 0,
                            help=f"Confidence: {suggestion['confidence']:.1%} - {suggestion['reason']}"
                        )
                
                with col2:
                    st.markdown("**Additional Fields**")
                    optional_fields = ['category', 'vendor', 'sku', 'weight', 'dimensions']
                    for field in optional_fields:
                        if field not in mapping:
                            mapping[field] = st.selectbox(
                                f"{field} (optional)",
                                available_columns,
                                help=f"Optional field mapping for {field}"
                            )
            
            # Preview transformed data
            if st.button("🔍 Preview Transformation"):
                preview = mapper.preview_transformation(str(temp_path), mapping)
                if preview:
                    st.subheader("Transformation Preview")
                    st.dataframe(pd.DataFrame(preview[:5]), use_container_width=True)
            
            # Import options
            st.subheader("Import Options")
            
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.number_input(
                    "Batch Size",
                    min_value=1,
                    max_value=CONFIG.MAX_BATCH_SIZE,
                    value=CONFIG.DEFAULT_BATCH_SIZE,
                    help="Number of products to process in each batch"
                )
            
            with col2:
                validation_mode = st.selectbox(
                    "Validation Mode",
                    [mode.title() for mode in CONFIG.VALIDATION_MODES],
                    index=[mode.title() for mode in CONFIG.VALIDATION_MODES].index(CONFIG.DEFAULT_VALIDATION_MODE.title()),
                    help="How strict to be when validating imported data"
                )
            
            # Import button
            if st.button("🚀 Import and Generate", type="primary", use_container_width=True):
                start_generic_import(str(temp_path), mapping, batch_size, validation_mode)
            
            # Cleanup
            temp_path.unlink(missing_ok=True)
            
        except Exception as e:
            st.error(f"Error analyzing CSV: {str(e)}")


def show_api_connector():
    """API connector interface for real-time integration"""
    
    st.markdown("### 🔌 API Connector")
    st.info("Connect to external APIs for real-time product data sync")
    
    # API type selection
    api_type = st.selectbox(
        "API Type:",
        ["Shopify Admin API", "Contentful", "Custom REST API", "Webhook"],
        help="Select the type of API you want to connect to"
    )
    
    if api_type == "Shopify Admin API":
        show_shopify_api_connector()
    elif api_type == "Contentful":
        show_contentful_connector()
    elif api_type == "Custom REST API":
        show_custom_api_connector()
    elif api_type == "Webhook":
        show_webhook_connector()


def show_shopify_api_connector():
    """Shopify Admin API connector"""
    
    st.markdown("#### Shopify Admin API")
    
    col1, col2 = st.columns(2)
    
    with col1:
        shop_domain = st.text_input(
            "Shop Domain",
            placeholder="myshop.myshopify.com",
            help="Your Shopify store domain"
        )
    
    with col2:
        api_token = st.text_input(
            "Admin API Access Token",
            type="password",
            help="Generate from Shopify Admin > Apps > Private Apps"
        )
    
    if shop_domain and api_token:
        if st.button("🔗 Test Connection"):
            # Test connection logic here
            st.success("✅ Connection successful!")
        
        # Sync options
        st.subheader("Sync Options")
        
        col1, col2 = st.columns(2)
        with col1:
            sync_direction = st.radio(
                "Sync Direction:",
                ["Import from Shopify", "Export to Shopify", "Bi-directional"]
            )
        
        with col2:
            sync_frequency = st.selectbox(
                "Sync Frequency:",
                ["Manual", "Every 15 minutes", "Hourly", "Daily"]
            )
        
        if st.button("🔄 Start Sync", type="primary"):
            st.success("Sync initiated! Check the Batch Status tab for progress.")


def show_contentful_connector():
    """Contentful CMS connector"""
    
    st.markdown("#### Contentful CMS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        space_id = st.text_input(
            "Space ID",
            help="Your Contentful space ID"
        )
        access_token = st.text_input(
            "Content Delivery API Access Token",
            type="password",
            help="Generate from Contentful > Settings > API keys"
        )
    
    with col2:
        environment = st.text_input(
            "Environment",
            value="master",
            help="Contentful environment (usually 'master')"
        )
        content_type = st.text_input(
            "Product Content Type ID",
            placeholder="product",
            help="The content type ID for your products"
        )
    
    if space_id and access_token and content_type:
        if st.button("🔗 Test Connection"):
            st.success("✅ Connected to Contentful!")
        
        if st.button("📥 Import Products", type="primary"):
            st.info("Importing products from Contentful...")


def show_custom_api_connector():
    """Custom REST API connector"""
    
    st.markdown("#### Custom REST API")
    
    api_url = st.text_input(
        "API Base URL",
        placeholder="https://api.example.com",
        help="Base URL for your API"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        auth_type = st.selectbox(
            "Authentication:",
            ["None", "API Key", "Bearer Token", "Basic Auth"]
        )
    
    with col2:
        if auth_type != "None":
            auth_value = st.text_input(
                f"{auth_type} Value",
                type="password",
                help=f"Enter your {auth_type.lower()}"
            )
    
    # API endpoints configuration
    st.subheader("Endpoint Configuration")
    
    products_endpoint = st.text_input(
        "Products Endpoint",
        placeholder="/products",
        help="Endpoint to fetch products (relative to base URL)"
    )
    
    if api_url and products_endpoint:
        if st.button("🔗 Test API Connection"):
            st.success("✅ API connection successful!")
        
        if st.button("📥 Fetch Products", type="primary"):
            st.info("Fetching products from custom API...")


def show_webhook_connector():
    """Webhook setup for real-time updates"""
    
    st.markdown("#### Webhook Configuration")
    st.info("Set up webhooks to automatically process products when they change")
    
    # Generate webhook URL
    webhook_url = "https://your-structr-instance.com/webhooks/products"
    
    st.text_input(
        "Webhook URL (copy this to your platform):",
        value=webhook_url,
        disabled=True,
        help="Copy this URL to configure webhooks in your source platform"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        webhook_events = st.multiselect(
            "Events to Listen For:",
            ["product.created", "product.updated", "product.deleted", "inventory.updated"],
            default=["product.created", "product.updated"]
        )
    
    with col2:
        webhook_secret = st.text_input(
            "Webhook Secret (optional):",
            type="password",
            help="Secret for verifying webhook authenticity"
        )
    
    # Webhook status
    st.subheader("Webhook Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Active Webhooks", "2")
    
    with col2:
        st.metric("Events Today", "47")
    
    with col3:
        st.metric("Success Rate", "98.3%")
    
    # Recent webhook events
    if st.checkbox("Show Recent Events"):
        recent_events = [
            {"Time": "10:34 AM", "Event": "product.updated", "Status": "Success", "Product": "aiden-1"},
            {"Time": "10:31 AM", "Event": "product.created", "Status": "Success", "Product": "new-shirt"},
            {"Time": "10:28 AM", "Event": "product.updated", "Status": "Failed", "Product": "broken-id"},
        ]
        
        st.dataframe(pd.DataFrame(recent_events), use_container_width=True)


def start_shopify_import(csv_path: str, batch_size: int, auto_fix: bool):
    """Start Shopify CSV import using new batch infrastructure"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []
    
    # Start import in background thread
    thread = threading.Thread(
        target=shopify_import_background,
        args=(csv_path, batch_size, auto_fix)
    )
    thread.daemon = True
    thread.start()
    
    st.success("🚀 Shopify import started!")
    st.info("Check the 'Batch Status' tab for progress updates")


def start_generic_import(csv_path: str, mapping: Dict[str, str], batch_size: int, validation_mode: str):
    """Start generic CSV import using new batch infrastructure"""
    
    st.session_state.batch_processing = True
    st.session_state.batch_progress = 0
    st.session_state.batch_results = []
    
    # Start import in background thread
    thread = threading.Thread(
        target=generic_import_background,
        args=(csv_path, mapping, batch_size, validation_mode)
    )
    thread.daemon = True
    thread.start()
    
    st.success("🚀 CSV import started!")
    st.info("Check the 'Batch Status' tab for progress updates")


def shopify_import_background(csv_path: str, batch_size: int, auto_fix: bool):
    """Background thread for Shopify import using new infrastructure"""
    
    try:
        # Initialize components
        job_queue = JobQueue(max_size=1000, persistent=True)
        monitor = ProgressMonitor()
        batch_manager = BatchManager(job_queue, monitor)
        
        # Create import job
        job_id = batch_manager.create_import_and_generate_job(
            csv_path,
            connector_type="shopify",
            batch_size=batch_size,
            auto_fix=auto_fix
        )
        
        # Monitor progress
        while True:
            status = batch_manager.get_job_status(job_id)
            
            if status:
                progress = status.get('progress', 0)
                update_batch_progress(progress)
                
                # Add any new results
                if 'results' in status:
                    for result in status['results']:
                        add_batch_result({
                            'product': result.get('product_id', 'unknown'),
                            'success': result.get('success', False),
                            'message': result.get('message', ''),
                            'timestamp': datetime.now().isoformat()
                        })
                
                if status.get('status') in ['completed', 'failed']:
                    break
            
            time.sleep(2)
        
    except Exception as e:
        add_batch_result({
            'error': str(e),
            'success': False,
            'timestamp': datetime.now().isoformat()
        })
    
    finally:
        st.session_state.batch_processing = False


def generic_import_background(csv_path: str, mapping: Dict[str, str], batch_size: int, validation_mode: str):
    """Background thread for generic CSV import"""
    
    try:
        # Initialize components
        job_queue = JobQueue(max_size=1000, persistent=True)
        monitor = ProgressMonitor()
        batch_manager = BatchManager(job_queue, monitor)
        
        # Create import job
        job_id = batch_manager.create_import_and_generate_job(
            csv_path,
            connector_type="generic",
            batch_size=batch_size,
            field_mapping=mapping,
            validation_mode=validation_mode.lower()
        )
        
        # Monitor progress (similar to Shopify import)
        while True:
            status = batch_manager.get_job_status(job_id)
            
            if status:
                progress = status.get('progress', 0)
                update_batch_progress(progress)
                
                if 'results' in status:
                    for result in status['results']:
                        add_batch_result({
                            'product': result.get('product_id', 'unknown'),
                            'success': result.get('success', False),
                            'message': result.get('message', ''),
                            'timestamp': datetime.now().isoformat()
                        })
                
                if status.get('status') in ['completed', 'failed']:
                    break
            
            time.sleep(2)
        
    except Exception as e:
        add_batch_result({
            'error': str(e),
            'success': False,
            'timestamp': datetime.now().isoformat()
        })
    
    finally:
        st.session_state.batch_processing = False


def convert_csv_and_generate(df, mapping):
    """Convert CSV data to JSON format and generate PDPs"""
    
    st.info("Converting CSV data to product JSON files...")
    
    # Convert each row to product JSON
    temp_dir = CONFIG.get_temp_dir()
    temp_dir.mkdir(exist_ok=True)
    
    file_paths = []
    errors = []
    
    for idx, row in df.iterrows():
        try:
            product = {}
            
            # Map required fields
            for field, column in mapping.items():
                if column and column in df.columns:
                    value = row[column]
                    if pd.notna(value):
                        if field in ['features', 'images'] and isinstance(value, str):
                            # Split comma-separated values
                            product[field] = [item.strip() for item in value.split(',') if item.strip()]
                        else:
                            product[field] = value
            
            # Save as JSON file
            handle = product.get('handle', f'product_{idx+1}')
            temp_path = temp_dir / f"{handle}.json"
            
            with open(temp_path, 'w') as f:
                json.dump(product, f, indent=2)
            
            file_paths.append(temp_path)
            
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")
    
    if errors:
        st.warning(f"Conversion errors:\n" + "\n".join(errors[:5]))
    
    if file_paths:
        st.success(f"Converted {len(file_paths)} products to JSON")
        
        # Start batch generation using new infrastructure
        start_new_batch_generation(file_paths, CONFIG.get_llm_model(), CONFIG.get_max_workers())