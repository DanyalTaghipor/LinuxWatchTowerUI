import os
import shutil
import ansible_runner
import sys
import tempfile

def setup_runner_environment(nicknames, play_source):
    # Create a temporary directory
    base_path = tempfile.mkdtemp(prefix="ansible_runner_")
    project_path = os.path.join(base_path, 'project')
    roles_path = os.path.join(project_path, 'roles')
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
            hosts_file.write('[all]\n' + '\n'.join(nicknames))
    else:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('[all]\nlocalhost')

    return base_path, 'project/playbook.yml'

def install_tool(nicknames, role_name):
    play_source = f"""
---
- name: Install and configure {role_name}
  hosts: all
  roles:
    - {role_name}
    """
    print(f"Generated Playbook:\n{play_source}")  # Print playbook for debugging
    base_path, playbook_name = setup_runner_environment(nicknames, play_source)
    print(f"Running Ansible Runner with playbook at {os.path.join(base_path, playbook_name)}")  # Debug print statement

    envvars = {
        'ANSIBLE_STDOUT_CALLBACK': 'default',  # Avoid using awx_display callback
        'ANSIBLE_LOAD_CALLBACK_PLUGINS': 'True',  # Ensure callback plugins are loaded
    }

    r = ansible_runner.run(private_data_dir=base_path, playbook=playbook_name, envvars=envvars)
    return r
