# V9.1 — origem dos valores nos registradores ARM9

## Resultado confirmado do relatório V9.0

As oito janelas de instrução examinadas nos backups originais
USA Rev0 de HeartGold/SoulSilver apresentaram o mesmo comportamento
estático nos dois jogos, incluindo hashes coincidentes.

- `0x021E169C`: `LDR`, `ADD #1`, `STR` no mesmo endereço.
  É uma hipótese de **contador**, ainda não uma prova.
- `0x021E16A0`: `LDRH`, `CMP #0`, instrução condicional.
  É uma hipótese de **campo de controle**.
- `0x021E16A8`: três sequências usam `STR`, outra usa
  `LDR`. Ainda não sabemos a origem de todos os valores gravados.
- `0x021E16AC`: leitura seguida de escrita no mesmo endereço,
  porém sem comprovação do valor que foi escrito.
- `0x021E16A4`: um dos candidatos a ponteiro de thread atual,
  mas sem comprovação da estrutura real.

O relatório V9.0 não confirma que esses trechos são executáveis
nem que a estrutura corresponde ao `OSThreadInfo` do NitroSDK.

## O que esta versão acrescenta

Analisa as mesmas oito janelas de até oito instruções ARM
reconstruídas a partir de ROMs originais, mas passa a acompanhar
a **proveniência dos dados** em registradores:

- qual endereço literal foi usado para um acesso de memória;
- qual registrador recebeu um valor desconhecido daquela posição;
- se o valor foi copiado com `MOV` ou transformado com
  `ADD/SUB` imediatos;
- se uma escrita posterior recebeu valor lido da **mesma
  posição**, inclusive uma sequência de read-modify-write;
- se um `CMP` imediato compara com zero um valor lido;
- em que instrução a análise para por condição, desvio ou
  comando ARM não suportado.

A ferramenta **não lê dados da RAM do console**. Os valores
carregados são apenas rótulos abstratos do tipo
`valor_lido_em_0x021E169C`, e nunca são usados como endereço
para seguir um ponteiro.

Não exporta bytes originais das ROMs ou disassembly.
Os resultados são **hipóteses estáticas**; não provam
execução real nem autorizam alterar threads ou Wi-Fi.

## Testar no Windows

1. Extraia o ZIP do GitHub Actions preservando as pastas
   `v7_3`, `v7_4`, `v7_5`, `v7_6`, `v8_0`,
   `v8_1`, `v8_2`, `v8_4`, `v8_5`,
   `v8_9`, `v9_0` e `v9_1`.
2. Selecione seus backups originais `HeartGold.nds` e
   `SoulSilver.nds`, USA Rev0.
3. Arraste os dois para
   `v9_1/COMPARAR_ORIGEM_REGISTRADORES.bat`.
4. Compartilhe somente
   `v9_1/wifi_v91_hgss_register_provenance.json`.

Também pode executar:

    python tools/v9_1/hgss_register_provenance.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v91_hgss_register_provenance.json

O programa rejeita nomes de saída terminados em
`.nds`, `.sav`, `.dsv` e `.walker`.

**Não precisa modificar o DSi, o bootstrap V8.8 nem o
aplicativo Android.** Hotspot, Wi-Fi, save e transferência do
Pokéwalker permanecem fora deste teste.

## Próxima decisão

O JSON permite verificar quais registradores participam de
operações de leitura-modificação-escrita, comparações e
gravações de ponteiros candidatos. Mesmo se for confirmado
um contador de 32 bits e um campo de controle de 16 bits,
ainda será necessário identificar a estrutura verdadeira
`OSi_ThreadInfo`, a ABI das threads, memória persistente
própria e a posse dos recursos de rádio ARM7.
