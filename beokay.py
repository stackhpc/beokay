#!/usr/bin/env python3

"""
It'll all beokay.

Manage Kayobe configuration environments.
"""

import argparse
try:
    from argparse import BooleanOptionalAction
except ImportError:
    # Introduced in Python 3.9.
    BooleanOptionalAction = "store_true"
import os
import os.path
import shutil
import subprocess
import sys


def parse_args():
    description = "Manage Kayobe deployment environments"
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers(help="Actions", dest="action")
    create_parser = subparsers.add_parser("create",
                                          help="Create a Kayobe environment")
    create_parser.add_argument("--base-path", default=os.getcwd(),
                               help="Path to base of Kayobe environment")
    create_parser.add_argument("--git-ssh-key", default=None,
                               help="Path to an SSH key to use for Git pulls")
    create_parser.add_argument("--kayobe-in-requirements", default=False,
                               action=BooleanOptionalAction,
                               help="Install Kayobe using requirements.txt in "
                                    "kayobe configuration")
    create_parser.add_argument("--no-bootstrap", action='store_true',
                               help="Don't run kayobe control host bootstrap")
    create_parser.add_argument("--kayobe-repo",
                               default="https://github.com/openstack/kayobe",
                               help="Kayobe repository")
    create_parser.add_argument("--kayobe-branch", default="master",
                               help="Kayobe branch")
    create_parser.add_argument("--kayobe-config-repo", required=True,
                               help="Kayobe configuration repository")
    create_parser.add_argument("--kayobe-config-branch", default="master",
                               help="Kayobe configuration branch")
    create_parser.add_argument("--kayobe-config-env", default="kayobe-env",
                               help="Kayobe configuration environment file to "
                                    "source")
    create_parser.add_argument("--kayobe-config-env-name", default=None,
                               help="Kayobe configuration environment name to "
                                    "use")
    create_parser.add_argument("--python", default="python3", help="Python "
                               "executable to use to create the Kayobe "
                               "virtual environment")
    create_parser.add_argument("--vault-password-file", help="Path to an "
                               "Ansible Vault password file used to encrypt "
                               "secrets")
    destroy_parser = subparsers.add_parser("destroy",
                                           help="Destroy a Kayobe environment")
    destroy_parser.add_argument("--base-path", default=os.getcwd(),
                                help="Path to base of Kayobe environment")
    run_parser = subparsers.add_parser("run",
                                       help="Run a Kayobe command")
    run_parser.add_argument("command", nargs="+")
    run_parser.add_argument("--base-path", default=os.getcwd(),
                            help="Path to base of Kayobe environment")
    run_parser.add_argument("--kayobe-config-env", default="kayobe-env",
                            help="Kayobe configuration environment file to "
                                 "source")
    run_parser.add_argument("--kayobe-config-env-name", default=None,
                            help="Kayobe configuration environment name to "
                                 "use")
    run_parser.add_argument("--vault-password-file", help="Path to an Ansible "
                            "Vault password file used to encrypt secrets")
    parsed_args = parser.parse_args()

    if parsed_args.action == None:
        parser.print_help()
        sys.exit(1)

    return parsed_args


def get_path(parsed_args, *args):
    """Return an absolute path, given a path relative to the base."""
    base_path = os.path.abspath(parsed_args.base_path)
    return os.path.join(base_path, *args)


def get_env_name(parsed_args):
    """Return the kayobe environment to use, if specified"""
    return (f" --environment {parsed_args.kayobe_config_env_name}"
            if parsed_args.kayobe_config_env_name else "")


def ensure_paths(parsed_args):
    mode = 0o700
    base_path = get_path(parsed_args)
    if os.path.exists(base_path):
        overwrite = input(f"'{base_path}' already exists. Do you want to overwrite it? [Y/N]: ")
        if overwrite.lower() not in ['y', 'yes']:
            print("Exiting due to existing directory.")
            sys.exit(0)
        shutil.rmtree(base_path)
    os.makedirs(base_path, mode)
    paths = {"src", "venvs"}
    for path in paths:
        path = get_path(parsed_args, path)
        if not os.path.exists(path):
            os.mkdir(path, mode)


def set_vault_password(parsed_args):
    if parsed_args.vault_password_file:
        with open(parsed_args.vault_password_file) as f:
            os.environ["KAYOBE_VAULT_PASSWORD"] = f.read()


