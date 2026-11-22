# V7.1.5 — teste limitado do painel de diagnóstico no Nintendo DSi

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
3. Baixe o artefato **v71-5-dsi-prelaunch-logging-test-only** na execução
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

## Foto física V7.1.3 e correção do protocolo IPC V7.1.4

A foto V7.1.3 confirma `ARM7: no diagnostic reply`, com o último
valor IPC `0x554E454D` (comando `MENU`). O HGSS continua operando,
mas o diagnóstico ainda não informa o estágio de instalação.

**Causa plausível no código:** a versão V7.1.3 enviava `WPDG` uma vez,
e encerrava a consulta ao ver qualquer valor diferente de `WPDG`,
inclusive `MENU`. O loop do ARM7 escreve `MENU` para confirmar
comandos processados; há uma janela em que uma consulta emitida
pelo ARM9 pode ser apagada antes de ser reconhecida. A imagem, sozinha,
não comprova qual linha descartou o comando.

A V7.1.4 muda SOMENTE o mecanismo de diagnóstico:
- ARM9 reenvia `WPDG` caso a caixa de mensagens volte ao estado ocioso
  `MENU`, num máximo de 90 quadros. Não reenvia se houver outro serviço.
- ARM7 guarda o comando que despachou naquele quadro e não substitui um
  comando novo recebido depois do despacho.
- A resposta `WPDK` continua preservada até ser reconhecida pelo ARM9.
- O painel mantém os códigos de falha de instalação introduzidos na
  V7.1.3, permitindo investigar a ausência de `walkerControl`.

O teste no DSi deve mostrar `VIRTUAL POKEWALKER V7.1.4` e, idealmente,
`Boot stage` ou o estado do hook. Faça backup do Nightly e use apenas
save descartável; não testar Wi-Fi nem envio/recebimento de Pokémon.

## Foto física V7.1.4: Boot stage 0x03 — arquivo não selecionado, RAM não reservada

A foto do DSi confirma que o IPC ARM7/ARM9 funciona com o retry:
`VIRTUAL POKEWALKER V7.1.4`, `Walker: hook not published`,
`Boot stage: 0x03`, `No file + no RAM area`.

**Interpretação importante:** 0x03 não prova duas falhas independentes.
`walkerBoot()` registra os bits `!walkerCluster` e `!walkerBase`.
Em `bootloaderi/source/arm7/hook_arm9.c`, a reserva de RAM só acontece
se `walkerWanted()` for verdadeiro, e esse predicado já exige
`walkerCluster != 0`. Portanto, um arquivo não selecionado normalmente
impede também a reserva de RAM. Deve-se investigar **primeiro por que
`walkerPrepare()` deixou `conf->walkerCluster == 0`**, não os padrões de IR.

A preparação do NTR DSi exige: ROM e save no filesystem do SD do próprio
DSi; título HGSS (`IPK`/`IPG`); opção `VIRTUAL_WALKER=1` na seção
correspondente ao hash do caminho da ROM em
`sd:/_nds/nds-bootstrap/pokewalker.ini`; `savPath` configurado;
nenhum `.walker.lease`; `.walker` com 65.536 bytes no mesmo diretório
do save (nome derivado do save); e snapshot pré-lançamento bem-sucedido.
Se o arquivo não existir, o launcher normalmente tenta criá-lo com 0xFF.

**Exclusão explícita importante:** `walkerPrepare()` retorna sem
selecionar Walker em um DSi NTR quando a ROM é iniciada de um
flashcart/R4 (`gameOnFlashcard && dsiFeatures() && !b4dsMode`).
O predicado `walkerWanted()` também exige `!gameOnFlashcard`.
A opção visual "On" em um menu aberto para uma ROM de
`fat:/` pode estar salva em `fat:/_nds/nds-bootstrap/pokewalker.ini`,
mas isso não torna o caminho suportado. Teste com ROM e save de teste
copiados ao cartão SD **interno do DSi**, carregados pelo TWiLight Menu++
desse cartão, não diretamente pelo R4. Faça backups antes de qualquer
movimentação e não use o save principal.

