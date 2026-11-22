# Pokéwalker V7.5 — chamadas WCM/SOC reais de HGSS

## Evidência até V7.4

Os relatórios de HG/SS enviados pelo usuário confirmaram os hashes das ROMs
USA originais, a mesma imagem ARM9 reconstruída em tamanho (1.122.040 bytes),
hashes diferentes entre jogos e overlay 72 idêntico. V7.4 ainda não identificou
funções de rede executáveis durante gameplay.

## Objetivo da V7.5

Antes de executar qualquer função, mapear as instruções de chamada que a
descompilação pública identifica com nomes WCM/SOC. O analisador extrai os
overlays 13, 39 e 72 *na memória do computador*, descompacta os marcados BLZ,
verifica os opcodes próximos aos callsites e decodifica o destino de cada BL.

Referências publicadas no projeto pret/pokeheartgold:

- overlay 72, 0x02237E0C (Thumb): WCM_GetPhase
- overlay 13, 0x02223712 (Thumb): WCM_Init
- overlay 13, 0x02223736 (Thumb): WCM_StartupAsync
- overlay 39, 0x02229AE8 (ARM): SOC_Socket
- overlay 39, 0x02229C5C (ARM): SOC_Connect

A API declarada pode ser compilada como código ARM, Thumb ou mediante
linker veneer. **O destino imediato de uma BL não é necessariamente a função final.**
A localização do destino no ARM9 principal não confirma inicialização,
residência, ABI, interoperabilidade com ARM7 ou segurança para HGSS.

## Como testar (somente no computador)

1. Extraia o ZIP do GitHub Actions mantendo as pastas v7_3, v7_4 e v7_5 lado a lado.
2. Selecione seus dois backups originais HeartGold.nds e SoulSilver.nds no Explorador do Windows.
3. Arraste **os dois arquivos juntos** para v7_5/COMPARAR_HGSS_WIFI.bat.
4. Envie o único arquivo wifi_calls_HGSS_comparativo.json gerado.
5. Se arrastar dois arquivos não funcionar, rode o BAT pelo terminal com os dois caminhos como argumentos.
6. Não copie nada para o DSi e não atualize o Android nesta etapa.

Também é possível testar individualmente, arrastando cada ROM para
v7_5/TESTAR_CALLS_WIFI.bat; os resultados são salvos separadamente.

Alternativa:

    python tools/v7_5/hgss_wifi_call_targets.py "HeartGold.nds" --compare "SoulSilver.nds" --output wifi_calls_HGSS_comparativo.json

O JSON contém apenas endereços e metadados, nunca código da ROM.
Uma instrução diferente da esperada interrompe o diagnóstico de forma segura.

## Gate posterior

Cruzar os destinos dos dois jogos com binários descompactados e o código
NitroWiFi, validar veneers e convenções de chamada, confirmar vida útil das
funções e posse dos recursos de rádio, e só então permitir PING real.

**Até a validação do driver, Wi-Fi não está habilitado.** Nenhuma chamada é
feita no ARM7/ARM9, e o arquivo .walker permanece intocado.
