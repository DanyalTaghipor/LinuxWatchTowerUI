import os
import shutil
import ansible_runner
import sys
import tempfile
import logging

def setup_runner_environment(nicknames, play_source):
    base_path = tempfile.mkdtemp(prefix="ansible_runner_")
    project_path = os.path.join(base_path, 'project')
    roles_path = os.path.join(project_path, 'roles')
    inventory_path = os.path.join(base_path, 'inventories')

    os.makedirs(project_path, exist_ok=True)
    os.makedirs(roles_path, exist_ok=True)
    os.makedirs(inventory_path, exist_ok=True)

    playbook_path = os.path.join(project_path, 'playbook.yml')
    with open(playbook_path, 'w') as playbook_file:
        playbook_file.write(play_source)

    roles_src_path = os.path.join(sys._MEIPASS, 'ansible_utils', 'roles')
    if os.path.exists(roles_src_path):
        shutil.copytree(roles_src_path, roles_path, dirs_exist_ok=True)
    else:
        logging.warning(f"Roles directory does not exist at {roles_src_path}")

    hosts_path = os.path.join(inventory_path, 'hosts')
    if nicknames:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('[all]\n' + '\n'.join(nicknames))
    else:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('[all]\nlocalhost')

    logging.debug("Contents of inventory file:")
    with open(hosts_path, 'r') as file:
        logging.debug(file.read())

    return base_path, 'playbook.yml', inventory_path

def install_tool(nicknames, role_name, sudo_password=None):
    play_source = f"""
---
- name: Install and configure {role_name}
  hosts: all
  become: true  # Ensure tasks run with elevated privileges
  roles:
    - {role_name}
    """
    logging.debug(f"Generated Playbook:\n{play_source}")
    base_path, playbook_name, inventory_path = setup_runner_environment(nicknames, play_source)
    logging.debug(f"Running Ansible Runner with playbook at {os.path.join(base_path, playbook_name)}")

    envvars = {
        'ANSIBLE_STDOUT_CALLBACK': 'default',
        'ANSIBLE_LOAD_CALLBACK_PLUGINS': 'True',
    }

    if sudo_password:
        logging.debug(f"Sudo password provided for installation on hosts: {nicknames}")
        envvars['ANSIBLE_BECOME_PASSWORD'] = sudo_password
        logging.debug(f"Environment Variables: {envvars}")
    else:
        logging.debug("No sudo password provided.")

    r = ansible_runner.run(private_data_dir=base_path, playbook=playbook_name, inventory=inventory_path, envvars=envvars, verbosity=3)
    logging.debug(f"Ansible Runner finished with status: {r.status}")
    return r
