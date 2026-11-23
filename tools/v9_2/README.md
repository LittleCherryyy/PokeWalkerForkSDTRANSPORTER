# V9.2 — origem dos registradores antes de escritas ARM9

## Descobertas do relatório V9.1

O usuário executou a V9.1 nos backups originais USA Rev0.
As oito sequências ARM9 são equivalentes entre HeartGold e
SoulSilver. A análise de proveniência demonstrou, de forma
**estática**, que:

- `0x021E169C`: `LDR` → `ADD +1` → `STR` da mesma palavra,
  com o mesmo valor transformado; **candidato forte a contador**.
- `0x021E16A0`: `LDRH` → `CMP #0`, usando o mesmo valor lido;
  **candidato a flag de 16 bits**.
- `0x021E16A8`: três `STR` conhecidos, mas a origem do
  registrador escrito não foi identificada pela V9.1.
- `0x021E16AC`: uma leitura e uma escrita no mesmo local
  sem prova de reaproveitamento do valor carregado.

O código da ROM não foi executado durante a análise. A estrutura
`OSi_ThreadInfo` e a ABI das threads continuam sem confirmação.

## O que a V9.2 acrescenta

A V9.1 examinava instruções **após** a carga de um literal
de endereço. Porém, o valor que um `STR` escreve pode ser
preparado **antes** dessa instrução.

A V9.2 inspeciona, apenas nos backups originais, até **12
instruções ARM anteriores** às seguintes escritas:

- `0x020D18A4`: `STR` em `0x021E16A8`;
- `0x020D2034`: `STR` em `0x021E16A8`;
- `0x020D20D4`: `STR` em `0x021E16A8`;
- `0x020D21D8`: `STR` em `0x021E16AC`.

A ferramenta registra o registrador de origem da escrita
e, quando possível, sua **última atribuição local** por uma
instrução `MOV`, `ADD/SUB` imediato, `LDR` ou literal
carregado da ROM. Ela pode acompanhar até três etapas
simples de cópia/aritimética de registradores, sempre dentro
dos mesmos 12 endereços de instrução.

Instruções condicionais, desvios, chamadas, operações
não reconhecidas e mudanças ambíguas em registradores
interrompem a análise sem inferir valores. Valores carregados
da RAM são rotulados como **desconhecidos** e não usados
como ponteiros.

**Importante:** uma instrução anterior encontrada por varredura
estática não prova que ela realmente definiu o valor usado
na escrita; outra rota de execução pode chegar ao mesmo local.
O resultado sempre mantém `executed_path_verified=false`.

Nenhum byte de ROM nem opcode é exportado. Nenhum dado da
RAM do DSi é lido. ROMs, saves, `.walker` e APKs não são
modificados.

## Teste Windows

1. Extraia o ZIP do GitHub Actions preservando todas as
   pastas dos analisadores, de `v7_3` até `v9_2`.
2. Arraste seus backups originais
   `HeartGold.nds` e `SoulSilver.nds` para
   `v9_2/COMPARAR_ESCRITAS_ARM9.bat`.
3. Envie somente o arquivo gerado
   `v9_2/wifi_v92_hgss_store_value_backtrace.json`.

Pelo terminal:

    python tools/v9_2/hgss_store_value_backtrace.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v92_hgss_store_value_backtrace.json

Não altere o `nds-bootstrap` V8.8 já instalado; não há
teste no console nem no hotspot Android nesta versão.

## Próximo marco

Usaremos os resultados para diferenciar possíveis constantes
inicializadoras, valores de argumentos e valores recebidos da
memória pelo mecanismo que escreve o campo `0x021E16A8`.

Mesmo que as origens correspondam entre HG e SS, **não**
ativaremos Wi-Fi ou criaremos threads até provar o contexto
não-IRQ de execução, a área de memória própria para o
worker e a posse dos recursos Wi-Fi/IRQ pelo ARM7.
