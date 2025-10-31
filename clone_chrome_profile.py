"""
Create a dedicated copy of your Chrome profile for the agent.
This allows the agent to use your logged-in sessions without interfering with your main Chrome.
"""
import shutil
import os
from pathlib import Path
from datetime import datetime

print("\n" + "="*80)
print("🔧 CHROME PROFILE CLONER FOR AGENT")
print("="*80 + "\n")

# Source profile (your existing Chrome profile)
source_profile = Path(r"C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default")

# Destination (new agent profile)
agent_profiles_dir = Path("C:/Agent-S-Redfinger/chrome_profiles")
agent_profile = agent_profiles_dir / "AgentProfile"

print(f"📂 Source Profile: {source_profile}")
print(f"📂 Destination: {agent_profile}")
print()

# Check if source exists
if not source_profile.exists():
    print(f"❌ Source profile not found: {source_profile}")
    print("   Make sure Chrome has been run at least once.")
    exit(1)

# Create destination directory
agent_profiles_dir.mkdir(parents=True, exist_ok=True)

# Check if agent profile already exists
if agent_profile.exists():
    print(f"⚠️  Agent profile already exists: {agent_profile}")
    response = input("   Do you want to overwrite it? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled.")
        exit(0)
    print("🗑️  Removing existing agent profile...")
    shutil.rmtree(agent_profile)

print("\n🚀 Cloning Chrome profile...")
print("   This may take a minute depending on profile size...\n")

# Files/folders to exclude (large caches that aren't needed)
exclude_patterns = [
    'Service Worker',
    'Code Cache',
    'GPUCache',
    'ShaderCache',
    'DawnCache',
]

def should_exclude(path):
    """Check if path should be excluded from copy."""
    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern in path_str:
            return True
    return False

# Copy with progress tracking
total_size = 0
copied_files = 0
skipped_files = 0

try:
    # Create the base directory
    agent_profile.mkdir(parents=True, exist_ok=True)
    
    # Walk through source and copy files
    for root, dirs, files in os.walk(source_profile):
        root_path = Path(root)
        
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(root_path / d)]
        
        # Calculate relative path
        rel_path = root_path.relative_to(source_profile)
        dest_dir = agent_profile / rel_path
        
        # Create directory in destination
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file in files:
            src_file = root_path / file
            
            if should_exclude(src_file):
                skipped_files += 1
                continue
            
            dest_file = dest_dir / file
            
            try:
                shutil.copy2(src_file, dest_file)
                file_size = src_file.stat().st_size
                total_size += file_size
                copied_files += 1
                
                if copied_files % 100 == 0:
                    print(f"   Copied {copied_files} files ({total_size / (1024*1024):.1f} MB)...")
            except Exception as e:
                # Some files may be locked or inaccessible, skip them
                skipped_files += 1
                if "being used by another process" not in str(e):
                    print(f"   ⚠️  Skipped {file}: {e}")
    
    print(f"\n✅ Profile cloned successfully!")
    print(f"   📊 Copied: {copied_files} files")
    print(f"   📊 Size: {total_size / (1024*1024):.1f} MB")
    print(f"   📊 Skipped: {skipped_files} files (caches, locked files)")
    
except Exception as e:
    print(f"\n❌ Error during cloning: {e}")
    exit(1)

# Create a marker file with info
info_file = agent_profile / "AGENT_PROFILE_INFO.txt"
with open(info_file, "w") as f:
    f.write(f"Agent Profile Clone\n")
    f.write(f"===================\n\n")
    f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Source: {source_profile}\n")
    f.write(f"Files: {copied_files}\n")
    f.write(f"Size: {total_size / (1024*1024):.1f} MB\n\n")
    f.write(f"This is a dedicated profile for the AI agent.\n")
    f.write(f"It contains your logged-in sessions but is independent of your main Chrome profile.\n")

print("\n" + "="*80)
print("📋 USAGE INSTRUCTIONS")
print("="*80 + "\n")

print("Your agent profile is ready to use!\n")

print("🚀 Run agent with the cloned profile:\n")
print(f'$env:OPENAI_BASE_URL = $null')
print(f'C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `')
print(f'  --start "https://gmail.com" `')
print(f'  --goal "Check inbox" `')
print(f'  --provider openai `')
print(f'  --model gpt-5 `')
print(f'  --profile "{agent_profile}" `')
print(f'  --max-steps 2')

print("\n✅ BENEFITS OF THE CLONED PROFILE:")
print("-" * 80)
print("1. Agent has access to your logged-in sessions")
print("2. You can use Chrome normally while agent runs")
print("3. Agent's browsing won't affect your main profile")
print("4. Safe isolation - agent can't mess up your main profile")
print("5. Can delete/recreate anytime without risk")

print("\n⚠️  NOTES:")
print("-" * 80)
print("1. Sessions will eventually expire - reclone when needed")
print("2. This is a one-time snapshot - future logins won't sync")
print("3. To update, just run this script again")
print("4. The clone is ~500MB-2GB depending on your profile")

print("\n🔄 TO UPDATE THE PROFILE:")
print("-" * 80)
print("Just run this script again - it will replace the old clone with a fresh copy.")

print("\n" + "="*80 + "\n")
