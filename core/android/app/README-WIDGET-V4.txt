SD-Transporter / Pokewalker Widget V4

Mudancas:
- remove clique global que abria MainActivity;
- 3 botoes fisicos interativos:
  esquerda = receber Pokemon (2 toques para confirmar)
  centro = atualizar/cancelar confirmacao
  direita = devolver/enviar Pokemon ao console (2 toques para confirmar)
- toque no LCD abre apenas a configuracao do widget (perfil + IP/host do console);
- transferencia roda em foreground service dataSync;
- estado/progresso/erro da transferencia aparece no LCD do widget;
- resizeMode horizontal|vertical;
- layouts pequeno/medio/grande escolhidos conforme o tamanho do widget;
- sprite e dados do Pokemon continuam sendo exibidos.

Aplicacao:
Substitua a pasta src e o build.gradle do modulo Android pelos arquivos deste pacote.
Depois sincronize/recompile/reinstale. Remova e adicione novamente o widget para gravar o IP do console.
