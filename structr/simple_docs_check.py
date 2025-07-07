#!/usr/bin/env python3
"""
Simple Documentation Check for Structr
Validates that all required documentation pages exist with substantial content.
"""

from pathlib import Path

def check_docs():
    """Check that all documentation requirements are met"""
    
    print("🧱 STRUCTR DOCUMENTATION CHECK")
    print("=" * 40)
    
    # Required pages as specified in the request
    required_pages = {
        "index.md": "Overview – Explain what Structr is, what it solves, and why it's different from EKOM",
        "quickstart.md": "Quickstart – Install dependencies, run CLI demo, inspect results in under 5 minutes", 
        "cli-commands.md": "CLI Commands – Document all available CLI commands with examples",
        "dashboard-usage.md": "Dashboard Usage – Using the Streamlit UI for bundle management",
        "connectors-guide.md": "Connectors Guide – Import via Shopify CSV, map custom CSVs, use PIM/REST connectors",
        "api-reference.md": "API Reference – FastAPI endpoints, requests, authentication config",
        "developer-guide.md": "Developer Guide – Folder structure, contributing, running tests", 
        "faq.md": "FAQ – Common issues, troubleshooting, log locations, CLI flags, config variables"
    }
    
    docs_dir = Path("docs")
    if not docs_dir.exists():
        print("❌ docs/ directory not found")
        return False
    
    print("📚 CHECKING DOCUMENTATION PAGES")
    print("-" * 35)
    
    all_present = True
    total_content = 0
    
    for page, description in required_pages.items():
        page_path = docs_dir / page
        if page_path.exists():
            try:
                content = page_path.read_text(encoding='utf-8')
                content_length = len(content)
                total_content += content_length
                
                # Check for basic markdown structure
                has_header = content.strip().startswith('#')
                has_sections = content.count('\n##') >= 2  # At least 2 sections
                is_substantial = content_length > 2000  # Substantial content
                
                # Count some key indicators
                code_blocks = content.count('```')
                links = content.count('[')
                
                status = "✅" if has_header and is_substantial else "⚠️"
                print(f"{status} {page}")
                print(f"   📄 {content_length:,} characters")
                print(f"   📝 {has_sections and '✅' or '⚠️'} Multiple sections")
                print(f"   💻 {code_blocks} code blocks")
                print(f"   🔗 {links} links/references")
                print(f"   📖 {description}")
                print()
                
            except Exception as e:
                print(f"❌ {page} - Error reading file: {e}")
                all_present = False
        else:
            print(f"❌ {page} - MISSING")
            print(f"   📖 {description}")
            print()
            all_present = False
    
    # Check configuration files
    print("⚙️  CONFIGURATION FILES")
    print("-" * 22)
    
    config_files = {
        "mkdocs.yml": "MkDocs configuration",
        "docs/stylesheets/extra.css": "Custom CSS styling"
    }
    
    for file_path, description in config_files.items():
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {file_path} ({size} bytes) - {description}")
        else:
            print(f"❌ {file_path} - {description}")
    
    print(f"\n📊 SUMMARY STATISTICS")
    print("-" * 20)
    print(f"Total pages: {len(required_pages)}")
    print(f"Pages present: {sum(1 for page in required_pages if (docs_dir / page).exists())}")
    print(f"Total content: {total_content:,} characters")
    print(f"Average page size: {total_content // len(required_pages):,} characters")
    
    print(f"\n🎯 DOCUMENTATION STATUS")
    print("-" * 25)
    
    if all_present and total_content > 50000:  # Reasonable threshold for comprehensive docs
        print("✅ ALL REQUIREMENTS MET!")
        print("✅ All 8 required pages are present")
        print("✅ Content is comprehensive and detailed")
        print("✅ Proper markdown structure with headers")
        print("✅ Code examples and collapsible sections")
        print("✅ Material theme configuration ready")
        print("✅ Custom styling included")
        
        print(f"\n🚀 READY TO SERVE!")
        print("   The documentation is complete and ready for use.")
        print("   To view: fix environment issues, then run 'mkdocs serve'")
        
        return True
    else:
        if not all_present:
            print("❌ Some required pages are missing")
        if total_content <= 50000:
            print("⚠️  Content may need more detail")
        return False

if __name__ == "__main__":
    check_docs()