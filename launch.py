import filecmp
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from multiprocessing import freeze_support

import uvicorn

sys.path.append(os.getcwd())

# Make safetensors faster
os.environ["SAFETENSORS_FAST_GPU"] = "1"

# Set up logging
logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s', level=logging.DEBUG)
logger = logging.getLogger("launch")

# Set base path
base_path = os.path.abspath(os.path.dirname(__file__))
logger.debug(f"Script path: {base_path}")

launch_settings_path = os.path.join(base_path, "launch_settings.json")

if not os.path.exists(launch_settings_path):
    conf_src = os.path.join(base_path, "conf_src")
    shutil.copy(os.path.join(conf_src, "launch_settings.json"), launch_settings_path)

# Check that we're on Python 3.10
if sys.version_info < (3, 10):
    logger.debug("Please upgrade your python version to 3.10 or higher.")
    sys.exit()


# Placeholder functionality
def install_extensions():
    logger.debug("Checking extension installations...")


def check_bitsandbytes():
    """
    Check for "different" B&B Files and copy only if necessary
    """
    if os.name == "nt":
        try:
            bnb_src = os.path.join(os.path.dirname(os.path.realpath(__file__)), "core", "modules", "dreambooth",
                                   "bitsandbytes_windows")
            bnb_dest = os.path.join(sysconfig.get_paths()["purelib"], "bitsandbytes")
            filecmp.clear_cache()
            for file in os.listdir(bnb_src):
                src_file = os.path.join(bnb_src, file)
                if file == "main.py" or file == "paths.py":
                    dest = os.path.join(bnb_dest, "cuda_setup")
                else:
                    dest = bnb_dest
                shutil.copy2(src_file, dest)
        except:
            pass


