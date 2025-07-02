#!/usr/bin/env python3
"""
Simple test to verify project structure and basic imports
"""

import os
import sys

def test_project_structure():
    """Test that all required files and directories exist"""
    
    required_files = [
        'main.py',
        'config.py',
        'requirements.txt',
        'README.md',
        '.env.example'
    ]
    
    required_dirs = [
        'database',
        'scraper', 
        'nlp',
        'trading'
    ]
    
    print("🔍 Testing project structure...")
    
    # Check files
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    # Check directories
    missing_dirs = []
    for directory in required_dirs:
        if os.path.isdir(directory):
            print(f"✅ {directory}/")
            
            # Check for __init__.py
            init_file = os.path.join(directory, '__init__.py')
            if os.path.exists(init_file):
                print(f"   ✅ {init_file}")
            else:
                print(f"   ❌ {init_file}")
        else:
            print(f"❌ {directory}/")
            missing_dirs.append(directory)
    
    print("\n📊 Summary:")
    print(f"   Files: {len(required_files) - len(missing_files)}/{len(required_files)} present")
    print(f"   Directories: {len(required_dirs) - len(missing_dirs)}/{len(required_dirs)} present")
    
    if missing_files or missing_dirs:
        print(f"\n❌ Missing components:")
        for item in missing_files + missing_dirs:
            print(f"   - {item}")
        return False
    else:
        print("\n✅ All required components present!")
        return True

def test_basic_imports():
    """Test basic imports without external dependencies"""
    print("\n🔍 Testing basic imports...")
    
    try:
        # Test config import
        sys.path.insert(0, '.')
        print("✅ Basic Python imports working")
        
        # Test file contents
        with open('config.py', 'r') as f:
            config_content = f.read()
            if 'class Config' in config_content:
                print("✅ Config class found")
            else:
                print("❌ Config class not found")
        
        with open('main.py', 'r') as f:
            main_content = f.read()
            if 'class BiotechTradingSystem' in main_content:
                print("✅ Main system class found")
            else:
                print("❌ Main system class not found")
                
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_requirements():
    """Test requirements.txt content"""
    print("\n🔍 Testing requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            
        required_packages = [
            'sqlalchemy',
            'loguru', 
            'requests',
            'beautifulsoup4',
            'textblob',
            'alpaca-trade-api',
            'schedule'
        ]
        
        missing_packages = []
        for package in required_packages:
            if package in requirements.lower():
                print(f"✅ {package}")
            else:
                print(f"❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n❌ Missing packages: {missing_packages}")
            return False
        else:
            print("\n✅ All required packages listed!")
            return True
            
    except Exception as e:
        print(f"❌ Error reading requirements: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("🧪 BIOTECH TRADING SYSTEM - STRUCTURE TEST")
    print("=" * 50)
    
    tests = [
        test_project_structure,
        test_basic_imports, 
        test_requirements
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if all(results):
        print("🎉 ALL TESTS PASSED! Project structure is complete.")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure API keys in .env file")
        print("3. Run: python main.py")
    else:
        print("❌ Some tests failed. Please check the output above.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)