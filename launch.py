import json
import os
import shutil
import subprocess
import sys

from dreambooth.dreambooth import shared

# Make safetensors faster
os.environ["SAFETENSORS_FAST_GPU"] = "1"

# Set base path
path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
shared.script_path = path

launch_settings_path = os.path.join(shared.script_path, "launch_settings.json")

if not os.path.exists(launch_settings_path):
    conf_src = os.path.join(shared.script_path, "conf_src")
    shutil.copy(os.path.join(conf_src, "launch_settings.json"), launch_settings_path)

# Check that we're on Python 3.10
if sys.version_info < (3, 10):
    print("Please upgrade your python version to 3.10 or higher.")
    sys.exit()


# Placeholder functionality
def load_extensions():
    print("Load extensions or something")


def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    if desc:
        print(desc)

    if live:
        result = subprocess.run(command, shell=True, env=custom_env or os.environ)
        if result.returncode:
            raise RuntimeError(f"{errdesc or 'Error running command'}. Command: {command} Error code: {result.returncode}")
        return ""

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=custom_env or os.environ)

    if result.returncode:
        message = f"{errdesc or 'Error running command'}. Command: {command} Error code: {result.returncode}\n"
        message += f"stdout: {result.stdout.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        message += f"stderr: {result.stderr.decode(encoding='utf8', errors='ignore') or '<empty>'}\n"
        raise RuntimeError(message)

    return result.stdout.decode(encoding='utf8', errors='ignore')


# Install extensions first
load_extensions()

# Load launch settings
with open(os.path.join(path, "launch_settings.json"), "r") as ls:
    launch_settings = json.load(ls)

print(f"Launch settings: {launch_settings}")

# Set port
listen_port = 8080
if "listen_port" in launch_settings:
    listen_port = int(launch_settings["listen_port"])

# Set our venv
venv = None
python = sys.executable

user_venv = None
default_venv = os.path.join(shared.script_path, "venv")

if "venv" in launch_settings:
    user_venv = launch_settings["venv"]
    if os.path.isdir(user_venv):
        user_python = os.path.join(user_venv, "scripts", "python.exe" if os.name == "nt" else "python")
        if os.path.isfile(user_python):
            python = user_python
            venv = user_venv
        else:
            print(f"Unable to load user-specified python: {user_python}")

else:
    if not os.path.isdir(default_venv):
        venv_command = f"\"{python}\" -m venv \"{default_venv}\""
        # if sys.platform == "win32":
        #     venv_command = f"cmd.exe /c {venv_command}"
        print(f"Creating venv: {venv_command}")
        run(venv_command, "Creating venv.")
    default_python = os.path.join(default_venv, "scripts", "python.exe" if os.name == "nt" else "python")
    venv = default_venv
    if not os.path.isfile(default_python):
        print("Unable to find python executable!")
        sys.exit()
    python = default_python

path = os.environ.get("PATH")
print(f"Current path: {path}")
requirements = os.path.join(shared.script_path, "requirements.txt")

freeze_command = "pip freeze"
if sys.platform == "win32":
    activate = os.path.join(venv, "Scripts", "activate.bat")
    run_command = f"cmd /c {activate} & {freeze_command}"
else:
    activate = os.path.join(venv, "bin", "activate")
    run_command = f"source {activate} && {freeze_command}"

frozen = run(run_command)

do_install = False
with open(requirements, "r") as req_file:
    reqs = set(req_file.read().splitlines())
frozen = set(frozen.splitlines())

if reqs.difference(frozen):
    do_install = True

torch_command = None
if "torch_command" in launch_settings:
    torch_command = launch_settings["torch_command"]

if sys.platform == "win32":
    activate = os.path.join(venv, "Scripts", "activate.bat")
    install_command = f"cmd /c {activate} & {python} -m pip install -r {requirements}"
    torch_command = f"cmd /c {activate} & {python} -m {torch_command}"
    run_command = f"{activate} & uvicorn app.main:app --reload --port {listen_port}"
else:
    activate = os.path.join(venv, "bin", "activate")
    install_command = f"source {activate} && {python} -m pip install -r {requirements}"
    torch_command = f"source {activate} && {python} -m {torch_command}"
    run_command = f"uvicorn app.main:app --reload --port {listen_port}"
    run_command = f"source {activate} && {run_command}"

run(torch_command, "Checking torch versions...", "Unable to install torch.")

if do_install:
    print(f"Installing: {install_command}")
    run(install_command, "Installing requirements.", "Unable to install requirements.")

print(f"Running: {run_command}")

run(run_command, live=True)
