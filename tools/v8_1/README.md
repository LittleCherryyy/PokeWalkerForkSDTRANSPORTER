# V8.1 — Verificação offline do contexto de criação de threads NitroSDK

A V8.0 confirmou que HeartGold e SoulSilver USA Rev0 possuem três
destinos ARM9 estáticos de agendamento com **cinco chamadas validadas**:

| Função | Endereço ARM9 nos dois jogos |
| --- | --- |
| OS_IsThreadAvailable | 0x020D1AC4 |
| OS_CreateThread | 0x020D1AD4 |
| OS_WakeupThreadDirect | 0x020D1F34 |

Esses endereços, por si só, não demonstram que uma thread extra pode
ser criada durante a exploração normal do jogo.

## O que a V8.1 verifica

- A identidade das ROMs originais e a reconstrução ARM9 via V7.4/V8.0.
- Os hashes SHA-256 de 32 bytes de **cada entrada**, fixados com base
  no relatório real V8.0 do usuário, mais hashes de 128 bytes e
  inspeção limitada de desvios de entrada (sem copiar código de ROM).
- A sequência ARM original de preparação dos **seis argumentos**
  para `OS_CreateThread` no overlay 39:
  `thread, func, arg, stackTop, stackSize, priority`.
- O caso documentado do overlay 39 prepara **stackSize = 0x800
  (2048 bytes)**, o terceiro argumento `NULL`, prioridade **16**
  na inicialização e uma thread structure separada.
- A função inicial apontada pelo módulo 39 é um **trampoline**
  dentro do próprio overlay 39, com destino final
  `0x02229474`. Isso significa que não podemos reutilizar
  cegamente essa thread ou callback: o overlay pode descarregar.
- Se as sequências, argumentos e funções coincidem nas duas ROMs.

**Não há código de rede nem criação real de thread nesse teste.**

## Teste no Windows

1. Extraia o ZIP, preservando as pastas `v7_3`, `v7_4`,
   `v7_5`, `v7_6`, `v8_0` e `v8_1`.
2. Selecione os backups originais `HeartGold.nds` e
   `SoulSilver.nds` no Explorador de Arquivos.
3. Arraste os dois simultaneamente para
   `v8_1/COMPARAR_ABI_THREADS.bat`.
4. Envie apenas o arquivo `wifi_v81_hgss_thread_abi.json`.
5. Se surgir erro, envie a mensagem e não as ROMs.

Também é possível executar:

    python tools/v8_1/hgss_thread_abi_context.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v81_hgss_thread_abi.json

## Limites técnicos

Uma assinatura compatível não é prova de contexto vivo. A convenção
de seis argumentos no **local da chamada** é uma evidência mais forte
da interface do chamador, mas ainda não valida a estrutura interna
`OSThread`, a vida útil da pilha de uma **nova** thread, a
possibilidade de escalonamento durante o overworld, nem a interação
com as interrupções e funções de Wi-Fi do ARM7.

A V7.9 continua instalada no console; não altere SD, nds-bootstrap,
Android, ROM, .sav ou .walker nesta etapa. A integração de rede
permanece desativada até que exista um contexto independente com
controle seguro do rádio.

Código público usado como referência:
- https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s
- https://github.com/pret/pokeheartgold/blob/master/asm/overlay_13_thumb_2.s
