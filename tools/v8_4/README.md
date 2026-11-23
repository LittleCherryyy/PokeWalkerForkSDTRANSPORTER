# V8.4 — Referências ao estado de threads do HeartGold/SoulSilver

## Resultado do teste no Nintendo DSi

Na fotografia enviada em 22/11/2026, a tela `V8.3 ARM9 OS FLAG`
mostrou **`OS raw value: 0x00000001`**. O código original em
`0x020D1AC4` havia passado na comparação de suas quatro palavras de
instrução/literal.

Segundo a documentação NitroSDK,
[OS_IsThreadAvailable](https://twlsdk.randommeaninglesscharacters.com/docs/nitro/NitroSDK/os/thread/OS_IsThreadAvailable.html)
retorna TRUE quando o subsistema de threads foi inicializado e pode
ser utilizado pelo aplicativo.

Isso não identifica quantas threads existem nem comprova uma pilha
livre para o nosso programa.

## O que a V8.4 faz

Analisa **offline** duas ROMs originais US Rev0. Reconstrói o ARM9
estático e revalida V8.2 antes de considerar endereços.

Localiza as referências literais ao endereço conhecido `0x021E1688`
e a valores alinhados próximos (até 64 bytes antes/depois). Uma
referência só é incluída quando uma instrução ARM incondicional
`LDR Rd, [PC, +/-imediato]` aponta exatamente para o literal
dentro da imagem ARM9 reconstruída.

Os resultados fornecem endereços, diferenças numéricas, hashes
SHA-256 de janelas de 32 bytes e comparações HeartGold/SoulSilver.
Não exportam código ou dados de jogo nem leem memória real do DSi.

**Importante:** as referências são candidatas. Um valor próximo
de `0x021E1688` não é automaticamente o campo `currentThread`,
a lista de threads nem uma região segura para alocação. O scanner
também pode encontrar dados que apenas parecem instruções.

## Como executar

1. Extraia o pacote do GitHub Actions, preservando as pastas
   `v7_3`, `v7_4`, `v7_5`, `v7_6`, `v8_0`,
   `v8_1`, `v8_2` e `v8_4`.
2. Selecione os seus backups originais USA Rev0
   `HeartGold.nds` e `SoulSilver.nds`.
3. Arraste os dois para
   `v8_4/COMPARAR_REFERENCIAS_THREADS.bat`.
4. Envie somente o arquivo `v8_4/wifi_v84_thread_flag_xrefs.json`
   gerado. Se houver erro, envie somente o texto da mensagem.

Alternativa:

    python tools/v8_4/hgss_thread_flag_xrefs.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v84_thread_flag_xrefs.json

**Nada deve ser alterado no cartão SD, Android ou jogo.**
Mantenha a V8.3 no DSi, onde o flag já foi comprovado.

A futura thread própria depende de uma estrutura `OSThread`
com layout conhecido, uma pilha persistente fora dos overlays,
contexto seguro de inicialização e coordenação ARM7 para o rádio.
Os testes V7.9 e V8.3 ainda não autorizam iniciar Wi-Fi.
