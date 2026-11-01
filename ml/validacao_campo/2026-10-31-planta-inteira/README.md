# Capturas de 2026-10-31: planta inteira, sem controle de distância

**Dispositivo:** `ecovision-pi-01`, placa soldada
**Sujeito:** o mesmo pé de tomate do experimento de 2026-10-28, três dias depois

Quatro capturas tiradas durante uma sessão de hardware, **não sob
protocolo**. Servem como registro e como indício, **não como evidência
controlada**. Leia as ressalvas antes de citar qualquer número daqui.

---

## Resultados

| Arquivo | pinta_preta | saudavel | septoriose | Guarda |
|---|---|---|---|---|
| `seq_1.jpg` | 88,2 | 8,2 | 3,6 | passou |
| `seq_2.jpg` | 94,2 | 3,7 | 2,1 | passou |
| `iso_1.jpg` | **98,4** | 0,6 | 1,0 | passou |
| `iso_2.jpg` | 97,7 | 0,7 | 1,7 | passou |

`seq_1` e `seq_2` foram tiradas com 5 segundos de intervalo. Entre a série
`seq` e a série `iso`, os jumpers que apareciam no quadro foram afastados.

### Metadados

| Arquivo | Foco escolhido | Lux | Ganho | Nitidez | Arquivo |
|---|---|---|---|---|---|
| `seq_1` | 3,28 dpt = 30 cm | 31,1 | 8,75 | 38 | 1453 KB |
| `seq_2` | 3,10 dpt = 32 cm | 29,1 | 9,66 | 32 | 1461 KB |
| `iso_1` | 2,96 dpt = 34 cm | 30,0 | 10,04 | 34 | 1448 KB |
| `iso_2` | 2,87 dpt = 35 cm | 23,8 | 11,91 | 29 | 1469 KB |

---

## A distância não é 15cm

Três sinais independentes convergem para **26 a 35 cm**, e nenhum é 15:

| Sinal | Estimativa |
|---|---|
| Lente escolheu de 2,87 a 3,28 dioptrias | 30 a 35 cm |
| Lux caiu de 90,1 (a 15cm em 28/10) para ~30, pela lei do inverso do quadrado | ~26 cm |
| A planta inteira cabe no quadro | compatível com ~30 cm |

**O autofoco provavelmente não errou aqui.** O assunto está mesmo a ~30 cm.
A diferença em relação a 2026-10-28 é de enquadramento: lá o quadro pegava
algumas folhas de perto, aqui pega a planta inteira. São fotos de naturezas
diferentes.

---

## Ressalvas, que são sérias

**1. Não é comparação controlada com 2026-10-28.** Em 28/10, a ~30 cm, o
modelo disse `saudavel` 85,7%. Aqui, a ~30 cm, diz `pinta_preta` 88 a 98%.
Mas enquadramento, iluminação, ganho e nitidez mudaram todos ao mesmo tempo,
além de terem se passado três dias. Duas explicações cabem e os dados **não
separam as duas**:

- A planta piorou. As folhas têm visivelmente mais amarelamento e manchas
  escuras que em 28/10
- As condições de captura mudaram

**2. A confiança sobe conforme a imagem piora.** Ao longo das quatro, o ganho
subiu 36%, a nitidez caiu 24% e a confiança foi de 88% para 98%:

| Ganho | Nitidez | pinta_preta |
|---|---|---|
| 8,75 | 38 | 88,2% |
| 9,66 | 32 | 94,2% |
| 10,04 | 34 | 98,4% |
| 11,91 | 29 | 97,7% |

Isso tem precedente medido neste projeto. O comentário que justifica a guarda
de qualidade em `cloud/app/core/inference.py` registra, em 2026-10-17, que a
mesma folha sadia escurecida artificialmente ia de `saudavel` 0,69 a 0,97
conforme perdia luz. **A classe é outra, a forma é a mesma: imagem pior,
confiança maior.**

Com n=4 e variáveis confundidas (tempo, luz, ganho, nitidez, manuseio) não dá
para atribuir a subida a nenhuma delas. O que não se deve fazer é ler os
98,4% como "o sistema tem quase certeza".

**3. Não existe diagnóstico de referência.** Continua pendente com o Carlos.

**4. A nitidez não é comparável com a do preview.** O preview é 1280x720 e
estas são 4608x2592. Variância de laplaciano depende da resolução.

---

## O que é sólido

- **As capturas concordam entre si.** As duas de cada série dão a mesma
  classe com poucos pontos de diferença. O modelo está estável nesta cena
- **A guarda de qualidade aprovou as quatro**
- **O tamanho de arquivo (1,4 MB) está acima da faixa documentada** de
  204 KB a 718 KB do Blueprint. É o efeito do ganho alto: ruído não comprime.
  Importa para o dimensionamento de upload numa série de 24 h

---

## Contexto de hardware

Nesta sessão o **LED estava com defeito intermitente**: o GPIO18 caía sozinho
em 1/3 das amostras por contaminação na placa, e o LED piscava em vez de
acender firme. Uma comparação com LED ligado e desligado deu Lux 59,80 contra
59,72, ou seja **o flash não contribuiu nada** nestas capturas.

O que iluminou a cena foi a luz ambiente. Ver
[`docs/hardware/diagnostico-placa-2026-10-31.md`](../../../docs/hardware/diagnostico-placa-2026-10-31.md).

Isso é mais uma razão para não tratar estes números como medição: **a
condição de iluminação não é a de projeto.**

---

## Como reproduzir

Mesmo procedimento de
[`../2026-10-28-distancia/README.md`](../2026-10-28-distancia/README.md),
seção "Como reproduzir". As imagens estão em resolução nativa e
redimensionar antes muda os números.
