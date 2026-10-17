# GW2 Nexus Local Translator — Português do Brasil

Módulo para o addon Text Translator do Nexus, que traduz textos de Guild Wars 2 em tempo real.

Glossário, regras de plural e patches vêm primeiro dos arquivos locais incluídos na compilação. Opcionalmente, o módulo pode verificar atualizações no repositório público `DracanX/ProjetoTyria`; atualizações remotas só substituem os dados locais quando têm uma versão maior. O padrão é desligado e pode ser alterado pelo usuário. O texto do jogo nunca é enviado pela internet.

## Pastas do projeto

- `src\`: código do módulo, testes e ferramentas de compilação/publicação.
- `glossary\`: glossário local incluído na compilação.
- `plural\`: regras de plural versionadas, incluídas na compilação.
- `patch\pt_br\`: patch local incluído na compilação.
- `updates\`: manifesto com versões e hashes dos dados publicados no GitHub.
- `Dados_do_Modulo\`: pasta reservada a dados locais de execução durante o desenvolvimento; não é empacotada pela compilação. No módulo instalado, os dados do usuário continuam na pasta `PT_BR\` ao lado do executável, preservando o caminho existente.

Ao compilar, os dados de `glossary\`, `plural\` e `patch\pt_br\` na raiz do projeto são usados como fontes locais prioritárias. Os arquivos baixados do GitHub só passam à frente se tiverem uma versão maior.

## Como funciona

- O Text Translator envia os textos que aparecem no jogo ao módulo, junto com o ID do texto.
- O módulo responde com a tradução revisada do patch, quando existe. Caso contrário, traduz localmente com o modelo e aplica o glossário.
- As traduções ficam no cache do addon; o módulo também mantém um mapa local dos textos encontrados.
- O patch é lido de arquivos locais. As entradas são separadas por ID em partes.
- Quando habilitada, a atualização automática verifica no GitHub versões mais novas do patch, glossário e dados de plural.

O patch usa três tipos de entrada:

- `strings`: traduções revisadas;
- `auto`: traduções automáticas;
- `drop`: entradas automáticas antigas a remover.

Na cópia atual do patch pt-br, as entradas estão em `auto`; não há entradas em `strings`.

## Requisitos

- Guild Wars 2 no Windows 64-bit, com o idioma do jogo definido como inglês;
- addon loader Nexus;
- Text Translator v0.2.0 ou mais recente;
- aproximadamente 500 MB de memória livre enquanto joga e 250 MB de espaço em disco para o módulo e o modelo.

## Instalação

1. Compile ou copie a pasta local `Local_Translator_PT_BR` para `addons\text_translator\modules\local_translator_pt_br\`.
2. Inicie o jogo e habilite o Text Translator no Nexus, se necessário.

Na primeira inicialização, o módulo baixa automaticamente o modelo de tradução se ele ainda não estiver disponível em `PT_BR\model\`, como já fazia antes; esse download é separado do repositório de atualizações. Depois, o modelo fica nesse computador e a tradução roda localmente. Na primeira execução do arquivo compilado, o módulo cria `PT_BR\auto_updates.txt` com `off`. Para ativar as atualizações, altere esse valor para `on` e reinicie o jogo. O módulo consulta o manifesto no repositório público e, se houver versões maiores, baixa somente os dados de glossário, plural e patch. Não baixa nem substitui o módulo, o executável ou os caches do usuário. Se a verificação ou o download falhar, os dados locais continuam em uso. O texto do jogo não é enviado ao GitHub.

## Arquivos instalados

O módulo pt-br fica em `addons\text_translator\modules\local_translator_pt_br\`. Os dados específicos do idioma ficam na subpasta `PT_BR\`:

```text
addons\
  text_translator.dll
  text_translator\
    settings.toml
    modules\local_translator_pt_br\
      module.toml
      Local_Translator_PT_BR.exe
      cache.db
      PT_BR\
        model\
        patch\
          pt_br\
        updates\
          glossary_pt_br.json
          plural_pt_br.json
          patch\pt_br\
        patch_pt_br.db
        cache_pt_br.jsonl
        map_pt_br.db
      local_translator_pt_br.log
