# V8.5 — Comparação de estruturas do escalonador NitroSDK

## O que o relatório V8.4 confirmou

O JSON original do usuário (22/11/2026) contém **101 referências
ARM em cada jogo**, com **101 referências compartilhadas** entre HG e SS,
e hashes de contexto idênticos:

| Endereço em RAM | Referências ARM por jogo |
| --- | ---: |
| `0x021E16A0` | 64 |
| `0x021E167C` | 29 |
| `0x021E16B0` | 2 |
| `0x021E1688` | 1 |
| Outros endereços | 5 |

Uma referência é uma instrução candidata `LDR`, **não** uma thread.
No DSi, a V8.3 já tinha observado o *flag* do sistema de threads
em `0x021E1688` como `0x00000001`.

A documentação pública do NitroSDK explica que `OSThreadInfo` muda
de layout entre versões do SDK. No cabeçalho
[thread.h](https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h):

| Campo | SDK com THREAD_INFINITY | Layout antigo |
| --- | ---: | ---: |
| current | +4 | +8 |
| list | +8 | +12 |
| switchCallback | +12 | +16 |

**Nenhum desses dois layouts foi confirmado para o endereço candidato.**

## O que a V8.5 verifica

O script `v8_5/hgss_thread_info_layout_audit.py` verifica as ROMs
originais USA Rev0, reconstrói o ARM9 e revalida os endereços do
relatório V8.4. Para cada `LDR Rd, =endereço` que carregar
`0x021E16A0` ou `0x021E167C`, inspeciona **somente a instrução ARM
imediatamente seguinte**.

Se essa instrução for um acesso incondicional do tipo
`LDR/STR Rx, [Rd, #deslocamento]`, registra:
- o deslocamento, como `+4`, `+8`, `+12`, `+16`;
- se é leitura ou escrita, byte ou palavra;
- o endereço de instrução em cada jogo;
- se o mesmo padrão ocorre nas duas ROMs.

O resultado é uma hipótese sintática, não uma validação de que a
referência se encontra em código executável, de que o campo é
`OSThreadInfo` ou de que uma thread está ativa. Não lê ponteiros
reais, nem executa qualquer função original.

## Testar no Windows

1. Extraia o ZIP mantendo as pastas
   `v7_3`, `v7_4`, `v7_5`, `v7_6`,
   `v8_0`, `v8_1`, `v8_2`, `v8_4`, `v8_5`.
2. Selecione os backups originais `HeartGold.nds` e
   `SoulSilver.nds` (USA Rev0).
3. Arraste ambos para
   `v8_5/COMPARAR_LAYOUT_THREADS.bat`.
4. Envie somente
   `v8_5/wifi_v85_hgss_thread_layout.json`.

Também é possível usar:

    python tools/v8_5/hgss_thread_info_layout_audit.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v85_hgss_thread_layout.json

Se houver erro, envie o texto sem compartilhar nenhuma ROM.

**Não substitua o bootstrap V8.3, não atualize o Android e não
altere o cartão SD.**

## Próxima decisão

Se o cruzamento identificar padrões de acesso consistentes a uma
`OSThreadInfo`, podemos aprofundar a verificação de seu ABI e de uma
região de memória persistente própria. Não serão criadas threads ou
feitas chamadas Wi-Fi sem prova de segurança para o escalonamento e
para o ARM7.
