# V7.1 — DSi PING usando somente hotspot Android

**Modo pretendido: Android hotspot -> Nintendo DSi, sem roteador, sem Wi-Fi doméstico e sem digitar IP.** O celular é o hotspot/servidor TCP; o DSi é o cliente.

Esta é uma compilação diagnóstica homebrew independente. Não funciona dentro de HeartGold/SoulSilver ainda; não lê ou escreve save, ROM ou .walker, e não substitui o nds-bootstrap.

## Preparação

1. No Android V18, ative o **Direct DSi Sync**, que escuta na porta TCP **30821**.
2. Ative um hotspot **2,4 GHz com segurança realmente compatível com o modo Wi-Fi DS do homebrew**. Em muitos smartphones modernos, só WPA2/WPA3 está disponível; **isso não é compatível com o modo DS clássico** do DSi usado por `Wifi_InitDefault(WFC_CONNECT)`. Um hotspot aberto temporário (quando disponível e permitido) facilita testes, mas evite expor dados e desative-o ao terminar.
3. Configure a conexão Wi-Fi adequada nas configurações de conexão Nintendo DS do console (não apenas no navegador DSi). Se o hotspot não oferecer a segurança compatível, **não tente contornar com IP ou modo de rede doméstica: o teste não terá como conectar**.
4. Copie **PokeWalker_V71_HOTSPOT_PING.nds** do artefato GitHub Actions (somente após build verde) para o SD do DSi e abra no TWiLight Menu++.

## Comandos na tela do DSi

- O programa lê o IP local e o **gateway DHCP** da conexão. Quando conectado diretamente ao hotspot do Android, o gateway normalmente é o próprio telefone. Não é preciso escrever IP nem usar notebook.
- **B** envia um `OP_PING` de 88 bytes para a porta 30821 no gateway; exibe fase/código/erro, PINGs OK.
- **X** envia e confirma 2 KB sintéticos por `OP_TEST_ECHO`, sem saves.
- **START** sai. Pela ocorrência anterior de travamento ao fechar sockets DSWifi, o teste mantém uma única conexão e não chama `close()` explicitamente. Se houver erro de sessão ou for necessário mudar de rede, reinicie o DSi antes do novo teste.

Um PING positivo significa somente que o homebrew standalone conseguiu falar com o Android; **não prova Wi-Fi residente no HGSS**. Nenhuma transferência de Pokémon deve ser habilitada por causa desse resultado.

Código adaptado do diagnóstico V6.7 de SD Transporter, mantendo todos os créditos upstream e licenças.
