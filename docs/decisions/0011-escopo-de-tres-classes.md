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
