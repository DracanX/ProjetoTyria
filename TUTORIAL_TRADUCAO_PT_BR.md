# Tutorial: coletar, traduzir e preparar textos do Guild Wars 2

Este guia explica como encontrar o ID de um texto no jogo, exportar os textos conhecidos para uma planilha, identificar o que já está no patch e preparar traduções em lote.

> **Importante:** este projeto separa as traduções em automáticas e revisadas. Uma tradução aparecer no jogo ou estar salva no patch não significa que foi revisada por uma pessoa.

## 1. Como o patch é organizado

Os arquivos `p0000.json`, `p0001.json` e assim por diante são partes do mesmo patch de idioma, não patches semanais independentes. O arquivo `index.json` lista as partes que compõem o patch local.

Cada texto é identificado pelo seu ID do jogo:

- `strings`: traduções revisadas, feitas ou aprovadas por uma pessoa;
- `auto`: traduções automáticas incluídas no patch;
- `drop`: IDs que devem ter uma tradução automática antiga removida;
- `index.json`: lista as partes e seus códigos de verificação.

As traduções são organizadas em ordem crescente de ID e distribuídas em partes sequenciais. Cada parte pode ter até 300.000 caracteres; quando `p0000.json` atinge esse limite, o programa continua em `p0001.json`, depois `p0002.json` e assim por diante. A numeração não representa uma faixa fixa de IDs. O módulo do jogo também precisa estar atualizado para aceitar esse formato. Se uma nova tradução tiver o mesmo ID de uma antiga, ela atualiza aquela entrada; não cria uma segunda tradução concorrente para o ID.

Na cópia do projeto analisada para este guia, `patch/pt_br/` contém entradas em `auto` e nenhuma em `strings`. Portanto, as traduções portuguesas dessa cópia estão publicadas como automáticas, não como revisadas.

## 2. Encontrar o ID de um texto no jogo

O jogo deve estar configurado em inglês, pois o módulo traduz a partir do inglês.

1. Abra a pasta de dados do módulo:

   ```text
   C:\Program Files (x86)\Steam\steamapps\common\Guild Wars 2\addons\text_translator\modules\local_translator_pt_br\PT_BR
   ```

2. Crie nessa pasta um arquivo de texto chamado `show_keys.txt`.
3. Escreva `text` no arquivo, salve e reinicie o jogo.
4. O texto aparecerá com um número antes dele, por exemplo:

   ```text
   44547 - The original English text
   ```

   `44547` é o ID do texto. Esse ID identifica a entrada usada pelo patch.

O modo `text` mostra IDs em textos normais. O modo `all` também mostra textos internos e modelos com marcadores. Depois de terminar a busca, remova `show_keys.txt` ou apague seu conteúdo para deixar de mostrar os IDs.

## 3. Onde os textos encontrados são salvos

O módulo registra localmente os textos que encontra em:

```text
PT_BR\map_pt_br.db
```

Esse banco guarda IDs e textos conhecidos pelo módulo, incluindo inglês quando disponível, traduções atuais e sugestões locais. Ele não é o patch oficial e uma alteração direta nele não publica uma tradução.

Mantenha `map_pt_br.db` no seu computador. Ele pode conter textos em inglês do jogo; o README do projeto pede que esses dados sejam mantidos para uso pessoal, sem publicação ou compartilhamento.

### Enviar uma sugestão pelo navegador

O módulo também tem uma página local para sugerir correções enquanto o jogo está aberto. Para ativá-la:

1. Na pasta `PT_BR` do módulo, crie um arquivo chamado `contributor.json`.
2. Coloque nele seu nome de colaborador, por exemplo:

   ```json
   {"author":"Seu nome"}
   ```

