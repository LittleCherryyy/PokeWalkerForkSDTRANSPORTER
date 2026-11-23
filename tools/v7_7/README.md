# Pokewalker V7.7 — comparação CRC32 ARM9 ao vivo

O relatório V7.6 do usuário confirma cinco entradas ARM9 sem veneers
reconhecidos. Cada janela de 32 bytes possui o mesmo hash SHA256 nos dois
jogos originais USA revisão 0.

A V7.7 realiza **dois testes complementares**, com nenhuma chamada WCM/SOC:

1. **PC:** descompacta apenas na RAM o código ARM9 dos dois .nds,
   confirma os hashes SHA256 da V7.6 e registra os CRC32 dos mesmos
   32 bytes no arquivo wifi_v77_arm9_crc_reference.json.
2. **DSi:** durante o jogo, abra o menu do nds-bootstrap -> Virtual
   Pokewalker -> pressione **L**. A tela V7.7 ARM9 LIVE CRC calcula
   CRC32 dos mesmos cinco endereços ARM9 e mostra uma indicação PRO
   quando o primeiro word se parece com um prólogo ARM.

## Teste

1. Extraia o ZIP Windows V7.7 preservando v7_3, v7_4 e v7_7.
2. Arraste seus dois .nds originais para v7_7/COMPARAR_CRC_ARM9.bat.
3. Envie apenas o wifi_v77_arm9_crc_reference.json.
4. Faça backup de nds-bootstrap-nightly.nds e dos arquivos de save.
5. Instale o nds-bootstrap.nds experimental V7.7 do build GitHub,
   renomeando para sd:/_nds/nds-bootstrap-nightly.nds.
6. Selecione Nightly no TWiLight Menu++, abra HeartGold no DSi,
   abra Virtual Pokewalker e pressione L.
7. Fotografe a tela e envie. Se quiser, repita com SoulSilver.

Os valores apresentados na tela são CRC32 sem o prefixo 0x.
O campo PRO apenas indica um prólogo ARM plausível, e não uma ABI
comprovada. Uma combinação idêntica de CRC32 com o relatório do PC
indica os mesmos 32 bytes com probabilidade elevada; CRC32 não é uma
prova criptográfica. O SHA256 original de cada janela foi previamente
validado no PC e nas duas ROMs na V7.6.

Nenhum código Wi-Fi é inicializado ou chamado. Nenhuma ROM, save,
Pokewalker, tabela de interrupções ou registro de rádio é modificado.

O próximo marco exige descobrir como agendar funções de rede
no ARM9 fora do contexto IRQ e validar a posse do rádio ARM7/WM.
