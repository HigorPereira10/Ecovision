# ADR 0011: Escopo do modelo reduzido a três classes

**Status:** Decidido e em produção (2026-10-10, documentado em
2026-10-11). Reversível por construção, ver "Como reativar uma classe".

## Contexto

O TC1 e o Blueprint v3.0 descrevem um classificador de **10 classes**
do PlantVillage, e o catálogo agronômico do
[ADR 0006](0006-recomendacoes-por-diagnostico.md) tem recomendação de
manejo escrita e com fonte para todas as dez.

O modelo que efetivamente foi treinado e está em produção
(`ml/models/modelo.tflite`, gerado em 2026-10-10) reconhece **três**:

| Classe | Origem |
|---|---|
| `septoriose` | Pasta que no treino se chamava `distrator_septoria`, publicada com o nome da doença depois de o Carlos validar a classe |
| `pinta_preta` | Classe alvo principal |
| `saudavel` | Ausência de doença |

Esse descasamento entre o documento e a realidade é exatamente o tipo
de contradição que a banca encontra. Este ADR existe para que a resposta
seja uma decisão registrada, e não uma surpresa.

## Decisão

**O escopo de produção é de três classes, e isso é dito explicitamente
ao produtor dentro do app.**

A tela de Diagnóstico mostra, no pé, a frase gerada por
`resumoDoEscopoDoModelo()` (`app/src/domain/doencas.ts`): "A análise
reconhece 3 condições: Saudável, Septoriose, Pinta preta."

Isso não é detalhe de interface. Sem a frase, uma folha com requeima
classificada como "saudável" parece **erro da IA**, quando na verdade é
uma doença que ela nunca aprendeu a ver. A diferença entre as duas
leituras é a diferença entre um sistema com limite declarado e um
sistema que mente por omissão.

## Motivo

Três classes validadas por agrônomo valem mais, na estufa e na banca,
do que dez classes em que sete chutam.

O argumento técnico: `class_weight` e F1 ponderado (ver `ml/README.md`)
mitigam desequilíbrio de classes, não **ausência** de dado de treino
adequado. A classe minoritária do PlantVillage (Mosaic Virus, cerca de
299 imagens) ficaria com cerca de 45 imagens no teste, e um F1 calculado
sobre 45 imagens tem variância alta demais para se defender.

O argumento honesto: publicar dez classes com desempenho ruim em sete
delas produziria exatamente o cenário que o
[ADR 0006](0006-recomendacoes-por-diagnostico.md) tenta evitar, que é o
produtor aplicando defensivo pela recomendação errada.

## O catálogo das dez classes continua no código

`_CATALOGO_AGRONOMICO` em `cloud/app/core/inference.py` mantém as dez
entradas, com recomendação e fonte. Elas não atrapalham: o modelo
simplesmente nunca emite as outras sete, e o catálogo passa a ser o
trabalho já feito, esperando dado de treino.

No app, `app/src/domain/doencas.ts` repete essa separação com um campo
`ativa: boolean`. As sete inativas aparecem lá **sem nome científico**,
de propósito: nenhuma delas chega ao produtor hoje, e escrever um
binômio que ninguém conferiu seria criar informação para a banca cobrar
depois.

## Como reativar uma classe

Quando houver dado de treino suficiente para uma classe nova, a
alteração é em **três lugares, e os três têm que concordar**:

1. Retreinar, e exportar com `ml/src/export/convert_tflite.py`.
2. `_CLASSES_DO_MODELO` em `cloud/app/core/inference.py`: atualizar a
   lista na **ordem exata** das saídas do modelo.
3. `ativa: true` na classe correspondente em `app/src/domain/doencas.ts`.

**O item 2 é o perigoso.** A ordem vem do treino, onde
`tf.keras.utils.image_dataset_from_directory` ordena os diretórios de
classe alfabeticamente. Trocar o `.tflite` por um retreino com outra
quantidade ou outra ordem de classes **sem** atualizar aquela lista faz
cada predição sair com o nome e a recomendação de outra doença, **sem
nenhum erro visível**. O sistema continua respondendo 200, o app
continua bonito, e o diagnóstico está trocado.

## Duas armadilhas de integração já pagas, que não devem voltar

Registradas aqui porque custaram diagnóstico e porque um retreino pode
reintroduzi-las:

**1. O modelo normaliza por dentro.** A camada `preprocess_input` da
MobileNetV2 faz parte do grafo exportado, então quem chama tem que
passar **pixels crus de 0 a 255**. Dividir por 255 antes de enviar faz
todas as predições colapsarem para "saudavel" com cerca de 90% de
confiança, sem erro nenhum.

