import os
from rich.console import Console
from rich.table import Table
from ansible_utils.ansible_executor import install_tool
from ansible_utils.check_tool import check_tool_remote
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from db.database import log_installation, check_installation, update_installation

console = Console()

def install_ansible_role(role_name, version='latest'):
    import subprocess
    if version == 'latest':
        cmd = f"ansible-galaxy role install {role_name}"
    else:
        cmd = f"ansible-galaxy role install {role_name},{version}"
    result = subprocess.run(cmd, shell=True, check=True)
    return result.returncode == 0


def interactive_install():
    default_config_path = os.path.expanduser("~/.ssh/config")
    config_path = input(f"Enter the path to your config file (default is {default_config_path}): ") or default_config_path

    host_nicknames = get_host_nicknames(config_path=config_path)
    if not host_nicknames:
        console.print("No hosts found in the SSH config file.", style="bold red")
        return

    table = Table(title="\nAvailable Hosts")
    table.add_column("Number", justify="right", style="cyan", no_wrap=True)
    table.add_column("Host Nickname", style="magenta")

    for index, nickname in enumerate(host_nicknames, start=1):
        table.add_row(str(index), nickname)

    console.print(table)

    host_index = int(input("Select the host by number: ")) - 1
    if host_index < 0 or host_index >= len(host_nicknames):
        console.print("Invalid selection.", style="bold red")
        return

    nickname = host_nicknames[host_index]
    console.print(f"Selected host: {nickname}", style="bold green")

    tool_table = Table(title="\nAvailable Tools")
    tool_table.add_column("Number", justify="right", style="cyan", no_wrap=True)
    tool_table.add_column("Tool", style="magenta")
    tool_table.add_column("Status", style="yellow")

    tool_list = list(Tools)
    for index, tool in enumerate(tool_list, start=1):
        installed_in_db = check_installation(nickname, tool.name)
        status = "(present)" if installed_in_db else "(absent)"
        tool_table.add_row(str(index), tool.name, status)

    console.print(tool_table)

    tool_index = int(input("Select the tool by number: ")) - 1
    if tool_index < 0 or tool_index >= len(tool_list):
        console.print("Invalid selection.", style="bold red")
        return

    tool = tool_list[tool_index]
    tool_name = tool.name
    console.print(f"Selected tool: {tool_name}", style="bold green")

    console.print(f"\nAvailable versions for {tool_name}: {', '.join(tool.value['versions'])}")
    version = input("Enter the version to install (default is 'latest'): ") or 'latest'

    if version not in tool.value['versions']:
        console.print("Invalid version.", style="bold red")
        return

    if not check_tool_remote(nickname, tool_name):
        console.print(f"Installing {tool_name} version {version}...", style="bold blue")
        if install_ansible_role(tool.value['default'], version):
            log_installation(nickname, tool_name, version)
            console.print(f"Successfully installed {tool_name} version {version}.", style="bold green")
        else:
            console.print(f"Failed to install {tool_name} version {version}.", style="bold red")
    else:
        console.print(f"{tool_name} is already installed on the remote host but not in the DB. Updating the DB.", style="bold yellow")
        log_installation(nickname, tool_name, 'unknown')

    result = install_tool(nickname, tool.value['default'], version)
    if result == 0:
        log_installation(nickname, tool_name, version)

def check_state():
    default_config_path = os.path.expanduser("~/.ssh/config")
    config_path = input(f"Enter the path to your config file (default is {default_config_path}): ") or default_config_path

    host_nicknames = get_host_nicknames(config_path=config_path)
    if not host_nicknames:
        console.print("No hosts found in the SSH config file.", style="bold red")
        return

    table = Table(title="\nAvailable Hosts")
    table.add_column("Number", justify="right", style="cyan", no_wrap=True)
    table.add_column("Host Nickname", style="magenta")

    for index, nickname in enumerate(host_nicknames, start=1):
        table.add_row(str(index), nickname)

    console.print(table)

    host_index = int(input("Select the host by number (or 0 to check all hosts): ")) - 1

    if host_index == -1:
        selected_hosts = host_nicknames
    elif 0 <= host_index < len(host_nicknames):
        selected_hosts = [host_nicknames[host_index]]
    else:
        console.print("Invalid selection.", style="bold red")
        return

    for nickname in selected_hosts:
        console.print(f"\n[bold]Checking state for host:[/bold] {nickname}")
        all_synced = True
        installable_tools = []
        state_table = Table(title=f"\nTool States for {nickname}")
        state_table.add_column("Number", style="cyan")
        state_table.add_column("Tool", style="cyan")
        state_table.add_column("State", style="magenta")

        for index, tool in enumerate(Tools, start=1):
            tool_name = tool.name
            installed_in_db = check_installation(nickname, tool_name)
            installed_on_remote = check_tool_remote(nickname, tool_name)

            if installed_on_remote:
                if not installed_in_db:
                    log_installation(nickname, tool_name, 'unknown')
                    console.print(f"[green]Updated DB:[/green] {tool_name} is now marked as installed for host {nickname} in the DB.")
                state = "present in both DB and remote host"
            else:
                if installed_in_db:
                    update_installation(nickname, tool_name, remove=True)
                    console.print(f"[yellow]Updated DB:[/yellow] {tool_name} is now marked as absent for host {nickname} in the DB.")
                state = "absent"
                all_synced = False
                installable_tools.append(index)

            state_table.add_row(str(index), tool_name, state)

        console.print(state_table)

        if all_synced:
            console.print(f"[green]Everything is synchronized and installed for host {nickname}![/green]")
        else:
            while True:
                install_option = input(f"Do you want to install missing packages on the remote host {nickname}? Type 'all' to install all or enter package numbers separated by commas (e.g., 1,2,3): ").strip().lower()

                if install_option == 'all':
                    for tool in Tools:
                        tool_name = tool.name
                        installed_on_remote = check_tool_remote(nickname, tool_name)
                        if not installed_on_remote:
                            result = install_tool(nickname, tool.value['default'], 'latest')
                            if result == 0:
                                log_installation(nickname, tool_name, 'latest')
                                console.print(f"[green]Successfully installed {tool_name} on the remote host {nickname}.[/green]")
                            else:
                                console.print(f"[red]Failed to install {tool_name} on the remote host {nickname}.[/red]")
                    break
                else:
                    try:
                        selected_indices = [int(x) for x in install_option.split(',') if x.isdigit()]
                        for index in selected_indices:
                            if 1 <= index <= len(Tools):
                                tool = list(Tools)[index - 1]
                                tool_name = tool.name
                                installed_on_remote = check_tool_remote(nickname, tool_name)
                                if not installed_on_remote:
                                    result = install_tool(nickname, tool.value['default'], 'latest')
                                    if result == 0:
                                        log_installation(nickname, tool_name, 'latest')
                                        console.print(f"[green]Successfully installed {tool_name} on the remote host {nickname}.[/green]")
                                    else:
                                        console.print(f"[red]Failed to install {tool_name} on the remote host {nickname}.[/red]")
                            else:
                                console.print(f"[red]Invalid package number: {index}. Please enter valid numbers.[/red]")
                        break
                    except ValueError:
                        console.print("[red]Invalid input. Please enter numbers separated by commas or 'all'.[/red]")
