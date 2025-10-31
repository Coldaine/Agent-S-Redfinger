"""
Find and display Chrome profile paths on Windows.
"""
import os
from pathlib import Path

print("\n" + "="*80)
print("🔍 CHROME PROFILE FINDER")
print("="*80 + "\n")

# Common Chrome profile locations on Windows
chrome_paths = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
    Path(os.environ.get("APPDATA", "")) / "Google" / "Chrome" / "User Data",
]

found_profiles = []

for base_path in chrome_paths:
    if base_path.exists():
        print(f"✅ Found Chrome User Data: {base_path}\n")
        
        # List available profiles
        print("📂 Available Profiles:")
        print("-" * 80)
        
        # Default profile
        default_profile = base_path / "Default"
        if default_profile.exists():
            found_profiles.append(str(default_profile))
            print(f"  1. Default Profile")
            print(f"     Path: {default_profile}")
            print()
        
        # Numbered profiles (Profile 1, Profile 2, etc.)
        profile_num = 1
        while True:
            profile_path = base_path / f"Profile {profile_num}"
            if profile_path.exists():
                found_profiles.append(str(profile_path))
                print(f"  {len(found_profiles)}. Profile {profile_num}")
                print(f"     Path: {profile_path}")
                
                # Try to read profile name from Preferences
                prefs_file = profile_path / "Preferences"
                if prefs_file.exists():
                    try:
                        import json
                        with open(prefs_file, 'r', encoding='utf-8') as f:
                            prefs = json.load(f)
                            profile_name = prefs.get("profile", {}).get("name", "Unknown")
                            print(f"     Name: {profile_name}")
                    except Exception:
                        pass
                print()
                profile_num += 1
            else:
                break

if found_profiles:
    print("="*80)
    print("📋 USAGE INSTRUCTIONS")
    print("="*80 + "\n")
    
    print("To use your Chrome profile with the agent, run:\n")
    
    # Show command for first profile (usually Default)
    profile_path = found_profiles[0].replace("\\", "\\\\")
    
    print(f'$env:OPENAI_BASE_URL = $null')
    print(f'C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `')
    print(f'  --start "https://gmail.com" `')
    print(f'  --goal "Check inbox" `')
    print(f'  --provider openai `')
    print(f'  --model gpt-5 `')
    print(f'  --profile "{found_profiles[0]}" `')
    print(f'  --max-steps 2')
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("-" * 80)
    print("1. Close ALL Chrome windows before running (profile must not be in use)")
    print("2. The agent will have access to your:")
    print("   - Logged-in sessions (Gmail, GitHub, etc.)")
    print("   - Cookies and browsing history")
    print("   - Saved passwords (if not encrypted)")
    print("   - Extensions and settings")
    print("3. For safety, consider using a separate Chrome profile for automation")
    print("\n🔐 TO CREATE A NEW PROFILE FOR THE AGENT:")
    print("-" * 80)
    print("1. Open Chrome")
    print("2. Click your profile icon (top right)")
    print("3. Click 'Add'")
    print("4. Name it 'Agent Profile' or similar")
    print("5. Sign in to services you want the agent to access")
    print("6. Close Chrome")
    print("7. Use the new profile path with --profile flag")
    
    print("\n" + "="*80 + "\n")
else:
    print("❌ No Chrome profiles found!")
    print("   Make sure Chrome is installed and has been run at least once.")
    print("\n" + "="*80 + "\n")