**2. O redimensionamento tem que ser NEAREST.** Medido no conjunto de
validação externa: com `Image.Resampling.NEAREST`, 6 de 6 predições
batem com o modelo Keras original. Com BILINEAR ou BICUBIC, 0 de 6
batem, e **duas classes mudam**.

Nos dois casos o sistema não falha: ele responde com confiança alta e
está errado.

## Sem quantização, de propósito

A conversão com `tf.lite.Optimize.DEFAULT` derruba o arquivo de 8,90 MB
para 2,53 MB. Medido no conjunto de validação externa, a versão
quantizada **inverteu 2 de 7 predições**, com diferença de até 29 pontos
percentuais de confiança. A float32 divergiu no máximo 0,0004 ponto
percentual do Keras original.

Economizar 6 MB não paga mudar diagnóstico, especialmente com a RAM
sobrando (o interpretador inteiro ocupa cerca de 14 MB).

## Adendo (2026-10-17): o modelo não sabe recusar uma entrada

Medido depois do primeiro ciclo com o dispositivo montado, sobre o
`.tflite` em produção:

| Entrada | Classe | Confiança |
|---|---|---|
| Imagem preta | saudavel | 0,93 |
| Quase preta | saudavel | **0,97** |
| Ruído aleatório | saudavel | 0,94 |
| Verde liso | saudavel | 0,90 |
| Cinza liso | saudavel | 0,86 |

E, pior, a confiança **cresce** conforme a foto escurece. A mesma imagem
de folha sadia, escurecida artificialmente:

| Luz | Classe | Confiança |
|---|---|---|
| 100% | saudavel | 0,69 |
| 50% | saudavel | 0,91 |
| 25% | saudavel | **0,97** |

**O modelo confunde "escuro" com "saudável".** A causa é estrutural: ele
tem três saídas e nenhuma delas é "isto não é uma folha de tomate", logo
toda entrada é distribuída entre as três. Um classificador fechado não
tem como rejeitar o que está fora do domínio.

A consequência prática é a pior possível para este projeto: numa estufa
à noite, ou com o Ring LED fraco, o sistema afirmaria "saudável" com 95%
de confiança **mesmo com a planta doente**. Falso negativo sistemático,
e o produtor não teria como desconfiar.

**Mitigação implementada:** guarda de qualidade de imagem ANTES da
inferência (`avaliar_qualidade_imagem` em `cloud/app/core/inference.py`),
com limiares medidos e não arbitrados. Foto reprovada não vira
diagnóstico: vira a classe `imagem_inadequada`, com a foto guardada e
visível no app e um alerta de câmera. Decisão do grupo: guardar a imagem
é o que permite ao produtor conferir se o aviso estava certo e
identificar o problema olhando a própria foto.

**O que isso NÃO resolve:** ruído aleatório passa na guarda (brilho 127,
textura 49), e uma folha de outra espécie continua sendo forçada para
uma das três classes. A solução de fundo seria uma classe "outro" no
treino, ou um limiar de confiança calibrado, e isso depende de dado novo.

## Desempenho medido no conjunto de validação externa

Primeira medição de acurácia contra rótulos, em 2026-10-17:

| Imagem | Esperado | Previsto | Confiança |
|---|---|---|---|
| pinta_preta_01 | pinta_preta | pinta_preta | 0,43 |
| pinta_preta_03 | pinta_preta | pinta_preta | 0,80 |
| saudavel_01 | saudavel | **pinta_preta** | 0,47 |
| saudavel_02 | saudavel | **pinta_preta** | 0,52 |
| saudavel_03 | saudavel | saudavel | 0,65 |
| septoria_01 | septoriose | septoriose | 0,81 |

**4 de 6.** Os dois erros são no mesmo sentido: planta sadia
classificada como pinta preta, que leva o produtor a pulverizar
fungicida sem necessidade.

**Distinção importante para a banca:** a medição anterior, de "6 de 6
batendo com o Keras", verificava que a **conversão para TFLite está
fiel** ao modelo original. Não media acerto. São coisas diferentes, e
esta é a primeira vez que o acerto foi medido.

Com n=6, isto é indicativo e não conclusivo. Serve para orientar o
retreino, não para ser publicado como métrica de desempenho.

## Desempenho medido em 277 fotos de campo (2026-10-17)

Primeira medição com amostra grande, no dataset **PlantDoc** tomate
(`ml/data/plantdoc_tomate/`), que é fotografia em campo, não imagem de
laboratório. O modelo foi treinado em outro conjunto
(`../data/doenca` e `../data/dataset_hibrida`, conforme os notebooks de
`ml/training/`), então **nenhuma destas 277 imagens foi vista no
treino**.

