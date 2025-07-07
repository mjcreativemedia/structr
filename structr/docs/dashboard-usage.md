# Dashboard Usage Guide

Structr's Streamlit dashboard provides a visual interface for managing Product Detail Pages (PDPs), running batch operations, and monitoring system performance. Access powerful features through an intuitive web interface.

## Getting Started

### Launching the Dashboard

```bash
# Start the dashboard
python start_dashboard.py

# Or directly with Streamlit
streamlit run dashboard_app.py
```

The dashboard will open at `http://localhost:8501` by default.

### Navigation Overview

The dashboard is organized into five main sections:

| Section | Purpose | Key Features |
|---------|---------|--------------|
| 📊 **Overview** | Catalog insights and metrics | Quality scores, performance charts |
| 📦 **Bundle Explorer** | Browse and preview PDPs | HTML preview, file downloads |
| ⚡ **Batch Processor** | Bulk operations and imports | CSV upload, connector management |
| 🔍 **Audit Manager** | Quality analysis tools | Detailed scoring, compliance reports |
| 📤 **Export Center** | Data export and sync | Multiple formats, platform integration |

---

## 📊 Overview Page

The Overview page provides a high-level view of your catalog health and system performance.

### Catalog Metrics

![Overview Dashboard](assets/overview-dashboard.png)

The main metrics section displays:

=== "Quality Scores"
    - **Average Score**: Overall catalog quality
    - **Distribution**: Score ranges across products
    - **Trends**: Quality changes over time
    - **Top Performers**: Highest scoring products

=== "System Health"
    - **Job Queue**: Active and pending operations
    - **Processing Speed**: Products per minute
    - **Success Rate**: Completion percentage
    - **Resource Usage**: Memory and storage

=== "Recent Activity"
    - **Latest Generations**: Recently created PDPs
    - **Audit Results**: New quality assessments
    - **Import Operations**: CSV uploads and API syncs
    - **Error Reports**: Failed operations and issues

### Performance Charts

Interactive charts show trends and insights:

??? example "Quality Score Distribution"
    ```
    📊 Catalog Quality Distribution
    
    Excellent (90-100) ████████████ 45 products (32%)
    Good (80-89)       ██████████   35 products (25%)
    Fair (70-79)       ████████     28 products (20%)
    Poor (<70)         ████         32 products (23%)
    
    💡 Insight: 57% of products score above 80
    🎯 Goal: Improve 32 products to reach 80% good rating
    ```

??? example "Processing Performance"
    ```
    ⚡ Batch Performance (Last 7 Days)
    
    Day       | Jobs | Success | Avg Time | Products
    ----------|------|---------|----------|----------
    Today     |   12 |   100%  |   2.1s   |    156
    Yesterday |   15 |    95%  |   1.9s   |    203
    Dec 4     |    8 |   100%  |   2.3s   |     98
    Dec 3     |   11 |    89%  |   2.8s   |    145
    
    📈 Trend: Performance improving, 15% faster this week
    ```

---

## 📦 Bundle Explorer

Browse and manage generated PDP bundles with visual previews and detailed analysis.

### Bundle List View

The main list shows all generated bundles with key information:

| Column | Description | Actions |
|--------|-------------|---------|
| **Product** | Handle and title | Click to view details |
| **Score** | Quality rating with color coding | View audit breakdown |
| **Status** | Generation status and flags | Re-generate if needed |
| **Modified** | Last update timestamp | Track recent changes |
| **Actions** | Quick action buttons | Preview, download, edit |

### Bundle Detail View

Click any product to see comprehensive details:

=== "HTML Preview"
    Live preview of the generated PDP:
    
    - **Desktop View**: Full-width preview
    - **Mobile View**: Responsive mobile preview
    - **Source Code**: Raw HTML inspection
    - **Interactive Elements**: Test links and forms

=== "Audit Details"
    Comprehensive quality assessment:
    
    ```
    📊 AUDIT BREAKDOWN: summer-dress-blue
    
    🎯 TITLE ANALYSIS (92/100)
    ✅ Length: 48 characters (optimal)
    ✅ Keywords: Contains 3 target keywords
    ✅ Uniqueness: No duplicates found
    ⚠️  Improvement: Add seasonal keyword
    
    📝 META DESCRIPTION (85/100)
    ✅ Length: 156 characters (optimal)
    ✅ Call-to-action: "Shop now" present
    ⚠️  Keywords: Could include more variants
    
    🏷️  SCHEMA MARKUP (100/100)
    ✅ Valid JSON-LD Product schema
    ✅ All required fields present
    ✅ Google Rich Results compatible
    ✅ Price and availability included
    
    🖼️  IMAGES (88/100)
    ✅ Alt text present on all images
    ✅ Descriptive filenames
    ⚠️  Missing: High-res variants
    ```

