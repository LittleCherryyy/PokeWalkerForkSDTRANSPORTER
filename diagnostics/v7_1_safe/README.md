# V7.1 — preparação técnica segura (ainda NÃO testável no DSi)

## Estado verdadeiro
A V7.0 foi inserida nos fontes do menu, mas NÃO foi compilada neste ambiente. O resolver `walker_hgss_net.c` da V18 informa `ready=1` somente pela presença de um endereço global de gateway, apesar de deixar TODAS as funções WCM/SOCL em zero. O transporte real exige essas funções e não efetua conexões quando ausentes. Portanto não existe ainda caminho funcional de PING durante HeartGold.

## Alteração realizada
O patch substitui a definição de `ready` por uma verificação conservadora de todas as entradas necessárias. Ele previne um falso positivo de disponibilidade de rede e não introduz endereços especulativos. Não modifica o menu, app Android, skins, ROM nem save. É apenas uma etapa de segurança, NÃO a V7.1 pronta.

## Aplicação opcional aos fontes V18
No PowerShell, a partir da pasta extraída:

```powershell
powershell -ExecutionPolicy Bypass -File .\aplicar_v71_preparacao.ps1 -Bootstrap "C:\Users\marcu\OneDrive\Documentos\Projetos\SD-Transporter-main DIRECT-DSI-SYNC\bootstrap"
```

O script verifica SHA256 ANTES de modificar e gera backup. Não execute com fontes que não correspondam ao snapshot V18; não retire verificação.

## Diagnóstico confirmado nos fontes
- `bootstrap/retail/common/source/walker_hgss_net.c`: `walkerResolveHgssNet` deixa `wcmInit`, `socSocket`, `socConnect`, `socRecv`, `socSend`, `socClose` e outras funções em zero.
- `bootstrap/retail/cardengine/arm9/source/walker_direct_transport.c`: `walkerDirectTransportTickArm9` sai quando `apiComplete()` é falso; mesmo quando verdadeiro, chamadas reais estão explicitamente bloqueadas para etapa futura.
- `bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c`: apenas exibe painel V7.0, sem rede.

## Critérios para uma V7.1 TESTÁVEL
1. Resolver ENDEREÇOS REAIS das APIs de rede ou implementar serviço independente compatível com interrupções ARM7/ARM9 e ambiente do jogo.
2. Conectar a `192.168.6.192:30821`, enviar PWDSI001 OP_PING e receber OP_OK DURANTE HeartGold, com timeout e sem travar o menu.
3. Compilar todos componentes com devkitARM/libnds e validar execução/retorno ao jogo; preservar cópia do bootstrap atual.

**Não instalar no SD e não afirmar que o PING funciona até cumprir esses critérios.**
