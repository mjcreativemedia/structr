"""
Enhanced CSV import/export functionality for Structr dashboard
"""

import streamlit as st
import pandas as pd
import json
import io
from pathlib import Path
from datetime import datetime
import tempfile
import subprocess

from config import CONFIG

def show_enhanced_csv_operations():
    """Enhanced CSV import and export operations"""
    
    st.header("📊 CSV Import/Export Center")
    
    tab1, tab2, tab3 = st.tabs(["📥 Import CSV", "📤 Export CSV", "🔄 Batch Operations"])
    
    with tab1:
        show_advanced_csv_import()
    
    with tab2:
        show_csv_export_options()
    
    with tab3:
        show_csv_batch_operations()


def show_advanced_csv_import():
    """Advanced CSV import with intelligent mapping"""
    
    st.subheader("📥 Advanced CSV Import")
    
    uploaded_file = st.file_uploader(
        "Upload Product CSV",
        type=['csv'],
        help="Upload a CSV file containing product data"
    )
    
    if uploaded_file:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Show basic info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                duplicates = df.duplicated().sum()
                st.metric("Duplicates", duplicates)
            
            # Preview
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(CONFIG.PREVIEW_ROWS), use_container_width=True)
            
            # Intelligent field mapping
            st.subheader("🧠 Intelligent Field Mapping")
            suggested_mapping = suggest_field_mapping(df.columns)
            
            # Show suggested mapping
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔍 Detected Mappings**")
                for structr_field, suggested_col in suggested_mapping.items():
                    if suggested_col:
                        confidence = calculate_mapping_confidence(structr_field, suggested_col)
                        st.markdown(f"• `{structr_field}` → `{suggested_col}` ({confidence:.0%} confidence)")
            
            with col2:
                st.markdown("**⚙️ Manual Mapping Override**")
                manual_mapping = {}
                available_columns = [''] + list(df.columns)
                
                # Build structr fields from config
                structr_fields = {}
                for field in CONFIG.REQUIRED_PRODUCT_FIELDS:
                    structr_fields[field] = f"{field.title()} (required)"
                for field in CONFIG.OPTIONAL_PRODUCT_FIELDS:
                    structr_fields[field] = f"{field.title()} (optional)"
                
                for field, description in structr_fields.items():
                    default_value = suggested_mapping.get(field, '')
                    manual_mapping[field] = st.selectbox(
                        f"{field}",
                        available_columns,
                        index=available_columns.index(default_value) if default_value in available_columns else 0,
                        help=description,
                        key=f"mapping_{field}"
                    )
            
            # Validation
            final_mapping = {k: v for k, v in manual_mapping.items() if v}
            required_fields = ['handle', 'title', 'description', 'price', 'brand']
            missing_required = [field for field in required_fields if field not in final_mapping or not final_mapping[field]]
            
            if missing_required:
                st.error(f"❌ Missing required field mappings: {', '.join(missing_required)}")
            else:
                # Show mapping preview
                st.subheader("📊 Mapped Data Preview")
                preview_df = create_mapping_preview(df, final_mapping)
                st.dataframe(preview_df.head(), use_container_width=True)
                
                # Import options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    batch_size = st.number_input("Batch Size", min_value=1, max_value=100, value=25)
                
                with col2:
                    model = st.selectbox("LLM Model", ["mistral", "llama2", "codellama"])
                
                with col3:
                    workers = st.number_input("Parallel Workers", min_value=1, max_value=5, value=2)
                
                # Import button
                if st.button("🚀 Import and Generate PDPs", type="primary", use_container_width=True):
                    import_csv_data(df, final_mapping, batch_size, model, workers)
        
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")


