# Evidências do lado IoT, para quem está trabalhando no modelo

**Gerado em:** 2026-10-29
**Origem:** sessão de hardware e validação de campo de 2026-10-28
**Dispositivo:** `ecovision-pi-01`, Raspberry Pi 3B+ com placa soldada definitiva

Este documento existe para separar duas conversas que estavam
misturadas. Tudo aqui é **medição feita no dispositivo real**, com as
fotos citadas por caminho. Nada aqui é opinião sobre arquitetura de
modelo: as perguntas que dependem disso estão reunidas no final, sem
resposta de propósito.

O que **não** está aqui: montagem, solda, pinagem, barramento I2C,
sensores de solo e ar. Isso fica no lado IoT e não muda nada no modelo.

---

## 1. O que o hardware entrega ao modelo, exatamente

A cadeia completa, para não haver dúvida sobre o que chega na entrada da
rede:

| Etapa | O que acontece | Onde |
|---|---|---|
| Captura | Camera Module 3 (`imx708`), JPEG nativo **4608x2592**, autofoco `AfMode.Auto` | `edge/src/capture.py` |
| Iluminação | LED de potência 5V por MOSFET IRLZ44N, aceso **durante toda a captura** | `edge/src/actuators/led_flash.py` |
| Compressão | Pillow com libjpeg-turbo, `quality=70`. Arquivo final de **204 KB a 718 KB** | `edge/src/compress.py` |
| Transporte | POST para a API, fila offline em JSON Lines se a rede cair | `edge/src/upload/uploader.py` |
| Guarda | Brilho e textura avaliados **antes** de classificar | `cloud/app/core/inference.py` |
| Pré-processamento | 224x224, RGB, float32 **cru de 0 a 255**, resize `NEAREST` | idem |
| Inferência | TFLite, 3 saídas, `argmax` sem piso de confiança | idem |

Três detalhes dessa cadeia são contraintuitivos e já custaram tempo:

**Não normalizar por fora.** O modelo exportado tem a camada de
normalização da MobileNetV2 dentro do grafo. Dividir por 255 de novo não
levanta erro: as predições colapsam para `saudavel` com cerca de 90% em
qualquer foto, inclusive folha visivelmente doente.

**O método de resize muda diagnóstico.** Medido nos conjuntos de teste
intocados: em laboratório (300 imagens) `BILINEAR` ganha de 1 ponto, em
campo (28 imagens) `NEAREST` ganha de 7. Como o sistema opera sobre foto
de estufa, `NEAREST` está em produção. Redimensionar os arquivos antes de
rodar qualquer experimento **muda os números**.

**Cena escura rende arquivo maior.** O sensor compensa com ganho alto e
ruído não comprime. Tamanho de arquivo é, indiretamente, uma medida de
qualidade de iluminação.

---

## 2. Inventário das fotos

Todas em `ml/validacao_campo/2026-10-28-distancia/`, resolução nativa,
saídas do pipeline de produção.

**Experimento controlado, 12 arquivos.** Quatro distâncias, três
capturas em cada, sem tocar em nada entre as três:

```
d30_1.jpg  d30_2.jpg  d30_3.jpg     30 cm
d20_1.jpg  d20_2.jpg  d20_3.jpg     20 cm
d15_1.jpg  d15_2.jpg  d15_3.jpg     15 cm
d09_1.jpg  d09_2.jpg  d09_3.jpg      9 cm
```

**Capturas preliminares, 3 arquivos** em `preliminar_sem_controle/`.
Feitas antes do protocolo, com distância, flash e enquadramento variando
ao mesmo tempo. **Servem de ilustração, não de evidência.**

Sujeito: um pé de tomate em vaso, com folhas verdes e folhas secas na
mesma planta. A planta chegou poucos dias antes e pegou pouco sol no
período, o que é relevante e volta na seção 7.

As capturas do experimento **não passaram pela nuvem**, para não gravar
foto de teste no banco de produção. As duas primeiras preliminares
passaram e estão como registros `29` e `30`.

---

## 3. O experimento de distância

Probabilidade por classe, em porcentagem. Inferência pelo mesmo
`cloud/app/core/inference.py` que roda em produção.

