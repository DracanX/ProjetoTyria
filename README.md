# Tradutor PT-BR para Guild Wars 2 (Nexus)

Este é um módulo de tradução para o Text Translator, o addon do Nexus criado por Ideka que traduz o Guild Wars 2 em tempo real à medida que joga. Inspirado no trabalho feito para francês por NikeGipple.

Este módulo traz o jogo para português

> **Idioma do modelo:** o modelo disponível é inglês–português (`en → pt`), não específico do Brasil (`pt-BR`). O glossário e as regras de plural ajudam na localização, mas algumas frases podem soar como português europeu.

## Ajustes de desempenho desta versão

Esta cópia experimental usa lotes de até **24 linhas** e **até 4 threads de CPU** por padrão, limitado ao número de CPUs disponíveis. `--threads N` em `module.toml` continua permitindo ajustar manualmente. O módulo roda em prioridade abaixo do normal no Windows para dar precedência ao jogo.

Para limitar o uso de CPU, acrescente `--threads 2` à linha `args` de `module.toml`, por exemplo:

```toml
args = ["--no-update", "--threads", "2"]
```

### Cache de traduções

As traduções são reutilizadas por dois caches: `cache_ptbr_local.jsonl` dentro da pasta `PT_BR` do módulo e o banco `cache.db` gerenciado pelo Text Translator na pasta do módulo. Preserve esses arquivos ao atualizar o executável; removê-los faz com que textos já vistos possam precisar ser processados novamente.

As traduções já disponíveis no cache são enviadas sem aguardar o worker do modelo. O despacho também limita a quantidade de solicitações processadas em cada ciclo para que um fluxo contínuo de textos não adie respostas prontas; os textos sem cache continuam na fila normal do modelo.

Quando há fila de traduções novas, linhas solicitadas mais recentemente entram primeiro nos lotes para reduzir o atraso de textos que acabaram de aparecer (por exemplo, legendas). Para não deixar textos antigos parados, cada lote cheio também processa a linha mais antiga da fila. O protocolo não identifica se um texto veio de NPC, então a prioridade é por recência, não por categoria. A resposta mais rápida pode ajudar a legenda atual, mas o módulo não consegue obrigar o addon Nexus a redesenhar texto que ele já exibiu.

## Compilar no Windows

Requisitos: Windows 10/11 de 64 bits, Python 3.12 de 64 bits e conexão à internet para baixar dependências e o modelo.

1. Abra o PowerShell na pasta do projeto.
2. Execute o script para instalar as dependências, baixar/verificar o modelo e compilar:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\build_ptbr.ps1
   ```

   Os arquivos intermediários ficam numa pasta temporária e são removidos ao final. O modelo também é guardado dentro de `nexus_build`; assim, o único resultado da compilação é a pasta pronta do módulo, sem uma pasta `PT_BR` separada ao lado dela.
3. Copie o conteúdo dessa pasta para:

   ```text
   [Guild Wars 2]\addons\text_translator\modules\local_translator_ptbr_perf\
   ```

   A pasta preparada já inclui o executável, `_internal`, `module.toml` e `PT_BR\model`. Ela não inclui nem substitui os caches e bancos locais do jogo.
4. Preserve os caches e bancos locais existentes no módulo. O arquivo de pesos deve ficar em `PT_BR\model\model\model.bin`.
5. Reinicie o Nexus/Guild Wars 2 e, nas opções do Text Translator, selecione **Tradutor PT-BR para Guild Wars 2 (Desempenho)**. Mantenha o idioma do jogo em inglês.

Para recompilar sem instalar dependências nem baixar novamente o modelo:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_ptbr.ps1 -SkipDependencyInstall -SkipModelDownload
```

## Personalização

Edite `glossary\glossary_pt-br.json` para ajustar termos do jogo; `src\glossary_pt-br.default.json` é o glossário incluído no executável. As regras de plural ficam em `src\plurale_pt_br.py`.