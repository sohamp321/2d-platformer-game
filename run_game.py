#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import venv

# ----- Configuration -----
# Name of the virtual environment folder
ENV_DIR = "env"

# List of packages to install
REQUIREMENTS = [
    "pygame",
    "numpy",
    "PyOpenGL",
]

# Path to main.py (adjust if necessary)
MAIN_SCRIPT = "main.py"

# ----- Functions -----
def create_virtualenv(env_dir):
    """Create a virtual environment if it doesn't exist."""
    if not os.path.exists(env_dir):
        print(f"Creating virtual environment in '{env_dir}'...")
        venv.EnvBuilder(with_pip=True).create(env_dir)
    else:
        print(f"Virtual environment '{env_dir}' already exists.")

def get_executable_path(env_dir, executable_name):
    """Return the path to an executable (python or pip) inside the virtual environment."""
    if platform.system() == "Windows":
        return os.path.join(env_dir, "Scripts", executable_name + ".exe")
    else:
        return os.path.join(env_dir, "bin", executable_name)

def install_packages(env_dir, requirements):
    """Install the required packages using pip from the virtual environment."""
    pip_executable = get_executable_path(env_dir, "pip")
    # Try to upgrade pip. If it fails, print a warning and continue.
    try:
        print("Upgrading pip...")
        subprocess.check_call([get_executable_path(env_dir, "python"), "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("Warning: Failed to upgrade pip. Continuing with installed version.")
    for package in requirements:
        print(f"Installing {package} ...")
        subprocess.check_call([pip_executable, "install", package])

def run_main_script(env_dir, script_path):
    """Run the main script using the virtual environment's python interpreter."""
    python_executable = get_executable_path(env_dir, "python")
    print(f"Running '{script_path}' using {python_executable} ...")
    subprocess.check_call([python_executable, script_path])

def main():
    # Create virtual environment if needed
    create_virtualenv(ENV_DIR)
    # Install packages
    install_packages(ENV_DIR, REQUIREMENTS)
    # Run the main application
    run_main_script(ENV_DIR, MAIN_SCRIPT)

if __name__ == "__main__":
    main()
