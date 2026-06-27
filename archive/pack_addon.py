import os
import zipfile
import re
import glob

# Configuration
addon_name = "AMP_AniMatePro"
base_dir = r"D:\Code\AMP_AniMatePro\AMP_AniMatePro_v0.25.10318"
addon_dir = os.path.join(base_dir, addon_name)
output_dir = base_dir

def get_next_version(output_dir, base_version="0.27.0"):
    # Look for existing zips matching AMP_AniMatePro_v.*.zip
    pattern = os.path.join(output_dir, "AMP_AniMatePro_v.*.zip")
    existing_zips = glob.glob(pattern)
    
    if not existing_zips:
        return base_version
        
    highest_major = 0
    highest_minor = 27
    highest_patch = -1
    
    version_regex = re.compile(r"AMP_AniMatePro_v\.(\d+)\.(\d+)\.(\d+)\.zip")
    
    for zip_file in existing_zips:
        basename = os.path.basename(zip_file)
        match = version_regex.match(basename)
        if match:
            major, minor, patch = map(int, match.groups())
            if (major, minor, patch) > (highest_major, highest_minor, highest_patch):
                highest_major, highest_minor, highest_patch = major, minor, patch
                
    if highest_patch == -1:
        # None matched exactly or they were lower than base
        return base_version
        
    return f"{highest_major}.{highest_minor}.{highest_patch + 1}"

def pack_addon():
    version_str = get_next_version(output_dir)
    zip_filename = f"AMP_AniMatePro_v.{version_str}.zip"
    zip_filepath = os.path.join(output_dir, zip_filename)
    
    print(f"Creating zip file: {zip_filepath}")
    
    # Files to exclude from zip (pyc, __pycache__, .git, etc)
    excludes = ['__pycache__', '.git', '.gitignore', '.vscode']
    
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(addon_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in excludes]
            
            for file in files:
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    continue
                    
                file_path = os.path.join(root, file)
                # The arcname should be AMP_AniMatePro/...
                arcname = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, arcname)
                
    print(f"Successfully packed {addon_name} into {zip_filename}")

if __name__ == "__main__":
    pack_addon()