```

O glossário, as regras de plural e o patch incluídos na compilação vêm das pastas da raiz do projeto. `PT_BR\updates\` guarda as versões baixadas quando a atualização automática está ligada. `PT_BR\patch\pt_br\` aceita atualizações de patch compartilhadas manualmente. `PT_BR\auto_updates.txt`, criado na primeira execução do arquivo compilado, controla a busca na inicialização (`off` ou `on`). O modelo deve estar disponível localmente. `cache.db`, `cache_pt_br.jsonl` e `map_pt_br.db` são arquivos locais; podem conter textos do jogo e devem permanecer no seu computador.

## Patch de tradução

Os arquivos de origem ficam em `patch\pt_br\`. O `index.json` lista as partes `pNNNN.json`; elas compõem juntas o patch pt-br. O mesclador organiza os IDs em ordem crescente e preenche cada parte até 300.000 caracteres; quando atinge esse limite, começa a próxima (`p0000.json`, `p0001.json`, `p0002.json`...). A numeração é sequencial, não baseada em faixas de ID. Uma tradução melhor para um ID substitui a entrada anterior daquele ID. A compilação inclui o patch atual e o módulo pode importar cópias locais mais novas sem recompilar.

O patch distribuído não contém o texto original em inglês. Para relatar uma tradução incorreta, abra uma issue com o ID, o texto visto no jogo, o local onde apareceu e a sugestão em português.

## Glossário

O glossário pt-br está em `glossary\glossary_pt_br.json` e contém:

- `exact`: substituições para textos inteiros;
- `terms`: termos e nomes mantidos ou traduzidos de forma consistente;
- `patterns`: regras para padrões de texto, usando `{X}` como trecho variável.

O glossário atual mantém em inglês muitos nomes próprios do jogo.

As regras de plural editáveis ficam em `plural\plural_pt_br.json`; a lógica de aplicação continua no código local `src\plurale_pt_br.py`. A versão dessas regras é independente da versão do programa.

## Atualizações automáticas opcionais

O arquivo `PT_BR\auto_updates.txt` é criado na primeira execução do arquivo compilado, com `off` como padrão. Troque somente esse valor para `on` e reinicie o jogo para consultar `https://github.com/DracanX/ProjetoTyria` na branch `main`. Para desligar novamente, volte para `off`.

