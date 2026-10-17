Fonte do aplicativo Mesclar_Patch_PT_BR

Arquivos:
- patch_tool.py: interface e mesclagem do patch.
- PTBR_server.py: funções compartilhadas de leitura, validação e geração do patch.

Para compilar no Windows:
1. Instale Python 3.12.
2. Abra o terminal nesta pasta e execute:
   py -m pip install xxhash pyinstaller
   py -m PyInstaller --noconfirm --onefile --windowed --name Mesclar_Patch_PT_BR --paths . --hidden-import xxhash patch_tool.py

O executável será criado em dist\Mesclar_Patch_PT_BR.exe.