### Verificação sem recompilar
1. Na lista de jogos do TWiLight Menu++ no cartão SD do DSi, escolha o
   arquivo HGSS em `sd:/roms/nds/` (ou outra pasta do mesmo SD).
2. Nas opções da ROM, alterne Virtual Pokéwalker Off e On novamente para
   regravar a chave baseada no caminho atual. Evite criar seções de hash
   manualmente.
3. Abra o jogo com save descartável, volte ao painel V7.1.4 e veja se
   o código deixa de ser `0x03`. Não tente transferir Pokémon.
4. Confira o diretório real do arquivo `.sav` (com frequência
   `sd:/roms/nds/saves/`) para encontrar o `.walker` correspondente
   com tamanho de 65.536 bytes.
5. Se houver `sd:/_nds/nds-bootstrap/pokewalker-error.txt`, leia
   o motivo e confira a data de modificação. Parte dos retornos iniciais
   não produz log, portanto ausência do arquivo não comprova sucesso.

A arquitetura continua sem ROM patch e sem Wi-Fi residente funcional.
O próximo teste depende da preparação do `.walker` pelo launcher, não
de uma nova compilação do nds-bootstrap.

## Nova foto da V7.1.4 e diagnóstico de pré-lançamento V7.1.5

A foto mais recente ainda mostra `Boot stage: 0x03` e
`No file + no RAM area`, mesmo após a indicação para lançar a
ROM diretamente do SD. Ela **não confirma por si só** onde estão
os arquivos nem qual condição de seleção foi recusada.

`walkerBase` depende de `walkerWanted()`, que por sua vez depende
de `walkerCluster`. Assim, a ausência da seleção do arquivo pode
explicar ambos os bits. A etapa a examinar é `walkerPrepare()`
no launcher ARM9, antes de executar o jogo.

Até a V7.1.4, os retornos por opção não habilitada, ROM/save
em dispositivos diferentes e ROM no flashcart do DSi podiam
acontecer **sem criar um arquivo de erro**. Na V7.1.5,
esses motivos passam a ser registrados para HGSS no
`pokewalker-error.txt`, com o caminho do jogo, caminho do save,
arquivo INI efetivamente consultado, seção SHA-1 esperada e
indicadores de flashcart/B4DS. Não altera a seleção, não pula
bloqueios, não cria transporte Wi-Fi. Na preparação bem-sucedida,
o fluxo existente continua removendo o log antigo.

Quando a V7.1.5 estiver compilada e disponível, teste com save
descartável e confira imediatamente após o lançamento:

- Para ROM no **SD do DSi**: `sd:/_nds/nds-bootstrap/pokewalker-error.txt`
- Para ROM no **flashcart/R4**: `fat:/_nds/nds-bootstrap/pokewalker-error.txt`
- No menu: `VIRTUAL POKEWALKER V7.1.5`, `Boot stage` e
  `Check Walker error log` se a seleção continuar faltando.

O arquivo de erro é diagnóstico; pode conter o caminho da ROM
e do save, mas **não contém o conteúdo do save nem da ROM**.
É mais informativo do que continuar trocando builds sem
ver o motivo recusado. Se o arquivo não existir, verificar
se o launcher customizado está sendo executado e qual SD
ou flashcart foi de fato utilizado.

O fluxo de testes continua com backup, save descartável
e **sem sincronização com o aplicativo Android**.

## Evidência física posterior: WalkerControl publicado após devolução do telefone

Uma foto fornecida pelo usuário após devolver o Walker de teste ao DSi
mostra o painel **V7.1.5** com:
- `Walker: DSi RAM unprobed`
- `Walker ptr: 0x0CFDC000`
- `Wi-Fi: NOT ENABLED`