=== "File Downloads"
    Access all generated files:
    
    - **index.html** - Complete PDP page
    - **sync.json** - Input data and metadata
    - **audit.json** - Detailed quality report
    - **schema.json** - Extracted JSON-LD markup
    - **Bundle ZIP** - All files in one archive

### Bulk Operations

Select multiple bundles for bulk actions:

- **Re-audit**: Update quality scores
- **Re-generate**: Create fresh content with LLM
- **Export**: Download selected bundles
- **Delete**: Remove bundles and files
- **Compare**: Side-by-side analysis

---

## ⚡ Batch Processor

Handle bulk operations, CSV imports, and connector management through four specialized tabs.

### Tab 1: Upload & Generate

Upload product data and generate PDPs in bulk:

=== "Upload Options"
    **JSON Files**
    ```
    📁 Multiple JSON Files
    ├── Upload individual product files
    ├── Automatic validation
    └── Preview before processing
    ```
    
    **CSV Files**
    ```
    📊 CSV Import
    ├── Intelligent column mapping
    ├── Data validation
    └── Transformation preview
    ```
    
    **JSON Arrays**
    ```
    📄 Bulk JSON
    ├── Array of product objects
    ├── Single file upload
    └── Batch size configuration
    ```

=== "Processing Options"
    Configure generation settings:
    
    - **LLM Model**: Choose `mistral`, `llama2`, or `codellama`
    - **Parallel Jobs**: 1-5 concurrent workers
    - **Template**: Output format and style
    - **Validation**: Quality thresholds and checks

=== "Progress Monitoring"
    Real-time processing updates:
    
    ```
    🚀 Batch Generation: products_batch_001
    
    Progress: ████████████░░░░░░░░ 65% (65/100 products)
    
    ⏱️  Elapsed: 2m 15s
    🎯 ETA: 1m 22s remaining
    ⚡ Speed: 2.3 products/minute
    
    📊 Results:
    ✅ Successful: 58 products
    ⚠️  Warnings: 5 products
    ❌ Failed: 2 products
    ```

### Tab 2: Bulk Fix

Repair quality issues across multiple products:

=== "Filter Options"
    Target specific problems:
    
    - **Score Threshold**: Fix products below X points
    - **Issue Types**: `title`, `meta_description`, `schema`, `images`
    - **Date Range**: Products modified within timeframe
    - **Category Filter**: Specific product types or brands

=== "Fix Preview"
    See what will be changed before applying:
    
    ```
    🔧 BULK FIX PREVIEW (15 products selected)
    
    Product              | Current Score | Issues to Fix
    --------------------|---------------|------------------
    summer-dress-blue   |      78      | meta_description
    winter-coat-black   |      72      | title, schema
    spring-shoes-white  |      81      | images
    
    💾 Estimated time: 45 seconds
    📈 Projected improvement: +12 average points
    ```

=== "Dry Run Mode"
    Test fixes without making changes:
    
    - Preview all modifications
    - Estimate score improvements  
    - Identify potential issues
    - Generate fix reports

### Tab 3: Batch Status

Monitor active operations and view results:

=== "Active Operations"
    Real-time job monitoring:
    
    ```
    🔄 RUNNING JOBS (2 active)
    
    Job ID: batch_gen_20250706_001
    ├── Type: Product Generation
    ├── Progress: 45/100 products (45%)
    ├── Speed: 2.1 products/minute
    └── ETA: 26 minutes remaining
    
    Job ID: bulk_audit_20250706_002  
    ├── Type: Quality Audit
    ├── Progress: 78/200 products (39%)
    ├── Speed: 3.8 products/minute
    └── ETA: 32 minutes remaining
    ```

=== "Completed Results"
    Historical operation results:
    
    - **Success Rates**: Completion percentages
    - **Performance Metrics**: Speed and efficiency
    - **Error Analysis**: Failed operations and causes
    - **Downloadable Reports**: CSV exports of results

### Tab 4: Connectors

Manage data import from external sources:

