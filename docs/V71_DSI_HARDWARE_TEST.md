# V7.1 — teste limitado do painel de diagnóstico no Nintendo DSi

**Este pacote NÃO transfere Pokémon por Wi-Fi.** O servidor Android, a ROM e
os arquivos de Pokémon não devem ser alterados para este teste. As funções
WCM/SOCL/SOC ainda não foram resolvidas e nenhuma conexão TCP é iniciada
pelo HGSS. Esta build é experimental e foi compilada, mas ainda não validada
em um DSi real.

## Antes do teste

1. Use exclusivamente um **save descartável de HeartGold/SoulSilver**.
   Faça cópias separadas de `.sav`, `.walker` e dos backups de transferência
   existentes. Não teste no save principal nem em um Pokéwalker com Pokémon
   que não possa perder.
2. No SD do DSi, copie o arquivo antigo
   `/_nds/nds-bootstrap-nightly.nds` para o computador como backup.
   Não altere o `nds-bootstrap-release.nds` nem sua ROM.
3. Baixe o artefato **v71-dsi-menu-diagnostic-test-only** na execução
   **Actions** do PR #4, extraia o `nds-bootstrap.nds` e confira o SHA-256
   com `nds-bootstrap.nds.sha256`. Este pacote é um artefato de teste,
   não uma release estável.
4. Faça uma cópia do arquivo extraído para
   `/_nds/nds-bootstrap-nightly.nds`. No TWiLight Menu++ selecione
   **Nightly** como versão do nds-bootstrap para o jogo. Não copie nem
   modifique arquivos adicionais nesta etapa.

## Teste 1 — inicialização

- Abra o HGSS com o save descartável.
- Confirme que o jogo chega ao menu inicial e permanece responsivo.
- Não sincronize Pokémon nem faça novos envios/retornos nesta etapa.

## Teste 2 — menu do Virtual Pokéwalker

- Abra o menu em jogo do nds-bootstrap com a combinação já configurada
  na sua instalação.
- Selecione **Virtual Pokewalker**.
- Tire uma foto da tela com os seguintes indicadores:
  - `Missing net APIs: 0x....` (máscara de 13 bits)
  - `Resolver: NOT READY`
  - `Bridge state`
  - `Write seq` e `Flushed seq`
  - `Wi-Fi: NOT ENABLED` (obrigatório mesmo que o painel tenha respondido)
- Se aparecer `Walker: not installed` ou `ARM7: no diagnostic reply`,
  registre exatamente a mensagem; não tente transferir Pokémon.
- Aperte **B**, confirme que retorna ao menu e depois ao jogo sem travar.

## Teste 3 — regressão sem transferência

- Jogue brevemente com o save descartável e abra/feche novamente o menu.
- Não use PUSH/PULL/CONFIRM, nem troque Pokémon com o Android nesta build.
- Se surgir travamento, tela branca, escrita incomum ou mensagem de erro,
  desligue o console e restaure os backups.

## Retorno/rollback

Desligue o DSi, remova o cartão SD pelo procedimento habitual e restaure
`/_nds/nds-bootstrap-nightly.nds` a partir do backup. Se necessário,
restaure também os arquivos de save descartável. Não use esta build com
seu save principal antes de uma validação em hardware.

## Critério de aprovação deste teste

- Jogo inicializa; menu V7.1 exibe a máscara de funções ausentes;
- O menu volta ao jogo sem travamentos;
- Não ocorre uma tentativa de rede nem uma operação de transferência.

**Este teste não valida Wi-Fi em HGSS, troca de Pokémon, persistência em
queda de energia ou compatibilidade com todas as regiões.** A próxima etapa
continua sendo identificar as APIs reais do HGSS e validar um PING/ACK
durante o jogo.
