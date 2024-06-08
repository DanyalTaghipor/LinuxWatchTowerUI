import os
import sys
import subprocess
import shutil
import json  # Ensure json is imported
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible import context
from ansible.module_utils.common.collections import ImmutableDict
from ansible.plugins.callback import CallbackBase
import ansible.constants as C

# Create a callback plugin to capture output
class ResultsCollectorJSONCallback(CallbackBase):
    def __init__(self, *args, **kwargs):
        super(ResultsCollectorJSONCallback, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}

    def v2_runner_on_unreachable(self, result):
        host = result._host
        self.host_unreachable[host.get_name()] = result

    def v2_runner_on_ok(self, result, *args, **kwargs):
        host = result._host
        self.host_ok[host.get_name()] = result
        print(json.dumps({host.name: result._result}, indent=4))

    def v2_runner_on_failed(self, result, *args, **kwargs):
        host = result._host
        self.host_failed[host.get_name()] = result


def list_directory_contents(directory):
    try:
        result = subprocess.run(['ls', '-l', directory], capture_output=True, text=True)
        print(f"Contents of {directory}:")
        print(result.stdout)
    except Exception as e:
        print(f"An error occurred while listing the directory contents: {e}")


def setup_and_run_playbook(nickname, play_source):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[nickname + ','])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # Determine the base path
    if getattr(sys, 'frozen', False):
        # If the application is frozen, use sys._MEIPASS
        base_path = sys._MEIPASS
    else:
        # If not frozen, use the current directory
        base_path = os.path.abspath(".")

    # List the contents of the base directory
    list_directory_contents(base_path)
    
    # List the contents of ansible_utils directory
    ansible_utils_path = os.path.join(base_path, 'ansible_utils')
    list_directory_contents(ansible_utils_path)
    
    # List the contents of roles directory within ansible_utils
    roles_path = os.path.join(ansible_utils_path, 'roles')
    list_directory_contents(roles_path)

    context.CLIARGS = ImmutableDict(module_path=['/to/mymodules', '/usr/share/ansible'],
                                    roles_path=roles_path,
                                    forks=10, become=None,
                                    become_method=None, become_user=None, check=False, diff=False, verbosity=0)
    results_callback = ResultsCollectorJSONCallback()

    # Initialize the TaskQueueManager before calling Play.load()
    tqm = TaskQueueManager(
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        passwords=dict(),
        stdout_callback=results_callback,
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    try:
        result = tqm.run(play)
        return result
    finally:
        tqm.cleanup()
        if loader:
            loader.cleanup_all_tmp_files()
        # Remove ansible tmpdir
        shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

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
