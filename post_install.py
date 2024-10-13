import os
import subprocess
import shutil

def check_git():
    if shutil.which("git") is None:
        raise EnvironmentError("Git is not installed. Please install Git and try again.")

def setup_repository():
    repo_url = "https://github.com/GirardeauLab/probeinterface_library.git"
    upstream_url = "https://github.com/spikeinterface/probeinterface_library.git"
    repo_path = os.path.expanduser("~/probeinterface_library")

    if not os.path.exists(repo_path):
        # Clone the repository if it doesn't exist
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)

    os.chdir(repo_path)
    # Add the original repository as a remote if it's not already added
    subprocess.run(["git", "remote", "add", "upstream", upstream_url], check=True)

if __name__ == "__main__":
    check_git()
    setup_repository()