def git_clone(repo, branch, path, ssh_key):
    if ssh_key:
        os.environ["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key}"
    subprocess.check_call(["git", "clone", repo, path, "--branch", branch])


def clone_kayobe_config(parsed_args):
    path = get_path(parsed_args, "src", "kayobe-config")
    git_clone(parsed_args.kayobe_config_repo, parsed_args.kayobe_config_branch,
              path, parsed_args.git_ssh_key)


def clone_kayobe(parsed_args):
    path = get_path(parsed_args, "src", "kayobe")
    git_clone(parsed_args.kayobe_repo, parsed_args.kayobe_branch, path, parsed_args.git_ssh_key)


def create_venv(parsed_args):
    python = parsed_args.python
    venv_path = get_path(parsed_args, "venvs", "kayobe")
    subprocess.check_call([python, "-m", "venv", venv_path, "--prompt", r"kayobe in ${KAYOBE_ENVIRONMENT:-base}"])
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.check_call([pip_path, "install", "--upgrade", "pip"])
    subprocess.check_call([pip_path, "install", "--upgrade", "setuptools"])
    if parsed_args.kayobe_in_requirements:
        requirements_path = get_path(parsed_args, "src", "kayobe-config",
                                     "requirements.txt")
        subprocess.check_call([pip_path, "install", "-r", requirements_path])
    else:
        kayobe_path = get_path(parsed_args, "src", "kayobe")
        subprocess.check_call([pip_path, "install", kayobe_path])


def activate_venv_cmd(parsed_args):
    activate_path = get_path(parsed_args, "venvs", "kayobe", "bin", "activate")
    return ["source", activate_path]


def run_kayobe(parsed_args, kayobe_cmd):
    cmd = activate_venv_cmd(parsed_args)
    env_name = get_env_name(parsed_args)
    kayobe_config_path = get_path(parsed_args, "src", "kayobe-config")
    if os.path.exists(kayobe_config_path):
        env_path = os.path.join(kayobe_config_path,
                                parsed_args.kayobe_config_env)
        cmd += ["&&", "source", f"{env_path}{env_name}"]
    cmd += ["&&"]
    cmd += kayobe_cmd
    subprocess.check_call(" ".join(cmd), shell=True, cwd=kayobe_config_path,
                          executable="/bin/bash")


def control_host_bootstrap(parsed_args):
    cmd = ["kayobe", "control", "host", "bootstrap"]
    run_kayobe(parsed_args, cmd)


def create_env_vars_script(parsed_args):
    """Creates an env-vars script for the kayobe environment."""
    env_vars_file = os.path.join(get_path(parsed_args), 'env-vars.sh')
    env_name = get_env_name(parsed_args)
    vault_password = (f"export KAYOBE_VAULT_PASSWORD=$(cat {parsed_args.vault_password_file})"
                      if parsed_args.vault_password_file else "")

    # Construct the content for the script
    content = f"""#!/bin/bash
{vault_password}
source {get_path(parsed_args, 'venvs', 'kayobe', 'bin', 'activate')}
source {get_path(parsed_args, 'src', 'kayobe-config', 'kayobe-env')}{env_name}
source <(kayobe complete)
cd {get_path(parsed_args, 'src', 'kayobe-config', 'etc', 'kayobe/')}
    """

    # Write the script
    with open(env_vars_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Make the env-vars script executable
    os.chmod(env_vars_file, 0o755)

    print(f"env-vars script created at {env_vars_file}")


def create(parsed_args):
    ensure_paths(parsed_args)
    clone_kayobe_config(parsed_args)
    if not parsed_args.kayobe_in_requirements:
        clone_kayobe(parsed_args)
    create_venv(parsed_args)
    set_vault_password(parsed_args)
    create_env_vars_script(parsed_args)
    if not parsed_args.no_bootstrap:
        control_host_bootstrap(parsed_args)


def destroy(parsed_args):
    base_path = get_path(parsed_args)
    if os.path.exists(base_path):
        shutil.rmtree(base_path)


def run(parsed_args):
    set_vault_password(parsed_args)
    run_kayobe(parsed_args, parsed_args.command)


def main():
    parsed_args = parse_args()
    if parsed_args.action == "create":
        create(parsed_args)
    elif parsed_args.action == "destroy":
        destroy(parsed_args)
    elif parsed_args.action == "run":
        run(parsed_args)
    else:
        raise Exception("Unknown command")


if __name__ == "__main__":
    main()
