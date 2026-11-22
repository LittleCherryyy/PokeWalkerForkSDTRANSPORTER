# V7.1.3 — teste limitado do painel de diagnóstico no Nintendo DSi

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
3. Baixe o artefato **v71-3-dsi-boot-hook-status-diagnostic-test-only** na execução
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
  - `Missing net APIs: 0x....` (máscara de 13 bits, se o hook estiver válido)
  - `Resolver: NOT READY`
  - `Bridge state`
  - `Write seq` e `Flushed seq`
  - `Wi-Fi: NOT ENABLED` (obrigatório mesmo que o painel tenha respondido)
- Se aparecer `Walker: hook not published`, `Walker: RAM addr rejected`,
  `Walker: invalid header` ou `ARM7: no diagnostic reply`,
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

## Correção V7.1.1 — falso negativo de RAM estendida

A primeira execução física da V7.1 mostrou `Walker: not installed`
mesmo com a opção Virtual Pokéwalker ativada. A validação anterior do
painel aceitava apenas `0x02000000–0x023FFFFF`, embora o carregador NTR do
DSi possa reservar o controle do Walker na RAM estendida,
por exemplo `0x0CFDC000`. Na V7.1.1 o diagnóstico também aceita a janela
`0x0C000000–0x0CFFFFFF`, com alinhamento e limite de tamanho.

O novo painel diferencia três situações se o Walker ainda não for validado:
`hook not published` (nenhum ponteiro publicado pelo carregador),
`RAM addr rejected` (ponteiro fora das janelas suportadas) ou
`invalid header` (memória endereçável com assinatura/versão inesperada).
Isso não comprova que a sincronização esteja disponível; o transporte Wi-Fi
continua desativado. Se o hook não for publicado, inspecione no SD
`/_nds/nds-bootstrap/pokewalker-error.txt` e confirme a presença do
arquivo `.walker` correspondente ao save de teste.

## Resultado real da V7.1.1 e correção V7.1.2

O segundo teste físico mostrou o HeartGold inicializando e o menu
`VIRTUAL POKEWALKER V7.1.1` exibindo **ARM7: no diagnostic reply**.
Diferentemente da V7.1, o processador ARM9 não recebeu sequer o ACK;
não é possível concluir se o hook foi instalado.

Uma hipótese fundamentada na diferença de código é que a V7.1.1 passou
a desreferenciar `0x0Cxxxxxx` (espelho da RAM estendida DSi) do contexto
ARM7 sem comprovar o mapeamento naquele modo de execução. Esse acesso
poderia impedir a resposta do menu. Não é prova definitiva da causa.

A V7.1.2 retorna ao comportamento *fail-closed*: quando o ponteiro está na
janela estendida, o ARM7 responde apenas o status
`Walker: DSi RAM unprobed` e o endereço `Walker ptr: 0x........`,
**sem ler o conteúdo da RAM estendida**. Se o comando não for respondido,
o painel mostra também `Last IPC: 0x........`, para orientar o próximo
diagnóstico. Todos os testes continuam somente leitura; nenhuma operação
de Wi-Fi do HGSS é realizada.

**Teste restrito**: no save descartável, abrir o jogo, mostrar o painel
V7.1.2, fotografar todas as mensagens e pressionar B para retornar ao
jogo. Não testar PUSH/PULL nem usar saves principais. Mantenha a cópia
de `/_nds/nds-bootstrap-nightly.nds` anterior para recuperação.

## Foto real V7.1.2 e novo diagnóstico V7.1.3

O DSi confirmou `VIRTUAL POKEWALKER V7.1.2`, `Walker: hook not published`
e `Wi-Fi: NOT ENABLED`, ao lado do menu original do jogo. O painel
recebeu a resposta do ARM7; agora o problema está *antes* da publicação
do ponteiro do Walker. A presença do comando de menu
`Connect to Pokéwalker` no HGSS não prova que o hook foi instalado.

A V7.1.3 cria um campo **append-only** `walkerBootStatus` no cabeçalho
compartilhado do cardengine ARM7 e registra a primeira causa de falha
observada no procedimento de instalação. Os códigos são:

| Código hexadecimal | Significado |
| --- | --- |
| 00 | `walkerBoot()` não foi chamado |
| 01 | Arquivo/cluster `.walker` não selecionado |
| 02 | Memória para o Walker não reservada |
| 03 | Falta seleção e falta memória |
| 10 | Assinatura da rotina IR de leitura não encontrada/ambígua |
| 11 | Assinatura da rotina IR de escrita ausente ou stub sem espaço |
| 12 | Assinatura da rotina de status do chip IR ausente |
| 13 | Assinatura da inicialização IR ausente |
| 14 | Falha ao ler os 64 KiB da EEPROM virtual |
| FF | O carregador publicou o hook, mas o painel não recebeu o endereço |

Na tela, `Boot stage: 0x..` e um texto curto aparecem apenas quando o
Walker não está validado. Não tente usar o código como evidência de Wi-Fi
ou transferência. Continue apenas com o save descartável e o backup do
`nds-bootstrap-nightly.nds`; caso não seja `FF`, o código aponta qual
subetapa investigar.

Como verificação adicional no SD, procure
`/_nds/nds-bootstrap/pokewalker-error.txt`. Algumas opções que impedem
a seleção do Walker retornam silenciosamente; por exemplo, no atual
caminho NTR do DSi o código `walkerWanted()` exige ROM no SD, não
iniciada diretamente de um flashcart/R4. A opção **On** no menu não é,
por si só, evidência de uma sessão pronta.