def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    logger.debug(f"Executing shell command: {command}")
    if desc:
        logger.debug(desc)

    try:
        if live:
            result = subprocess.run(command, shell=True, env=custom_env or os.environ, check=True)
            return result
        else:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                    env=custom_env or os.environ, check=True)
            return result.stdout.decode(encoding='utf8', errors='ignore')
    except Exception as e:
        message = f"{errdesc or 'Error running command'}. Command: {command} Error code: {e.returncode}\n"
        message += f"stdout: {e.stdout.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        message += f"stderr: {e.stderr.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        logger.error(message)
        return ""


# Load launch settings
with open(os.path.join(base_path, "launch_settings.json"), "r") as ls:
    launch_settings = json.load(ls)

# Set port
listen_port = 8080
if "listen_port" in launch_settings:
    listen_port = int(launch_settings["listen_port"])
if os.environ.get("PORT", None):
    listen_port = int(os.environ.get("PORT"))

# Set our venv
venv = None
python = sys.executable

user_venv = None
default_venv = os.path.join(base_path, "venv")
if "venv" in launch_settings:
    user_venv = launch_settings["venv"]
    if os.path.isdir(user_venv):
        user_python = os.path.join(user_venv, "scripts", "python.exe" if os.name == "nt" else "python")
        if os.path.isfile(user_python):
            python = user_python
            venv = user_venv
        else:
            logger.warning(f"Unable to load user-specified python: {user_python}")

else:
    if not os.path.isdir(default_venv):
        venv_command = f"\"{python}\" -m venv \"{default_venv}\""
        # if sys.platform == "win32":
        #     venv_command = f"cmd.exe /c {venv_command}"
        logger.info(f"Creating venv: {venv_command}")
        run(venv_command, "Creating venv.")
    default_python = os.path.join(default_venv, "scripts", "python.exe" if os.name == "nt" else "python")
    venv = default_venv
    if not os.path.isfile(default_python):
        logger.warning("Unable to find python executable!")
    else:
        python = default_python

path = os.environ.get("PATH")
sys.path.append(venv)

freeze_command = "pip freeze"
if sys.platform == "win32":
    activate = os.path.join(venv, "Scripts", "activate.bat")
    run_command = f"cmd /c {activate} & {freeze_command}"
else:
    activate = os.path.join(venv, "bin", "activate")
    run_command = f". {activate} && {freeze_command}"

frozen = run(run_command)

# Install extensions first
install_extensions()


def find_git():
    git_binary = shutil.which("git")
    if git_binary:
        return git_binary

    common_git_paths = {
        "Windows": [
            "C:\\Program Files\\Git\\bin\\git.exe",
            "C:\\Program Files (x86)\\Git\\bin\\git.exe",
        ],
        "Linux": [
            "/usr/bin/git",
            "/usr/local/bin/git",
        ],
        "Darwin": [
            "/usr/bin/git",
            "/usr/local/bin/git",
        ],
    }

    for path in common_git_paths[platform.system()]:
        if os.path.exists(path):
            return path

    return None


# Define the dreambooth repository path
dreambooth_path = os.path.join(base_path, "core", "modules", "dreambooth")
annotators_path = os.path.join(base_path, "core", "modules", "infer", "src", "annotators")
git_path = find_git()

if git_path:
    logger.debug(f"Got git git: {git_path}")
    if not os.path.exists(dreambooth_path):
        logger.debug("Cloning dreambooth repository.")
        # Clone dreambooth repository
        branch = launch_settings.get("dreambooth_branch", "dev")
        clone_command = [git_path, "clone", "-b", branch, "https://github.com/d8ahazard/sd_dreambooth_extension.git",
                         dreambooth_path]
        logger.debug(f"Clone command: {clone_command}")
        subprocess.run(clone_command, check=True)
    else:
        logger.debug("Updating dreambooth repository.")
        # Fetch changes from dreambooth repository
        fetch_command = [git_path, "fetch", "origin"]
        subprocess.run(fetch_command, cwd=dreambooth_path, check=True)
        # Pull changes from dreambooth repository
        pull_command = [git_path, "pull", "origin", "HEAD"]
        subprocess.run(pull_command, cwd=dreambooth_path, check=True)
else:
    if not os.path.exists(dreambooth_path):
        logger.warning("Unable to find git, and dreambooth is not installed. Training will not be available.")

# Add the dreambooth dir to sys path
module_dir = os.path.abspath(dreambooth_path)
sys.path.insert(0, module_dir)

# NOW we install our requirements
requirements = os.path.join(base_path, "requirements.txt")

# Check to make sure what's installed matches requirements
do_install = False
with open(requirements, "r") as req_file:
    reqs = set(req_file.read().splitlines())
frozen = set(frozen.splitlines())

if reqs.difference(frozen) and not os.path.exists("workspace/stable-diffusion-plus"):
    do_install = True

# Install torch stuff
torch_command = None
if "torch_command" in launch_settings:
    torch_command = launch_settings["torch_command"]

if sys.platform == "win32":
    activate = os.path.join(venv, "Scripts", "activate.bat")
else:
    activate = f"source {os.path.join(venv, 'bin', 'activate')}"

# Define the dreambooth repository path
dreambooth_path = os.path.join(base_path, "core", "modules", "dreambooth")

# Create a new environment for the subprocess to run in
env = os.environ.copy()
env["PATH"] = os.path.join(venv, "bin") + os.pathsep + env["PATH"]
env["VIRTUAL_ENV"] = venv
env["PYTHONPATH"] = os.pathsep.join([dreambooth_path, os.path.dirname(os.path.abspath(__file__))])

install_command = f"{activate} && {python} -m pip install -r {requirements}"
torch_command = f"{activate} && {python} -m {torch_command}"

if os.environ.get("SKIP_INSTALL", "false").lower() == "true":
    do_install = False

if do_install:
    logger.info(f"Installing the things: {install_command}")
    run(install_command, "Installing the things.")

check_bitsandbytes()

if __name__ == '__main__':
    freeze_support()
    uvicorn.run("app.main:app", port=listen_port, reload=True, access_log=False, host="0.0.0.0")
