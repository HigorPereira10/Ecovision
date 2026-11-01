# Validação de campo: efeito da distância no diagnóstico

**Data:** 2026-10-28
**Dispositivo:** `ecovision-pi-01`, placa soldada definitiva
**Sujeito:** um pé de tomate em vaso, com folhas verdes e folhas secas na mesma planta

Primeira validação de campo do projeto. Até aqui o modelo só tinha sido
avaliado contra dataset (95,3% laboratório) e contra foto de campo avulsa
(74,0%), sem controle de geometria. Este experimento isola a **distância
entre a câmera e a planta** e mede o efeito dela no diagnóstico.

---

## Onde estao as imagens citadas

As capturas cruas deste experimento (`d09_*.jpg` a `d30_*.jpg` e
`preliminar_sem_controle/`) **nao estao versionadas**: sao 20 MB de JPEG
do dispositivo, e o git guardaria esse binario para sempre. Elas seguem
para o deposito do Zenodo (ver `docs/tcc/zenodo-deposito.md`) e
continuam na maquina de quem rodou o experimento.

O que esta aqui no repositorio e a analise, que e o que permite conferir
a conclusao sem rebaixar as imagens: `gradcam/grade_gradcam.png`,
`oclusao/grade_oclusao.png`, `oclusao/oclusao.json`, `ladrilhos.json` e
`porta_resumo.json`.

---

## Por que existe

A pergunta surgiu de um acidente: duas capturas da mesma planta, com
minutos de diferença, deram classes opostas. Antes de culpar o modelo era
preciso saber se a variação vinha dele ou da cena.

---

## Protocolo

Quatro distâncias, **três capturas em cada uma, sem tocar em nada entre
elas**. As três repetições são o controle: elas medem quanto o resultado
varia com a cena parada, e só acima desse valor faz sentido atribuir uma
diferença à distância.

Captura pelo código de produção (`edge/src/capture.py`), com o flash
acionado pelo MOSFET da placa. Inferência pelo mesmo
`cloud/app/core/inference.py` que roda em produção, modelo de 3 classes.

As capturas **não passaram pela nuvem**, para não gravar foto de teste no
banco de produção.

---

## Resultados

Probabilidade por classe, em porcentagem.

| Arquivo | saudavel | pinta_preta | septoriose | Vencedora | Guarda de qualidade |
|---|---|---|---|---|---|
| `d30_1.jpg` | 88.7 | 10.8 | 0.5 | saudavel | passou |
| `d30_2.jpg` | 81.1 | 17.8 | 1.1 | saudavel | passou |
| `d30_3.jpg` | 87.4 | 11.8 | 0.8 | saudavel | passou |
| **média 30cm** | **85.7** | **13.5** | **0.8** | saudavel | |
| `d20_1.jpg` | 61.0 | 32.4 | 6.6 | saudavel | passou |
| `d20_2.jpg` | 45.2 | 45.7 | 9.1 | pinta_preta | passou |
| `d20_3.jpg` | 57.6 | 33.2 | 9.2 | saudavel | passou |
| **média 20cm** | **54.6** | **37.1** | **8.3** | **ALTERNOU** | |
| `d15_1.jpg` | 26.7 | 69.5 | 3.7 | pinta_preta | passou |
| `d15_2.jpg` | 21.2 | 74.5 | 4.3 | pinta_preta | passou |
| `d15_3.jpg` | 21.7 | 74.5 | 3.8 | pinta_preta | passou |
| **média 15cm** | **23.2** | **72.9** | **3.9** | pinta_preta | |
| `d09_1.jpg` | 55.9 | 31.6 | 12.5 | saudavel | passou |
| `d09_2.jpg` | 37.6 | 47.6 | 14.8 | pinta_preta | passou |
| `d09_3.jpg` | 42.6 | 42.4 | 15.0 | saudavel | passou |
| **média 9cm** | **45.3** | **40.5** | **14.1** | **ALTERNOU** | |

### Metadados da câmera

| Distância | Foco escolhido | Erro de foco | Lux | Ganho | Nitidez | Pixels estourados |
|---|---|---|---|---|---|---|
| 30cm | 79.5 a 84.7 cm | 2.7x | 56.9 | 4.28 | 243 | 0.07% |
| 20cm | 39.2 a 40.5 cm | 2.0x | 76.3 | 3.32 | 125 | 0.14% |
| **15cm** | 24.1 a 24.6 cm | **1.6x** | 90.1 | 2.73 | **157** | 0.24% |
| 9cm | 15.4 a 16.0 cm | 1.7x | 122.7 | 2.00 | **97** | 0.42% |

Nitidez é a variância do laplaciano no recorte central: quanto maior, mais
nítido. Erro de foco é a razão entre a distância que a lente escolheu e a
distância real do sujeito.

---

## O que o experimento mostra

### 1. O modelo é repetível, a cena é que muda a resposta

Com a cena parada, as três capturas dão a mesma classe e a confiança varia
poucos pontos (7.6 no pior caso, a 30cm). Isso elimina instabilidade do
modelo como explicação e autoriza atribuir as diferenças entre distâncias
à própria distância.

