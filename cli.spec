# -*- mode: python -*-

block_cipher = None


a = Analysis(['clkhash\\cli.py'],
             pathex=['C:\\Users\\tho802\\Development\\clkhash'],
             binaries=[],
             datas=[
                 ('clkhash/data/randomnames-schema.json', 'clkhash'),
                 ('clkhash/data/*.csv', 'clkhash'),
                 ('clkhash/master-schemas/*.json', 'clkhash')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='cli',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='cli')