=== "Shopify CSV Importer"
    ```
    🛍️  SHOPIFY CSV IMPORT
    
    📁 Upload: products_export.csv
    
    📊 Analysis Results:
    ├── Total Products: 150
    ├── Detected Columns: 12
    ├── Confidence Score: 95%
    └── Estimated Time: 2m 30s
    
    🔗 Field Mapping:
    Handle          ← id
    Title           ← title
    Body (HTML)     ← body_html
    Vendor          ← vendor
    Variant Price   ← price
    
    ⚙️  Import Options:
    ├── Batch Size: 25 products
    └── Auto-fix: Enabled
    ```

=== "Generic CSV Mapper"
    ```
    📄 GENERIC CSV ANALYSIS
    
    🤖 AI-Powered Field Detection:
    
    product_name      → title (95% confidence)
    item_description  → description (89% confidence)  
    retail_price      → price (100% confidence)
    brand_name        → brand (92% confidence)
    
    📊 Data Quality: 88/100
    ├── Completeness: 94%
    ├── Consistency: 82%
    └── Format Issues: 3 detected
    ```

=== "API Connectors"
    Connect to live data sources:
    
    - **Shopify Admin API**: Real-time product sync
    - **Contentful CMS**: Content management integration
    - **Custom REST APIs**: Flexible endpoint configuration
    - **Webhooks**: Automatic updates on data changes

---

## 🔍 Audit Manager

Advanced quality analysis tools for comprehensive catalog assessment.

### Audit Dashboard

Overview of catalog quality with drill-down capabilities:

=== "Quality Overview"
    ```
    📊 CATALOG QUALITY OVERVIEW
    
    Overall Health: 🟢 Good (Average: 82/100)
    
    Quality Distribution:
    🟢 Excellent (90+):  45 products (32%)
    🟡 Good (80-89):     35 products (25%) 
    🟠 Fair (70-79):     28 products (20%)
    🔴 Poor (<70):       32 products (23%)
    
    🎯 Quick Actions:
    • Fix 32 poor-scoring products
    • Optimize 28 fair products to good
    • Review 5 products with schema errors
    ```

=== "Issue Breakdown"
    Categorized problem analysis:
    
    ```
    🔍 COMMON ISSUES (Top 5)
    
    1. Meta Description Too Short
       📊 Affects: 28 products (20%)
       🎯 Impact: -8 avg points
       🔧 Fix: Expand descriptions to 150+ chars
    
    2. Missing Alt Text
       📊 Affects: 15 products (11%)
       🎯 Impact: -12 avg points  
       🔧 Fix: Add descriptive image alt text
    
    3. Schema Warnings
       📊 Affects: 12 products (9%)
       🎯 Impact: -5 avg points
       🔧 Fix: Update product schema format
    ```

### Compliance Reports

Generate detailed compliance reports:

=== "SEO Compliance"
    ```
    📈 SEO COMPLIANCE REPORT
    
    Title Tags:           ✅ 95% compliant
    Meta Descriptions:    ⚠️  78% compliant  
    Header Structure:     ✅ 91% compliant
    Image Alt Text:       ⚠️  85% compliant
    Schema Markup:        ✅ 97% compliant
    
    🏆 SEO Score: 89/100 (Excellent)
    
    📋 Action Items:
    • Fix 31 meta descriptions
    • Add alt text to 21 images
    • Review 4 schema errors
    ```

=== "Accessibility Audit"
    ```
    ♿ ACCESSIBILITY COMPLIANCE
    
    Color Contrast:       ✅ 100% compliant
    Keyboard Navigation:  ✅ 95% compliant
    Screen Reader:        ⚠️  88% compliant
    Focus Indicators:     ✅ 92% compliant
    
    🎯 WCAG AA Score: 94/100
    
    🔧 Improvements Needed:
    • Add ARIA labels to 18 elements
    • Fix 5 heading hierarchy issues
    • Update 3 form accessibility features
    ```

### Historical Analysis

Track quality changes over time:

```
📈 QUALITY TRENDS (30 Days)

Dec 6  ████████████████████ 82 (Current)
Dec 1  ███████████████████░ 79 (+3)
Nov 26 ██████████████████░░ 76 (+3)
Nov 21 █████████████████░░░ 74 (+2)
Nov 16 ████████████████░░░░ 72 (+2)

📊 Insights:
• +10 point improvement over 30 days
• 15% more products in "Good" category
• Schema compliance improved 8%
• Fastest improving: meta descriptions
```

---

## 📤 Export Center

Export optimized data in multiple formats for various platforms and use cases.

### Export Options

=== "Format Selection"
    Choose from multiple export formats:
    
    - **CSV**: Spreadsheet-compatible catalog data
    - **JSON**: Structured data for APIs
    - **HTML**: Complete PDP pages
    - **XML**: Platform-specific feeds
    - **Shopify**: Direct import format