Prova disso no próprio resultado: as pastas `train` e `test` do PlantDoc
deram 57,0% e 57,1%. Se o modelo tivesse visto alguma delas, a de treino
seria muito mais alta. É uma medição limpa, fora da amostra.

| Classe | n | Precisão | Revocação | F1 |
|---|---|---|---|---|
| saudavel | 60 | 0,52 | 0,62 | 0,56 |
| pinta_preta | 79 | 0,47 | 0,70 | 0,56 |
| septoriose | 138 | 0,75 | 0,48 | 0,58 |

**Acurácia: 57,0%. F1 ponderado: 57,3%.**

| Referência | Valor |
|---|---|
| Acaso, com 3 classes | 33,3% |
| **Medido em foto de campo** | **57,3%** |
| Meta mínima do projeto para imagem real (`ml/README.md`) | 65% |
| Meta ideal | 72% |

O modelo está claramente acima do acaso e **abaixo da meta mínima**.
Este é o número que faltava para a dupla métrica, e ele é honesto:
PlantDoc é mais difícil que o dataset de treino justamente por ser foto
de campo, com fundo real, luz variável e folha fora de enquadramento,
que é o que o Raspberry Pi vai capturar.

### A confiança não serve como filtro

| | Confiança média |
|---|---|
| Quando acerta | 0,82 |
| Quando erra | 0,73 |

A diferença é pequena demais para separar um do outro, e **32 dos 119
erros aconteceram com confiança acima de 0,90**. Não existe limiar de
confiança que descarte os erros sem descartar junto a maioria dos
acertos. O número exibido ao lado do diagnóstico indica o quanto a saída
da rede pendeu para uma classe, não a probabilidade de estar certa, e o
texto do TCC não deve tratá-lo como tal.

### Onde o modelo erra mais

A revocação de septoriose é **0,48**: menos da metade das folhas com
septoriose é identificada. E a precisão de pinta preta é **0,47**: menos
da metade do que ele chama de pinta preta é pinta preta de verdade. Na
prática, o modelo tende a chamar septoriose de pinta preta.

Isso é coerente com a origem da classe: a pasta de septoriose nasceu no
treino como `distrator_septoria`, incluída justamente para evitar que
tudo virasse pinta preta. O problema que ela existia para resolver ainda
não está resolvido.

## Ajuste de dois domínios (2026-10-24): o modelo em produção mudou

O modelo de 90,7% em laboratório e 57,0% em campo foi **substituído** por
um ajuste fino que treina com os dois domínios ao mesmo tempo.

### O caminho até aqui, incluindo a tentativa que não serviu

**Primeira tentativa, só com foto de campo.** Ajustar o baseline usando
as 249 fotos de campo que já estavam em `ml/data/plantdoc_tomate/`
subiu campo de 50,3% para 69,3% (validação cruzada de 5 dobras, vitória
em 5 de 5). Parecia resolvido.

**Mas era troca, não melhora.** Medido depois em 3300 imagens de
laboratório, aquele modelo caía de 90,7% para 78,2%, e passava a chamar
**495 das 1100 pinta pretas de laboratório de septoriose**. Herdou o
desequilíbrio do PlantDoc, onde septoriose é 138 das 277 imagens. Ganhava
19 pontos de um lado e perdia 12 do outro.

**A correção foi mostrar os dois domínios no treino.** O desequilíbrio
entre eles é grande (3000 de laboratório contra 249 de campo), então cada
foto de campo entra valendo por cerca de 12 no cálculo do `class_weight`.
Sem isso o campo vira ruído estatístico e o ajuste não muda nada.

### Resultado

Validação cruzada de 5 dobras sobre 3577 imagens, cada uma testada
exatamente uma vez, comparação **pareada** nas mesmas imagens de cada
dobra:

| Domínio | Baseline | Em produção | Ganho |
|---|---|---|---|
| Laboratório (PlantVillage) | 90,7% ± 0,2 | **95,3% ± 0,8** | +4,5 p.p. |
| Campo (PlantDoc) | 57,0% ± 4,7 | **74,0% ± 2,3** | +17,0 p.p. |

**Dez comparações pareadas, dez vitórias.** E em campo o desvio caiu pela
metade: o modelo não é só melhor, é mais consistente entre amostras.

Nas 6 imagens de `ml/validacao_externa/`, independentes de todo treino:
**6 de 6**, contra 4 de 6 do baseline, e com confiança bem maior nos
acertos (0,56 a 0,98 contra 0,43 a 0,81).

### Por que `class_weight` e descongelamento parcial, e não outra coisa

