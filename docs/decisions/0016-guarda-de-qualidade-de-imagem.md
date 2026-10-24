# ADR 0016: Foto ruim não vira diagnóstico

**Status:** Decidido e em produção (2026-10-17).

## Contexto

O classificador tem três saídas: `septoriose`, `pinta_preta` e
`saudavel`. Nenhuma delas é "isto não é uma folha de tomate".

Isso não é descuido do treino, é propriedade de um classificador
fechado: toda entrada é distribuída entre as classes existentes, somando
1. Não existe para onde mandar o que está fora do domínio.

Medindo para onde o modelo empurra o que não entende, descobrimos algo
pior do que "chuta":

| Entrada | Classe | Confiança |
|---|---|---|
| Imagem preta | saudavel | 0,93 |
| Quase preta | saudavel | **0,97** |
| Ruído aleatório | saudavel | 0,94 |
| Verde liso | saudavel | 0,90 |

E a confiança **cresce** conforme a foto escurece. A mesma imagem de
folha sadia, escurecida artificialmente:

| Luz | Classe | Confiança |
|---|---|---|
| 100% | saudavel | 0,69 |
| 50% | saudavel | 0,91 |
| 25% | saudavel | **0,97** |

**O modelo confunde escuridão com saúde.**

A consequência prática é a pior possível para este projeto. Numa estufa
à noite, ou com o Ring LED fraco ou queimado, o sistema afirmaria
"saudável" com 95% de confiança **mesmo com a planta doente**. Falso
negativo sistemático, e o produtor não teria como desconfiar: a tela
mostraria um resultado confiante.

Isso não é hipótese. Nos primeiros testes com o dispositivo montado, uma
foto de quarto escuro voltou como "Saudável 100%".

## Decisão

A imagem é avaliada **antes** de classificar. Reprovada, a captura é
gravada normalmente, mas **nenhum diagnóstico é afirmado**.

O que acontece com uma captura reprovada:

| | |
|---|---|
| Foto | **guardada** no Storage e exibida no app |
| Leituras de sensor | gravadas normalmente |
| Alertas ambientais | gerados normalmente |
| Classe gravada | `imagem_inadequada`, confiança 0.0 |
| Alerta | "Não foi possível analisar a foto", severidade média |
| Alerta de doença | **nenhum** |

### Por que guardar a foto, e não descartar

Decisão do grupo, e ela melhorou a proposta original. Descartar a
captura pareceria mais limpo, mas tira do produtor a única coisa capaz
de explicar o que aconteceu.

Com a foto na tela, ele vê se a lente estava tampada, se o LED não
acendeu, se a câmera apontou para o lugar errado, ou se a captura caiu
de madrugada. **E consegue conferir se o aviso estava certo.** Um
sistema que diz "não consegui analisar" sem mostrar o que viu pede
confiança cega.

Por isso a tela de Diagnóstico mostra a foto em tamanho normal, com
"Sem análise" em cinza, sem porcentagem de confiança e sem barra, mais
o motivo em linguagem de produtor e um convite a comparar com o que ele
esperava ver.

**A confiança não aparece de propósito.** Exibir "0% de confiança"
sugeriria que houve análise e ela deu quase nada, quando análise nenhuma
foi feita.

## Os limiares, e de onde vieram

Medidos, não arbitrados. Sobre as 6 fotos reais de
`ml/validacao_externa/`, que o modelo classifica de forma utilizável:

| | Faixa nas fotos boas |
|---|---|
| Brilho médio | 74,6 a 207,1 |
| Textura (desvio padrão) | 35,2 a 71,4 |

Contra a mesma foto escurecida e imagens sem conteúdo:

| Caso | Brilho | Textura |
|---|---|---|
| 25% de luz | 51,4 | 17,8 |
| 15% de luz | 30,6 | 10,7 |
| Parede, lente tampada | qualquer | **0,0** |

**Reprova se brilho < 40 ou textura < 25.**

A textura separa melhor que o brilho: ela cai junto com a luz e vai a
zero em imagem lisa. O piso de 25 mantém margem sobre a pior foto boa
(35,2) e ainda pega a de 25% de luz (17,8), que foi onde o modelo
devolveu 0,97 de confiança para lixo.

Há teste travando esses números: subir `TEXTURA_MINIMA` para perto de 35
passaria a reprovar foto legítima, e o teste quebra explicando isso.

## Limitação conhecida

Ruído aleatório passa na guarda (brilho 127, textura 49). Não é modo de
falha de câmera real: uma câmera com defeito produz foto escura, borrada
ou lisa, não ruído uniforme. Inventar um terceiro teste para cobrir um
caso que não acontece custaria mais do que entrega.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Limiar de confiança ("só mostra acima de 85%") | **Não funciona aqui.** Medido: o modelo erra com 0,65 e acerta com 0,43, e 32 dos 119 erros tinham confiança acima de 0,90. A confiança não é calibrada, então qualquer corte joga fora acertos junto com erros |
| Descartar a captura reprovada | Tira do produtor a evidência que explica o problema |
| Classificar e marcar como "baixa qualidade" | Ainda mostra um resultado que pode ser lixo, ao lado de um aviso que muita gente não lê |
| Treinar uma classe "outro" | É a solução de fundo, e exige dado novo que não existe |

## Relação com o modelo de dois domínios (ADR 0011)

O modelo que entrou em produção em 2026-10-24 **não resolve o viés do
escuro**, e nem poderia, pelo motivo estrutural descrito acima. Medido
nele: foto a 25% de luz continua saindo como "saudavel", agora com 0,99.

Houve uma melhora lateral: o lixo deixou de receber confiança altíssima
(caiu de 0,86 a 0,97 para 0,55 a 0,90). Um modelo que hesita diante do
que não entende é mais honesto. Mas hesitar não basta: 0,78 numa imagem
preta ainda viraria "saudável" na tela.

**A guarda continua obrigatória**, e cada medição nova a reforçou em vez
de dispensá-la.

## Implementação

- `cloud/app/core/inference.py` (`avaliar_qualidade_imagem`,
  `CLASSE_IMAGEM_INADEQUADA`, `BRILHO_MINIMO`, `TEXTURA_MINIMA`)
- `cloud/app/api/routes/diagnostico.py` (guarda antes da inferência,
  alerta de câmera em vez de alerta de doença)
- `app/src/domain/doencas.ts` (`semDiagnostico`: o contrário de
  "saudável" deixou de ser "doente", existe um terceiro estado)
- `app/src/screens/DiagnosticoScreen.tsx` (foto sem veredito)
- Testes: `cloud/tests/test_inference.py`, `cloud/tests/test_diagnostico.py`

## Nota de implementação que vale guardar

Quatro testes antigos quebraram quando a guarda entrou. A imagem de
teste deles era um quadrado de cor única, que é exatamente o que a
guarda reprova.

A quebra foi útil: provou que a guarda pega o caso para o qual foi
escrita. A correção foi trocar o quadrado por um padrão quadriculado com
ruído leve, e isso ficou documentado no próprio arquivo de teste.