### 2. Existe um ponto ótimo, e são os 15cm

A curva **sobe e desce**. Não é "quanto mais perto, melhor":

```
30cm   pinta_preta 13.5%   saudavel estável
20cm   pinta_preta 37.1%   CLASSE ALTERNA
15cm   pinta_preta 72.9%   pinta_preta estável   <- ótimo
 9cm   pinta_preta 40.5%   CLASSE ALTERNA
```

Os 15cm dão simultaneamente a maior confiança (72.9%) e o menor
espalhamento entre repetições (5 pontos). É a distância que o Blueprint já
especificava, por causa da distância de trabalho da Camera Module 3. Agora
existe medição.

### 3. Errar a distância inverte o diagnóstico, não só o degrada

A 20cm e a 9cm **a classe vencedora muda entre capturas idênticas**. A
`d20_2` virou por meio ponto percentual: 45.7 contra 45.2.

Em produção, com ciclo de 2 horas, isso significaria alerta aparecendo e
sumindo sozinho, sem nada ter mudado na estufa.

### 4. O autofoco nunca encontrou o sujeito

Erro de 1.6x a 2.7x nas doze capturas. A lente sempre focou mais longe que
a planta. A 15cm ela usou 4.13 dioptrias quando o correto seria 6.67.

### 5. A degradação a 9cm é de foco, não de luz

Duas hipóteses foram testadas:

- **Estouro de luz: descartada.** Menos de 0.5% de pixels saturados em
  todas as distâncias. A exposição automática compensou o LED mais próximo
  baixando o ganho de 4.28 para 2.00.
- **Perda de foco: sustentada.** A 9cm a nitidez cai 38% frente aos 15cm
  (97 contra 157). De perto a profundidade de campo encolhe, então o mesmo
  erro relativo de foco borra muito mais.

### 6. A guarda de qualidade aprovou todas as doze

O que está correto: ela filtra imagem escura e sem textura
([ADR 0016](../../../docs/decisions/0016-guarda-de-qualidade-de-imagem.md)),
não imagem mal enquadrada. Hoje nada no sistema recusa uma captura por
distância errada, nem por decisão apertada entre classes.

---

## Ressalvas

Três, e nenhuma invalida o resultado principal, mas todas precisam ser
ditas se alguém questionar:

1. **A série de 15cm tem um confundidor.** Além de aproximar, o vaso foi
   girado. A tendência de 30cm para 20cm já existia sem o giro, e os 15cm
   continuam a mesma curva, mas o ponto não é limpo. Refazer com suporte
   fixo e sem girar.
2. **A métrica de nitidez a 30cm não vale.** Ali o que está nítido é o
   rejunte do azulejo do fundo, que é alto contraste. A comparação justa é
   entre 15cm e 9cm, onde a planta domina o quadro nas duas.
3. **Não existe diagnóstico de referência.** O sistema afirma pinta preta
   com 72.9% quando bem enquadrado, e não há laudo de agrônomo dizendo se
   está certo. A planta tem folhas secas visíveis, mas folha velha e
   sintoma de doença não são a mesma coisa. **Confirmar com o Carlos.**

---

## Consequências para o projeto

| Pendência | Status antes | Status depois |
|---|---|---|
| Case com 15cm rígidos | preferência de montagem | **requisito medido de precisão** |
| Travar a lente em 6.67 dioptrias | otimização de tempo de ciclo | **justificado por 12 capturas** |
| Limiar mínimo de confiança | não existia | **proposta nova**, ver abaixo |

### Sobre o limiar de confiança

`cloud/app/core/inference.py` grava a classe de maior pontuação sem piso de
confiança. Nas capturas a 20cm, o sistema teria gravado e alertado assim:

| Ciclo | O que o produtor veria |
|---|---|
| `d20_1` | planta saudável |
| `d20_2` | **alerta de pinta preta** |
| `d20_3` | planta saudável |

Sem nada ter mudado. Decidir um piso, e o que o app mostra abaixo dele, é
decisão de grupo e depende do trabalho de calibração do modelo.

---

## Pasta `preliminar_sem_controle/`

Três capturas feitas **antes** do protocolo, com distância, flash e
enquadramento variando ao mesmo tempo. Servem de ilustração, **não de
evidência**, e foram o que motivou o experimento.

| Arquivo | Condição | Resultado |
|---|---|---|
| `01_planta_inteira_sem_flash.jpg` | ~10cm estimados, sem flash | saudavel 83.6% |
| `02_folha_proxima_com_flash.jpg` | ~7cm estimados, com flash | pinta_preta 54.6% |
| `03_distancia_nao_confirmada.jpg` | distância revisada depois | pinta_preta 62.2% |

As duas primeiras passaram pela nuvem e estão no banco de produção, como
registros `29` e `30`.

---

## Como reproduzir

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

As imagens estão em resolução nativa (4608x2592), que é a que sai da
câmera. `preprocessar_imagem` reduz para 224x224 com `NEAREST`, então
redimensionar os arquivos antes mudaria os números.
