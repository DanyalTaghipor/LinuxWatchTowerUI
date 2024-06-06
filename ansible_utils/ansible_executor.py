import subprocess
import os
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.playbook.play import Play
from ansible.module_utils.common.collections import ImmutableDict
from ansible import context

def install_ansible_role(role_name):
    """Install an Ansible role using ansible-galaxy"""
    command = ["ansible-galaxy", "install", role_name]
    subprocess.run(command, check=True)

def setup_and_run_playbook(hosts_str, play_source):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[hosts_str])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    context.CLIARGS = ImmutableDict(
        connection='ssh',
        module_path=None,
        forks=10,
        become=None,
        become_method=None,
        become_user=None,
        check=False,
        diff=False,
        remote_user=None,
        verbosity=3
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            passwords=dict(),
        )
        result = tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()
    return result

def install_tool(hosts, role_name, version):
    hosts_str = ','.join(hosts) + ','  # Required format for Ansible
    play_source = {
        'name': 'Install tool',
        'hosts': 'all',
        'roles': [
            {'role': role_name}
        ]
    }

    # Install the required role locally
    install_ansible_role(role_name)

    return setup_and_run_playbook(hosts_str, play_source)
