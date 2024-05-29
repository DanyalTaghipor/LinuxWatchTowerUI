# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        ('/usr/lib/x86_64-linux-gnu/libpython3.9.so.1.0', '.'),
    ],
    datas=[
        ('ui/*', 'ui'),
        ('ansible_utils/*', 'ansible_utils'),
        ('db/*', 'db'),
    ],
    hiddenimports=[
        'ui',
        'ansible_utils',
        'db',
        'rich',
        'sqlite3',
        'customtkinter',
        'ansible',
        'ansible.inventory.manager',
        'ansible.parsing.dataloader',
        'ansible.vars.manager',
        'ansible.playbook.play',
        'ansible.executor.task_queue_manager',
        'ansible.module_utils.common.collections',
        'ansible.utils.display',
        'ansible.plugins.callback',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
