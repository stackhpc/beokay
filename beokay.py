#!/usr/bin/env python

"""
It'll all beokay.

Manage Kayobe configuration environments.
"""

import argparse
import os
import os.path
import shutil
import subprocess


def parse_args():
    description = "Manage Kayobe deployment environments"
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers(help="Actions", dest="action")
    create_parser = subparsers.add_parser("create",
                                          help="Create a Kayobe environment")
    create_parser.add_argument("--base-path", default=os.getcwd(),
                               help="Path to base of Kayobe environment")
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
    parsed_args = parser.parse_args()
    return parsed_args


def get_path(parsed_args, *args):
    """Return an absolute path, given a path relative to the base."""
    base_path = os.path.abspath(parsed_args.base_path)
    return os.path.join(base_path, *args)


def ensure_paths(parsed_args):
    mode = 0700
    base_path = get_path(parsed_args)
    if not os.path.exists(base_path):
        os.makedirs(base_path, mode)
    paths = {"src", "venvs"}
    for path in paths:
        path = get_path(parsed_args, path)
        if not os.path.exists(path):
            os.mkdir(path, mode)


def git_clone(repo, branch, path):
    subprocess.check_call(["git", "clone", repo, path, "--branch", branch])


def clone_kayobe_config(parsed_args):
    path = get_path(parsed_args, "src", "kayobe-config")
    git_clone(parsed_args.kayobe_config_repo, parsed_args.kayobe_config_branch,
              path)


def clone_kayobe(parsed_args):
    path = get_path(parsed_args, "src", "kayobe")
    git_clone(parsed_args.kayobe_repo, parsed_args.kayobe_branch, path)


def create_venv(parsed_args):
    venv_path = get_path(parsed_args, "venvs", "kayobe")
    subprocess.check_call(["virtualenv", venv_path])
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.check_call([pip_path, "install", "--upgrade", "pip"])
    kayobe_path = get_path(parsed_args, "src", "kayobe")
    subprocess.check_call([pip_path, "install", kayobe_path])


def activate_venv_cmd(parsed_args):
    activate_path = get_path(parsed_args, "venvs", "kayobe", "bin", "activate")
    return ["source", activate_path]


def run_kayobe(parsed_args, kayobe_cmd):
    cmd = activate_venv_cmd(parsed_args)
    kayobe_config_path = get_path(parsed_args, "src", "kayobe-config")
    if os.path.exists(kayobe_config_path):
        env_path = os.path.join(kayobe_config_path,
                                parsed_args.kayobe_config_env)
        cmd += ["&&", "source", env_path]
    cmd += ["&&"]
    cmd += kayobe_cmd
    kayobe_path = get_path(parsed_args, "src", "kayobe")
    subprocess.check_call(" ".join(cmd), shell=True, cwd=kayobe_path,
                          executable="/bin/bash")


def control_host_bootstrap(parsed_args):
    cmd = ["kayobe", "control", "host", "bootstrap"]
    run_kayobe(parsed_args, cmd)


def create(parsed_args):
    ensure_paths(parsed_args)
    clone_kayobe_config(parsed_args)
    clone_kayobe(parsed_args)
    create_venv(parsed_args)
    control_host_bootstrap(parsed_args)


def destroy(parsed_args):
    base_path = get_path(parsed_args)
    if os.path.exists(base_path):
        shutil.rmtree(base_path)


def run(parsed_args):
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
