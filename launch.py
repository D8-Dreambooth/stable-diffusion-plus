import json
import logging
import os
import platform
import re
import shutil
import site
import subprocess
import sys

from venv import EnvBuilder

logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s', level=logging.DEBUG)
logger = logging.getLogger("launch")
# Set up logging
to_skip = ["urllib3", "PIL", "accelerate", "matplotlib", "h5py", "xformers", "tensorflow", "passlib", "asyncio",
           "tensorboard"]
for skip in to_skip:
    logging.getLogger(skip).setLevel(logging.WARNING)


def create_venv(venv_dir):
    """
    Creates a virtual environment at the given path.
    """
    logger.info(f"Creating virtual environment at {venv_dir}")
    builder = EnvBuilder(with_pip=True)
    builder.create(venv_dir)


def activate_venv(venv_dir):
    bin_dir = os.path.join(venv_dir, 'bin')
    if sys.platform == 'win32':
        bin_dir = os.path.join(venv_dir, 'Scripts')

    # add virtualenv bin to PATH
    os.environ['PATH'] = bin_dir + os.pathsep + os.environ['PATH']

    # point Python-related paths to the virtualenv
    base = os.path.abspath(venv_dir)
    site_packages = os.path.join(base, 'lib', 'python' + sys.version[:3], 'site-packages')
    prev_sys_path = list(sys.path)
    sys.real_prefix = sys.prefix
    sys.prefix = base
    # add the site-packages of the virtualenv
    site.addsitedir(site_packages)
    # add the virtualenv's libraries to sys.path
    sys.path.insert(0, base)

    # remove standard Python paths
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path


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


def install_requirements(venv_path, requirements_path):
    """
    Installs the requirements specified in the given requirements file into the virtual environment at the given path.
    """
    logger.info(f"Installing requirements from {requirements_path} into virtual environment at {venv_path}")
    pip_exe = os.path.join(venv_path, "Scripts", "pip.exe") if sys.platform == "win32" else os.path.join(venv_path,
                                                                                                         "bin", "pip")
    subprocess.run([pip_exe, "install", "-r", requirements_path], check=False)


def get_latest_git_tag(git_path, repo_path):
    """
    Returns the latest git tag in the repository.
    """
    output = subprocess.check_output([git_path, "describe", "--tags"], cwd=repo_path)
    return output.strip().decode()


def get_wheel_version(wheel_file):
    """
    Returns the version number from the wheel filename.
    """
    match = re.search(r'-([\d.]+)-', wheel_file)
    if match:
        return match.group(1)


def check_dreambooth(git_path, dreambooth_path):
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


# Placeholder functionality
def install_extensions():
    pass


def run_server(debug, port):
    server = None
    try:
        import uvicorn
        config = uvicorn.Config("app.main:app", reload=debug, host="0.0.0.0", port=port, access_log=False)
        server = uvicorn.Server(config=config)
        server.run()
    except KeyboardInterrupt:
        if server is not None:
            server.shutdown()
        pass  # Handle KeyboardInterrupt in main part of your scr


if __name__ == "__main__":
    # Check that we're on Python 3.10
    if sys.version_info < (3, 10):
        logger.error("Please upgrade your python version to 3.10 or higher.")
        sys.exit()

    sys.path.append(os.getcwd())

    # Make safetensors faster
    os.environ["SAFETENSORS_FAST_GPU"] = "1"

    if os.name == "posix":
        # For now disable Torch2 Dynamo on Linux
        os.environ["TORCHDYNAMO_DISABLE"] = "1"

    # Set base path
    base_path = os.path.abspath(os.path.dirname(__file__))
    launch_settings_path = os.path.join(base_path, "launch_settings.json")
    conf_src = os.path.join(base_path, "conf_src")

    if not os.path.exists(launch_settings_path):
        shutil.copy(os.path.join(conf_src, "launch_settings.json"), launch_settings_path)

    with open(os.path.join(conf_src, "launch_settings.json"), "r") as ls_base:
        launch_settings_base = json.load(ls_base)
    # Load launch settings
    with open(launch_settings_path, "r") as ls:
        launch_settings = json.load(ls)

    for key, value in launch_settings_base.items():
        if key not in launch_settings:
            launch_settings[key] = value

    to_remove = []
    for key, value in launch_settings.items():
        if key not in launch_settings_base:
            to_remove.append(key)

    if len(to_remove) > 0:
        logger.warning(f"Found {len(to_remove)} invalid launch settings, removing them.")
        for key in to_remove:
            del launch_settings[key]
        with open(launch_settings_path, "w") as ls:
            json.dump(launch_settings, ls, indent=4)

    debug = launch_settings.get("debug", False)
    logging.basicConfig(format='[%(asctime)s][%(levelname)s][%(name)s] - %(message)s',
                        level=logging.INFO if not debug else logging.DEBUG)
    logger = logging.getLogger("launch")
    # Set up logging
    to_skip = ["urllib3", "PIL", "accelerate", "matplotlib", "h5py", "xformers", "tensorflow", "passlib", "asyncio",
               "tensorboard"]
    for skip in to_skip:
        logging.getLogger(skip).setLevel(logging.WARNING)
    # Set port
    port = 8080
    if "listen_port" in launch_settings:
        port = int(launch_settings["listen_port"])
    if os.environ.get("PORT", None):
        port = int(os.environ.get("PORT"))

    # Set our venv

    venv_dir = os.path.join(base_path, "venv")

    if "venv" in launch_settings:
        user_venv = launch_settings["venv"]
        if user_venv:
            venv_dir = user_venv

    if os.name == 'nt':
        # For Windows
        python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        # For Unix or Linux
        python = os.path.join(venv_dir, "bin", "python")

    if not os.path.isdir(venv_dir) or not os.path.exists(python):
        create_venv(venv_dir)

    # Check if running in venv, and if not, relaunch with the proper python
    if sys.executable != python:
        logger.debug("Relaunching with proper python executable")
        os.execl(python, '"' + python + '"', *sys.argv)

    # Activate the virtual environment
    activate_venv(venv_dir)

    # Install extensions first
    install_extensions()

    sys.path.append(venv_dir)

    # Define the dreambooth repository path
    dreambooth_path = os.path.join(base_path, "core", "modules", "dreambooth")

    # Add the dreambooth dir to sys path
    module_dir = os.path.abspath(dreambooth_path)
    sys.path.insert(0, module_dir)

    # Define the dreambooth repository path
    dreambooth_path = os.path.join(base_path, "core", "modules", "dreambooth")

    # Create a new environment for the subprocess to run in
    env = os.environ.copy()
    env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + env["PATH"]
    env["VIRTUAL_ENV"] = venv_dir
    env["PYTHONPATH"] = os.pathsep.join([dreambooth_path, os.path.dirname(os.path.abspath(__file__))])

    git_path = find_git()

    if git_path:
        try:
            check_dreambooth(git_path, dreambooth_path)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Unable to update/fetch dreambooth repository: {e}")
    else:
        if not os.path.exists(dreambooth_path):
            logger.warning("Unable to find git, and dreambooth is not installed. Training will not be available.")

    # Install the requirements
    requirements = os.path.join(base_path, "requirements.txt")
    install_requirements(venv_dir, requirements)

    # in the main part of your script
    try:
        run_server(debug, port)
    except KeyboardInterrupt:
        print("Server stopped")