def show_csv_export_options():
    """CSV export options for optimized data"""
    
    st.subheader("📤 Export Optimized Data")
    
    # Load existing bundles
    bundles = load_existing_bundles_for_export()
    
    if not bundles:
        st.info("No bundles found to export")
        return
    
    # Export options
    export_format = st.radio(
        "Export Format",
        ["Shopify Import CSV", "Generic Product CSV", "Audit Report CSV", "Custom Format"]
    )
    
    # Filter options
    st.subheader("🔍 Filter Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider("Minimum Score", 0, 100, 0)
    
    with col2:
        status_filter = st.multiselect(
            "Status Filter",
            ["excellent", "good", "fair", "poor"],
            default=["excellent", "good", "fair", "poor"]
        )
    
    with col3:
        fixed_only = st.checkbox("Fixed Bundles Only", value=False)
    
    # Apply filters
    filtered_bundles = apply_export_filters(bundles, min_score, status_filter, fixed_only)
    
    st.info(f"Found {len(filtered_bundles)} bundles matching filters")
    
    if filtered_bundles:
        # Export preview
        if export_format == "Shopify Import CSV":
            export_data = create_shopify_export(filtered_bundles)
            st.subheader("📋 Shopify Import Preview")
            st.dataframe(export_data.head(), use_container_width=True)
            
        elif export_format == "Generic Product CSV":
            export_data = create_generic_export(filtered_bundles)
            st.subheader("📋 Generic Product CSV Preview")
            st.dataframe(export_data.head(), use_container_width=True)
            
        elif export_format == "Audit Report CSV":
            export_data = create_audit_export(filtered_bundles)
            st.subheader("📋 Audit Report Preview")
            st.dataframe(export_data.head(), use_container_width=True)
            
        elif export_format == "Custom Format":
            export_data = create_custom_export(filtered_bundles)
            st.subheader("📋 Custom Format Preview")
            st.dataframe(export_data.head(), use_container_width=True)
        
        # Download button
        if 'export_data' in locals():
            csv_buffer = io.StringIO()
            export_data.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"structr_export_{export_format.lower().replace(' ', '_')}_{timestamp}.csv"
            
            st.download_button(
                label=f"📥 Download {export_format}",
                data=csv_content,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )


def show_csv_batch_operations():
    """Batch operations using CSV data"""
    
    st.subheader("🔄 CSV-Driven Batch Operations")
    
    operation = st.selectbox(
        "Choose Operation",
        ["Audit Multiple Products", "Fix Multiple Products", "Regenerate from CSV", "Bulk Analysis"]
    )
    
    if operation == "Audit Multiple Products":
        show_bulk_audit_from_csv()
    elif operation == "Fix Multiple Products":
        show_bulk_fix_from_csv()
    elif operation == "Regenerate from CSV":
        show_regenerate_from_csv()
    elif operation == "Bulk Analysis":
        show_bulk_analysis_csv()


def suggest_field_mapping(columns):
    """Suggest field mapping based on column names"""
    
    # Common mapping patterns
    mapping_patterns = {
        'handle': ['handle', 'id', 'product_id', 'sku', 'identifier'],
        'title': ['title', 'name', 'product_name', 'product_title'],
        'description': ['description', 'desc', 'body', 'content', 'details'],
        'price': ['price', 'cost', 'amount', 'value'],
        'brand': ['brand', 'vendor', 'manufacturer', 'make'],
        'category': ['category', 'type', 'product_type', 'class'],
        'images': ['image', 'images', 'photo', 'picture', 'img_url'],
        'features': ['features', 'attributes', 'specs', 'specifications'],
        'sku': ['sku', 'part_number', 'product_code']
    }
    
    suggested = {}
    columns_lower = [col.lower() for col in columns]
    
    for field, patterns in mapping_patterns.items():
        best_match = None
        best_score = 0
        
        for col, col_lower in zip(columns, columns_lower):
            for pattern in patterns:
                if pattern in col_lower:
                    score = len(pattern) / len(col_lower)  # Longer matches get higher score
                    if score > best_score:
                        best_score = score
                        best_match = col
        
        suggested[field] = best_match
    
    return suggested


def calculate_mapping_confidence(field, column):
    """Calculate confidence level for field mapping"""
    
    column_lower = column.lower()
    field_lower = field.lower()
    
    if field_lower in column_lower:
        return 0.9
    elif any(keyword in column_lower for keyword in [field_lower[:3], field_lower[-3:]]):
        return 0.7
    else:
        return 0.5


def create_mapping_preview(df, mapping):
    """Create preview of mapped data"""
    
    preview_data = {}
    
    for structr_field, csv_column in mapping.items():
        if csv_column and csv_column in df.columns:
            preview_data[structr_field] = df[csv_column]
    
    return pd.DataFrame(preview_data)


def import_csv_data(df, mapping, batch_size, model, workers):
    """Import and process CSV data"""
    
    try:
        # Create product objects
        products = []
        
        for _, row in df.iterrows():
            product = {}
            
            for structr_field, csv_column in mapping.items():
                if csv_column and csv_column in df.columns:
                    value = row[csv_column]
                    
                    # Handle different data types
                    if pd.notna(value):
                        if structr_field == 'price':
                            try:
                                product[structr_field] = float(str(value).replace('$', '').replace(',', ''))
                            except:
                                product[structr_field] = 0.0
                        elif structr_field in ['features', 'images']:
                            # Handle comma-separated values
                            if isinstance(value, str) and ',' in value:
                                product[structr_field] = [item.strip() for item in value.split(',')]
                            else:
                                product[structr_field] = [str(value)]
                        else:
                            product[structr_field] = str(value)
            
            if product.get('handle') and product.get('title'):
                products.append(product)
        
        if products:
            st.success(f"✅ Created {len(products)} valid product entries")
            
            # Save to temporary file and trigger batch processing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                json.dump(products, tmp_file, indent=2)
                tmp_path = tmp_file.name
            
            # Start batch processing via CLI
            with st.spinner("Starting batch processing..."):
                result = subprocess.run([
                    'python', 'cli.py', 'batch', 'generate',
                    '--input', tmp_path,
                    '--workers', str(workers),
                    '--model', model
                ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                st.success("🚀 Batch processing started successfully!")
                st.info("Check the Batch Status tab to monitor progress")
            else:
                st.error(f"❌ Failed to start batch processing: {result.stderr}")
        
        else:
            st.error("❌ No valid products could be created from the CSV data")
    
    except Exception as e:
        st.error(f"Error importing CSV data: {str(e)}")


def load_existing_bundles_for_export():
    """Load existing bundles with all relevant data"""
    
    output_dir = Path(st.session_state.get('output_dir', 'output'))
    bundles_dir = output_dir / "bundles"
    
    bundles = []
    
    if not bundles_dir.exists():
        return bundles
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            bundle_data = load_bundle_export_data(bundle_dir)
            if bundle_data:
                bundles.append(bundle_data)
    
    return bundles


def load_bundle_export_data(bundle_dir):
    """Load comprehensive bundle data for export"""
    
    bundle_data = {
        'id': bundle_dir.name,
        'path': str(bundle_dir),
        'score': 0,
        'status': 'unknown'
    }
    
    # Load audit data
    audit_file = bundle_dir / "audit.json"
    if audit_file.exists():
        with open(audit_file, 'r') as f:
            audit = json.load(f)
        bundle_data.update(audit)
        
        score = bundle_data.get('score', 0)
        if score >= 90:
            bundle_data['status'] = 'excellent'
        elif score >= 80:
            bundle_data['status'] = 'good'
        elif score >= 60:
            bundle_data['status'] = 'fair'
        else:
            bundle_data['status'] = 'poor'
    
    # Load sync data
    sync_file = bundle_dir / "sync.json"
    if sync_file.exists():
        with open(sync_file, 'r') as f:
            sync = json.load(f)
        
        input_data = sync.get('input', {})
        bundle_data.update(input_data)
    
    # Load HTML content
    html_file = bundle_dir / "index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            bundle_data['html_content'] = f.read()
        
        # Extract optimized metadata
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(bundle_data['html_content'], 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                bundle_data['optimized_title'] = title_tag.text.strip()
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                bundle_data['optimized_meta_description'] = meta_desc.get('content', '')
            
        except:
            pass
    
    # Check fix history
    fix_log_file = bundle_dir / "fix_log.json"
    if fix_log_file.exists():
        with open(fix_log_file, 'r') as f:
            fix_logs = json.load(f)
        bundle_data['fix_count'] = len(fix_logs) if isinstance(fix_logs, list) else 1
        bundle_data['has_been_fixed'] = True
    else:
        bundle_data['fix_count'] = 0
        bundle_data['has_been_fixed'] = False
    
    return bundle_data


def apply_export_filters(bundles, min_score, status_filter, fixed_only):
    """Apply filters to bundle list"""
    
    filtered = []
    
    for bundle in bundles:
        # Score filter
        if bundle.get('score', 0) < min_score:
            continue
        
        # Status filter
        if bundle.get('status') not in status_filter:
            continue
        
        # Fixed only filter
        if fixed_only and not bundle.get('has_been_fixed', False):
            continue
        
        filtered.append(bundle)
    
    return filtered


def create_shopify_export(bundles):
    """Create Shopify-compatible CSV export"""
    
    export_data = []
    
    for bundle in bundles:
        row = {
            'Handle': bundle.get('handle', bundle.get('id', '')),
            'Title': bundle.get('optimized_title', bundle.get('title', '')),
            'Body (HTML)': bundle.get('html_content', ''),
            'Vendor': bundle.get('brand', ''),
            'Product Category': bundle.get('category', ''),
            'Type': bundle.get('product_type', ''),
            'Tags': ', '.join(bundle.get('features', [])) if bundle.get('features') else '',
            'Variant Price': bundle.get('price', 0),
            'Variant SKU': bundle.get('sku', ''),
            'SEO Title': bundle.get('optimized_title', ''),
            'SEO Description': bundle.get('optimized_meta_description', ''),
            'Audit Score': bundle.get('score', 0),
            'Status': bundle.get('status', 'unknown')
        }
        export_data.append(row)
    
    return pd.DataFrame(export_data)


def create_generic_export(bundles):
    """Create generic product CSV export"""
    
    export_data = []
    
    for bundle in bundles:
        row = {
            'Product ID': bundle.get('handle', bundle.get('id', '')),
            'Product Name': bundle.get('optimized_title', bundle.get('title', '')),
            'Description': bundle.get('description', ''),
            'Optimized HTML': bundle.get('html_content', ''),
            'Price': bundle.get('price', 0),
            'Brand': bundle.get('brand', ''),
            'Category': bundle.get('category', ''),
            'Features': ', '.join(bundle.get('features', [])) if bundle.get('features') else '',
            'Images': ', '.join(bundle.get('images', [])) if bundle.get('images') else '',
            'Meta Title': bundle.get('optimized_title', ''),
            'Meta Description': bundle.get('optimized_meta_description', ''),
            'Audit Score': bundle.get('score', 0),
            'Quality Status': bundle.get('status', 'unknown'),
            'Fix Count': bundle.get('fix_count', 0)
        }
        export_data.append(row)
    
    return pd.DataFrame(export_data)


def create_audit_export(bundles):
    """Create audit-focused CSV export"""
    
    export_data = []
    
    for bundle in bundles:
        row = {
            'Bundle ID': bundle.get('id', ''),
            'Product Title': bundle.get('title', ''),
            'Audit Score': bundle.get('score', 0),
            'Status': bundle.get('status', 'unknown'),
            'Missing Fields': len(bundle.get('missing_fields', [])),
            'Flagged Issues': len(bundle.get('flagged_issues', [])),
            'Schema Errors': len(bundle.get('schema_errors', [])),
            'Metadata Issues': len(bundle.get('metadata_issues', [])),
            'Total Issues': (
                len(bundle.get('missing_fields', [])) +
                len(bundle.get('flagged_issues', [])) +
                len(bundle.get('schema_errors', [])) +
                len(bundle.get('metadata_issues', []))
            ),
            'Has Been Fixed': bundle.get('has_been_fixed', False),
            'Fix Count': bundle.get('fix_count', 0),
            'Last Audit': bundle.get('timestamp', ''),
            'Generation Time': bundle.get('generation_time', 0)
        }
        export_data.append(row)
    
    return pd.DataFrame(export_data)


def create_custom_export(bundles):
    """Create customizable export format"""
    
    st.subheader("🔧 Customize Export Fields")
    
    available_fields = {
        'id': 'Bundle ID',
        'title': 'Original Title',
        'optimized_title': 'Optimized Title',
        'description': 'Description',
        'price': 'Price',
        'brand': 'Brand',
        'category': 'Category',
        'score': 'Audit Score',
        'status': 'Quality Status',
        'fix_count': 'Fix Count',
        'has_been_fixed': 'Has Been Fixed',
        'timestamp': 'Last Updated',
        'generation_time': 'Generation Time',
        'html_content': 'Full HTML Content',
        'optimized_meta_description': 'Optimized Meta Description'
    }
    
    selected_fields = st.multiselect(
        "Select fields to export",
        options=list(available_fields.keys()),
        default=['id', 'title', 'score', 'status'],
        format_func=lambda x: available_fields[x]
    )
    
    if selected_fields:
        export_data = []
        
        for bundle in bundles:
            row = {}
            for field in selected_fields:
                value = bundle.get(field, '')
                
                # Format specific field types
                if field in ['features', 'images'] and isinstance(value, list):
                    row[available_fields[field]] = ', '.join(value)
                else:
                    row[available_fields[field]] = value
            
            export_data.append(row)
        
        return pd.DataFrame(export_data)
    
    return pd.DataFrame()


def show_bulk_audit_from_csv():
    """Run bulk audit operations from CSV input"""
    
    st.markdown("Upload a CSV with product handles to audit:")
    
    uploaded_file = st.file_uploader("Product Handles CSV", type=['csv'])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        
        handle_column = st.selectbox("Select handle column", df.columns)
        
        if st.button("🔍 Run Bulk Audit"):
            handles = df[handle_column].tolist()
            run_bulk_audit_operation(handles)


def show_bulk_fix_from_csv():
    """Run bulk fix operations from CSV input"""
    
    st.markdown("Upload a CSV with product handles to fix:")
    
    uploaded_file = st.file_uploader("Product Handles CSV", type=['csv'])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df.head())
        
        handle_column = st.selectbox("Select handle column", df.columns)
        
        if st.button("🔧 Run Bulk Fix"):
            handles = df[handle_column].tolist()
            run_bulk_fix_operation(handles)


def run_bulk_audit_operation(handles):
    """Execute bulk audit operation"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    for i, handle in enumerate(handles):
        status_text.text(f"Auditing {handle}...")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'audit', handle
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                results.append({"Handle": handle, "Status": "✅ Success", "Details": "Audit completed"})
            else:
                results.append({"Handle": handle, "Status": "❌ Failed", "Details": result.stderr})
        
        except Exception as e:
            results.append({"Handle": handle, "Status": "❌ Error", "Details": str(e)})
        
        progress_bar.progress((i + 1) / len(handles))
    
    # Show results
    results_df = pd.DataFrame(results)
    st.subheader("Audit Results")
    st.dataframe(results_df)


def run_bulk_fix_operation(handles):
    """Execute bulk fix operation"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    for i, handle in enumerate(handles):
        status_text.text(f"Fixing {handle}...")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'fix', handle
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                results.append({"Handle": handle, "Status": "✅ Fixed", "Details": "Fix completed"})
            else:
                results.append({"Handle": handle, "Status": "❌ Failed", "Details": result.stderr})
        
        except Exception as e:
            results.append({"Handle": handle, "Status": "❌ Error", "Details": str(e)})
        
        progress_bar.progress((i + 1) / len(handles))
    
    # Show results
    results_df = pd.DataFrame(results)
    st.subheader("Fix Results")
    st.dataframe(results_df)