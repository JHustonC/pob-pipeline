#!/usr/bin/env python3
"""
Windows Setup for PoB Pipeline Fetch Character Server
=====================================================
Run this on your Windows gaming machine to set up the PoB Pipeline.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Windows paths
USER_HOME = Path.home()
POB_PIPELINE_DIR = USER_HOME / "pob-pipeline"
POB_PIPELINE_DATA = USER_HOME / ".pob_pipeline"
POB_REPO_DIR = USER_HOME / "pob_repo"

# Required environment variables
REQUIRED_ENV = {
    "GH_GIST_ID": "your-gist-id-here",
    "GH_TOKEN": "ghp_xxx-your-token-here"
}

def check_python():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required. Found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_luajit():
    """Check if LuaJIT is installed."""
    try:
        result = subprocess.run(["luajit", "-v"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ LuaJIT: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ LuaJIT not found. Install: winget install LuaJIT.LuaJIT")
    return False

def check_git():
    """Check if Git is installed."""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Git: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ Git not found. Install: winget install Git.Git")
    return False

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def clone_repos():
    """Clone PoB Pipeline and PoB repos."""
    print("\n📥 Cloning repositories...")
    
    # PoB Pipeline
    if not POB_PIPELINE_DIR.exists():
        try:
            subprocess.run(["git", "clone", "https://github.com/JHustonC/pob-pipeline.git", str(POB_PIPELINE_DIR)], check=True)
            print(f"✅ Cloned pob-pipeline to {POB_PIPELINE_DIR}")
        except subprocess.CalledProcessError:
            print("❌ Failed to clone pob-pipeline")
            return False
    else:
        print(f"✅ pob-pipeline already exists at {POB_PIPELINE_DIR}")
        # Pull latest
        subprocess.run(["git", "-C", str(POB_PIPELINE_DIR), "pull"], check=True)
    
    # PoB Repo (for headless)
    if not POB_REPO_DIR.exists():
        try:
            subprocess.run(["git", "clone", "https://github.com/PathOfBuildingCommunity/PathOfBuilding.git", str(POB_REPO_DIR)], check=True)
            print(f"✅ Cloned PoB repo to {POB_REPO_DIR}")
        except subprocess.CalledProcessError:
            print("❌ Failed to clone PoB repo")
            return False
    else:
        print(f"✅ PoB repo already exists at {POB_REPO_DIR}")
        subprocess.run(["git", "-C", str(POB_REPO_DIR), "pull"], check=True)
    
    return True

def create_data_dirs():
    """Create data directories."""
    POB_PIPELINE_DATA.mkdir(parents=True, exist_ok=True)
    print(f"✅ Data directory: {POB_PIPELINE_DATA}")

def create_env_file():
    """Create .env file for environment variables."""
    env_path = POB_PIPELINE_DIR / ".env"
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write("# PoB Pipeline Environment Variables\n")
            f.write("# Fill in your values below:\n")
            f.write("GH_GIST_ID=your-gist-id-here\n")
            f.write("GH_TOKEN=ghp_xxx-your-token-here\n")
        print(f"✅ Created .env file at {env_path}")
        print("   ⚠️  Edit this file with your actual Gist ID and GitHub token!")
    else:
        print(f"✅ .env file already exists at {env_path}")

def create_startup_bat():
    """Create startup batch file."""
    bat_path = POB_PIPELINE_DIR / "start_pob_pipeline.bat"
    with open(bat_path, "w") as f:
        f.write("@echo off\n")
        f.write("REM PoB Pipeline Fetch Character Server Startup\n")
        f.write("cd /d \"%~dp0\"\n")
        f.write("\n")
        f.write("REM Load environment variables from .env\n")
        f.write("if exist .env (\n")
        f.write("    for /f \"tokens=1,* delims==\" %%a in (.env) do (\n")
        f.write("        set \"%%a=%%b\"\n")
        f.write("    )\n")
        f.write(")\n")
        f.write("\n")
        f.write("REM Check required variables\n")
        f.write("if \"%GH_GIST_ID%\"==\"\" (\n")
        f.write("    echo ERROR: GH_GIST_ID not set. Edit .env file.\n")
        f.write("    pause\n")
        f.write("    exit /b 1\n")
        f.write(")\n")
        f.write("if \"%GH_TOKEN%\"==\"\" (\n")
        f.write("    echo ERROR: GH_TOKEN not set. Edit .env file.\n")
        f.write("    pause\n")
        f.write("    exit /b 1\n")
        f.write(")\n")
        f.write("\n")
        f.write("echo Starting PoB Pipeline Fetch Character Server...\n")
        f.write("echo Dashboard: http://localhost:8080\n")
        f.write("echo Press Ctrl+C to stop\n")
        f.write("\n")
        f.write("python fetch_character_server.py\n")
        f.write("\n")
        f.write("pause\n")
    
    print(f"✅ Created startup script: {bat_path}")

def create_task_scheduler_xml():
    """Create Task Scheduler XML for auto-start on login."""
    xml_path = POB_PIPELINE_DIR / "PoBPipeline_Task.xml"
    python_exe = sys.executable
    script_path = POB_PIPELINE_DIR / "fetch_character_server.py"
    working_dir = POB_PIPELINE_DIR
    
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{__import__('datetime').datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</Date>
    <Author>{os.getlogin()}</Author>
    <URI>\\PoBPipeline_FetchCharacterServer</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{os.getlogin()}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>{script_path}</Arguments>
      <WorkingDirectory>{working_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
    
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml_content)
    
    print(f"✅ Created Task Scheduler XML: {xml_path}")
    print(f"   Import with: schtasks /create /xml \"{xml_path}\" /tn \"PoBPipeline_FetchCharacterServer\"")

def print_summary():
    """Print setup summary."""
    print("\n" + "="*60)
    print("✅ WINDOWS SETUP COMPLETE")
    print("="*60)
    print(f"\n📁 Pipeline directory: {POB_PIPELINE_DIR}")
    print(f"📁 Data directory: {POB_PIPELINE_DATA}")
    print(f"📁 PoB repo: {POB_REPO_DIR}")
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Edit .env file with your Gist ID and GitHub token:")
    print(f"   notepad {POB_PIPELINE_DIR / '.env'}")
    print(f"\n2. Run the server:")
    print(f"   cd {POB_PIPELINE_DIR}")
    print(f"   start_pob_pipeline.bat")
    print(f"\n3. For auto-start on login, run as Administrator:")
    print(f"   schtasks /create /xml \"{POB_PIPELINE_DIR / 'PoBPipeline_Task.xml'}\" /tn \"PoBPipeline_FetchCharacterServer\"")
    print(f"\n4. Dashboard will be at: http://localhost:8080")
    print(f"   Access from other devices via Cloudflare Tunnel / Tailscale / ngrok")
    print(f"\n5. GitHub Pages dashboard (reads from Gist):")
    print(f"   Enable GitHub Pages on pob-pipeline repo")
    print(f"   Visit: https://YOURNAME.github.io/pob-pipeline/")

def main():
    print("="*60)
    print("PoB PIPELINE - WINDOWS SETUP")
    print("="*60)
    
    # Checks
    if not check_python(): return 1
    if not check_luajit(): return 1
    if not check_git(): return 1
    
    # Install
    if not install_dependencies(): return 1
    if not clone_repos(): return 1
    
    # Setup
    create_data_dirs()
    create_env_file()
    create_startup_bat()
    create_task_scheduler_xml()
    
    print_summary()
    return 0

if __name__ == "__main__":
    sys.exit(main())