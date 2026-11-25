# Virtual Slot-2 v0.1.0-beta

## Objetivo
Emular um cartucho GBA no Slot-2 do Nintendo DSi por meio de um provider externo do nds-bootstrap. O jogo DS continua usando o fluxo original do Pal Park; o save GBA é lido e as alterações são persistidas no SD. Não é um editor de Pokémon nem uma implementação de Wi-Fi.

## Instalação
1. Baixe o [bootstrap NBP016](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/45546143437/artifacts/14991950123) e o [TWLM03 DSi/NES](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/45546166642/artifacts/14990769748).
2. Copie os arquivos das pastas `_nds` dos dois pacotes para a raiz do SD: `nds-bootstrap-nightly.nds`, `nds-bootstrap/plugins/virtual_slot2.nbp` e `TWiLightMenu/dsimenu.srldr`. Use o canal Nightly.
3. Mantenha a configuração existente ou insira inicialmente uma ROM GBA compatível pelo menu Y sobre o jogo GBA. A opção de inserção depende de um save associado. A ROM e o save também podem ser configurados em `sd:/_nds/nds-bootstrap/slot2.ini`. Consulte o exemplo distribuído no pacote. Não substitua configurações funcionais indiscriminadamente.
4. Abra um jogo DS compatível. Para os títulos/revisões suportados, o bypass diário é opt-in pelo menu Y ou por `migration.ini`.
5. Salve o progresso do jogo DS. Abra o menu interno com L + Down + Select e selecione Virtual Slot-2. Up/Down troca edição, Left/Right troca save, A confirma e reinicia, B cancela.
6. Confira MIGRATE FROM no menu do jogo e complete o Pal Park. Antes de desligar, salve no jogo DS e aguarde a gravação.

## Compatibilidade e evidência
- DSi, SD interno, Pearl (USA, ROM modificada para Ranch): migração Emerald completa e remoção confirmada no save GBA; FireRed reconhecido; Ruby, Sapphire e LeafGreen reportados como funcionando pelo usuário. A combinação NBP016 + TWLM03 foi confirmada funcionando pelo usuário; isso não equivale a uma matriz completa de transferências nessa versão.
- Diamond, Platinum, HeartGold, SoulSilver: implementação prevista, transferência integral ainda não validada neste projeto.
- R4/Acekard: temas do TWLM03 compilados; não testados em hardware. Flashcards/B4DS não suportados pelo provider desta beta.
- Saves GBA de 128 KiB, ou 128 KiB + 16 bytes de RTC. Hacks com Game ID alterado podem ficar de fora. O catálogo usa cabeçalho da ROM e nomes de saves; não verifica integralmente o conteúdo nem a compatibilidade de hacks.
- Até 96 entradas no catálogo; procura na pasta GBA e diretórios configurados. Cada save é associado a uma variante da ROM; para forçar outra variante, insira-a inicialmente pelo menu GBA ou configure os caminhos.
- O reset atual é uma reinicialização do bootstrap, não um hot-swap sem reset. A troca requer cartucho inicialmente válido. Gravação verificada por setores; não há transação atômica entre save GBA e DS. Backups recomendados.
- Diagnósticos: NBP016.BIN, NBP016-BOOT.TXT, NDSBTSRP.LOG. Logs pessoais e saves não devem ser enviados ao Git.

## Fonte e reprodução
A implementação desta beta é aplicada sobre o commit upstream `75610fa9905ac252609081287121e8d4c44febed` pelo workflow [NBP016](../.github/workflows/nbp016-swap.yml). O pacote contém integration.patch e os créditos/licença. O [TWLM03](../.github/workflows/twlm03-clean-menu.yml) recompila o menu upstream sem as duas linhas extras do TWLM02. Ambos usam devkitpro/devkitarm:20241104. Os artefatos Actions têm retenção limitada; veja [manifesto](release.json) para os IDs exatos. Os workflows históricos continuam na branch experimental original; nenhum merge com o Pokéwalker foi realizado.

## Créditos
SD Transporter (Shinygati e contribuidores), nds-bootstrap e TWiLight Menu++ (DS-Homebrew e contribuidores). Preserve GPLv3, avisos e licenças de componentes. Não afiliado à Nintendo.
