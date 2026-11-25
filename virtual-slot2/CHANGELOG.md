# Histórico — Virtual Slot-2

## v0.1.0-beta — 2026-11-25
- NBP016 + TWLM03: confirmação de funcionamento pelo usuário em DSi.
- Provider externo, migração nativa, gravação verificada, bypass opt-in.
- Seletor interno por edição e save com D-pad, reinicialização do bootstrap, reaproveitamento do catálogo e transferência de registro por buffer compartilhado.
- Menu Y do DS sem seletores redundantes; inserção inicial pelo menu GBA preservada.

## Histórico experimental
- NBP003–011: provider externo, detecção de famílias, correção de leitura parcial, bypass e persistência. NBP011 validou migração Emerald → Pearl completa.
- TWLM01–02: seletor antes do jogo, suporte a variantes e cópias.
- NBP012–013: menu interno, troca após flush, correção da abertura do menu.
- NBP014–015: catálogo otimizado, agrupamento por edição e navegação direta. Erro de leitura do catálogo observado em NBP015.
- NBP016/TWLM03: transferência de registro em uma única operação, correção do contador e limpeza do menu DS.

Próximos passos: validar todos os destinos Gen IV, migrações repetidas, melhorar inicialização sem cartucho configurado e estudar integração com o bootstrap do Pokéwalker sem regressões.
