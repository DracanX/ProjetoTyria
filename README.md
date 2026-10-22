# Tradução Brasileira para Guild Wars 2

**Tradução Brasileira** é o módulo PT-BR para o addon [**Text Translator**](https://github.com/ideka/text-translator-public), de [Ideka](https://github.com/ideka), carregado pelo [Nexus](https://raidcore.gg/Nexus). Ele traduz textos do Guild Wars 2 em tempo real para português brasileiro.

| Idioma | Módulo | Arquivo para baixar | Situação |
|---|---|---|---|
| Português do Brasil | Tradução Brasileira | `Traducao_Brasileira_1.0_PT_BR.zip` | Versão 1.0 final; traduções automáticas ainda precisam de revisão |

## O que o módulo faz

- **Traduz no próprio computador.** Usa o modelo OPUS-MT tc-big inglês→português, convertido para int8 com CTranslate2. O marcador `>>pob<<` direciona a saída para português brasileiro. Durante o jogo, os textos não são enviados ao provedor do modelo: a tradução é local.
- **Preserva títulos reconhecidos.** Um catálogo local, opcional, reúne nomes oficiais do jogo e mantém títulos reconhecidos em inglês. Correspondências não reconhecidas não são adivinhadas: o texto segue para tradução.
- **Usa correções e termos consistentes.** O glossário aplica regras e protege nomes; o patch contém traduções revisadas que substituem a tradução automática.
- **Distribui somente a Tradução Brasileira (PT-BR).**

> **Créditos:** `text_translator.dll` é o addon Text Translator, criado por Ideka e incluído para que o pacote tenha tudo o que é necessário. Este projeto fornece o módulo de idioma baseado no protocolo público do addon.

## Requisitos

- Guild Wars 2 em Windows de 64 bits, com o idioma do jogo definido como **inglês**.
- [Nexus](https://raidcore.gg/Nexus).
- Text Translator **v0.2.0 ou superior**.
- Python 3.12 recomendado para preparar e compilar o projeto. A conversão do modelo exige espaço em disco e memória; a velocidade de tradução depende do processador.
- O modelo OPUS-MT tc-big usa a licença CC-BY-4.0. Respeite os termos e a atribuição ao redistribuí-lo.

## Instalação do pacote

1. Baixe `Traducao_Brasileira_<versão>_PT_BR.zip` na página de lançamentos.
2. Extraia o conteúdo na pasta do Guild Wars 2. A pasta `addons` se mescla à existente; os outros addons não são substituídos.
3. Inicie o jogo. Se necessário, habilite o Text Translator na lista de addons do Nexus. A Tradução Brasileira inicia junto com ele.

O pacote de idioma também seleciona a Tradução Brasileira e configura opções recomendadas. Se já usa o Text Translator e quer manter as próprias configurações, baixe o pacote sem configurações e selecione a Tradução Brasileira na aba *Modules* das opções do Text Translator.

## Como o texto percorre o programa

O Text Translator é quem extrai o texto da interface do jogo. A Tradução Brasileira **não lê a tela nem extrai texto por conta própria**: ela recebe do addon as strings capturadas e responde com a versão que deve ser exibida.

```text
Guild Wars 2
    │ o addon captura o texto visível
    ▼
Text Translator (text_translator.dll)
    │ envia texto + identificador/hash locais pelo protocolo do módulo
    ▼
src/module.py — recebe a solicitação e coordena o fluxo
    │
    ├── Título completo conhecido? ── sim ──> devolve o original em inglês
    │
    ├── Patch/sugestão revisada disponível? ── sim ──> usa a correção
    │
    ├── Glossário/cache já resolvem o texto? ── sim ──> usa o resultado salvo
    │
    └── Caso contrário:
          título de tooltip reconhecido? ──> preserva título e processa descrição
          src/server.py ── protege tags e aplica regras do glossário
          OPUS-MT via CTranslate2 ── traduz o texto restante localmente
    │
    ▼
Text Translator recebe a resposta e mostra/salva o texto no jogo
```

### Etapas detalhadas durante o jogo

1. **Captura:** o addon Text Translator detecta uma string exibida pelo jogo. A extração e a atribuição do identificador são responsabilidade do addon.
2. **Envio ao módulo:** Text Translator envia a string, um identificador local e um hash do texto original pelo protocolo entre processos. O identificador não é um ID de item ou skill da API do Guild Wars 2; ele não permite descobrir a categoria do texto.
3. **Filtragem imediata:** `src/module.py` verifica se o texto é vazio/trivial, se já corresponde a um nome protegido pelo glossário ou se o texto inteiro corresponde a um nome do catálogo. Títulos conhecidos são devolvidos em inglês antes de procurar sugestões, patch, cache ou modelo.
4. **Correções existentes:** se o texto não foi preservado, o módulo verifica sugestões válidas e traduções do patch. Um patch para tooltip também pode ser ajustado para manter um título reconhecido em inglês.
5. **Separação de tooltip:** se não houver resposta pronta, o módulo procura uma quebra de linha ou `<br>`. Só separa o primeiro trecho quando ele coincide exatamente, após normalização, com um nome do catálogo e existe texto descritivo depois. O título original é preservado; a descrição continua no fluxo de tradução. Sem correspondência segura, o texto inteiro segue normalmente.
6. **Glossário e cache:** o motor verifica traduções locais já calculadas e as regras do glossário. O glossário pode manter termos consistentes durante a tradução; o catálogo de títulos, por outro lado, não transforma nomes em proteções de palavras dentro de frases.
7. **Preparação do texto:** antes de chamar o modelo, o motor protege tags de interface, variáveis e marcadores de gramática. Textos longos são processados em partes, para que linhas ou trechos não sejam descartados.
8. **Tradução:** o modelo OPUS-MT convertido, executado pelo CTranslate2 na CPU local, traduz as partes que ainda precisam de tradução. A busca do modelo usa `beam_size = 6`, avaliando mais hipóteses do que a configuração anterior, com possível aumento no tempo de resposta. As tags e marcadores são recolocados na resposta.
9. **Resposta e armazenamento:** o módulo devolve o texto ao Text Translator, que o exibe e mantém no próprio cache. O módulo também conserva seu cache de tradução e o mapa local de textos encontrados.

**Regra principal do filtro:** o catálogo só decide preservar um título quando o texto completo — ou, em um tooltip claramente separado, seu primeiro trecho — corresponde a um nome conhecido. Não se usa busca aproximada nem correspondência por substring. Por exemplo, encontrar o nome de uma skill no meio de uma descrição não bloqueia a tradução dessa descrição.

### Contexto e divisão dos textos

O tradutor mantém uma frase inteira como uma unidade de tradução sempre que ela cabe no limite de entrada do modelo. Isso dá ao OPUS-MT mais contexto para escolher o sentido das palavras. Uma quebra explícita `<br>` continua separando blocos da interface. Se um bloco ultrapassar o limite seguro, ele é dividido primeiro em limites de frase ou oração; limites entre palavras são usados somente como último recurso. Os separadores e a formatação são preservados na remontagem. Ao iniciar com essa versão, o cache local de traduções antigas é invalidado para que os textos possam ser gerados novamente com o novo `beam_size` e as novas regras de divisão.

## Catálogo de títulos da API

O catálogo é construído por `src/gw2_titles.py` e salvo em `build\gw2_titles.db`. Abaixo estão todas as categorias e fontes que o sincronizador atual inclui:

| Categoria no catálogo | Fonte | O que é incluído |
|---|---|---|
| Itens (`items`) | API `/v2/items` | Nomes oficiais dos itens: equipamentos, armas, armaduras, consumíveis, materiais, skins e demais itens retornados pela API. Somente o nome é guardado, não a descrição. |
| Habilidades (`skills`) | API `/v2/skills` | Nomes das skills. |
| Traits | API `/v2/traits` | Nomes das características/traits. |
| Especializações (`specializations`) | API `/v2/specializations` | Nomes de especializações, incluindo especializações de elite disponíveis na API. |
| Profissões e trilhas de treinamento (`professions`, `training`) | API `/v2/professions` | Nomes das profissões e nomes das opções de treinamento contidas em cada profissão. |
| Mapas permitidos (`maps`) | API `/v2/maps` | Nomes apenas dos mapas cujos tipos estão explicitamente permitidos no código: `Public`, `Pvp`, `GvG`, `WvW`, `Center`, `BlueHome`, `GreenHome`, `RedHome`, `EdgeOfTheMists` e `Dungeon`. Outros tipos são descartados. |
| Efeitos de combate (`combat_effects`) | Fatos `Buff` e `PrefixedBuff` de `/v2/skills` e `/v2/traits` | O campo `status` dos efeitos nomeados que a API encontra nas skills e traits. Inclui boons e conditions e também outros efeitos nomeados; a API não fornece um endpoint separado que os classifique somente como boon ou condition. |
| Deuses humanos (`gods`) | `/v2/backstory/questions` e `/v2/backstory/answers` | Localiza na API a pergunta “The Six Gods” e coleta os títulos das respostas dela. A API retorna os seis deuses jogáveis; Abaddon não é uma resposta dessa pergunta. |
| Temporadas de história (`story_seasons`) | `/v2/stories/seasons` | Nomes das temporadas e histórias agrupadas pela API, incluindo expansões e Living World. A temporada “My Story” é excluída por ser a história pessoal; capítulos e episódios individuais não são consultados. |

Nas fontes da API com IDs numéricos, o sincronizador busca a lista de IDs e solicita os registros em lotes de até 200. A lista de itens é solicitada em `/v2/items` sem `ids=all`, pois esse endpoint não aceita esse parâmetro. A janela mostra a fonte, o número do lote e o tempo decorrido. O arquivo novo só substitui o catálogo anterior se todas as fontes forem processadas com sucesso. O SQLite guarda o nome original, seu formato normalizado, a categoria de origem e o ID da fonte; descrições e outros campos da API são descartados.

**Limites importantes da API:** não existe `/v2/buffs` nem `/v2/expansions`. Boons e conditions são descobertos examinando o campo `status` dos fatos `Buff` e `PrefixedBuff` em skills e traits. Como esses fatos também descrevem outros efeitos nomeados, o catálogo os inclui na categoria mais ampla `combat_effects`; não há no retorno da API um campo confiável que permita separar apenas boons e conditions. Deuses vêm das respostas oficiais à pergunta de história pessoal “The Six Gods”; assim, são incluídos os seis nomes que a API retorna, não uma lista manual de deuses adicionais. Expansões e temporadas vêm de `/v2/stories/seasons`, de modo que novos nomes publicados nesse endpoint entram na próxima sincronização sem atualizar uma lista fixa.

### Como atualizar o catálogo depois de uma atualização do jogo

**Se a API já fornece o nome em uma fonte existente:** feche o jogo/módulo e execute `src\sync_gw2_titles.bat`. O sincronizador baixa novamente as fontes configuradas e atualiza `build\gw2_titles.db`. Depois execute `build.bat` para copiar o banco atualizado para o pacote. Não é necessário baixar ou converter o modelo de tradução novamente.

**Se a API passou a fornecer uma nova categoria ou recurso:** atualizar o banco sozinho não basta; primeiro é necessário adaptar o código:

1. Consulte a documentação da API para confirmar o endpoint, o campo que contém o nome, o tipo de ID, o idioma suportado e eventuais filtros necessários.
2. Para um endpoint de entidades com IDs numéricos e resposta compatível com o formato atual, adicione o recurso à constante `ENTITY_TYPES` em `src\gw2_titles.py`. O sincronizador genérico obtém a lista e busca os registros em lotes.
3. Para filtrar mapas ou outra fonte por um campo como `type`, ajuste a lista de valores permitidos e o filtro aplicado em `sync_catalog`. Não inclua automaticamente instâncias de teste ou categorias que não devam ser preservadas.
4. Se a resposta tiver estrutura diferente — como `/v2/professions`, que inclui trilhas dentro de cada profissão — implemente um coletor específico semelhante a `_sync_professions`. IDs textuais também devem ser armazenados como texto no banco.
5. Se os dados tiverem estrutura própria, implemente um coletor específico. Os coletores `_sync_human_gods` e `_sync_story_seasons` são exemplos para IDs textuais/respostas aninhadas e para temporadas.
6. Atualize os testes em `src\tests\test_gw2_titles.py` com respostas simuladas da nova fonte. Verifique que os nomes entram no catálogo, que os tipos indesejados são filtrados e que uma falha não substitui o banco anterior.
7. Execute `python -m unittest discover -s src\tests -v`, sincronize com `src\sync_gw2_titles.bat` e gere o pacote com `build.bat`.

Os pontos principais para uma futura expansão são `ENTITY_TYPES`, `VALID_MAP_TYPES`, `SKILL_EFFECT_FACT_TYPES`, `_sync_resource`, `_sync_professions`, `_sync_human_gods`, `_sync_story_seasons` e `sync_catalog`, todos em `src\gw2_titles.py`. Depois de alterar a estrutura ou a política do catálogo, revise também os testes e este README.

## Arquivos instalados

A pasta do módulo e o nome exibido pelo addon são **Tradução Brasileira**:

```text
addons\
  text_translator.dll                 Text Translator, de Ideka
  text_translator\
    settings.toml                     configurações do addon
    modules\Tradução Brasileira\
      module.toml                     configuração do módulo
      Tradução Brasileira.exe         módulo compilado
      _internal\                      bibliotecas incluídas pelo PyInstaller
      cache.db                        cache do addon Text Translator
      PT_BR\
        model\                        modelo OPUS-MT convertido
        gw2_titles.db                 catálogo local de títulos (opcional)
        glossary_pt_br.json           glossário
        patch_pt_br.db                traduções revisadas
        cache_pt_br.jsonl             cache local de traduções
        map_pt_br.db                  mapa local dos textos encontrados
      traducao_brasileira.log         registro do módulo
```

Os arquivos `cache.db`, `cache_pt_br.jsonl` e `map_pt_br.db` são gerados localmente durante o uso. Eles podem conter textos do jogo; não os publique nem os compartilhe.

## Como funcionam glossário e patch

O glossário PT-BR fica em [`glossary/glossary_pt_br.json`](glossary/glossary_pt_br.json):

- `exact`: substituições aplicadas ao texto completo;
- `terms`: regras para traduzir ou preservar termos em frases;
- `patterns`: regras para linhas inteiras, com `{X}` representando palavras variáveis;
- `keep` (opcional): nomes que devem permanecer em inglês, inclusive quando aparecem em frases.

Entradas idênticas em `terms`, entradas `exact` cujo resultado é o próprio original e nomes em `keep` são preservados em inglês. Essa é uma função do glossário existente. O catálogo de API tem uma função mais restrita: reconhecer títulos completos e títulos no início de tooltips; ele não é usado para preservar automaticamente cada ocorrência de um nome dentro de uma frase.

O patch revisado fica em [`patch/pt_br/`](patch/pt_br/), dividido em partes para que atualizações baixem apenas o que mudou. Ele contém traduções, não o texto original em inglês. Se uma string do jogo for alterada em uma atualização, o texto antigo do patch não deve ser aplicado à string nova; o módulo poderá traduzi-la novamente.

O Text Translator usa hashes para identificar strings armazenadas. A dependência `xxhash` permite localizar traduções de títulos protegidos no patch/cache do addon para que não substituam o inglês. Sem ela, o bypass ainda funciona quando o jogo solicita o texto, mas a limpeza prévia dos registros localizados por hash fica limitada.

### Exportar e importar revisões pela interface gráfica

Os testes foram organizados em `src\tests\`. Execute `python -m unittest discover -s src\tests -v` para rodar todos.

O código-fonte da interface está em `CSV Hub\review_gui.py`. Execute `CSV Hub\review_gui.bat` para abrir a GUI nativa no Windows durante o desenvolvimento. Ela usa navegação lateral estilizada e não depende de navegador/web. Para compilar a versão standalone, execute `CSV Hub\build_review_gui.bat`; o arquivo gerado é `dist\CSV_Hub.exe`. Ele inclui Python, CustomTkinter, recursos visuais e o código necessário, podendo ser copiado e executado sozinho. Os arquivos de entrada e saída continuam sendo selecionados localmente.

Na aba **Unir CSVs**, selecione uma pasta de CSVs e o destino do resultado. As linhas são unidas pela coluna `chave`; células vazias não apagam valores existentes e, em conflitos, o último valor não vazio na ordem alfabética dos arquivos vence. A aba **Aplicar / criar patch** importa revisões para um JSON mestre (com backup datado quando já existe) ou cria, em uma pasta nova, o JSON mestre e `pt_br\index.json` com as partes `pNNNN.json`. A ferramenta não publica no GitHub nem altera automaticamente o patch publicado. O CSV exportado contém texto original em inglês, portanto mantenha-o privado.

## Privacidade e conexões de rede

- A sincronização de `gw2_titles.db` acessa a API pública do Guild Wars 2 apenas quando `src\sync_gw2_titles.bat` é executado.
- Durante o jogo, o módulo lê o catálogo local; ele não consulta a API para cada string.
- A inferência do OPUS-MT é local. O texto do jogo não é enviado a um serviço de tradução.
- O módulo consulta `DracanX/ProjetoTyria`, branch `Main`, para verificar atualizações de glossário e patch. O repositório precisa conter `glossary/glossary_pt_br.json` e `patch/pt_br/index.json` com suas partes `pNNNN.json`; enquanto esses arquivos não forem publicados, as tentativas de atualização retornarão erro e o patch/glossário local atual será mantido.
- O Text Translator é uma dependência externa do Nexus para carregar o módulo e pode se conectar aos serviços do autor. O código do módulo também depende do protocolo público do Text Translator. O projeto não baixa patch nem glossário do repositório de origem `NikeGipple/gw2-nexus-local-translator`; ele é citado apenas como referência de arquitetura.
- A preparação do modelo baixa os arquivos OPUS-MT necessários do Hugging Face.

## Compilar o projeto no Windows

1. Execute `src\prepare_opus.bat` uma vez para baixar o modelo OPUS-MT, convertê-lo para int8/CTranslate2 e preparar os tokenizadores.
2. Para habilitar o filtro por nomes da API, execute `src\sync_gw2_titles.bat` e aguarde a confirmação de conclusão.
3. Execute `build.bat`. O script compila `Tradução Brasileira.exe` e copia o modelo e, se estiver disponível, `build\gw2_titles.db` para a pasta de saída `dist\Tradução Brasileira`.
4. Copie o conteúdo da pasta de saída e `src\text_translator\pt_br\module.toml` para `addons\text_translator\modules\Tradução Brasileira`.

### Compilar o CSV Hub standalone

Execute `CSV Hub\build_review_gui.bat` para criar `dist\CSV_Hub.exe`, um único executável Windows com a interface nativa estilizada. O arquivo pode ser copiado e aberto sozinho: não requer Python, navegador, servidor local, modelo de tradução ou arquivos auxiliares ao lado do `.exe`. Durante a execução, ele apenas acessa os CSVs, bancos e patches locais escolhidos nos diálogos.

Para atualizar apenas o banco de títulos, basta executar novamente `src\sync_gw2_titles.bat` e `build.bat`. O banco é opcional: sem ele, o módulo ainda pode usar os nomes protegidos pelo glossário, mas não terá o filtro adicional da API.

Comandos equivalentes para preparar manualmente o modelo:

```text
pip install -r src\requirements.txt "transformers[torch]>=4.44,<5"
python src\prepare_opus.py
```

Prefira `src\prepare_opus.bat`, que configura as dependências e prepara os dois tokenizadores exigidos pelo módulo.

## Jogar sem travamentos: *Pause Refreshes*

Quando chegam traduções, o Text Translator pode atualizar os textos do jogo; cada atualização pode causar uma breve pausa. O pacote de idioma ativa **Pause Refreshes** por padrão:

- **Ativado:** evita pausas durante a atualização. Uma string encontrada pela primeira vez pode continuar em inglês até aparecer novamente ou até usar **Refresh Now**.
- **Desativado:** as traduções novas aparecem após a atualização, mas isso pode causar pausas. Aumentar *Refresh Debounce Time* reduz a frequência das atualizações.

## Solução de problemas

- **Nada é traduzido:** confirme que o idioma do jogo está em inglês e que o modelo foi preparado com `src\prepare_opus.bat`.
- **O log mostra `NOT_FOUND` para `source.spm`, embora o arquivo exista:** atualize o executável; versões anteriores não carregam o SentencePiece corretamente quando o caminho da instalação contém caracteres acentuados.
- **O texto novo continua em inglês:** com *Pause Refreshes* ativado, use **Refresh Now** ou aguarde o texto aparecer novamente.
- **Um título conhecido foi traduzido:** confira se `gw2_titles.db` está na pasta `PT_BR` instalada e se o título está no catálogo. Atualize-o com `src\sync_gw2_titles.bat` e gere o pacote novamente.
- **O sincronizador parece parado:** confira a linha de progresso; itens exigem centenas de requisições. Uma solicitação individual pode levar até 45 segundos antes de expirar. Se houver falha, o arquivo de catálogo anterior não é substituído.
- **O jogo pausa muitas vezes:** mantenha **Pause Refreshes** ativado.
- **Registros:** mensagens do módulo aparecem no log do Nexus com o prefixo `[Text Translator] [Tradução Brasileira]` e também em `traducao_brasileira.log`.
- **Opções avançadas:** `module.toml` aceita `--threads N` para definir as threads da CPU (padrão 2) e `--stats-every SEGUNDOS` para definir o intervalo das estatísticas (padrão 300). Preserve os demais argumentos já configurados.

## Código-fonte

O código do módulo fica em [`src/`](src):

- `module.py`: protocolo com o addon, recebimento e encaminhamento das solicitações;
- `server.py`: glossário, normalização, proteção de tags, cache, divisão de textos e motor OPUS-MT;
- `patch_db.py`: patch PT-BR, downloads incrementais e interação com o cache do addon;
- `gw2_titles.py`: sincronização da API e consulta do catálogo local de títulos;
- `src\prepare_opus.py` e `src\prepare_opus.bat`: download e conversão do modelo;
- `src\sync_gw2_titles.bat`: atualização do catálogo;
- `text_translator/pt_br/`: configuração inicial do módulo enviada no pacote.

O nome da pasta do módulo ou o argumento `--lang` em `module.toml` seleciona o código do idioma. Para este projeto, o idioma é `pt_br`.

## Créditos

- **Ideka**, autor do [Text Translator](https://github.com/ideka/text-translator-public) e do [protocolo de módulos](https://github.com/ideka/modulep).
- **Helsinki-NLP**, pelo modelo [OPUS-MT tc-big inglês→português](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-en-pt), sob licença CC-BY-4.0.
- **ArenaNet**, pelos nomes disponibilizados na [API do Guild Wars 2](https://wiki.guildwars2.com/wiki/API:Main).
- **OpenNMT**, pelo [CTranslate2](https://github.com/OpenNMT/CTranslate2).
- **Raidcore**, pelo Nexus.
- **NikeGipple** — baseado na arquitetura do [gw2-nexus-local-translator](https://github.com/NikeGipple/gw2-nexus-local-translator). A estrutura do módulo foi reutilizada; o conteúdo de patch e glossário, a filtragem de títulos e o modo de tradução são desenvolvimentos próprios.

## Aviso legal

Este é um projeto comunitário não oficial. Não é afiliado nem endossado pela ArenaNet, NCSOFT, Raidcore, Ideka ou Helsinki-NLP.

© ArenaNet LLC. Todos os direitos reservados. NCSOFT, ArenaNet, Guild Wars, Guild Wars 2, GW2, Heart of Thorns, Path of Fire, End of Dragons, Secrets of the Obscure, Janthir Wilds, Visions of Eternity e todas as marcas e logotipos associados são marcas comerciais ou marcas registradas da NCSOFT Corporation. As demais marcas pertencem aos respectivos proprietários.

## Licença

O código deste projeto é distribuído sob a [licença MIT](LICENSE). `text_translator.dll`, os modelos e os demais componentes de terceiros permanecem sujeitos aos direitos e às licenças de seus respectivos autores.
