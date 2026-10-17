Codigo-fonte do modulo Local Translator PT-BR

Arquivos necessarios:
- PTBR_module.py: ponto de entrada do modulo iniciado pelo Text Translator.
- PTBR_server.py: idioma, glossario, traducoes locais e migracao do mapa.
- patch_db.py: leitura e atualizacao local do patch.
- editor.py: pagina local de sugestoes dos colaboradores.
- plurale_pt_br.py: regras de plural pt-BR usadas pelo modulo nos templates com %num%.
- module.toml: configuracao do modulo para o Nexus.
- requirements.txt: dependencias Python do projeto.

Esta versao migra bancos locais antigos que tenham a coluna pt_br para a coluna
translation. Ela nao procura uma coluna chamada it.

Para compilar no Windows com Python 3.12:
1. Abra o PowerShell nesta pasta.
2. Instale as dependencias de compilacao local:
   py -m pip install -r requirements.txt pyinstaller
3. Gere o modulo:
   py -m PyInstaller --noconfirm --clean --distpath ..\Tradução --workpath build Local_Translator_PT_BR.spec
4. Copie module.toml para a pasta dist\Local_Translator_PT_BR:
   Copy-Item module.toml dist\Local_Translator_PT_BR\module.toml -Force

O glossario, as regras de plural e o patch usados na compilacao vêm das pastas da raiz:
..\glossary\, ..\plural\ e ..\patch\pt_br. A pasta updates\ guarda o manifesto para publicar.
Na primeira execucao do modulo compilado, PT_BR\auto_updates.txt e criado com off; mude para on
para verificar atualizacoes na inicializacao. Esse arquivo de escolha nao faz parte da pasta-fonte.
Para atualizar sem recompilar, copie a pasta patch\pt_br para
PT_BR\patch\pt_br na instalacao e reinicie o jogo; o modulo valida o index e as partes antes
de importar uma versao mais nova no banco local.
O atualizador consulta updates\manifest.json para comparar versoes; baixa somente glossario,
plural e patch quando forem superiores às fontes locais. Nao baixa cache, modulo ou executavel
do repositorio, e valida SHA-256 sem executar codigo remoto. O download separado do modelo
permanece como antes. Para publicar dados atualizados, rode `py src\update_manifest.py` na raiz
do projeto e envie updates\manifest.json junto com glossario, plural e patch para main.
O CTranslate2 esta fixado em 4.8.3, a versao mais recente do repositorio oficial nesta atualizacao.
O arquivo .spec prioriza os fontes do modulo nesta pasta, mesmo se o comando for executado de outra
pasta; a compilacao nao substitui esses arquivos por fontes baixados.
O modelo e carregado em INT8 na CPU por padrao. Para manter a precisao salva no modelo nesta
execucao, use --compute-type default. O benchmark comparativo local esta em int8\README.txt.
Templates com contagem recebem marcadores de plural somente quando o vocabulário local em cache
confirma uma forma; casos incertos ficam sem alteração. Caches antigos desses templates sao
retraduzidos na primeira inicializacao apos esta atualizacao.
Para executar os testes das regras de plural, use `py -m unittest discover -s tests -v`
nesta pasta.
O modulo baixa o modelo OPUS-MT de uma versao fixa do projeto se ele nao estiver instalado em
PT_BR\model. O download contem somente o modelo; os textos do jogo nao sao enviados.
Para compilar com o modelo embutido, coloque model.bin, source.spm e target.spm na pasta ..\model.
Sem modelo local ou conexao para baixa-lo, o modulo preserva o ingles quando o patch e o glossario
nao conseguem resolver um texto.

A pasta compilada fica em dist\Local_Translator_PT_BR. Instale-a em:
Guild Wars 2\addons\text_translator\modules\local_translator_pt_br\

Mantenha uma copia de seguranca dos dados pessoais da pasta PT_BR antes de
substituir uma instalacao existente.