As atualizações seguem uma regra de prioridade: primeiro são carregados os arquivos locais incluídos na compilação e as versões locais compartilhadas; só depois o módulo compara as versões publicadas no GitHub. Para fazer essa comparação, consulta `updates\manifest.json` (metadados de versão e SHA-256). Uma atualização de glossário, plural ou patch só é baixada e instalada quando sua versão é estritamente maior. Empates preservam a cópia local. Esses arquivos de dados são validados antes de serem gravados em `PT_BR\updates\`. O módulo não baixa caches do repositório, o código-fonte nem o executável; tampouco executa código recebido pela rede.

Para publicar as atualizações, mantenha no repositório estes caminhos: `updates\manifest.json`, `glossary\glossary_pt_br.json`, `plural\plural_pt_br.json` e `patch\pt_br\` com `index.json` e todas as partes listadas nele. Depois de atualizar os dados locais, rode na raiz do projeto:

```powershell
py src\update_manifest.py
```

Envie o manifesto gerado e os arquivos correspondentes para a branch `main`. Aumente `_version` no JSON do glossário quando editá-lo e `version` no JSON do plural quando alterar as regras; o mesclador já incrementa `version` do patch. O manifesto calcula as somas SHA-256 e registra as versões. Não reutilize uma versão para conteúdo diferente.

## Encontrar o ID de um texto

Na pasta de dados `...\local_translator_pt_br\PT_BR\`, crie `show_keys.txt`, escreva `text` e reinicie o jogo. O texto será exibido com seu ID, por exemplo `44547 - Texto`. Use `all` para incluir também modelos e textos internos. Remova o arquivo ou apague seu conteúdo para desligar esse modo.

## Exportar textos para revisão

O módulo pode exportar um CSV completo dos textos conhecidos no mapa local e no patch. No PowerShell, por exemplo:

```powershell
& "C:\caminho\para\Local_Translator_PT_BR.exe" --lang pt_br --export-review "$env:USERPROFILE\Desktop\revisao.csv"
```

O CSV tem uma linha por ID e as colunas `key`, `ingles_original`, `pt_br_atual`, `pt_br_patch` e `nova tradução`. A exportação é completa, não apenas dos textos novos. Compare os IDs da exportação anterior com a nova para localizar novidades. O CSV pode conter texto em inglês do jogo; não publique nem compartilhe esses dados.

## Mesclar traduções no patch

Abra a versão compilada do aplicativo com um clique duplo, se ela tiver sido fornecida em uma pasta separada. Para executar pelo código-fonte, instale as dependências e inicie:

```powershell
py -m pip install -r src\requirements.txt
py src\patch_tool.py
```

Na janela, o botão **Exportar textos para revisão** executa a exportação do módulo instalado: selecione `Local_Translator_PT_BR.exe` e escolha onde salvar `revisao.csv`. Para incluir os textos vistos durante o jogo, feche o jogo antes de exportar. Depois, selecione o CSV e clique em **Mesclar e gerar partes**. O mesclador importa `pt_br_atual` como tradução automática quando o campo “nova tradução” está vazio; os valores preenchidos nesse campo entram como traduções revisadas. A coluna `pt_br_patch` identifica revisões que já estavam no patch. Assim, o CSV recém-exportado já pode gerar partes, sem precisar preencher manualmente “nova tradução” para cada texto automático. Um `-` nesse campo remove uma tradução revisada existente. Para iniciar um patch do zero, use **Criar patch vazio** ou selecione uma pasta vazia e faça a mesclagem; o aplicativo cria o índice inicial automaticamente. As traduções são mescladas pelo ID, e uma cópia de segurança é criada antes de substituir um patch existente.

O botão **Mesclar CSVs de outros usuários na minha base** combina a planilha selecionada com outros CSVs pelo ID, sem alterar os arquivos originais. IDs novos e campos vazios são preenchidos; traduções que já existem na base têm prioridade, mesmo se estiverem em outra coluna de tradução. Conflitos são informados e os dados da base são mantidos. A saída é salva em outro CSV e passa a ser a planilha selecionada.

O aplicativo valida os arquivos atuais, mantém os metadados das entradas não alteradas, atualiza hashes, versões, partes e índice, e verifica a saída antes de substituir os arquivos. Para voltar à cópia anterior, feche o jogo e o módulo, renomeie `patch\pt_br` para outro nome e renomeie a cópia de segurança desejada para `pt_br`.

O módulo carrega o patch local na inicialização. Para compartilhar uma atualização sem recompilar, copie a pasta completa `patch\pt_br` para `PT_BR\patch\pt_br` dentro da pasta de dados do módulo de destino e reinicie o jogo. O módulo valida `index.json` e os hashes das partes antes de importar; uma versão mais antiga não substitui uma mais nova. Compartilhe somente essa pasta de patch, não `map_pt_br.db`, que pode conter texto original do jogo.

## Desenvolvimento

O código-fonte fica em `src\`. Para gerar o executável no Windows com Python 3.12:

```powershell
py -m pip install -r src\requirements.txt pyinstaller
py -m PyInstaller --noconfirm --clean --distpath dist --workpath src\build src\Local_Translator_PT_BR.spec
```

O CTranslate2 está fixado em `4.8.3`, a versão mais recente disponível no repositório oficial na data desta atualização. A instalação das dependências seleciona essa versão exata. O módulo usa INT8 na CPU por padrão; para uma execução de comparação na precisão salva no modelo, use `--compute-type default`. O benchmark local e as instruções ficam em `src\int8\`. O arquivo `.spec` procura primeiro os fontes locais em `src\` e inclui o patch atual de `patch\pt_br` na compilação, independentemente da pasta de onde o comando é executado; não baixa nem substitui `PTBR_module.py`, `PTBR_server.py` ou os demais fontes do projeto. Para alterar o código, edite os arquivos locais e compile novamente.

Copie o conteúdo de `dist\Local_Translator_PT_BR\` e `src\text_translator\pt_br\module.toml` para `addons\text_translator\modules\local_translator_pt_br\`. O `.spec` inclui o modelo na compilação se `model\` estiver na raiz do projeto com `model.bin`, `source.spm` e `target.spm`; caso contrário, o módulo o baixa na primeira inicialização.

Para empacotar o mesclador como um executável de janela separado:

```powershell
pyinstaller --onefile --windowed --name Mesclar_Patch_PT_BR --paths src --hidden-import xxhash src\patch_tool.py
```

O patch local também pode ser compartilhado sem recompilar: copie `patch\pt_br\` para `PT_BR\patch\pt_br\` na instalação de destino e reinicie o jogo. Para atualizações pela internet, `PT_BR\auto_updates.txt` deve conter `on`; a opção é independente do download inicial do modelo de tradução. Uma instalação antiga pode conservar patches em `PT_BR\patch_pt_br.db`; faça uma cópia de segurança antes de substituir ou limpar esses dados.

O exportador e mesclador usa `PTBR_server.py` e `xxhash`; a pasta `codigo_fonte` que acompanha o executável contém os fontes necessários e instruções para recompilá-lo. Em `src\plurale_pt_br.py`, o módulo usa as regras conservadoras para acrescentar marcadores de plural em templates com `%num%`, apoiando-se no vocabulário das traduções em cache. Formas sem evidência suficiente permanecem inalteradas. O arquivo de patch preparado localmente e a publicação em um repositório remoto são etapas separadas.

## Créditos

- **Ideka**, autor do Text Translator e do protocolo de módulos;
- **Helsinki-NLP**, pelo modelo OPUS-MT `eng-por`, distribuído sob CC BY 4.0;
- **NikeGipple**, pela conversão do modelo de tradução PT-BR utilizado pelo módulo;
- **OpenNMT**, pelo CTranslate2;
- **Raidcore**, pelo Nexus.

Este é um projeto comunitário não oficial, sem afiliação com ArenaNet, NCSOFT, Raidcore, Ideka ou Helsinki-NLP. O código do projeto é distribuído sob a licença MIT; componentes locais de terceiros mantêm suas licenças originais.