| Arquivo | saudavel | pinta_preta | septoriose | Vencedora |
|---|---|---|---|---|
| `d30_1.jpg` | 88.7 | 10.8 | 0.5 | saudavel |
| `d30_2.jpg` | 81.1 | 17.8 | 1.1 | saudavel |
| `d30_3.jpg` | 87.4 | 11.8 | 0.8 | saudavel |
| **média 30cm** | **85.7** | **13.5** | **0.8** | saudavel |
| `d20_1.jpg` | 61.0 | 32.4 | 6.6 | saudavel |
| `d20_2.jpg` | 45.2 | 45.7 | 9.1 | pinta_preta |
| `d20_3.jpg` | 57.6 | 33.2 | 9.2 | saudavel |
| **média 20cm** | **54.6** | **37.1** | **8.3** | **ALTERNOU** |
| `d15_1.jpg` | 26.7 | 69.5 | 3.7 | pinta_preta |
| `d15_2.jpg` | 21.2 | 74.5 | 4.3 | pinta_preta |
| `d15_3.jpg` | 21.7 | 74.5 | 3.8 | pinta_preta |
| **média 15cm** | **23.2** | **72.9** | **3.9** | pinta_preta |
| `d09_1.jpg` | 55.9 | 31.6 | 12.5 | saudavel |
| `d09_2.jpg` | 37.6 | 47.6 | 14.8 | pinta_preta |
| `d09_3.jpg` | 42.6 | 42.4 | 15.0 | saudavel |
| **média 9cm** | **45.3** | **40.5** | **14.1** | **ALTERNOU** |

### Metadados da câmera

| Distância | Foco escolhido | Erro de foco | Lux | Ganho | Nitidez | Pixels estourados |
|---|---|---|---|---|---|---|
| 30cm | 79.5 a 84.7 cm | 2.7x | 56.9 | 4.28 | 243 | 0.07% |
| 20cm | 39.2 a 40.5 cm | 2.0x | 76.3 | 3.32 | 125 | 0.14% |
| **15cm** | 24.1 a 24.6 cm | **1.6x** | 90.1 | 2.73 | **157** | 0.24% |
| 9cm | 15.4 a 16.0 cm | 1.7x | 122.7 | 2.00 | **97** | 0.42% |

Nitidez é a variância do laplaciano no recorte central. Erro de foco é a
razão entre a distância que a lente escolheu e a distância real.

### O que isso sustenta

**O modelo é repetível, a cena é que muda a resposta.** Com a cena
parada, as três capturas dão a mesma classe e a confiança varia poucos
pontos (7.6 no pior caso, a 30cm). Isso elimina instabilidade do modelo
como explicação e autoriza atribuir as diferenças entre distâncias à
própria distância. **É o controle que faz o resto do experimento valer.**

**A curva sobe e desce, com ótimo em 15cm.** Não é "quanto mais perto,
melhor":

```
30cm   pinta_preta 13.5%   saudavel estável
20cm   pinta_preta 37.1%   CLASSE ALTERNA
15cm   pinta_preta 72.9%   pinta_preta estável   <- ótimo
 9cm   pinta_preta 40.5%   CLASSE ALTERNA
```

Os 15cm dão ao mesmo tempo a maior confiança (72.9%) e o menor
espalhamento entre repetições (5 pontos).

**Errar a distância inverte o diagnóstico, não só o degrada.** A 20cm e
a 9cm a classe vencedora muda entre capturas idênticas. A `d20_2` virou
por meio ponto percentual: 45.7 contra 45.2. Em produção, com ciclo de 2
horas, isso significaria alerta aparecendo e sumindo sozinho, sem nada
ter mudado na estufa.

**O autofoco nunca encontrou o sujeito.** Erro de 1.6x a 2.7x nas doze
capturas, sempre focando mais longe que a planta. A 15cm a lente usou
4.13 dioptrias quando o correto seria 6.67.

**A degradação a 9cm é de foco, não de luz.** Estouro de luz foi
descartado: menos de 0.5% de pixels saturados em todas as distâncias, e
a exposição automática compensou o LED mais próximo baixando o ganho de
4.28 para 2.00. Perda de foco se sustenta: a nitidez cai 38% frente aos
15cm (97 contra 157), porque de perto a profundidade de campo encolhe e
o mesmo erro relativo borra muito mais.

### Ressalvas, que precisam ser ditas se alguém questionar

