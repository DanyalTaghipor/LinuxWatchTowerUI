import os

# Paths to Ansible configuration files and collections
BASE_YML = os.getenv('BASE_YML')
RUNTIME_YML = os.getenv('RUNTIME_YML')
COLLECTION = os.getenv('COLLECTION')

# Data files to be included
datas = [
    ("ui", "ui"),
    ("ansible_utils", "ansible_utils"),
    ("db", "db"),
    (BASE_YML, "ansible/config"),
    (RUNTIME_YML, "ansible/config"),
    (COLLECTION, "ansible_collections")
]

# Hidden imports
hiddenimports = [
    "ui", "ansible_utils", "db", "rich", "sqlite3", "customtkinter",
    "ansible", "ansible.inventory.manager", "ansible.parsing.dataloader",
    "ansible.vars.manager", "ansible.playbook.play",
    "ansible.executor.task_queue_manager", "ansible.module_utils.common.collections",
    "ansible.utils.display", "ansible.plugins.callback",
    "ansible.plugins.inventory", "ansible.builtin.memory",
    "ansible.builtin.jsonfile", "ansible.netcommon.memory",
    "ansible.plugins.loader", "ansible.plugins.filter", "ansible.plugins.strategy",
    "ansible.plugins.action", "ansible.plugins.lookup", "ansible.plugins.vars",
    "ansible.plugins.connection", "ansible.plugins.become", "ansible.plugins.test",
    "ansible.plugins.terminal", "ansible.plugins.httpapi", "ansible.plugins.netconf",
    "ansible.plugins.network", "ansible.plugins.shell", "ansible.plugins.text",
    "ansible.module_utils.basic", "ansible.module_utils.urls"
]

spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas={datas},
    hiddenimports={hiddenimports},
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='linuxwt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='linuxwt'
)
"""

with open("linuxwt.spec", "w") as f:
    f.write(spec_content)
