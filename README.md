# Tradutor PT-BR para Guild Wars 2 (Nexus)

Módulo de tradução local de inglês para português para o addon **Text Translator**, do Nexus. O texto do jogo é processado no computador; não é enviado a serviços de tradução online.

> O modelo disponível é inglês–português (`en → pt`), não um modelo específico do Brasil (`pt-BR`). O glossário e as regras do projeto adaptam nomes e plurais, mas algumas frases podem soar como português europeu.

## Publicar esta pasta no GitHub

1. No GitHub, crie um repositório vazio (público ou privado); não é preciso configurar Git no computador.
2. Abra o repositório e escolha **Add file → Upload files**.
3. Arraste o conteúdo desta pasta, incluindo `.gitignore`, mantendo as subpastas, e confirme que `README.md`, `src`, `tests`, `tools` e `glossary` aparecem antes de enviar.
4. Escreva uma mensagem, como `Primeira versão do tradutor PT-BR`, e clique em **Commit changes**.

Os pesos do modelo e os arquivos gerados de compilação não estão nesta pasta, então não serão enviados ao GitHub.

## Compilar no Windows

Requisitos: Windows 10/11 de 64 bits, Python 3.12 de 64 bits e internet para baixar as dependências e o modelo uma única vez.

1. Baixe este repositório (ou clone-o) e abra o PowerShell na pasta do projeto.
2. Execute:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\build_ptbr.ps1
   ```

   O script instala os pacotes Python necessários, baixa o modelo English–Portuguese, verifica seu SHA-256 e compila o executável. O modelo fica em `PT_BR\model` e não é incluído no Git.
3. Copie o conteúdo de `dist\Local_Translator_PTBR\` para:

   ```text
   [Guild Wars 2]\addons\text_translator\modules\local_translator_ptbr\
   ```
4. Copie `src\text_translator\module.toml` para essa mesma pasta.
5. Copie a pasta `PT_BR\model` do projeto para `local_translator_ptbr\PT_BR\model`, mantendo a estrutura. O arquivo do modelo deve ficar em `PT_BR\model\model\model.bin`.
6. No Nexus, selecione **Tradutor PT-BR para Guild Wars 2** e mantenha o idioma do jogo em inglês.

Não substitua o `settings.toml` do addon: ele contém as preferências locais do usuário. Se o módulo não aparecer, confira o nome da pasta `local_translator_ptbr` e se `module.toml` está dentro dela.

## Testes e desenvolvimento

Instale as dependências e rode os testes:

```powershell
py -3.12 -m pip install -r src\requirements.txt
py -3.12 -m unittest discover -s tests -v
```

O modelo pode ser baixado separadamente com `py -3.12 tools\prepare_ptbr_model.py`. Para recompilar sem reinstalar dependências ou baixar o modelo novamente, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_ptbr.ps1 -SkipDependencyInstall -SkipModelDownload
```

Termos e nomes do jogo podem ser ajustados em `glossary\glossary_pt-br.json` (glossário editável) e `src\glossary_pt-br.default.json` (glossário incluído no executável). As regras de plural ficam em `src\plurale_pt_br.py`.

## Modelo e licenças

O modelo OPUS English–Portuguese é distribuído pelo pacote Argos Translate `translate-en_pt-1_9`. Os pesos não fazem parte deste repositório: o script baixa o pacote e verifica o checksum antes de instalá-lo. Consulte [MODEL_LICENSE.md](MODEL_LICENSE.md) para atribuição e licença do modelo. O código do projeto está sob a licença MIT (arquivo `LICENSE`).

## English quick start

Build on Windows with Python 3.12 by running:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_ptbr.ps1
```

Copy `dist\Local_Translator_PTBR\`, `src\text_translator\module.toml`, and the downloaded `PT_BR\model` folder into the Nexus Text Translator module directory `local_translator_ptbr`. Keep the game language set to English. The included OPUS model is tagged generic Portuguese (`pt`), so it may use some European Portuguese wording.
