"""
Schema Validation UI components for Structr dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional

from config import CONFIG
from validators.schema_validator import validate_all_bundles, validate_single_bundle, GoogleProductSchemaValidator


def show_schema_validation_tab():
    """Show the schema validation tab in Audit Manager"""
    
    st.subheader("🔍 Google Product Schema Validation")
    st.markdown("Validate JSON-LD Product schema against Google Merchant requirements")
    
    # Control tabs
    validation_mode = st.radio(
        "Validation Mode:",
        ["All Bundles Overview", "Single Bundle Analysis", "Validation Rules"],
        horizontal=True
    )
    
    if validation_mode == "All Bundles Overview":
        show_all_bundles_validation()
    elif validation_mode == "Single Bundle Analysis":
        show_single_bundle_validation()
    else:
        show_validation_rules()


def show_all_bundles_validation():
    """Show validation results for all bundles"""
    
    st.markdown("### 📊 Schema Validation Overview")
    
    with st.spinner("Validating all product schemas..."):
        validation_results = validate_all_bundles()
    
    if not validation_results:
        st.info("No bundles found to validate")
        return
    
    # Create summary metrics
    show_validation_summary_metrics(validation_results)
    
    # Show validation charts
    show_validation_charts(validation_results)
    
    # Show detailed results table
    show_validation_results_table(validation_results)


def show_validation_summary_metrics(validation_results: List[Dict[str, Any]]):
    """Show summary metrics for validation results"""
    
    total_bundles = len(validation_results)
    schema_found = sum(1 for r in validation_results if r.get('schema_found', False))
    google_eligible = sum(1 for r in validation_results if r.get('google_eligible', False))
    
    # Calculate average compliance score
    scores = [r.get('compliance_score', 0) for r in validation_results if r.get('compliance_score')]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Bundles",
            total_bundles,
            help="Total number of product bundles analyzed"
        )
    
    with col2:
        schema_rate = (schema_found / total_bundles * 100) if total_bundles > 0 else 0
        st.metric(
            "Schema Found",
            f"{schema_found}/{total_bundles}",
            delta=f"{schema_rate:.1f}%",
            help="Bundles with valid Product schema detected"
        )
    
    with col3:
        eligible_rate = (google_eligible / total_bundles * 100) if total_bundles > 0 else 0
        st.metric(
            "Google Eligible",
            f"{google_eligible}/{total_bundles}",
            delta=f"{eligible_rate:.1f}%",
            help="Bundles eligible for Google Rich Results"
        )
    
    with col4:
        st.metric(
            "Avg Compliance",
            f"{avg_score:.1f}%",
            delta=f"Target: {CONFIG.SCORE_THRESHOLDS['good']}%",
            help="Average schema compliance score"
        )


def show_validation_charts(validation_results: List[Dict[str, Any]]):
    """Show validation charts and visualizations"""
    
    # Filter valid results
    valid_results = [r for r in validation_results if r.get('schema_found', False)]
    
    if not valid_results:
        st.warning("No valid schemas found for chart generation")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Compliance Score Distribution
        scores = [r.get('compliance_score', 0) for r in valid_results]
        
        fig = px.histogram(
            x=scores,
            nbins=10,
            title="Schema Compliance Score Distribution",
            labels={'x': 'Compliance Score (%)', 'y': 'Number of Products'},
            color_discrete_sequence=[CONFIG.COLORS['primary']]
        )
        
        # Add threshold lines
        fig.add_vline(
            x=CONFIG.SCORE_THRESHOLDS['good'], 
            line_dash="dash", 
            line_color=CONFIG.COLORS['warning'],
            annotation_text="Good Threshold"
        )
        
        fig.add_vline(
            x=CONFIG.SCORE_THRESHOLDS['excellent'], 
            line_dash="dash", 
            line_color=CONFIG.COLORS['success'],
            annotation_text="Excellent Threshold"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Google Eligibility Breakdown
        eligible_count = sum(1 for r in valid_results if r.get('google_eligible', False))
        not_eligible_count = len(valid_results) - eligible_count
        
        fig = px.pie(
            values=[eligible_count, not_eligible_count],
            names=["Google Eligible", "Not Eligible"],
            title="Google Rich Results Eligibility",
            color_discrete_sequence=[CONFIG.COLORS['success'], CONFIG.COLORS['danger']]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Field Compliance Heatmap
    if valid_results:
        show_field_compliance_heatmap(valid_results)


def show_field_compliance_heatmap(validation_results: List[Dict[str, Any]]):
    """Show field compliance heatmap"""
    
    st.markdown("#### 📋 Field Compliance Analysis")
    
    # Collect field compliance data
    field_data = {}
    
    for result in validation_results:
        bundle_id = result.get('bundle_id', 'Unknown')
        
        # Process required fields
        for field_name, field_result in result.get('required_fields', {}).items():
            if field_name not in field_data:
                field_data[field_name] = {'type': 'Required', 'bundles': {}}
            field_data[field_name]['bundles'][bundle_id] = 1 if (field_result.get('present') and field_result.get('valid')) else 0
        
        # Process recommended fields
        for field_name, field_result in result.get('recommended_fields', {}).items():
            if field_name not in field_data:
                field_data[field_name] = {'type': 'Recommended', 'bundles': {}}
            field_data[field_name]['bundles'][bundle_id] = 1 if (field_result.get('present') and field_result.get('valid')) else 0
        
        # Process offers fields
        for field_name, field_result in result.get('offers_fields', {}).items():
            offer_field_name = f"offers.{field_name}"
            if offer_field_name not in field_data:
                field_data[offer_field_name] = {'type': 'Offers (Required)', 'bundles': {}}
            field_data[offer_field_name]['bundles'][bundle_id] = 1 if (field_result.get('present') and field_result.get('valid')) else 0
    
    if field_data:
        # Create heatmap data
        bundle_ids = list(set(bundle_id for field_info in field_data.values() for bundle_id in field_info['bundles'].keys()))
        field_names = list(field_data.keys())
        
        # Create matrix
        matrix = []
        for field_name in field_names:
            row = []
            for bundle_id in bundle_ids:
                value = field_data[field_name]['bundles'].get(bundle_id, 0)
                row.append(value)
            matrix.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=bundle_ids,
            y=field_names,
            colorscale=[[0, CONFIG.COLORS['danger']], [1, CONFIG.COLORS['success']]],
            showscale=True,
            colorbar=dict(
                title="Compliance",
                tickvals=[0, 1],
                ticktext=["Missing/Invalid", "Present/Valid"]
            )
        ))
        
        fig.update_layout(
            title="Field Compliance Heatmap",
            xaxis_title="Product Bundles",
            yaxis_title="Schema Fields",
            height=max(400, len(field_names) * 30)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            required_fields = [f for f, info in field_data.items() if info['type'] == 'Required']
            required_compliance = sum(
                sum(field_data[f]['bundles'].values()) for f in required_fields
            ) / (len(required_fields) * len(bundle_ids)) * 100 if required_fields else 0
            
            st.metric("Required Fields", f"{required_compliance:.1f}%")
        
        with col2:
            recommended_fields = [f for f, info in field_data.items() if info['type'] == 'Recommended']
            recommended_compliance = sum(
                sum(field_data[f]['bundles'].values()) for f in recommended_fields
            ) / (len(recommended_fields) * len(bundle_ids)) * 100 if recommended_fields else 0
            
            st.metric("Recommended Fields", f"{recommended_compliance:.1f}%")
        
        with col3:
            offers_fields = [f for f, info in field_data.items() if info['type'] == 'Offers (Required)']
            offers_compliance = sum(
                sum(field_data[f]['bundles'].values()) for f in offers_fields
            ) / (len(offers_fields) * len(bundle_ids)) * 100 if offers_fields else 0
            
            st.metric("Offers Fields", f"{offers_compliance:.1f}%")


def show_validation_results_table(validation_results: List[Dict[str, Any]]):
    """Show detailed validation results in a table"""
    
    st.markdown("#### 📊 Detailed Validation Results")
    
    # Prepare table data
    table_data = []
    
    for result in validation_results:
        bundle_id = result.get('bundle_id', 'Unknown')
        schema_found = result.get('schema_found', False)
        google_eligible = result.get('google_eligible', False)
        compliance_score = result.get('compliance_score', 0)
        
        if schema_found:
            summary = result.get('summary', {})
            required_status = f"{summary.get('required_passed', 0)}/{summary.get('required_total', 0)}"
            recommended_status = f"{summary.get('recommended_passed', 0)}/{summary.get('recommended_total', 0)}"
            offers_status = f"{summary.get('offers_passed', 0)}/{summary.get('offers_total', 0)}"
            total_issues = summary.get('total_issues', 0)
        else:
            required_status = "N/A"
            recommended_status = "N/A"
            offers_status = "N/A"
            total_issues = "N/A"
        
        table_data.append({
            'Bundle ID': bundle_id,
            'Schema Found': '✅' if schema_found else '❌',
            'Google Eligible': '✅' if google_eligible else '❌',
            'Compliance Score': f"{compliance_score:.1f}%" if compliance_score else "0%",
            'Required Fields': required_status,
            'Recommended Fields': recommended_status,
            'Offers Fields': offers_status,
            'Issues': total_issues
        })
    
    df = pd.DataFrame(table_data)
    
    # Style the dataframe
    def style_eligibility(val):
        if val == '✅':
            return 'background-color: #d4edda; color: #155724;'
        elif val == '❌':
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
    
    styled_df = df.style.applymap(style_eligibility, subset=['Schema Found', 'Google Eligible'])
    styled_df = styled_df.applymap(style_score, subset=['Compliance Score'])
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Export option
    if st.button("📥 Export Schema Validation Report"):
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Download CSV Report",
            data=csv_data,
            file_name=f"schema_validation_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def show_single_bundle_validation():
    """Show detailed validation for a single bundle"""
    
    st.markdown("### 🔍 Single Bundle Schema Analysis")
    
    # Bundle selection
    bundles_dir = CONFIG.get_bundles_dir()
    
    if not bundles_dir.exists():
        st.warning("No bundles directory found")
        return
    
    bundle_options = [d.name for d in bundles_dir.iterdir() if d.is_dir()]
    
    if not bundle_options:
        st.info("No bundles found for validation")
        return
    
    selected_bundle = st.selectbox(
        "Select Bundle to Analyze:",
        bundle_options,
        help="Choose a product bundle for detailed schema validation"
    )
    
    if st.button("🔍 Analyze Schema", type="primary"):
        with st.spinner(f"Analyzing schema for {selected_bundle}..."):
            validation_result = validate_single_bundle(selected_bundle)
        
        if validation_result:
            show_detailed_bundle_validation(validation_result)
        else:
            st.error(f"Could not validate bundle: {selected_bundle}")


def show_detailed_bundle_validation(validation_result: Dict[str, Any]):
    """Show detailed validation results for a single bundle"""
    
    bundle_id = validation_result.get('bundle_id', 'Unknown')
    schema_found = validation_result.get('schema_found', False)
    
    if not schema_found:
        st.error(f"❌ No valid Product schema found in bundle: {bundle_id}")
        st.markdown(f"**Error:** {validation_result.get('error', 'Unknown error')}")
        return
    
    # Header with key metrics
    st.markdown(f"### 📋 Schema Analysis: {bundle_id}")
    
    google_eligible = validation_result.get('google_eligible', False)
    compliance_score = validation_result.get('compliance_score', 0)
    schema_type = validation_result.get('schema_type', 'Unknown')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Schema Type", schema_type)
    
    with col2:
        st.metric("Compliance Score", f"{compliance_score:.1f}%")
    
    with col3:
        status_icon = "✅" if google_eligible else "❌"
        st.metric("Google Eligible", status_icon)
    
    with col4:
        summary = validation_result.get('summary', {})
        total_issues = summary.get('total_issues', 0)
        st.metric("Total Issues", total_issues)
    
    # Detailed field validation
    st.markdown("---")
    
    # Create tabs for different field types
    req_tab, rec_tab, off_tab = st.tabs(["🔴 Required Fields", "🟡 Recommended Fields", "💰 Offers Fields"])
    
    with req_tab:
        show_field_validation_results(
            validation_result.get('required_fields', {}), 
            "Required Fields",
            "These fields are mandatory for Google Product schema compliance."
        )
    
    with rec_tab:
        show_field_validation_results(
            validation_result.get('recommended_fields', {}), 
            "Recommended Fields",
            "These fields improve SEO and user experience but are not mandatory."
        )
    
    with off_tab:
        show_field_validation_results(
            validation_result.get('offers_fields', {}), 
            "Offers Fields",
            "These fields are required within the offers object for pricing information."
        )
    
    # Summary and recommendations
    show_bundle_recommendations(validation_result)


def show_field_validation_results(field_results: Dict[str, Any], title: str, description: str):
    """Show validation results for a group of fields"""
    
    st.markdown(f"#### {title}")
    st.markdown(description)
    
    if not field_results:
        st.info("No fields to validate in this category")
        return
    
    for field_name, result in field_results.items():
        field_config = result.get('field_config', {})
        
        # Field header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Status indicator
            if result.get('present') and result.get('valid'):
                status_icon = "✅"
                status_color = "green"
            elif result.get('present') and not result.get('valid'):
                status_icon = "⚠️"
                status_color = "orange"
            else:
                status_icon = "❌"
                status_color = "red"
            
            st.markdown(f"**{status_icon} {field_name}** - {field_config.get('description', '')}")
        
        with col2:
            if result.get('value') is not None:
                value_preview = str(result['value'])[:50]
                if len(str(result['value'])) > 50:
                    value_preview += "..."
                st.code(value_preview)
        
        # Show issues and recommendations
        issues = result.get('issues', [])
        recommendations = result.get('recommendations', [])
        
        if issues:
            for issue in issues:
                st.error(f"🚫 {issue}")
        
        if recommendations:
            for rec in recommendations:
                st.info(f"💡 {rec}")
        
        # Google documentation reference
        google_docs = field_config.get('google_docs', '')
        if google_docs:
            st.caption(f"📚 Google: {google_docs}")
        
        st.markdown("---")


def show_bundle_recommendations(validation_result: Dict[str, Any]):
    """Show recommendations for improving schema compliance"""
    
    st.markdown("### 💡 Recommendations")
    
    google_eligible = validation_result.get('google_eligible', False)
    compliance_score = validation_result.get('compliance_score', 0)
    summary = validation_result.get('summary', {})
    
    if google_eligible:
        st.success("🎉 **Congratulations!** This product is eligible for Google Rich Results.")
        st.markdown("Your schema meets all required fields for Google Product markup.")
    else:
        st.error("❌ **Not Google Eligible** - Schema needs improvements for Rich Results")
    
    # Priority recommendations
    recommendations = []
    
    # Critical issues first
    critical_issues = summary.get('critical_issues', 0)
    if critical_issues > 0:
        recommendations.append({
            'priority': 'High',
            'title': 'Fix Required Field Issues',
            'description': f"Address {critical_issues} critical issues in required fields to enable Google Rich Results",
            'color': 'error'
        })
    
    # Compliance score improvements
    if compliance_score < CONFIG.SCORE_THRESHOLDS['good']:
        recommendations.append({
            'priority': 'High',
            'title': 'Improve Compliance Score',
            'description': f"Current score: {compliance_score:.1f}%. Target: {CONFIG.SCORE_THRESHOLDS['good']}%+",
            'color': 'warning'
        })
    
    # Recommended fields
    rec_passed = summary.get('recommended_passed', 0)
    rec_total = summary.get('recommended_total', 0)
    if rec_passed < rec_total:
        missing_count = rec_total - rec_passed
        recommendations.append({
            'priority': 'Medium',
            'title': 'Add Recommended Fields',
            'description': f"Add {missing_count} recommended fields to improve SEO and user experience",
            'color': 'info'
        })
    
    # Show recommendations
    for rec in recommendations:
        if rec['color'] == 'error':
            st.error(f"🔥 **{rec['priority']} Priority:** {rec['title']}")
        elif rec['color'] == 'warning':
            st.warning(f"⚡ **{rec['priority']} Priority:** {rec['title']}")
        else:
            st.info(f"💡 **{rec['priority']} Priority:** {rec['title']}")
        
        st.markdown(rec['description'])
        st.markdown("")
    
    if not recommendations:
        st.success("✨ **Excellent!** No critical recommendations at this time.")
    
    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔧 Auto-Fix Issues", help="Attempt to automatically fix schema issues"):
            st.info("Auto-fix functionality would trigger here")
    
    with col2:
        if st.button("📊 Re-validate", help="Run validation again"):
            st.rerun()
    
    with col3:
        if st.button("📋 Export Report", help="Export detailed validation report"):
            st.info("Export functionality would trigger here")


def show_validation_rules():
    """Show the validation rules and Google requirements"""
    
    st.markdown("### 📚 Google Product Schema Validation Rules")
    st.markdown("Understanding the requirements for Google Rich Results eligibility")
    
    # Create tabs for different rule categories
    req_tab, rec_tab, off_tab, ref_tab = st.tabs(["🔴 Required Fields", "🟡 Recommended Fields", "💰 Offers Fields", "📖 References"])
    
    with req_tab:
        show_field_requirements(GoogleProductSchemaValidator.REQUIRED_FIELDS, "Required Fields")
    
    with rec_tab:
        show_field_requirements(GoogleProductSchemaValidator.RECOMMENDED_FIELDS, "Recommended Fields")
    
    with off_tab:
        show_field_requirements(GoogleProductSchemaValidator.OFFERS_REQUIRED_FIELDS, "Offers Fields")
    
    with ref_tab:
        show_schema_references()


def show_field_requirements(field_config: Dict[str, Any], category: str):
    """Show field requirements and validation rules"""
    
    st.markdown(f"#### {category}")
    
    for field_name, config in field_config.items():
        with st.expander(f"📋 {field_name} - {config['description']}"):
            
            # Field details
            st.markdown(f"**Description:** {config['description']}")
            st.markdown(f"**Schema Path:** `{' > '.join(config['path'])}`")
            
            if 'alt_paths' in config:
                alt_paths_str = ", ".join([" > ".join(path) for path in config['alt_paths']])
                st.markdown(f"**Alternative Paths:** `{alt_paths_str}`")
            
            st.markdown(f"**Validation Type:** {config['validation']}")
            st.markdown(f"**Google Requirement:** {config['google_docs']}")
            
            # Show validation details based on type
            validation_type = config['validation']
            
            if 'string' in validation_type:
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be a non-empty string")
                st.markdown("- Minimum 3 characters")
                st.markdown("- No HTML tags (plain text preferred)")
            
            elif validation_type == 'required_image':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be a valid URL or ImageObject")
                st.markdown("- Supports arrays of multiple images")
                st.markdown("- Images should be high-resolution (1200px+ width)")
                st.markdown("- Accessible and fast-loading")
            
            elif validation_type == 'required_offers':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be an Offer object or array of Offers")
                st.markdown("- Each offer must have price, priceCurrency, and availability")
                st.markdown("- @type should be 'Offer'")
            
            elif validation_type == 'required_price':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be a valid number")
                st.markdown("- Must be greater than 0")
                st.markdown("- Can include currency symbols (will be cleaned)")
            
            elif validation_type == 'required_currency':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be a valid ISO 4217 currency code")
                st.markdown("- Examples: USD, EUR, GBP, JPY, CAD")
            
            elif validation_type == 'required_availability':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must use Schema.org availability values")
                st.markdown("- Valid values: InStock, OutOfStock, PreOrder, BackOrder, Discontinued, LimitedAvailability")
                st.markdown("- Can use full Schema.org URLs or short forms")
            
            elif validation_type == 'recommended_gtin':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be 8, 12, 13, or 14 digits")
                st.markdown("- Supports GTIN, UPC, EAN formats")
                st.markdown("- Helps with product matching and identification")
            
            elif validation_type == 'recommended_rating':
                st.markdown("**Validation Rules:**")
                st.markdown("- Must be an AggregateRating object")
                st.markdown("- Requires ratingValue (1-5 scale)")
                st.markdown("- Requires reviewCount or ratingCount")
                st.markdown("- Used for rich snippets with stars")
            
            elif validation_type == 'recommended_reviews':
                st.markdown("**Validation Rules:**")
                st.markdown("- Can be single Review or array of Reviews")
                st.markdown("- Each review should have reviewBody, author, reviewRating")
                st.markdown("- Improves trust and SEO signals")


def show_schema_references():
    """Show schema references and documentation links"""
    
    st.markdown("#### 📖 Official Documentation & References")
    
    st.markdown("##### Google Developer Resources")
    st.markdown("""
    - [Google Product Structured Data](https://developers.google.com/search/docs/appearance/structured-data/product)
    - [Google Merchant Center Requirements](https://support.google.com/merchants/answer/7052112)
    - [Rich Results Test](https://search.google.com/test/rich-results)
    - [Structured Data Testing Tool](https://validator.schema.org/)
    """)
    
    st.markdown("##### Schema.org References")
    st.markdown("""
    - [Schema.org Product](https://schema.org/Product)
    - [Schema.org Offer](https://schema.org/Offer)
    - [Schema.org AggregateRating](https://schema.org/AggregateRating)
    - [Schema.org Review](https://schema.org/Review)
    """)
    
    st.markdown("##### Validation Thresholds")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Compliance Scoring:**")
        st.markdown("- Required Fields: 60% weight")
        st.markdown("- Offers Fields: 25% weight")
        st.markdown("- Recommended Fields: 15% weight")
    
    with col2:
        st.markdown("**Score Thresholds:**")
        for level, threshold in CONFIG.SCORE_THRESHOLDS.items():
            st.markdown(f"- {level.title()}: {threshold}%+")
    
    st.markdown("##### Best Practices")
    st.markdown("""
    1. **Always include required fields** - These are mandatory for Google Rich Results
    2. **Use structured data consistently** - Apply schema to all product pages
    3. **Keep data accurate and up-to-date** - Sync with actual product information
    4. **Include high-quality images** - Multiple angles, high resolution
    5. **Add customer reviews and ratings** - Improves trust and click-through rates
    6. **Use proper identifiers** - GTIN, MPN, SKU for product matching
    7. **Test regularly** - Use Google's Rich Results Test tool
    8. **Monitor performance** - Track Rich Results appearance in Search Console
    """)
    
    st.markdown("---")
    st.info("💡 **Tip:** Use Structr's auto-fix functionality to automatically address common schema issues and improve compliance scores.")