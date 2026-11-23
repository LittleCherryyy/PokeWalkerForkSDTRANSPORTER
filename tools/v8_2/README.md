# Pokéwalker Virtual V8.2 — referências de estado do escalonador

## Resultado que motivou esta etapa

O relatório V8.1 das ROMs americanas originais comprovou:

- Três destinos ARM9 de `OS_IsThreadAvailable`, `OS_CreateThread`
  e `OS_WakeupThreadDirect` com assinaturas SHA-256 (32 e 128 bytes)
  coincidentes nos dois jogos.
- Convenção da chamada `OS_CreateThread` com seis argumentos no
  módulo de rede overlay 39.
- Pilha original entre `0x0222AED0` e `0x0222B6D0`, com
  2.048 bytes; prioridade inicial 16.
- `OSThread` original em `0x0222ADF8`, dentro da alocação do
  overlay 39. A separação entre o **início** desse objeto e a pilha
  é 216 bytes — **isso não é uma prova do sizeof(OSThread)**.

## Objetivo da V8.2

Investigar as referências de memória do próprio código NitroSDK para
identificar possíveis dados globais do escalonador, sem executar nenhum
método OS nem acessar a RAM viva do DSi.

O script analisa somente os primeiros **128 bytes** de cada função
ARM9, confirmando seus hashes SHA-256 V8.1. Reconhece:

- `LDR Rd, [PC, +/-offset]` incondicional, com literal dentro da
  imagem ARM9 (a ferramenta lê somente esse literal estático).
- Valores de ponteiros que apontam à RAM NTR, como **candidatos**,
  nunca como um estado já verificado do escalonador.
- Acessos imediatos com base em `r0` como **offsets sintáticos**,
  sem atribuir nomes aos campos internos da estrutura `OSThread`.
- Interrupção da análise linear em retorno ou desvio incondicional
  reconhecido. Desvios desconhecidos não são seguidos.

Os resultados comparam HeartGold e SoulSilver. Nenhum byte de
código da ROM, dump de memória, save, identificador de Pokémon ou
conteúdo de arquivo `.walker` é exportado.

As referências dependem da interpretação ARM e podem incluir
instruções que não estão efetivamente no caminho executado.
**Não são prova de estado vivo nem de controle seguro do escalonador.**

## Como testar no Windows

1. Extraia o ZIP do GitHub Actions preservando:
   `v7_3`, `v7_4`, `v7_5`, `v7_6`, `v8_0`,
   `v8_1` e `v8_2`.
2. Selecione seus dois backups originais dos jogos USA Rev0.
3. Arraste ambos para `v8_2/COMPARAR_ESTADO_THREADS.bat`.
4. Envie somente `wifi_v82_hgss_scheduler_refs.json`.
5. Em caso de erro, compartilhe a mensagem, sem enviar os arquivos .nds.

Alternativa:

    python tools/v8_2/hgss_thread_scheduler_refs.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v82_hgss_scheduler_refs.json

**Mantenha a V7.9 no DSi.** Nenhum novo bootstrap, aplicativo
Android ou arquivo de save é necessário nesta fase.

## Próximo gate

Analisar os endereços candidatos e elaborar uma verificação **somente
de leitura** da RAM ARM9, com limites fixos e comportamento seguro caso
os dados não estejam presentes. Mesmo com escalonador inicializado,
será necessário comprovar memória permanente, contexto de thread,
coordenação do ARM7 e controle do rádio antes de tentar qualquer PING.

Nenhuma função `OS_CreateThread`, `OS_WakeupThreadDirect`, `WCM_*`
ou `SOC_*` é executada por esta versão.