1. **A série de 15cm tem um confundidor.** Além de aproximar, o vaso foi
   girado. A tendência de 30cm para 20cm já existia sem o giro, e os
   15cm continuam a mesma curva, mas o ponto não é limpo. **Vai ser
   refeito com suporte fixo.**
2. **A nitidez a 30cm não vale.** Ali o que está nítido é o rejunte do
   azulejo do fundo, que é alto contraste. A comparação justa é entre
   15cm e 9cm, onde a planta domina o quadro nas duas.
3. **Não existe diagnóstico de referência.** O sistema afirma pinta
   preta com 72.9% quando bem enquadrado, e **não há laudo de agrônomo**
   dizendo se está certo. Pendente com o Carlos.

---

## 4. Capturas preliminares, sem controle

| Arquivo | Condição | Resultado |
|---|---|---|
| `01_planta_inteira_sem_flash.jpg` | ~10cm estimados, sem flash | saudavel 83.6% |
| `02_folha_proxima_com_flash.jpg` | ~7cm estimados, com flash | pinta_preta 54.6% |
| `03_distancia_nao_confirmada.jpg` | distância revisada depois | pinta_preta 62.2% |

Foram o que motivou o experimento: duas capturas da mesma planta, com
minutos de diferença, deram classes opostas. Antes de culpar o modelo
era preciso saber se a variação vinha dele ou da cena. Vinha da cena.

---

## 5. O que o flash faz, medido

Medir efetividade de flash por **brilho médio da imagem é inútil**: a
exposição automática compensa e a razão sai em 1.0x. Isso quase levou à
conclusão errada de que o flash não funcionava. As métricas certas são
Lux e ganho analógico:

| Métrica | Sem LED | Com LED |
|---|---|---|
| Lux | 3,89 | **36,5** (9,4x) |
| AnalogueGain | **16,0 (saturado)** | 7,42 |

O ganho é a prova mais forte: sem flash a câmera amplificava no máximo,
o que significa foto ruidosa. Com flash ela caiu para menos da metade.

**Consequência para o modelo:** o LED pontual ao lado da lente produz
reflexo especular branco na folha e sombra dura projetada. O Blueprint
especifica Ring LED em volta da lente justamente por isso, e **reflexo
branco pode ser confundido com lesão.** Essa troca está pendente.

O LED fica aceso durante **todo** o ciclo de captura, e quem domina esse
tempo é o autofoco: 5,6s com o LED junto da lente, 8s no ciclo real do
cron, 27s no pior caso medido. O "flash de 0,5s" do documento original
não corresponde à realidade.

---

## 6. A guarda de qualidade, e o que ela não pega

Em `cloud/app/core/inference.py`, limiares medidos e não arbitrados:
`BRILHO_MINIMO = 40.0` e `TEXTURA_MINIMA = 25.0`.

Ela existe porque o modelo empurra o que não entende para `saudavel`,
medido em 2026-10-17:

```
imagem preta      -> saudavel  0.93
quase preta       -> saudavel  0.97
ruído aleatório   -> saudavel  0.94
verde liso        -> saudavel  0.90
```

E a confiança **cresce** conforme a foto escurece. A mesma folha sadia,
escurecida artificialmente: 0.69 a 100% de luz, 0.91 a 50%, 0.97 a 25%.
Isso é falso negativo sistemático, o pior erro possível para o propósito
do projeto, porque o produtor não tem como desconfiar.

**O ponto importante para o modelo: a guarda aprovou todas as doze
capturas do experimento.** Isso está correto, ela filtra imagem escura e
sem textura ([ADR 0016](../../docs/decisions/0016-guarda-de-qualidade-de-imagem.md)),
não imagem mal enquadrada. **Hoje nada no sistema recusa uma captura por
distância errada, nem por decisão apertada entre classes.**

Limitação conhecida: ruído aleatório puro passa nos dois testes (brilho
127, textura 49).

---

## 7. O problema de fundo, que o IoT não resolve

A planta do experimento pegou pouco sol nos dias anteriores e tem folhas
secas visíveis. Isso levanta a pergunta que o lado IoT não tem como
responder: **as lesões são pinta preta ou estresse abiótico?**

Três fatos que convergem e por isso não se separam com o dado atual:

