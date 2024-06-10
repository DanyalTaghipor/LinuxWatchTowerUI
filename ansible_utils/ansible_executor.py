import os
import shutil
import ansible_runner
import sys
import tempfile

def setup_runner_environment(nicknames, role_name, play_source):
    # Create a temporary directory
    base_path = tempfile.mkdtemp(prefix="ansible_runner_")
    project_path = os.path.join(base_path, 'project')
    roles_path = os.path.join(base_path, 'roles')
    inventory_path = os.path.join(base_path, 'inventories')

    # Ensure directories exist
    os.makedirs(project_path, exist_ok=True)
    os.makedirs(roles_path, exist_ok=True)
    os.makedirs(inventory_path, exist_ok=True)

    # Write the playbook
    playbook_path = os.path.join(project_path, 'playbook.yml')
    with open(playbook_path, 'w') as playbook_file:
        playbook_file.write(play_source)

    # Copy roles to roles_path
    roles_src_path = os.path.join(sys._MEIPASS, 'ansible_utils', 'roles')  # Use sys._MEIPASS to reference the bundled directory
    if os.path.exists(roles_src_path):
        shutil.copytree(roles_src_path, roles_path, dirs_exist_ok=True)
    else:
        print(f"Roles directory does not exist at {roles_src_path}")

    # Write the inventory
    hosts_path = os.path.join(inventory_path, 'hosts')
    if nicknames:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('\n'.join(nicknames))
    else:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('localhost')

    return base_path, 'playbook.yml'


def install_tool(nicknames, role_name, version):
    play_source = """
    ---
    - name: Simple Playbook
      hosts: all
      tasks:
        - name: Ping
          ping:
    """
    print(f"Generated Playbook:\n{play_source}")  # Print playbook for debugging
    base_path, playbook_name = setup_runner_environment(nicknames, role_name, play_source)
    r = ansible_runner.run(private_data_dir=base_path, playbook=playbook_name)
    return r
