# Pokéwalker Virtual V8.0 — verificação de threads NitroSDK HGSS

## Por que esta etapa existe

Na V7.9, as fotos do DSi comprovaram que uma solicitação curta
passou de estado `00` para `02` depois de um callback normal de leitura
da ROM. As leituras elegíveis continuaram aumentando, inclusive na Rota 35.

Isso **não** equivale à criação de uma tarefa independente. O callback
`cardRead()` é essencial para carregar dados do jogo: nenhuma
inicialização de Wi-Fi, conexão de socket, espera de rede ou tarefa de
duração indefinida pode ser colocada ali sem provar ausência de bloqueio.

O código original de HeartGold e SoulSilver possui funções NitroSDK
de escalonamento já utilizadas em seus overlays de comunicação.
O objetivo da V8.0 é verificar **offline** os destinos das chamadas
`OS_IsThreadAvailable`, `OS_CreateThread` e `OS_WakeupThreadDirect`,
antes de escrever qualquer código que as invoque.

Os cinco pontos de chamada foram derivados da desmontagem pública:
- [pret/pokeheartgold / overlay_13_thumb_2.s](https://github.com/pret/pokeheartgold/blob/master/asm/overlay_13_thumb_2.s)
- [pret/pokeheartgold / overlay_39_arm.s](https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s)

A ferramenta valida os bytes do código original americano (revisão 0)
com SHA-1, reusa as verificações V7.4/V7.5, reconstrói o ARM9 em
memória e verifica as instruções dos cinco callsites. O JSON contém
somente endereços, modo ARM/Thumb, região e hashes SHA-256 de janelas
de 32 bytes; não contém código de ROM.

## Testar no Windows

1. Extraia o pacote ZIP do GitHub Actions mantendo juntas as pastas
   `v7_3`, `v7_4`, `v7_5` e `v8_0`.
2. Selecione suas ROMs originais `HeartGold.nds` e
   `SoulSilver.nds` no Windows Explorer.
3. Arraste os **dois arquivos** sobre `v8_0/COMPARAR_THREADS_HGSS.bat`.
4. Envie apenas `v8_0/wifi_v80_hgss_threads.json` para análise.
5. Em caso de falha, envie o texto do erro sem compartilhar a ROM.

Alternativa:

    python tools/v8_0/hgss_thread_callsite_audit.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v80_hgss_threads.json

**Nenhuma alteração no cartão SD, nds-bootstrap, Android ou saves.**

## Limitações do resultado

- Um endereço de função estática não garante que sua convenção de chamada
  foi validada ou que existe um agendador independente ativo.
- Um overlay pode não estar carregado no mapa normal do HeartGold.
- Mesmo que os endereços sejam idênticos entre HG e SS, não está
  autorizado chamar os APIs, instalar handlers, alocar uma OSThread
  ou inicializar o WM/rádio ARM7.
- A criação de threads exige um contexto válido, pilha própria,
  prioridades, alinhamento e coordenação com a lógica NitroSDK do jogo.
- A primeira comunicação real permanecerá um PING limitado e sem saves,
  **depois** de provar propriedade do rádio e contexto independente.

Esta ferramenta é uma etapa de investigação reproduzível, não um patch de
jogo nem um recurso de rede funcional.
