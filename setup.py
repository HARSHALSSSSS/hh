#!/usr/bin/env python3
"""
Setup script for Biotech Trading System
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_system_requirements():
    """Check system requirements"""
    print("🔍 Checking system requirements...")
    
    # Check for chrome/chromium
    browsers = ['google-chrome', 'chromium-browser', 'chromium']
    browser_found = False
    
    for browser in browsers:
        try:
            subprocess.run([browser, '--version'], 
                         capture_output=True, check=True)
            print(f"✅ Browser found: {browser}")
            browser_found = True
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    if not browser_found:
        print("⚠️  Chrome/Chromium not found - required for web scraping")
        print("   Install with: sudo apt install chromium-browser")
    
    return browser_found

def create_virtual_environment():
    """Create and setup virtual environment"""
    print("\n🔧 Setting up virtual environment...")
    
    venv_path = Path("biotech_env")
    
    if venv_path.exists():
        print("📁 Virtual environment already exists")
        return True
    
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], 
                      check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        print("   Try: sudo apt install python3-venv")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    
    venv_python = Path("biotech_env/bin/python")
    venv_pip = Path("biotech_env/bin/pip")
    
    if not venv_python.exists():
        print("❌ Virtual environment not found")
        return False
    
    try:
        # Upgrade pip
        subprocess.run([str(venv_pip), "install", "--upgrade", "pip"], 
                      check=True)
        
        # Install requirements
        subprocess.run([str(venv_pip), "install", "-r", "requirements.txt"], 
                      check=True)
        
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment_file():
    """Setup environment configuration file"""
    print("\n⚙️  Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("📁 .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env file with your API keys:")
        print("   - ALPACA_API_KEY")
        print("   - ALPACA_SECRET_KEY")
        return True
    else:
        print("❌ .env.example not found")
        return False

def initialize_database():
    """Initialize the database"""
    print("\n🗄️  Initializing database...")
    
    venv_python = Path("biotech_env/bin/python")
    
    if not venv_python.exists():
        print("❌ Virtual environment not found")
        return False
    
    try:
        subprocess.run([
            str(venv_python), "-c", 
            "from database.models import init_database; init_database()"
        ], check=True)
        
        print("✅ Database initialized successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def create_run_script():
    """Create a convenient run script"""
    print("\n📜 Creating run script...")
    
    run_script = """#!/bin/bash
# Biotech Trading System Runner

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
source biotech_env/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Run the system
echo "🚀 Starting Biotech Trading System..."
python main.py
"""
    
    with open("run.sh", "w") as f:
        f.write(run_script)
    
    os.chmod("run.sh", 0o755)
    print("✅ Created run.sh script")
    return True

def print_final_instructions():
    """Print final setup instructions"""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("📋 Next Steps:")
    print("1. Configure your API keys in .env file:")
    print("   nano .env")
    print()
    print("2. Get Alpaca API keys:")
    print("   https://alpaca.markets/ (start with paper trading)")
    print()
    print("3. Run the system:")
    print("   ./run.sh")
    print("   # or manually:")
    print("   source biotech_env/bin/activate")
    print("   python main.py")
    print()
    print("4. Test individual components:")
    print("   source biotech_env/bin/activate")
    print("   python test_structure.py")
    print()
    print("🔒 Security Notes:")
    print("- Keep your API keys secure")
    print("- Start with paper trading")
    print("- Monitor the system closely")
    print("- Review all trades before live trading")
    print()
    print("📖 Documentation: README.md")
    print("🐛 Issues: Check biotech_trader.log")

def main():
    """Main setup function"""
    print("=" * 60)
    print("🧬 BIOTECH TRADING SYSTEM SETUP")
    print("=" * 60)
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Checking system requirements", check_system_requirements),
        ("Creating virtual environment", create_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment file", setup_environment_file),
        ("Initializing database", initialize_database),
        ("Creating run script", create_run_script),
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n🔄 {step_name}...")
        try:
            result = step_func()
            results.append(result)
            if result:
                print(f"✅ {step_name} completed")
            else:
                print(f"❌ {step_name} failed")
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 Setup Summary: {success_count}/{total_count} steps completed")
    
    if all(results):
        print_final_instructions()
        return True
    else:
        print("\n❌ Setup incomplete. Please resolve the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)