=== "Field Customization"
    Select which data to include:
    
    ```
    📋 EXPORT FIELDS SELECTION
    
    ✅ Core Product Data:
    ├── handle, title, description
    ├── price, brand, category
    └── sku, weight, dimensions
    
    ✅ Optimized Content:
    ├── meta_title, meta_description
    ├── schema_markup, og_tags
    └── optimized_html
    
    ✅ Quality Metrics:
    ├── audit_score, last_updated
    ├── issues_count, status
    └── compliance_flags
    ```

=== "Platform Templates"
    Pre-configured export templates:
    
    - **Shopify Import**: Ready for Shopify bulk import
    - **BigCommerce**: Compatible field mapping
    - **WooCommerce**: WordPress e-commerce format
    - **Magento**: Adobe Commerce structure
    - **Custom API**: Flexible JSON schema

### Sync Integration

Direct platform synchronization:

=== "Shopify Sync"
    ```
    🛍️  SHOPIFY SYNCHRONIZATION
    
    Store: mystore.myshopify.com
    Status: ✅ Connected
    
    📊 Sync Statistics:
    ├── Products to Update: 23
    ├── New Products: 5
    ├── Estimated Time: 45 seconds
    └── Last Sync: 2 hours ago
    
    ⚙️  Sync Options:
    ├── Update existing products
    ├── Create new products  
    ├── Sync metafields
    └── Update product images
    ```

=== "API Sync"
    ```
    🔌 CUSTOM API SYNC
    
    Endpoint: https://api.mystore.com/products
    Authentication: ✅ API Key Valid
    
    📤 Sync Payload:
    ├── Products: 45 selected
    ├── Batch Size: 10 per request
    ├── Rate Limit: 2 requests/second
    └── Retry Logic: 3 attempts
    
    📋 Sync Preview:
    • Update 40 existing products
    • Create 5 new products
    • Skip 0 unchanged products
    ```

---

## System Settings

Configure dashboard behavior and preferences:

### User Preferences

=== "Display Options"
    - **Theme**: Light/dark mode toggle
    - **Page Size**: Items per page (10-100)
    - **Auto-refresh**: Real-time updates interval
    - **Notifications**: Success/error alerts

=== "Default Settings"
    - **Default Workers**: Parallel processing count
    - **Batch Size**: Default import batch size
    - **Quality Threshold**: Minimum acceptable score
    - **Export Format**: Preferred export format

### System Configuration

=== "Performance Tuning"
    ```
    ⚡ PERFORMANCE SETTINGS
    
    Memory Usage:         ████████░░ 78% (3.2GB)
    CPU Usage:           ██████░░░░ 45% (4 cores)
    Disk Space:          ██████████ 89% (450GB)
    
    ⚙️  Optimization:
    ├── Worker Pool: 4 threads
    ├── Cache Size: 512MB
    ├── Cleanup: Auto-archive after 30 days
    └── Logging: INFO level
    ```

---

## Keyboard Shortcuts

Speed up your workflow with keyboard shortcuts:

| Shortcut | Action | Context |
|----------|--------|---------|
| ++ctrl+n++ | New batch operation | Global |
| ++ctrl+f++ | Search bundles | Bundle Explorer |
| ++ctrl+r++ | Refresh current view | Global |
| ++ctrl+e++ | Quick export | Bundle selected |
| ++ctrl+d++ | Duplicate settings | Any form |
| ++esc++ | Cancel operation | Any modal |
| ++space++ | Preview toggle | Bundle detail |
| ++tab++ | Next field | Forms |

---

## Troubleshooting

Common dashboard issues and solutions:

!!! bug "Common Issues"

    === "Dashboard Won't Load"
        **Problem**: Browser shows connection error
        
        **Solutions**:
        ```bash
        # Check if dashboard is running
        ps aux | grep streamlit
        
        # Restart dashboard
        python start_dashboard.py
        
        # Try different port
        streamlit run dashboard_app.py --server.port 8502
        ```

    === "Slow Performance"
        **Problem**: Dashboard feels sluggish
        
        **Solutions**:
        - Reduce batch size for large operations
        - Clear browser cache and cookies
        - Close unused browser tabs
        - Restart dashboard service

    === "Upload Failures"
        **Problem**: CSV upload fails or hangs
        
        **Solutions**:
        - Check file size (limit: 50MB)
        - Verify CSV format and encoding
        - Try smaller batch sizes
        - Check available disk space

---

Next: Learn about [Connectors](connectors-guide.md) for importing data from various sources.