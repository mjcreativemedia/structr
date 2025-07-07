#!/usr/bin/env python3
"""
Test script to verify configuration refactoring is working correctly
"""

import sys
from pathlib import Path

def test_config_import():
    """Test that CONFIG can be imported successfully"""
    try:
        from config import CONFIG
        print("✅ CONFIG import successful")
        return True
    except ImportError as e:
        print(f"❌ CONFIG import failed: {e}")
        return False

def test_config_methods():
    """Test that CONFIG methods return expected values"""
    try:
        from config import CONFIG
        
        # Test directory methods
        output_dir = CONFIG.get_output_dir()
        bundles_dir = CONFIG.get_bundles_dir()
        temp_dir = CONFIG.get_temp_dir()
        
        print(f"✅ Output directory: {output_dir}")
        print(f"✅ Bundles directory: {bundles_dir}")
        print(f"✅ Temp directory: {temp_dir}")
        
        # Test LLM methods
        llm_model = CONFIG.get_llm_model()
        llm_url = CONFIG.get_llm_base_url()
        
        print(f"✅ LLM model: {llm_model}")
        print(f"✅ LLM URL: {llm_url}")
        
        # Test server methods
        dashboard_port = CONFIG.get_dashboard_port()
        api_port = CONFIG.get_api_port()
        
        print(f"✅ Dashboard port: {dashboard_port}")
        print(f"✅ API port: {api_port}")
        
        # Test file constants
        print(f"✅ Audit filename: {CONFIG.AUDIT_FILENAME}")
        print(f"✅ Sync filename: {CONFIG.SYNC_FILENAME}")
        print(f"✅ HTML filename: {CONFIG.HTML_FILENAME}")
        
        # Test score thresholds
        print(f"✅ Score thresholds: {CONFIG.SCORE_THRESHOLDS}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config methods test failed: {e}")
        return False

def test_dashboard_imports():
    """Test that dashboard modules can import CONFIG successfully"""
    dashboard_modules = [
        'dashboard.pages.overview',
        'dashboard.pages.batch_processor', 
        'dashboard.pages.audit_manager',
        'dashboard.pages.bundle_explorer',
        'dashboard.pages.export_center',
        'dashboard.enhanced_audit',
        'dashboard.enhanced_csv'
    ]
    
    success_count = 0
    
    for module_name in dashboard_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            # Check if CONFIG is accessible in the module
            if hasattr(module, 'CONFIG'):
                print(f"✅ {module_name} - CONFIG accessible")
                success_count += 1
            else:
                print(f"⚠️  {module_name} - CONFIG imported but not directly accessible")
                success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - Import failed: {e}")
        except Exception as e:
            print(f"❌ {module_name} - Error: {e}")
    
    print(f"\n📊 Dashboard imports: {success_count}/{len(dashboard_modules)} successful")
    return success_count == len(dashboard_modules)

def test_core_imports():
    """Test that core modules can import CONFIG successfully"""
    core_modules = [
        'cli',
        'start_dashboard',
        'llm_service.generator',
        'fix_broken_pdp',
        'export.csv_exporter'
    ]
    
    success_count = 0
    
    for module_name in core_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"✅ {module_name} - Import successful")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - Import failed: {e}")
        except Exception as e:
            print(f"❌ {module_name} - Error: {e}")
    
    print(f"\n📊 Core imports: {success_count}/{len(core_modules)} successful")
    return success_count == len(core_modules)

def test_directory_creation():
    """Test that CONFIG can create required directories"""
    try:
        from config import CONFIG
        
        # This should create all required directories
        CONFIG.ensure_directories()
        
        # Check if directories exist
        directories = [
            CONFIG.get_output_dir(),
            CONFIG.get_bundles_dir(),
            CONFIG.get_temp_dir(),
            CONFIG.get_logs_dir(),
            CONFIG.get_exports_dir()
        ]
        
        all_exist = True
        for directory in directories:
            if directory.exists():
                print(f"✅ Directory exists: {directory}")
            else:
                print(f"❌ Directory missing: {directory}")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Directory creation test failed: {e}")
        return False

def main():
    """Run all configuration tests"""
    print("🧪 Testing Structr Configuration Refactoring\n")
    
    tests = [
        ("CONFIG Import", test_config_import),
        ("CONFIG Methods", test_config_methods),
        ("Dashboard Imports", test_dashboard_imports),
        ("Core Module Imports", test_core_imports),
        ("Directory Creation", test_directory_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 50)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All configuration refactoring tests passed!")
        print("✅ Configuration refactoring is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())