**O modelo não tem como diferenciar.** Três saídas, softmax, nenhuma
delas é "outro" ou "não sei". Toda entrada é distribuída entre
`septoriose`, `pinta_preta` e `saudavel`. O próprio ADR 0011 já
registra: *"uma folha de outra espécie continua sendo forçada para uma
das três classes. A solução de fundo seria uma classe 'outro' no treino,
ou um limiar de confiança calibrado, e isso depende de dado novo."*

**Existe viés medido na direção exata do problema.** Na validação
externa de 2026-10-17, 2 de 3 folhas sadias foram classificadas como
pinta preta:

| Imagem | Esperado | Previsto | Confiança |
|---|---|---|---|
| `saudavel_01` | saudavel | **pinta_preta** | 0,47 |
| `saudavel_02` | saudavel | **pinta_preta** | 0,52 |
| `saudavel_03` | saudavel | saudavel | 0,65 |

O ADR 0011 anota a consequência: leva o produtor a pulverizar fungicida
sem necessidade.

**Nenhuma das duas hipóteses é falsificável com o dado de hoje.**
Doença real e folha estressada caindo no viés conhecido **predizem a
mesma saída de 72.9%.** Sem laudo do Carlos, o experimento de distância
prova repetibilidade e sensibilidade à geometria, mas não prova acerto.

Diferença visual relatada na literatura, para a pergunta objetiva ao
agrônomo: pinta preta (*Alternaria solani*) dá lesão discreta com
**anéis concêntricos** e **halo amarelo**, começando pelas folhas
velhas; estresse abiótico dá amarelecimento **difuso** ou queima de
**borda e ponta**, sem anéis. A pergunta ao Carlos é: existe mancha com
anéis concêntricos, ou é só borda secando?

---

## 8. Contexto de desempenho já medido (ADR 0017)

Para não refazer medição que já existe:

| Domínio | O que é | Acurácia | F1 | Falso negativo | Falso positivo |
|---|---|---|---|---|---|
| Laboratório | folha arrancada, fundo uniforme, luz de estúdio | 94,3% | 0,943 | 2,5% | 0,0% |
| Campo | planta na lavoura, fundo heterogêneo, luz variável | 74,1% | 0,744 | 5,3% | indeterminado |

Inferência em 33,7 ms no p95, contra meta de 500 ms.

**A captura real do Pi fica entre os dois domínios**, então nenhum dos
dois números sozinho descreve o sistema. O falso positivo de campo está
declarado pendente e não reprovado: são 2 erros em 8 imagens, e o
intervalo de Wilson a 95% vai de **7,1% a 59,1%**, com a meta de 15%
dentro dele. O ADR aponta o que resolve: coleta de campo com planta
sadia, que produz dezenas de capturas exatamente dessa natureza.

Já existe `ml/data/plantdoc_tomate/` com divisão train/test e
`plantdoc_tomate_divisao.csv`, usado na medição de 277 fotos de campo.
Nenhuma dessas imagens foi vista no treino, e a prova está no próprio
resultado: `train` e `test` deram 57,0% e 57,1%, praticamente iguais.

---

## 9. O que o lado IoT pode coletar daqui para frente

Isto é a parte mais acionável deste documento, porque é capacidade real
e já montada, não proposta.

**Série temporal de planta estressada em recuperação.** A planta está
estressada agora e vai se recuperar conforme pegar sol. Fotografá-la
todo dia, no mesmo suporte, a 15cm, produz uma série rotulada de **folha
estressada mas não doente**, que é justamente o dado que as buscas não
acharam público em RGB (o que existe sobre seca em tomate é
hiperespectral, não fotografia de câmera).

Custo: zero além do equipamento montado. Basta ligar a linha de captura
no cron, que é uma linha e o ambiente já foi testado:

```
0 */2 * * * .../edge/.venv/bin/python .../edge/src/main.py >> .../logs/captura.log 2>&1
```

A 2 horas por ciclo, isso dá 12 capturas por dia.

**Capturas múltiplas por ciclo.** O experimento mostrou que o sistema já
sabe distinguir o caso duvidoso: a 15cm as três repetições concordaram, a
20cm e a 9cm não. Tirar N fotos por ciclo em vez de uma custa poucos
segundos e entrega o sinal de concordância de graça. **Se o lado do
modelo quiser usar isso como critério, o IoT entrega.**

