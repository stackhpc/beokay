======
Beokay
======

An environment management tool for `Kayobe
<https://github.com/openstack/kayobe>`_.

A Kayobe operator's environment is comprised of a few parts:

* A set of `Kayobe configuration
  <https://github.com/openstack/kayobe-config>`_, typically version controlled
* An optional Kayobe git repository checkout, installed into a Python virtual
  environment. Alternatively Kayobe may be installed using a
  ``requirements.txt`` file in the Kayobe configuration.
* A set of Ansible role dependencies, installed from `Ansible Galaxy
  <https://galaxy.ansible.com>`_
* `Kolla Ansible <https://docs.openstack.org/kolla-ansible/latest/>`_,
  installed into a Python virtual environment

It's easy for these dependencies to get out of sync, and can lead to not
applying the correct configuration to a system.

Beokay provides a simple Python script that can be used to manage Kayobe
environments.  The hope is that this will encourage making these environments
more disposable, leading to more reliable, repeatable operations.

Usage
=====

Beokay has no dependencies outside of the Python standard library.  The
``beokay.py`` script supports three subcommands:

create
    Create a Kayobe environment
destroy
    Destroy a Kayobe environment
run
    Run a command in a Kayobe environment

The command provides help at the global level (``beokay.py -h``), and for each
subcommand (``beokay.py <command> -h``).
