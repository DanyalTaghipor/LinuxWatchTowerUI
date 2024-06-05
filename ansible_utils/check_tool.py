from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.utils.display import Display
from ansible import context
from ansible.plugins.callback import CallbackBase

class ResultCallback(CallbackBase):
    def __init__(self):
        super().__init__()
        self.results = {}

    def v2_runner_on_ok(self, result):
        self.results[result._host.get_name()] = result._result

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.results[result._host.get_name()] = result._result

def check_tool_remote(nickname, tool_name):
    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=[nickname + ','])
    variable_manager = VariableManager(loader=loader, inventory=inventory)

    # Suppress Ansible logs
    display = Display(verbosity=0)
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
        verbosity=0
    )

    play_source = dict(
        name="Check Tool",
        hosts=nickname,
        gather_facts='no',
        tasks=[
            dict(
                name=f"Check if {tool_name.lower()} is installed",
                action=dict(module='command', args=dict(cmd=f'which {tool_name.lower()}')),
                register='tool_check',
                failed_when="tool_check.rc != 0",
                ignore_errors=True
            ),
            dict(
                name=f"Get {tool_name.lower()} version",
                action=dict(module='command', args=dict(cmd=f'{tool_name.lower()} --version')),
                register='tool_version',
                when="tool_check.rc == 0",
                failed_when="tool_version.rc != 0",
                ignore_errors=True
            )
        ]
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
    callback = ResultCallback()

    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            passwords=dict(),
            stdout_callback=callback,
        )
        tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()

    host_result = callback.results.get(nickname)
    if host_result:
        installed = host_result.get('tool_check', {}).get('rc') == 0
        version = host_result.get('tool_version', {}).get('stdout', 'N/A') if installed else 'N/A'
        return installed, version

    return False, "N/A"