**Metadados por captura.** Lux, ganho, posição de lente e nitidez já são
legíveis, como mostra a tabela da seção 3. Hoje não são gravados no
banco. Se forem úteis como feature ou como filtro, é mudança pequena no
lado da borda.

**Geometria fixa.** A case com 15cm rígidos deixou de ser preferência de
montagem e passou a ser **requisito medido de precisão**. Travar a lente
em 6,67 dioptrias com `AfMode.Manual` está justificado pelas 12
capturas, e derruba o ciclo de 8s para menos de 2s.

---

## 10. Perguntas abertas, que são do lado do modelo

Deixadas sem resposta de propósito.

1. **Piso de confiança.** `rodar_inferencia()` grava a classe de maior
   pontuação sem nenhum piso. Nas capturas a 20cm o produtor veria
   "saudável", depois "**alerta de pinta preta**", depois "saudável", sem
   nada ter mudado. Qual o valor, como calibrar, e o que o app mostra
   abaixo dele?
2. **Classe "outro" ou abiótico.** O ADR 0011 descartou 10 classes
   porque sete chutariam. Acrescentar uma quarta classe mal treinada
   repete a decisão que o grupo já tomou contra. Existe dado que
   sustente?
3. **Concordância entre capturas** como critério de publicação do
   diagnóstico. O IoT entrega o dado, a regra é decisão de modelo.
4. **Domínio.** Vocês já pagaram 94,3% laboratório contra 74,1% campo.
   Dataset público de outra região e cultivar reintroduz o mesmo gap. Vale?
5. **Metadados como feature.** Nitidez e erro de foco preveem
   instabilidade de classe neste experimento. Isso é aproveitável ou é
   coincidência de n=12?

---

## 11. Como reproduzir os números da seção 3

```bash
cd cloud
./.venv/Scripts/python.exe - <<'EOF'
import os, sys
import numpy as np
from dotenv import load_dotenv
load_dotenv(); sys.path.insert(0, os.getcwd())
from app.core import inference as inf

modelo = os.path.join("..", os.environ["TFLITE_MODEL_PATH"])
interp = inf.carregar_modelo_tflite(modelo)
pasta = os.path.join("..", "ml", "validacao_campo", "2026-10-28-distancia")

for arq in sorted(os.listdir(pasta)):
    if not arq.endswith(".jpg"):
        continue
    b = open(os.path.join(pasta, arq), "rb").read()
    interp.set_tensor(interp.get_input_details()[0]["index"],
                      inf.preprocessar_imagem(b))
    interp.invoke()
    s = interp.get_tensor(interp.get_output_details()[0]["index"])[0]
    print(arq, inf._CLASSES_DO_MODELO[int(np.argmax(s))], "%.1f%%" % (s.max()*100))
EOF
```

Ordem das saídas do modelo: índice 0 `septoriose`, 1 `pinta_preta`,
2 `saudavel`. Vem do treino, onde
`tf.keras.utils.image_dataset_from_directory` ordena os diretórios
alfabeticamente, e tem que bater com `CLASSES` de
`ml/src/export/convert_tflite.py`.

**Não redimensionar os arquivos antes de rodar.** Eles estão em 4608x2592,
que é o que sai da câmera, e `preprocessar_imagem` reduz para 224x224 com
`NEAREST`. Reduzir antes muda os números.

---

## Referências no repositório

| Documento | O que tem |
|---|---|
| [`2026-10-28-distancia/README.md`](2026-10-28-distancia/README.md) | protocolo completo do experimento |
| [ADR 0011](../../docs/decisions/0011-escopo-de-tres-classes.md) | as 3 classes, ajuste de dois domínios, validação externa |
| [ADR 0016](../../docs/decisions/0016-guarda-de-qualidade-de-imagem.md) | foto ruim não vira diagnóstico |
| [ADR 0017](../../docs/decisions/0017-metas-revistas-por-dominio.md) | metas revistas, números por domínio |
| [ADR 0001](../../docs/decisions/0001-camera-module-3.md) | por que Camera Module 3 e não V2 |
| [`blueprint-v4.md`](../../docs/architecture/blueprint-v4.md) | seções 3.1, 3.2 e 10.2 |
| `cloud/app/core/inference.py` | guarda, pré-processamento, catálogo, inferência |
| `edge/src/capture.py` | captura e autofoco |
