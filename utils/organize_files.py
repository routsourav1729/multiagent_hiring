import os
import shutil
import sys

def organize_files(folder_path):
    # Create target directories
    md_dir = os.path.join(folder_path, 'markdown_files')
    txt_dir = os.path.join(folder_path, 'rawtext_files')
    os.makedirs(md_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)

    # Organize files
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        if os.path.isfile(file_path):
            if filename.lower().endswith(('.md', '.markdown')):
                shutil.move(file_path, os.path.join(md_dir, filename))
                print(f"Moved {filename} to markdown_files/")
            elif filename.lower().endswith('.txt'):
                shutil.move(file_path, os.path.join(txt_dir, filename))
                print(f"Moved {filename} to rawtext_files/")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python organize_files.py <folder_path>")
        sys.exit(1)
    
    target_folder = sys.argv[1]
    
    if not os.path.isdir(target_folder):
        print(f"Error: {target_folder} is not a valid directory")
        sys.exit(1)

    organize_files(target_folder)
    print("\nOrganization complete!")