As duas lacunas apontadas antes neste projeto eram justamente essas: o
`class_weight` que o `ml/README.md` prometia e nunca entrou no treino, e
a ausência de uma etapa de ajuste fino (a base ficava congelada do começo
ao fim). O ganho veio de implementar as duas.

Só as 30 camadas finais da base são descongeladas, e as de
BatchNormalization ficam congeladas. As camadas iniciais detectam borda e
textura, que valem para qualquer imagem; descongelar tudo com poucas
fotos de campo causaria esquecimento catastrófico, que foi exatamente o
que aconteceu na tentativa anterior. A taxa de aprendizado é 1e-5, cem
vezes menor que a do treino original, pelo mesmo motivo.

### Ressalvas que ficam

**Aproximação assumida:** o Keras só aceita peso por classe, não por
amostra. O peso de domínio entra embutido na contagem efetiva por classe,
o que não é equivalente a pesar cada imagem. Funcionou na medição, mas
não é a formulação exata do problema.

**O dataset original do baseline não estava disponível** (`data/doenca`,
`data/dataset_hibrida`). O "laboratório" medido aqui é PlantVillage, da
mesma família mas não o mesmo recorte. A comparação entre os dois modelos
é justa, porque ambos foram medidos no mesmo conjunto.

**O viés do escuro não foi resolvido**, e nem poderia: é estrutural, de
um classificador fechado sem classe de rejeição. A guarda de qualidade de
imagem continua obrigatória, e este ajuste reforça isso.

**Nenhum conjunto de teste é foto do Pi.** PlantVillage é folha arrancada
em fundo uniforme; PlantDoc é foto de web. A captura real fica entre os
dois, e o número de produção só existirá depois da coleta na estufa.

Reprodutível por `ml/src/training/ajuste_dois_dominios.py`, que registra
no cabeçalho de onde veio cada dado e cada decisão.

## Interpolação: treino e produção usam métodos diferentes

| Onde | Chamada | Interpolação |
|---|---|---|
| Treino | `image_dataset_from_directory(...)` | **bilinear** (padrão) |
| Script de comparação e Grad-CAM | `load_img(..., target_size=(224,224))` | **nearest** (padrão) |
| Produção | `imagem.resize(..., NEAREST)` | nearest |

A medição que fixou NEAREST em produção comparava a saída da API com a
do **script de comparação**, não com o pipeline de treino. É uma
inconsistência real, e o comentário no código que afirmava que o treino
usou `load_img` estava errado (corrigido).

**ATUALIZAÇÃO (2026-10-24):** com o modelo de dois domínios, a
preferência passou a depender do DOMÍNIO, não do modelo. Medido nos
conjuntos intocados: em laboratório bilinear ganha de 1 ponto; em foto de
campo, NEAREST ganha de 7. Como o caso de uso é foto de estufa, NEAREST
continua sendo o certo, e **nenhuma linha de código precisou mudar**. A
medição abaixo é do modelo anterior.

**Alinhar com o treino PIORAVA o resultado**, e por isso nada foi
trocado:

| Conjunto | NEAREST (produção) | BILINEAR (igual ao treino) |
|---|---|---|
| PlantDoc test (28) | **57,1%** | 42,9% |
| PlantDoc train (249) | **57,0%** | 51,4% |

Numa amostra de 6 imagens, bilinear parecia melhor por ser mais estável
e mais confiante. Com 277, nearest ganha em todas as fatias. Fica o
registro: a inconsistência existe, mas corrigi-la pela teoria custaria
acerto na prática, e acerto medido vale mais que coerência de pipeline.

### Subproduto: as decisões são frágeis

Reencodar a mesma imagem em JPEG, mesmo com qualidade alta, troca a
classe prevista em parte dos casos. Não é defeito da compressão do
`edge/`: é sintoma de decisões tomadas perto do limiar, que qualquer
perturbação de pixel desloca.

## Pendências

- Documentar o gap entre F1 no dataset e desempenho em foto de campo,
  que é a dupla métrica que `ml/README.md` já exige. Depende do João
  entregar os números.
- Corrigir as contradições do TC1 citadas em `docs/tcc/README.md`
  (câmera V2 contra V3, contagem de classes), agora que o número de
  classes em produção está decidido e registrado aqui.
- O catálogo agronômico tem uma inconsistência na classe inativa
  `vira_cabeca`: o texto diz "vírus transmitido pela mosca-branca", mas
  vira-cabeça (Tospovirus) é transmitido por tripes; quem a
  mosca-branca transmite é o begomovírus. Como a classe está inativa,
  isso não chega a produtor nenhum, mas tem que ser resolvido antes de
  reativá-la. Confirmar com o Carlos.
