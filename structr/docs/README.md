# Structr Documentation

This directory contains the complete documentation for Structr, built with MkDocs and the Material theme.

## 📚 Documentation Structure

### Core Pages

- **[Overview](index.md)** - What Structr is, problems it solves, and comparison with EKOM
- **[Quickstart](quickstart.md)** - 5-minute setup guide with CLI demo and result inspection  
- **[CLI Commands](cli-commands.md)** - Complete reference for all CLI commands with examples
- **[Dashboard Usage](dashboard-usage.md)** - Streamlit UI guide for visual PDP management
- **[Connectors Guide](connectors-guide.md)** - Data import from Shopify, CSVs, PIM systems, APIs
- **[API Reference](api-reference.md)** - FastAPI endpoints, authentication, and integration
- **[Developer Guide](developer-guide.md)** - Architecture, contributing, testing, and extending
- **[FAQ](faq.md)** - Troubleshooting, common issues, configuration, and best practices

### Features

✅ **125,000+ characters** of comprehensive documentation  
✅ **Material Design** theme with dark/light mode support  
✅ **Code syntax highlighting** with copy buttons  
✅ **Collapsible sections** and tabbed content  
✅ **Search functionality** across all pages  
✅ **Responsive design** for mobile and desktop  
✅ **Custom styling** with Structr branding  

## 🚀 Building the Documentation

### Prerequisites

```bash
pip install mkdocs mkdocs-material
```

### Local Development

```bash
# Start development server (auto-reload)
mkdocs serve

# Open in browser
open http://localhost:8000
```

### Build Static Site

```bash
# Build static HTML
mkdocs build

# Output will be in site/ directory
ls site/
```

### Deploy to GitHub Pages

```bash
# Deploy to gh-pages branch
mkdocs gh-deploy
```

## 📝 Content Guidelines

### Writing Style

- **Clear and concise** - Aim for actionable content
- **Code-first examples** - Show real usage scenarios  
- **Progressive disclosure** - Basic → advanced concepts
- **Visual hierarchy** - Use headers, lists, and formatting

### Markdown Extensions

The documentation supports advanced Markdown features:

```markdown
!!! note "Information blocks"
    Use admonitions for important notes

=== "Tabbed content"
    Use tabs for multiple options

??? example "Collapsible sections"
    Perfect for detailed examples
```

### Code Examples

All code examples should be:
- **Syntax highlighted** with language tags
- **Copy-pasteable** without modification  
- **Tested** to ensure they work
- **Contextual** with setup/teardown when needed

## 🎨 Styling and Theming

### Custom CSS

Custom styles are in `stylesheets/extra.css`:

- Structr brand colors and variables
- Enhanced code block styling  
- Custom admonition types
- Responsive feature grids
- File tree visualization

### Theme Configuration

The Material theme is configured in `mkdocs.yml` with:

- Navigation tabs and sections
- Search highlighting  
- Code copy buttons
- Light/dark mode toggle
- Social links and metadata

## 📊 Content Statistics

| Page | Length | Code Blocks | Links |
|------|--------|-------------|-------|
| Overview | 7,867 chars | 4 | 27 |
| Quickstart | 7,428 chars | 46 | 7 |
| CLI Commands | 14,817 chars | 106 | 21 |
| Dashboard Usage | 16,879 chars | 44 | 2 |
| Connectors Guide | 22,572 chars | 66 | 31 |
| API Reference | 19,920 chars | 102 | 20 |
| Developer Guide | 28,809 chars | 70 | 57 |
| FAQ | 7,329 chars | 22 | 3 |

**Total: 125,621 characters across 8 comprehensive pages**

## 🔧 Maintenance

### Updating Content

1. Edit the relevant `.md` file in the `docs/` directory
2. Test locally with `mkdocs serve`
3. Commit changes to the repository
4. Deploy updates with `mkdocs gh-deploy`

### Adding New Pages

1. Create new `.md` file in `docs/`
2. Add to navigation in `mkdocs.yml`
3. Update cross-references in other pages
4. Test and deploy

### Custom Components

The documentation includes several custom components:

- **Feature comparison tables** - Structr vs competitors
- **File tree displays** - Project structure visualization  
- **Command reference grids** - Organized CLI documentation
- **Code example tabs** - Multiple implementation options

## 🏆 Quality Assurance

The documentation has been validated for:

✅ All required pages present and comprehensive  
✅ Proper markdown structure with clear headers  
✅ Substantial content with code examples  
✅ Cross-references and navigation links  
✅ Mobile-responsive design  
✅ Search functionality  
✅ Professional styling and branding  

Run the validation script to verify completeness:

```bash
python simple_docs_check.py
```

---

**The Structr documentation is complete and ready to serve your users!** 🚀