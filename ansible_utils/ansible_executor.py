import os
import shutil
import ansible_runner
import sys
import tempfile
import logging

def setup_runner_environment(host, play_source, custom_roles_path=None):
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

    if custom_roles_path and os.path.exists(custom_roles_path):
        shutil.copytree(custom_roles_path, roles_path, dirs_exist_ok=True)
    else:
        if custom_roles_path:
            logging.warning(f"Custom roles directory does not exist at {custom_roles_path}")

    hosts_path = os.path.join(inventory_path, 'hosts')
    if host:
        with open(hosts_path, 'w') as hosts_file:
            if isinstance(host, str):
                hosts_file.write('[all]\n' + host)
            else:
                hosts_file.write('[all]\n' + '\n'.join(host))
    else:
        with open(hosts_path, 'w') as hosts_file:
            hosts_file.write('[all]\nlocalhost')

    logging.debug("Contents of inventory file:")
    with open(hosts_path, 'r') as file:
        logging.debug(file.read())

    return base_path, 'playbook.yml', inventory_path

def install_tool(host, role_name, sudo_password=None, custom_roles_path=None):
    play_source = f"""
---
- name: Install and configure {role_name}
  hosts: all
  become: true
  roles:
    - {role_name}
  vars:
    ansible_become_password: "{{{{ lookup('env', 'ANSIBLE_BECOME_PASSWORD') }}}}"
    """
    logging.debug(f"Generated Playbook For {host}:\n{play_source}")
    base_path, playbook_name, inventory_path = setup_runner_environment(host, play_source, custom_roles_path)
    logging.debug(f"Running Ansible Runner with playbook at {os.path.join(base_path, playbook_name)}")

    envvars = {
        'ANSIBLE_STDOUT_CALLBACK': 'default',
        'ANSIBLE_LOAD_CALLBACK_PLUGINS': 'True',
    }

    if sudo_password:
        os.environ['ANSIBLE_BECOME_PASSWORD'] = sudo_password
        logging.debug(f"Environment Variables: {envvars}")
    else:
        logging.debug("No sudo password provided.")

    r = ansible_runner.run(private_data_dir=base_path, playbook=playbook_name, inventory=inventory_path, envvars=envvars, verbosity=3)
    logging.debug(f"Ansible Runner finished with status: {r.status}")
    
    # Finding the log file in the artifacts directory
    log_dir = os.path.join(base_path, 'artifacts')
    logs = "No log file found."

    if os.path.exists(log_dir):
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file == 'stdout':
                    log_file = os.path.join(root, file)
                    with open(log_file, 'r') as f:
                        logs = f.read()
                        break

    return r.status, logs
