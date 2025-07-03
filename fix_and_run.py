#!/usr/bin/env python3
"""
Fix and Run Script for Biotech Trading System
Handles common issues and provides better error reporting
"""

import sys
import os
import subprocess

def check_dependencies():
    """Check and install missing dependencies"""
    print("🔍 Checking dependencies...")
    
    missing_packages = []
    
    # Essential packages to check
    essential_packages = [
        'pydantic', 'loguru', 'schedule', 'sqlalchemy',
        'requests', 'beautifulsoup4', 'selenium', 'pandas',
        'textblob', 'transformers', 'alpaca_trade_api'
    ]
    
    for package in essential_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--break-system-packages'
            ] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    return True

def check_chrome_driver():
    """Check Chrome/Chromium installation"""
    print("\n🌐 Checking Chrome/Chromium...")
    
    chrome_commands = ['google-chrome', 'chromium-browser', 'chromium']
    chrome_found = False
    
    for cmd in chrome_commands:
        try:
            result = subprocess.run([cmd, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Found: {result.stdout.strip()}")
                chrome_found = True
                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    if not chrome_found:
        print("❌ Chrome/Chromium not found")
        print("📦 Installing Chromium...")
        try:
            subprocess.check_call(['sudo', 'apt-get', 'update'])
            subprocess.check_call(['sudo', 'apt-get', 'install', '-y', 'chromium-browser'])
            print("✅ Chromium installed successfully!")
        except subprocess.CalledProcessError:
            print("⚠️  Could not install Chromium automatically")
            print("   Please install manually: sudo apt-get install chromium-browser")
            return False
    
    return True

def check_config():
    """Check configuration file"""
    print("\n⚙️  Checking configuration...")
    
    if not os.path.exists('.env'):
        print("⚠️  .env file not found - creating from template...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✅ Created .env from template")
            print("📝 Please edit .env file with your credentials:")
            print("   - ALPACA_API_KEY and ALPACA_SECRET_KEY")
            print("   - EMAIL_USER and EMAIL_PASSWORD (optional)")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file exists")
    
    return True

def fix_common_issues():
    """Fix common runtime issues"""
    print("\n🔧 Applying fixes...")
    
    # Fix 1: Update WebDriver service import
    base_scraper_path = "scraper/base.py"
    if os.path.exists(base_scraper_path):
        with open(base_scraper_path, 'r') as f:
            content = f.read()
        
        if "ChromeDriverManager().install()" in content and "Service" not in content:
            print("🔧 Fixing WebDriver service issue...")
            content = content.replace(
                "from webdriver_manager.chrome import ChromeDriverManager",
                "from webdriver_manager.chrome import ChromeDriverManager\nfrom selenium.webdriver.chrome.service import Service"
            )
            content = content.replace(
                "self.driver = webdriver.Chrome(\n                    ChromeDriverManager().install(),\n                    options=chrome_options\n                )",
                "service = Service(ChromeDriverManager().install())\n                self.driver = webdriver.Chrome(\n                    service=service,\n                    options=chrome_options\n                )"
            )
            
            with open(base_scraper_path, 'w') as f:
                f.write(content)
            print("✅ WebDriver service fixed")
    
    # Fix 2: Add timezone handling
    main_path = "main.py"
    if os.path.exists(main_path):
        with open(main_path, 'r') as f:
            content = f.read()
        
        if "pytz" not in content:
            print("🔧 Adding timezone support...")
            content = content.replace(
                "import os\nimport sys",
                "import os\nimport sys\nimport pytz"
            )
            
            with open(main_path, 'w') as f:
                f.write(content)
            print("✅ Timezone support added")
    
    print("✅ Common fixes applied")
    return True

def run_system():
    """Run the biotech trading system"""
    print("\n🚀 Starting Biotech Trading System...")
    print("Press Ctrl+C to stop the system")
    print("=" * 50)
    
    try:
        import main
        main.main()
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("1. Check .env file has correct credentials")
        print("2. Ensure internet connection is working")
        print("3. Verify Alpaca API keys are valid")
        print("4. Check system logs for detailed errors")
        return False
    
    return True

def main():
    """Main function"""
    print("🧬 BIOTECH TRADING SYSTEM - FIX & RUN")
    print("=" * 50)
    
    steps = [
        ("Checking dependencies", check_dependencies),
        ("Checking Chrome/Chromium", check_chrome_driver),
        ("Checking configuration", check_config),
        ("Applying fixes", fix_common_issues),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            print(f"❌ Failed: {step_name}")
            print("Please fix the issues above and try again.")
            return 1
    
    print("\n✅ All checks passed!")
    print("🚀 Ready to start the system!")
    
    # Ask user if they want to run
    response = input("\nStart the biotech trading system now? (y/n): ")
    if response.lower() in ['y', 'yes']:
        return 0 if run_system() else 1
    else:
        print("System ready to run. Use: python3 main.py")
        return 0

if __name__ == "__main__":
    sys.exit(main())