import os
import shutil
import ansible_runner

def setup_runner_environment(nicknames, role_name, play_source):
    # Define paths
    base_path = os.path.join(os.getcwd(), 'temp', 'runner_env')
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
    roles_src_path = os.path.join(os.getcwd(), 'ansible_utils', 'roles')
    if os.path.exists(roles_src_path):
        shutil.copytree(roles_src_path, roles_path, dirs_exist_ok=True)
    else:
        print(f"Roles directory does not exist at {roles_src_path}")

    # Write the inventory
    hosts_path = os.path.join(inventory_path, 'hosts')
    with open(hosts_path, 'w') as hosts_file:
        hosts_file.write('\n'.join(nicknames))

    return base_path, 'playbook.yml'

def install_tool(nicknames, role_name, version):
    play_source = f"""
    ---
    - name: Install {role_name}
      hosts: all
      gather_facts: no
      tasks:
        - name: Install {role_name}
          import_role:
            name: {role_name}
    """
    base_path, playbook_name = setup_runner_environment(nicknames, role_name, play_source)
    r = ansible_runner.run(private_data_dir=base_path, playbook=playbook_name)
    return r
