# V9.0 — janelas semânticas ARM9 em HeartGold / SoulSilver

## Resultado da V8.9 fornecido pelo usuário

O relatório das duas ROMs originais USA Rev0 apresentou:

- **101** referências estáticas candidatas por jogo;
- **38 acessos diretos** identificados em cada ROM;
- **38/38 coincidências** entre HeartGold (IPKE) e SoulSilver (IPGE);
- **1 novo acesso de 16 bits**, um `LDRH` em `0x0211190C`,
  lendo `0x021E16A0` por meio do literal em `0x02111A08`;
- os demais 37 acessos correspondem aos anteriores de 32 bits;
- a ferramenta ainda não demonstrou código executável ou a estrutura
  verdadeira do escalonador.

Os campos lidos no DSi pela V8.8 foram:
`169C=00000003`, `16A0=00000000`,
`16A4=021E1770`, `16A8=021E3864`,
`16AC=00000000`, `16B0=0000001F`.

A interpretação do layout fixo antigo `OSThreadInfo`
com início em `0x021E169C` é desfavorecida, pois o hipotético
`max_entry` seria zero e o hipotético `entry[0]` seria `0x1F`,
que não é um ponteiro alinhado. O layout real permanece **não provado**.

## O que muda na V9.0

A V8.9 olhava apenas para a **instrução imediatamente seguinte**
ao carregamento de um endereço literal. Esta ferramenta observa
até **sete instruções adicionais** em oito pontos de interesse:

- `0x02111908` — cabeçalho/controle de 16 bits;
- `0x020D16C0` — acesso à palavra `0x021E169C`;
- `0x020D18A0`, `0x020D2030`, `0x020D20D0` — escritas em `0x021E16A8`;
- `0x020D1F5C` — leitura de `0x021E16A8`;
- `0x020A6878` — leitura de `0x021E16A4`;
- `0x020D21D0` — leitura de `0x021E16AC`.

Os endereços são validados contra a imagem ARM9 original, e as
assinaturas necessárias do jogo são verificadas novamente.

O pequeno rastreador reconhece somente algumas operações ARM
incondicionais e simples: LDR/STR/LDRH/STRH, MOV sem shift,
ADD/SUB imediatos e CMP/TST. Interrompe no primeiro desvio,
instrução condicional, escrita no PC ou instrução desconhecida.
O relatório registra operações e endereços calculados, **sem**
exportar bytes de ROM nem executar instruções.

**Limitações:** é apenas leitura estática. Dados da ROM podem
parecer instruções, e uma janela linear não prova que a CPU
percorre esse código. Não são abertas listas ou objetos de
threads e nenhuma estrutura é considerada segura para criar
uma thread por conta própria.

## Como executar no Windows

1. Extraia o ZIP preservando a estrutura das pastas de `tools`.
2. Separe seus backups originais USA Rev0
   `HeartGold.nds` e `SoulSilver.nds`.
3. Arraste ambos simultaneamente para:
   `v9_0/COMPARAR_JANELAS_ARM9.bat`.
4. Envie somente `v9_0/wifi_v90_hgss_scheduler_windows.json`.

Também é possível executar:

    python tools/v9_0/hgss_arm9_thread_trace_windows.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v90_hgss_scheduler_windows.json

A ferramenta exige Python 3, não instala bibliotecas novas e
não modifica ROMs nem os arquivos `.sav` e `.walker`.

**Não atualize o bootstrap V8.8, não altere o Android e não use
o hotspot neste teste.** Nenhuma API do NitroSDK, de Wi-Fi ou
de threads será chamada.

O próximo resultado orientará a revisão das rotinas ARM9 antes
de tentar reservar memória persistente para um serviço separado.