Isso substitui o erro anterior `Boot stage: 0x03`: o carregador agora
publica um ponteiro de controle. Em
`bootloaderi/source/arm7/walker_boot.c`, `ce7->walkerControl` é
preenchido **somente depois** que os patches em memória das funções de IR
foram escritos, e logo antes de marcar
`WALKER_BOOT_INSTALLED`. Logo, a evidência apoia fortemente que o hook
foi instalado pelo carregador. **Não comprova** que o HGSS tenha
executado o stub, que a EEPROM tenha respondido ou que um Pokémon tenha
sido transferido com sucesso. O menu ARM7 deliberadamente não lê a
estrutura na janela estendida DSi `0x0C...`, por segurança.

O desaparecimento do bloqueio de preparação após a devolução do Walker
é consistente com a liberação do `.walker.lease`; a foto isolada não
prova qual operação específica limpou o bloqueio.

### Próximo teste físico, sem nova build e com save descartável
- Backup de `.sav` e `.walker`; conferir que o console não está
  segurando uma sessão externa de sincronização.
- Sair do menu do nds-bootstrap e abrir
  `CONNECT TO POKéWALKER` no menu original do HGSS.
- Na tela de busca/conexão original do jogo, **pressionar SELECT uma vez**,
  sem segurar e **sem pressionar LEFT**. O código do emulador usa SELECT
  como botão de ativação do Walker. Segurar SELECT+LEFT por cerca de
  dois segundos nessa tela **reinicializa o Walker** e não deve fazer
  parte de um teste normal.
- Registrar apenas se o jogo reconhece a conexão e quais mensagens
  aparecem. Não iniciar uma transferência com Pokémon/saves importantes.
- Depois da tentativa, deixar o jogo salvar/concluir o estado antes
  de desligar. Se falhar, registrar tela e `pokewalker-error.txt`,
  sem apagar arquivos manualmente.

O Wi-Fi residente nds-bootstrap → Android TCP 30821 **ainda não foi
implementado**. A conexão IR virtual local, mesmo que funcione,
não comprova transporte para o celular.

## Video test 2026-11-22 — original HGSS virtual IR send succeeds after retry

The user supplied a ~46-second real-DSi video of the existing V7.1.5
experimental nds-bootstrap on HeartGold. Observed directly:

1. In the game's Pokéwalker workflow the player selects **Rocky**, a male
   **Onix Lv. 5**, chooses a stroll course (Refreshing Field is visible),
   and enters the Nintendo DS-to-Pokéwalker connection screen.
2. A first connection attempt reports **"Connection was disrupted. Please
   try your connection again."**
3. The connection is retried within the game. A later frame displays
   **"Rocky went to the Pokéwalker!"**

This is concrete hardware evidence that the original HGSS game executed
the hooked Pokéwalker exchange sufficiently far to report successful
sending on the retry. It advances the project beyond mere publication of
`WalkerControl` at `0x0CFDC000`.

**Not verified by this video:** durable write of the 64 KiB `.walker`
EEPROM on SD, companion reading correct Pokémon data, subsequent return
to HGSS, integrity under interrupted power, Android TCP 30821 or resident
HGSS Wi-Fi. An initial communication interruption was observed: success
on retry should not be described as first-attempt reliability.

### Safe next verification (no new build)
- Let HGSS finish its save/connection sequence before exiting or removing SD.
- Back up the save and all .walker-related files before examining them.
- Close HGSS and open the Walker in the existing DSi companion **without
  transferring it to the phone**, to inspect whether Rocky appears as the
  current partner; use a disposable test save only.
- If the partner appears, test the game's ordinary *return from stroll*
  with the same test save (after backup); confirm HGSS receives Rocky and
  that the game save finishes. If any error appears, retain the files/logs.
- Do not manually delete `.walker`, `.lease` or `.phone` artifacts.
- The nds-bootstrap-resident Wi-Fi bridge to Android remains unavailable.
