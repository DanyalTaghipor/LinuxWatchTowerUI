import os, sys
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible import context
from ansible.module_utils.common.collections import ImmutableDict

def setup_and_run_playbook(nickname, play_source):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[nickname + ','])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # Determine the roles path dynamically
    if getattr(sys, 'frozen', False):
        # If running in a PyInstaller bundle
        roles_path = os.path.join(sys._MEIPASS, 'roles')
    else:
        # If running in a normal Python environment
        roles_path = os.path.join(os.path.dirname(__file__), '..', 'roles')

    print(f'Roles Path => {roles_path}')
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
        verbosity=3,
        roles_path=roles_path  # Set roles path here
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
        return result
    finally:
        if tqm is not None:
            tqm.cleanup()

def install_tool(nicknames, role_name, version):
    hosts_str = ','.join(nicknames)
    play_source = dict(
        name=f"Install {role_name}",
        hosts=hosts_str,
        gather_facts='no',
        tasks=[
            dict(name=f"Install {role_name}", import_role=dict(name=role_name))
        ]
    )
    return setup_and_run_playbook(hosts_str, play_source)
