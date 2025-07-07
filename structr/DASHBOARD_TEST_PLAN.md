# 🧪 Structr Dashboard Test Plan

## 🎯 Overview
Test plan to verify all enhanced dashboard functionalities work correctly in the live environment.

**Dashboard URL:** `https://structr-enhanced.loca.lt` (or current tunnel URL)

---

## 📋 Test Checklist

### ✅ 1. Bundle Explorer Preview
**Location:** Bundle Explorer tab

- [ ] **HTML Preview Test**
  - Navigate to Bundle Explorer
  - Select any product bundle from the dropdown
  - Verify HTML preview renders correctly in the iframe
  - Check that CSS styling is preserved
  - Confirm no rendering errors or broken layouts

- [ ] **Bundle Information Display**
  - Verify product metadata (title, handle, price) displays correctly
  - Check that file timestamps show when bundle was created/modified
  - Confirm bundle status indicators work

### ✅ 2. Interactive Audit Results
**Location:** Audit Manager tab

- [ ] **Visual Audit Charts**
  - Navigate to Audit Manager
  - Check that audit score distribution chart loads
  - Verify top issues chart shows common problems
  - Test chart interactivity (hover, zoom if available)

- [ ] **Audit Filtering & Search**
  - Test search functionality for finding specific products
  - Try filtering by audit score ranges
  - Verify filter results update charts in real-time

- [ ] **Bulk Actions**
  - Select multiple products using checkboxes
  - Test "Re-audit Selected" button functionality
  - Test "Fix Selected" button functionality
  - Verify progress indicators show during batch operations

### ✅ 3. Schema Validation Tool
**Location:** Audit Manager → Schema Validation tab

- [ ] **Product Schema Analysis**
  - Navigate to Schema Validation tab
  - Select a product from the dropdown
  - Verify required fields checklist displays (name, image, description, etc.)
  - Check recommended fields section shows brand, mpn, gtin13, etc.
  - Confirm Google Rich Results eligibility status displays

- [ ] **Validation Results**
  - Test with a complete product (should show ✅ checkmarks)
  - Test with incomplete product (should show ❌ warnings)
  - Verify validation summary shows overall compliance status

### ✅ 4. CSV Import Functionality
**Location:** Batch Processor tab

- [ ] **Shopify CSV Import**
  - Navigate to Batch Processor
  - Go to "Shopify Import" tab
  - Test file upload widget (upload any CSV)
  - Verify preview shows parsed data
  - Check field mapping interface works

- [ ] **Generic CSV Import**
  - Switch to "Generic CSV" tab
  - Upload a custom CSV file
  - Test AI-powered field detection
  - Verify manual field mapping options

- [ ] **Import Processing**
  - Test "Start Import" button
  - Verify progress monitoring shows status
  - Check that imported products appear in Bundle Explorer

### ✅ 5. CSV Export Functionality
**Location:** Export Center tab

- [ ] **Export Options**
  - Navigate to Export Center
  - Test different export formats (CSV, JSON, HTML)
  - Verify custom field selection works
  - Test date range filtering for exports

- [ ] **Download Functionality**
  - Generate an export file
  - Verify download button appears
  - Test file download completes successfully
  - Check exported file contains expected data

### ✅ 6. CLI Integration via Buttons
**Location:** Multiple tabs

- [ ] **Individual Product Actions**
  - In Bundle Explorer, test "Re-audit" button on single product
  - Test "Fix Issues" button on single product
  - Verify status updates show progress

- [ ] **Batch CLI Operations**
  - In Audit Manager, test bulk re-audit functionality
  - Test bulk fix operations
  - Verify CLI output displays in dashboard
  - Check that operations complete successfully

### ✅ 7. General Dashboard Navigation
**Location:** All tabs

- [ ] **Tab Navigation**
  - Test all tab transitions work smoothly
  - Verify no broken links or missing pages
  - Check sidebar navigation updates correctly

- [ ] **Session State**
  - Verify selected products persist across tab changes
  - Test that form inputs maintain state
  - Check that dashboard remembers user preferences

- [ ] **Error Handling**
  - Test behavior with missing files
  - Try invalid inputs in forms
  - Verify graceful error messages display

---

## 🚨 Known Issues to Monitor

1. **Tunnel URL Stability:** If the `loca.lt` tunnel expires, dashboard may become inaccessible
2. **File Permissions:** Ensure dashboard can read/write to `/home/scrapybara/structr/output/`
3. **Memory Usage:** Monitor for performance issues with large CSV imports
4. **CLI Integration:** Verify subprocess calls to `cli.py` work correctly from dashboard

---

## 📊 Success Criteria

**✅ Dashboard is fully functional when:**
- All tabs load without errors
- Bundle previews render correctly
- Audit charts display real data
- Schema validation shows accurate results
- CSV import/export completes successfully
- CLI operations execute via dashboard buttons
- User experience is smooth and intuitive

---

## 🔄 Next Steps After Testing

Based on test results:

1. **If all tests pass:** Dashboard is production-ready for demo/usage
2. **If issues found:** Document specific problems for targeted fixes
3. **Performance optimization:** Identify any slow operations for improvement
4. **User feedback:** Gather input on UI/UX improvements

---

## 📝 Test Notes
*Use this space to record any issues or observations during testing:*

- **Issue 1:** [Description]
- **Issue 2:** [Description]
- **Performance Notes:** [Observations]
- **UI/UX Feedback:** [Suggestions]