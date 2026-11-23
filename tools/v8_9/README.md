# V8.9 — Acessos ARM9 a campos de 16 e 32 bits (somente offline)

## Resultados observados fisicamente no Nintendo DSi (V8.8)

| Endereço | Valor bruto |
| --- | --- |
| `0x021E169C` | `0x00000003` |
| `0x021E16A0` | `0x00000000` |
| `0x021E16A4` | `0x021E1770` |
| `0x021E16A8` | `0x021E3864` |
| `0x021E16AC` | `0x00000000` |
| `0x021E16B0` | `0x0000001F` |

Na estrutura clássica de `OSThreadInfo` do NitroSDK 2.x com base
`0x021E169C`, o valor bruto de `max_entry` seria zero e
`entry[0]` seria `0x1F` — incompatível com um ponteiro
alinhado para uma thread na RAM principal NTR.

**Isso desfavorece essa hipótese, mas não prova o endereço
verdadeiro da estrutura.** Mesmo que a disposição de quatro
palavras a partir de `0x021E16A0` pareça com o layout
`SDK_THREAD_INFINITY`, a build pública original de HGSS
utiliza NitroSDK 2.0, portanto é necessário verificar o código
compilado, inclusive as diferenças de versão do SDK.

## O que a ferramenta V8.9 faz

Esta versão complementa as análises V8.4/V8.5 com leitura estática
de instruções ARM de **16 bits de dados (LDRH / STRH)**,
além das leituras e escritas de 32 e 8 bits já interpretadas.

Uma instrução só entra no relatório quando:

- a ROM original USA Rev0 passa por todos os verificadores
  anteriores (SHA-1, ARM9, chamadas e assinaturas);
- uma instrução `LDR Rd, [PC, #imediato]` incondicional
  aponta exatamente para um literal válido;
- o literal vale um dos endereços candidatos examinados;
- a instrução imediatamente seguinte é um acesso
  `LDRH / STRH / LDR / STR / LDRB / STRB` compatível
  com aquele mesmo registrador, com offset imediato e sem writeback.

O relatório registra **endereços e metadados**, nunca bytes de
código de ROM. O endereço efetivo é **calculado**, não lido:
nenhum ponteiro apontado pela ROM é seguido. O analisador não
pode comprovar que a sequência pertence a código executável,
nem identificar sozinho `OSThreadInfo`. Portanto, os resultados
continuam rotulados como candidatos.

As duas ROMs são comparadas automaticamente.

## Teste no Windows

1. Extraia o ZIP do GitHub Actions, preservando as pastas
   `v7_3`, `v7_4`, `v7_5`, `v7_6`, `v8_0`,
   `v8_1`, `v8_2`, `v8_4`, `v8_5`, `v8_9`.
2. Selecione os backups originais USA Rev0
   `HeartGold.nds` e `SoulSilver.nds`.
3. Arraste ambos para
   `v8_9/COMPARAR_CAMPOS_THREADS.bat`.
4. Envie somente
   `v8_9/wifi_v89_hgss_thread_field_xrefs.json`.

Alternativamente:

    python tools/v8_9/hgss_scheduler_field_xrefs.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v89_hgss_thread_field_xrefs.json

Não altere a V8.8 já instalada no DSi. O Android e o hotspot não
são necessários para esta etapa. Nenhuma ROM, `.sav`, `.walker`
ou imagem de Pokéwalker é modificada ou exportada.

## Próximo marco

Os acessos de `u16` poderão esclarecer se
`0x021E169C`, `0x021E16A0` e `0x021E16B0`
são variáveis distintas ou componentes de uma estrutura comum.
Mesmo com padrões compatíveis, será necessário comprovar o ABI do
jogo e reservar memória persistente, protegida e própria para uma
nova thread em contexto **não IRQ**.

Controle ARM7 do rádio e PING no hotspot Android continuam
desativados.

Referências públicas:
- https://github.com/pret/pokeheartgold/blob/master/meson.build
- https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h
