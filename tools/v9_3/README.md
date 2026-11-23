# V9.3 — descobrir a origem dos endereços de leitura ARM9

## O que o relatório V9.2 confirmou

Os backups originais USA Rev0 de HeartGold (IPKE) e SoulSilver
(IPGE) apresentaram a mesma proveniência sintática para quatro
escritas ARM9:

| Escrita | Valor escrito por | Última instrução de leitura identificada |
| --- | --- | --- |
| `0x020D18A4` → `0x021E16A8` | `r1` | `0x020D189C`: `LDR r1,[r0]` |
| `0x020D2034` → `0x021E16A8` | `r1` | `0x020D202C`: `LDR r1,[r8]` |
| `0x020D20D4` → `0x021E16A8` | `r1` | `0x020D20CC`: `LDR r1,[r7]` |
| `0x020D21D8` → `0x021E16AC` | `r5` | Não resolvida devido ao desvio em `0x020D21CC` |

A origem do registrador `r1` em cada uma das três escritas é
uma leitura de memória de 32 bits, **não** uma constante direta.
Mas os endereços de memória usados por `r0`, `r8` e `r7`
ainda são desconhecidos.

A quarta escrita é mantida como **não resolvida**. Não se cruza
o desvio em `0x020D21CC` nem se presume que o valor de
`r5` veio de qualquer instrução anterior.

## O que faz a V9.3

Nas três leituras originais, localiza a origem do registrador
**que contém o endereço da leitura** (não o registrador
que recebe o valor lido). Examina até 16 instruções anteriores
a cada uma delas, sem seguir desvios de execução.

A ferramenta valida novamente as duas ROMs originais,
o SHA-1, o SHA-256 do ARM9 descomprimido, as assinaturas do
NitroSDK e a cadeia de verificadores V7–V9.2. Reconhece
somente instruções ARM incondicionais com efeitos simples
e desconhecidos que são explicitamente interrompidos.

**Detalhe importante:** no primeiro caso, o registrador
`r0` usado pela leitura de `0x020D189C` é posteriormente
sobrescrito pela instrução `LDR r0, =0x021E167C` que
prepara o destino da escrita em `0x020D18A4`. Portanto,
a V9.3 informa explicitamente se o registrador foi
sobrescrito **depois** da leitura, para não atribuir
erroneamente o endereço do destino ao endereço da fonte.

Se uma origem for um literal de endereço estático na ROM,
o relatório pode informar o endereço calculado sem ler o
seu conteúdo. Quando a origem é outro carregamento
da RAM, o endereço e o valor dinâmicos permanecem
desconhecidos. **Nenhum ponteiro é seguido.**

Um produtor sintático de registrador não prova uma rota real
de execução, o nome de uma estrutura ou a presença de uma
thread executável. Os relatórios nunca ativam o Wi-Fi.

## Testar no Windows

1. Extraia o pacote mantendo os subdiretórios `tools/` dos
   analisadores anteriores e o novo `tools/v9_3`.
2. Selecione seus backups originais USA Rev0
   `HeartGold.nds` e `SoulSilver.nds`.
3. Arraste os dois arquivos para:
   `v9_3/COMPARAR_BASES_LEITURAS_ARM9.bat`.
4. Envie somente o arquivo
   `v9_3/wifi_v93_hgss_source_load_base_origins.json`.

Alternativamente:

    python tools/v9_3/hgss_store_address_register_origins.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v93_hgss_source_load_base_origins.json

Não há alteração no DSi, no nds-bootstrap V8.8, no Android
nem no hotspot. Não compartilhe ROMs ou saves.

## Próxima decisão

O JSON permitirá ver se os registros de fonte `r0`, `r8`
e `r7` têm valores que vieram de argumentos de função,
constantes estáticas de RAM ou outras leituras da memória.
A análise permanece não conclusiva para saltos e
instruções ambíguas.

Para a comunicação direta DSi ↔ Android ainda faltam
provas sobre a identidade real de `OSi_ThreadInfo`, sua ABI,
a memória independente de um worker, o contexto não-IRQ
e a posse do rádio/IRQ pelo ARM7 do bootstrap.
