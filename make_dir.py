#!/usr/bin/env python3
"""
Setup script to create the resume-ai project directory structure
"""
import os
import sys

def create_directories():
    # Define the parent directory where everything should be created
    parent_dir = "/raid/biplab/souravr/TIH/TIH_RESUME/JD_CV"
    
    # Define the base directory structure relative to parent directory
    directories = [
        "config",
        "data/input/resumes",
        "data/input/job_descriptions",
        "data/output/extracted",
        "data/output/evaluated", 
        "data/output/summarized",
        "data/output/final",
        "data/knowledge/sources",
        "models/gguf",
        "agents",
        "tools",
        "utils"
    ]
    
    # Create the directories
    for directory in directories:
        path = os.path.join(parent_dir, directory)
        os.makedirs(path, exist_ok=True)
        print(f"Created directory: {path}")
    
    # Create __init__.py files in Python module directories
    init_files = [
        "agents",
        "tools",
        "utils"
    ]
    
    for directory in init_files:
        init_path = os.path.join(parent_dir, directory, "__init__.py")
        with open(init_path, 'w') as f:
            f.write(f"# {directory} module initialization\n")
        print(f"Created __init__.py in {directory}")
    
    # Create placeholder config files
    config_files = {
        "agents.yaml": "# Agent configurations for CrewAI framework\n",
        "tasks.yaml": "# Task configurations for CrewAI framework\n",
        "model_config.yaml": "# Model configuration for all stages\n"
    }
    
    for filename, content in config_files.items():
        file_path = os.path.join(parent_dir, "config", filename)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Created placeholder config file: {file_path}")
    
    # Create basic main script
    run_path = os.path.join(parent_dir, "run.py")
    with open(run_path, 'w') as f:
        f.write("""#!/usr/bin/env python3
\"\"\"
Main entry point for resume processing system
\"\"\"
import os
import argparse
from pathlib import Path

def main():
    print("Resume Processing System")
    
if __name__ == "__main__":
    main()
""")
    print(f"Created main script: {run_path}")
    
    print("\nDirectory structure setup complete!")

if __name__ == "__main__":
    create_directories()