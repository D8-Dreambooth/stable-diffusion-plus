import json
import logging
import os
import platform
import shutil
import site
import subprocess
import sys
from multiprocessing import freeze_support

logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s', level=logging.DEBUG)
logger = logging.getLogger("launch")


# Placeholder functionality
def install_extensions():
    pass


def run(command, desc=None, errdesc=None, custom_env=None, live=False):
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


def main():
    sys.path.append(os.getcwd())

    # Make safetensors faster
    os.environ["SAFETENSORS_FAST_GPU"] = "1"

    # Set up logging
    to_skip = ["urllib3", "PIL", "accelerate", "matplotlib", "h5py", "xformers", "tensorflow", "passlib", "asyncio"]
    for skip in to_skip:
        logging.getLogger(skip).setLevel(logging.WARNING)

    # Set base path
    base_path = os.path.abspath(os.path.dirname(__file__))
    launch_settings_path = os.path.join(base_path, "launch_settings.json")

    if not os.path.exists(launch_settings_path):
        conf_src = os.path.join(base_path, "conf_src")
        shutil.copy(os.path.join(conf_src, "launch_settings.json"), launch_settings_path)

    # Check that we're on Python 3.10
    if sys.version_info < (3, 10):
        logger.error("Please upgrade your python version to 3.10 or higher.")
        sys.exit()

    # Load launch settings
    with open(os.path.join(base_path, "launch_settings.json"), "r") as ls:
        launch_settings = json.load(ls)

    # Set port
    port = 8080
    if "listen_port" in launch_settings:
        port = int(launch_settings["listen_port"])
    if os.environ.get("PORT", None):
        port = int(os.environ.get("PORT"))

    # Set our venv
    venv_dir = None
    python = sys.executable

    default_venv = os.path.join(base_path, "venv")
    if "venv" in launch_settings:
        user_venv = launch_settings["venv"]
        if os.path.isdir(user_venv):
            user_python = os.path.join(user_venv, "scripts", "python.exe" if os.name == "nt" else "python")
            if os.path.isfile(user_python):
                python = user_python
                venv_dir = user_venv
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
        venv_dir = default_venv
        if not os.path.isfile(default_python):
            logger.warning("Unable to find python executable!")
        else:
            python = default_python

    sys.path.append(venv_dir)

    freeze_command = "pip freeze"
    if sys.platform == "win32":
        activate = os.path.join(venv_dir, "Scripts", "activate.bat")
        run_command = f"cmd /c {activate} & {freeze_command}"
    else:
        activate = os.path.join(venv_dir, "bin", "activate")
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
    git_path = find_git()

    if git_path:
        if not os.path.exists(dreambooth_path):
            logger.info("Cloning dreambooth repository...")
            # Clone dreambooth repository
            branch = launch_settings.get("dreambooth_branch", "dev")
            clone_command = [git_path, "clone", "-b", branch,
                             "https://github.com/d8ahazard/sd_dreambooth_extension.git",
                             dreambooth_path]
            subprocess.run(clone_command, check=True)
        else:
            logger.info("Updating dreambooth repository...")
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

    if sys.platform == "win32":
        activate = os.path.join(venv_dir, "Scripts", "activate.bat")
    else:
        activate = f"source {os.path.join(venv_dir, 'bin', 'activate')}"

    # Define the dreambooth repository path
    dreambooth_path = os.path.join(base_path, "core", "modules", "dreambooth")

    # Create a new environment for the subprocess to run in
    env = os.environ.copy()
    env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + env["PATH"]
    env["VIRTUAL_ENV"] = venv_dir
    env["PYTHONPATH"] = os.pathsep.join([dreambooth_path, os.path.dirname(os.path.abspath(__file__))])

    install_command = f"{activate} && {python} -m pip install -r {requirements}"

    if os.environ.get("SKIP_INSTALL", "false").lower() == "true":
        do_install = False

    if do_install:
        run(install_command, "Installing the things.")

    return port, python, venv_dir


if __name__ == "__main__":
    listen_port, python, base = main()
    # Prepend the venv's bin directory to the PATH environment variable if linux, otherwise prepend the Scripts
    # directory
    if sys.platform == "win32":
        os.environ["PATH"] = os.pathsep.join([os.path.join(base, "Scripts"), os.environ.get("PATH", "")])
    else:
        os.environ["PATH"] = os.pathsep.join([os.path.join(base, "bin"), os.environ.get("PATH", "")])

    # Set the VIRTUAL_ENV environment variable
    os.environ["VIRTUAL_ENV"] = base

    # Add the venv's site-packages directory to sys.path
    prev_length = len(sys.path)
    # If Windows, add Lib\site-packages to sys.path, otherwise add lib/pythonX.X/site-packages
    if sys.platform == "win32":
        site.addsitedir(os.path.join(base, "Lib", "site-packages"))
    else:
        lib_folders = ["lib/python{}".format(sys.version[:3]), "lib/python{}-packages".format(sys.version[:3])]
        for lib in lib_folders:
            path = os.path.join(base, lib)
            site.addsitedir(path)
    sys.path[:] = sys.path[prev_length:] + sys.path[0:prev_length]

    # Set the sys.real_prefix and sys.prefix variables
    sys.real_prefix = sys.prefix
    sys.prefix = base

    import uvicorn

    freeze_support()
    uvicorn.run("app.main:app", port=listen_port, reload=True, access_log=False, host="0.0.0.0")
