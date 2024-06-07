import os
import sys
import shutil
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

def setup_and_run_playbook(nickname, play_source):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[nickname + ','])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # Determine the module path dynamically
    if getattr(sys, 'frozen', False):
        # If running in a PyInstaller bundle
        module_path = os.path.join(sys._MEIPASS, 'roles')
    else:
        # If running in a normal Python environment
        module_path = os.path.join(os.path.dirname(__file__), '..', 'roles')

    print(f'Module Path => {module_path}')
    context.CLIARGS = ImmutableDict(
        connection='ssh',
        module_path=['/to/mymodules', '/usr/share/ansible'],
        forks=10,
        become=None,
        become_method=None,
        become_user=None,
        check=False,
        diff=False,
        remote_user=None,
        verbosity=3,
        roles_path='/nowhere'
    )

    os.environ['ANSIBLE_ROLES_PATH'] = '/path/to/your/roles'

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
