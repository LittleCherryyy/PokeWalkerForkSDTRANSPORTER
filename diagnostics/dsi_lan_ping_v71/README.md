# Diagnóstico V7.1 — PING DSi na rede local (SEM SAVE)

**Este programa é apenas uma ferramenta de diagnóstico homebrew.** Não é intermediário para transferir Pokémon; não altera o Pokémon HGSS, o nds-bootstrap, o widget ou qualquer save.

A V6.7 sempre enviava para o gateway, adequado ao hotspot. Agora o endereço do Android pode ser escolhido, inclusive numa rede doméstica em que o celular não é o roteador.

## DSi
1. Configure o DSi para conectar a uma rede Wi-Fi **compatível com Nintendo DS** (2,4 GHz e segurança compatível; jogos DS comuns não suportam WPA2). Redes abertas devem ser usadas apenas temporariamente e com cuidado.
2. Mantenha no Android V18 o serviço **Direct DSi Sync** ativo e acessível na porta TCP 30821.
3. Copie **somente** `PokeWalker_V71_LAN_PING.nds` para o SD do DSi e abra pelo TWiLight Menu++. Não modifique arquivos do HGSS nem substitua o nds-bootstrap.
4. O programa mostra o gateway e o endereço de destino Android. Na sua rede atual o gateway do Windows é `192.168.0.1` e o Android foi testado em `192.168.0.5`. **A rede usada no DSi pode ser diferente**. Ajuste o último octeto do destino com cima/baixo (±1) ou esquerda/direita (±10). `SELECT` restaura o gateway. Se os três primeiros octetos forem diferentes, use outra rede compatível; esta ferramenta não edita esses octetos.
5. Pressione **B** para PING (porta 30821) ou **X** para eco de 2 KB sintéticos; veja `Codigo`, `Fase`, `PING OK` e `ECO OK`.
6. Fotografe a tela com código, erro, IP do DSi e alvo Android. Após conectar, não é possível alterar o IP sem reiniciar o aplicativo no DSi: as sessões V6.7 persistem para evitar um problema observado no fechamento de socket.

**Importante:** o DSi normalmente só consegue usar redes com modos de segurança compatíveis com jogos DS. Seu Windows e Android estarem no mesmo Wi-Fi WPA2 não prova que o DSi consiga entrar nessa rede. O console pode exigir outro ponto de acesso temporário e adequado.

O teste envia apenas os pacotes de PING/ECHO definidos no código V6.7; não toca EEPROM, ROM ou save. Um PING positivo aqui **não** comprova funcionamento enquanto HeartGold/SoulSilver estiver rodando. Não é a transferência final do projeto.

## Builds
O GitHub Actions compila a versão de teste com a toolchain devkitPro e armazena o `.nds` como artefato, quando o job estiver verde. O código base continua em `diagnostics/dsi_ping_v6`; o workflow substitui apenas `source/main.c` antes do build.