3. Salve o arquivo e reinicie o jogo/módulo.
4. Abra no navegador [http://suggestions.localhost:8770](http://suggestions.localhost:8770).
5. Pesquise pelo texto como aparece no jogo, pelo texto em inglês quando conhecido ou pelo ID. Edite a tradução e salve.

A sugestão fica salva localmente em `PT_BR\map_pt_br.db`, na tabela de sugestões. Ela também é aplicada ao jogo imediatamente, mas continua sendo uma sugestão local: não é publicada nem incluída automaticamente no patch distribuído. Para compartilhar as sugestões com quem mantém o projeto, envie o arquivo `map_pt_br.db` de forma privada; ele pode conter textos em inglês do jogo, então não o publique. A página também permite desfazer a última sugestão de um texto.

Para deixar de disponibilizar a página, remova `contributor.json` e reinicie o módulo. A remoção desse arquivo não apaga as sugestões já salvas no banco.

## 4. Exportar os dados para uma planilha

Com o executável que você informou, abra o PowerShell e rode:

```powershell
& "C:\Program Files (x86)\Steam\steamapps\common\Guild Wars 2\addons\text_translator\modules\local_translator_pt_br\Local_Translator_PT_BR.exe" --lang pt_br --export-review "$env:USERPROFILE\Desktop\revisao.csv"
```

O arquivo `revisao.csv` será criado na Área de Trabalho. Essa exportação é uma lista completa dos textos conhecidos no mapa local e das entradas do patch; não exporta somente o que foi visto desde a última vez.

Abra o CSV no Excel ou LibreOffice Calc. Se o programa perguntar como importar:

- escolha a codificação UTF-8;
- escolha ponto e vírgula (`;`) como separador.

As colunas mais úteis são:

| Coluna | O que mostra |
|---|---|
| `key` | ID do texto no jogo |
| `ingles_original` | texto original em inglês, quando conhecido |
| `pt_br_atual` | tradução atualmente conhecida |
| `pt_br_patch` | tradução revisada que já está no patch |
| `nova tradução` | campo para inserir uma correção revisada |

Os nomes das colunas indicam o conteúdo em português do Brasil.

## 5. Filtrar textos sem tradução revisada

Na planilha, ative o filtro na linha dos títulos e aplique:

1. Em `ingles_original`, mostre somente células não vazias.
2. Em `pt_br_patch`, mostre somente células vazias.
3. Confira `pt_br_atual`: pode haver uma tradução automática ou local mesmo quando `pt_br_patch` está vazio.

Assim, você encontra textos com inglês conhecido que ainda não têm tradução revisada no patch. Célula vazia em `pt_br_patch` não significa necessariamente que o jogo exibirá inglês.

## 6. Separar o que foi encontrado desde a exportação anterior

Guarde cada CSV exportado, por exemplo `revisao_2026-10-01.csv` e `revisao_2026-10-16.csv`. Como o CSV novo é completo, compare a coluna `key` da versão nova com a da antiga.

Uma forma simples no Excel ou Calc:

1. Abra os dois CSVs como abas diferentes, chamadas `Antigo` e `Novo`.
2. Na aba `Novo`, crie uma coluna chamada `situação`.
3. Se o ID estiver na coluna A, use na primeira linha de dados:

   ```text
   =SE(CONT.SE(Antigo.$A:$A;A2)>0;"Já existia";"Novo")
   ```

   Em algumas versões do Excel, a referência pode precisar desta forma:

   ```text
   =SE(CONT.SE(Antigo!$A:$A;A2)>0;"Já existia";"Novo")
   ```

4. Copie a fórmula para baixo e filtre `situação` por `Novo`.
5. Para obter apenas novidades ainda sem revisão, aplique também o filtro de `pt_br_patch` vazio.

O ID é a comparação mais confiável. O mesmo texto pode aparecer em mais de uma situação do jogo com IDs diferentes; inversamente, uma tradução melhor para um ID existente é uma correção, não uma nova entrada.

## 7. Traduzir em lote com outro tradutor

Para preparar um lote, use apenas as linhas desejadas e envie ao tradutor o ID junto do inglês. Peça para ele devolver uma linha por ID e não modificar os IDs.

Ao trazer o resultado de volta:

1. associe a tradução ao mesmo `key`;
2. coloque-a na coluna “nova tradução”;
3. confira IDs duplicados ou ausentes;
4. preserve marcadores do jogo, como `%name%`, `%num1%`, tags `<...>` e quebras de linha;
5. revise nomes próprios, termos de jogo, contexto e concordância antes de considerar o texto definitivo.

Tradução automática em lote é um rascunho, não garantia de qualidade final. Este projeto não envia o CSV a serviços externos: a tradução automática, quando usada, roda com o modelo instalado localmente.

## 8. Editar e salvar as correções

Preencha somente a coluna “nova tradução” nas linhas que deseja corrigir. Deixe em branco as linhas que não quer alterar. Não mude o valor de `key`.

O aplicativo incluso faz essa mesclagem por ID:

- um ID já existente recebe a nova tradução revisada;
- um ID novo é incluído;
- a tradução revisada tem prioridade sobre a automática;
- escrever `-` na coluna de correção remove a entrada revisada daquele ID.

Dê um clique duplo no aplicativo compilado, se ele tiver sido fornecido em uma pasta separada. Para executar pelo código-fonte, instale as dependências do projeto uma vez e inicie pelo PowerShell:

```powershell
py -m pip install -r src\requirements.txt
py src\patch_tool.py
```

Na janela, feche o jogo, clique em **Exportar textos para revisão**, selecione `Local_Translator_PT_BR.exe` dentro da pasta do módulo e escolha onde salvar o CSV. Não precisa preencher a coluna “nova tradução” em todos os textos: quando ela estiver vazia, o programa importa `pt_br_atual` como tradução automática. Se preencher “nova tradução”, essa tradução será considerada revisada; `pt_br_patch` indica uma revisão já incluída no patch. Para fazer uma correção nova, preencha “nova tradução” somente nessa linha. Se esta é a primeira vez e ainda não existe patch, use **Criar patch vazio** e escolha a pasta onde deseja criar `pt_br`; ou selecione uma pasta vazia e faça a mesclagem para o aplicativo inicializá-la automaticamente. Depois selecione o CSV e clique em **Mesclar e gerar partes**. O aplicativo:

- ignora linhas em que “nova tradução” está vazia;
- combina as alterações pelo ID e distingue traduções revisadas de automáticas;
- atualiza a versão e os hashes e recria `pNNNN.json` e `index.json`;
- valida as partes geradas antes de substituir o patch;
- guarda a pasta anterior em `patch\pt_br_backup_<data_hora>`.

Uma tradução preenchida em “nova tradução” é marcada como revisada. O valor `-` remove uma tradução revisada existente. Traduções automáticas importadas de `pt_br_atual` são salvas como automáticas, não como revisadas. Se não houver nenhuma mudança, o aplicativo deixa os arquivos como estão. Para restaurar uma cópia de segurança, feche o jogo e o módulo, renomeie a pasta `patch\pt_br` atual e renomeie a cópia desejada para `pt_br`.

### Instalar ou compartilhar o patch

Ao compilar o módulo, a pasta `patch\pt_br` existente no projeto é incluída na compilação. Assim, as traduções adicionadas antes do build são carregadas pelo módulo quando o jogo inicia.

Para enviar atualizações a outra pessoa sem recompilar:

1. Feche o jogo e o módulo.
2. Copie a pasta completa `patch\pt_br` do projeto, incluindo `index.json` e todos os arquivos `pNNNN.json`.
3. Na instalação de destino, coloque-a em `...\addons\text_translator\modules\local_translator_pt_br\PT_BR\patch\pt_br`.
4. Inicie o jogo. O módulo valida o índice e as partes e importa a versão local mais recente.

Não renomeie nem envie somente partes isoladas sem o `index.json`. O módulo ignora versões mais antigas do que a já instalada. Para compartilhar as traduções, envie essa pasta de patch; não envie `map_pt_br.db`, que pode conter texto original do jogo.

### Atualizar patch, glossário e plural pelo GitHub

O módulo pode verificar atualizações do repositório `DracanX/ProjetoTyria` ao iniciar. Na primeira execução do módulo compilado, aparece `PT_BR\auto_updates.txt` com a opção desligada (`off`). Para ativar, troque `off` por `on` e reinicie o jogo; para desligar, volte para `off`. A consulta ao manifesto é usada para comparar versões; o módulo baixa somente os dados atualizados de glossário, plural e patch. Não baixa o executável, o código-fonte nem caches do repositório. O download do modelo de tradução, quando necessário, continua separado.

O módulo carrega primeiro as versões locais incluídas no executável e as cópias locais compartilhadas. Depois consulta o manifesto do GitHub. Só baixa glossário, plural ou patch quando a versão publicada é maior que a versão local; se forem iguais, a versão local é mantida. As atualizações baixadas ficam em `PT_BR\updates\` e são verificadas por SHA-256. A conexão não envia textos do jogo nem executa código baixado.

Para ativar ou desligar essa busca, edite `PT_BR\auto_updates.txt` na pasta instalada do módulo:

1. Feche o jogo antes de alterar o arquivo.
2. Troque a única opção da última linha para `on` (ativar) ou `off` (desativar). O padrão criado na primeira execução é `off`.
3. Salve e inicie o jogo. A busca ocorre na inicialização do módulo; se não houver atualização, os dados locais continuam sendo usados.

Para publicar uma atualização de dados:

1. Edite os arquivos-fonte nas pastas `glossary\`, `plural\` e/ou `patch\pt_br\` na raiz do projeto. Não publique `map_pt_br.db`, caches do jogo ou dados pessoais.
2. Ao editar o glossário, aumente `_version`; ao editar as regras em `plural\plural_pt_br.json`, aumente `version`. O mesclador incrementa a versão do patch ao gerar novas partes.
3. Na raiz do projeto, gere as somas e versões do manifesto:

```powershell
py src\update_manifest.py
```

4. Publique na branch `main` do repositório `DracanX/ProjetoTyria` o manifesto `updates\manifest.json` e os arquivos de dados correspondentes, mantendo estes caminhos: `glossary\glossary_pt_br.json`, `plural\plural_pt_br.json` e `patch\pt_br\` com `index.json` e todas as partes listadas nele.
5. Não reutilize uma versão para conteúdo diferente. O atualizador valida o manifesto, a versão e o SHA-256 de cada arquivo antes de instalar os dados; o patch também é conferido contra o `index.json` e os hashes de todas as partes.

### Combinar CSVs de outros usuários

Para juntar uma base recebida de outra pessoa à sua, primeiro selecione o seu CSV no campo **Planilha CSV** e clique em **Mesclar CSVs de outros usuários na minha base**. Selecione um ou mais CSVs recebidos e escolha um nome para o novo arquivo consolidado. A sua planilha e os arquivos recebidos não são alterados; o resultado é salvo separadamente e fica selecionado no aplicativo.

A combinação usa o ID (`key`): adiciona IDs que ainda não existem e preenche dados vazios. Se a sua planilha já tiver uma tradução para aquele ID, ela é preservada, mesmo que a tradução recebida esteja em outra coluna (`pt_br_atual`, `pt_br_patch` ou “nova tradução”). O aplicativo informa quantos IDs foram adicionados, quantos campos vazios foram preenchidos e quantas diferenças foram mantidas a favor da sua base. Depois, confira a nova planilha e use **Mesclar e gerar partes** para gerar o patch. Só importe CSVs de pessoas em quem confia e confira as traduções antes de distribuí-las.

Depois de conferir os arquivos, distribua a pasta do patch manualmente, inclua a versão atual na próxima compilação ou publique-a no repositório para quem ativou as atualizações automáticas. Na primeira execução, o módulo pode baixar o modelo de tradução; os textos do jogo não são enviados. Uma tradução melhor para um ID substitui a anterior daquele ID; as outras entradas continuam.

## Resumo do fluxo

```text
Mostrar ID no jogo
    -> texto é registrado em map_pt_br.db
    -> exportar revisao.csv
    -> filtrar por ID e estado da tradução
    -> traduzir/revisar mantendo cada ID
    -> preencher a coluna “nova tradução”
    -> mesclar e gerar partes com src\patch_tool.py
    -> conferir e publicar separadamente
```

Glossário, plural e patch são carregados primeiro dos arquivos locais; as atualizações do repositório são opcionais e desligadas por padrão. O modelo é baixado automaticamente apenas se estiver faltando; para atualizá-lo manualmente, substitua seus arquivos com o jogo fechado e mantenha uma cópia de segurança.
