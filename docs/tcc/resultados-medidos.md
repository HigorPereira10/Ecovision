# Resultados medidos

Tabelas prontas para o capítulo "Resultados Obtidos". Cada número aqui
foi medido, não estimado, e a seção diz como.

**Data da medição:** 24/10/2026.
**Artefato avaliado:** `ml/models/modelo.tflite`, o mesmo que está
servindo em produção.

As figuras correspondentes estão em [`figuras/`](figuras/), em PNG de
300 dpi (para colar no Word) e SVG (para reeditar).

---

## 1. O modelo

| | |
|---|---|
| Arquitetura | MobileNetV2 com ajuste fino de dois domínios |
| Peso pré-treinado | ImageNet |
| Entrada | 224 x 224 x 3, pixels crus de 0 a 255 |
| Saída | 3 classes: septoriose, pinta-preta, saudável |
| Tamanho | 8,47 MB, float32, sem quantização |
| Camadas descongeladas | as 30 últimas da base, exceto as de BatchNormalization |
| Taxa de aprendizado | 1e-5 |
| Épocas | 10, com parada antecipada |
| Tamanho do lote | 16 |
| Ponderação | por classe e por domínio |
| Script | `ml/src/training/ajuste_dois_dominios.py` |

A ponderação por domínio existe porque há cerca de 12 imagens de
laboratório para cada uma de campo. Sem compensar, as fotos de campo
viram ruído estatístico e o ajuste não muda nada.

---

## 2. Divisão dos conjuntos

### Laboratório, PlantVillage

| Classe | Treino | Teste | Total |
|---|---|---|---|
| Septoriose (`mancha_septoria`) | 1.000 | 100 | 1.100 |
| Pinta-preta (`pinta_preta`) | 1.000 | 100 | 1.100 |
| Saudável (`folhas_saudaveis`) | 1.000 | 100 | 1.100 |
| **Total** | **3.000** | **300** | **3.300** |

### Campo, PlantDoc

| Classe | Treino | Teste | Total |
|---|---|---|---|
| Septoriose (`distrator_septoria`) | 127 | 10 | 137 |
| Pinta-preta (`pinta_preta`) | 70 | 9 | 79 |
| Saudável (`saudavel`) | 52 | 8 | 60 |
| **Total** | **249** | **27** | **276** |

A validação interna do treino veio de 12% das imagens de treino,
sorteadas antes de qualquer época. **Os conjuntos de teste acima nunca
entraram no treino**, e é sobre eles que todas as métricas das seções
3 a 7 foram calculadas.

Figura correspondente: `04-distribuicao-das-imagens`.

---

## 3. Desempenho global

| Domínio | Imagens | Acertos | Acurácia | IC 95% | F1 ponderado |
|---|---|---|---|---|---|
| Laboratório | 300 | 283 | **94,3%** | 91,1% a 96,4% | 0,943 |
| Campo | 27 | 20 | **74,1%** | 55,3% a 86,8% | 0,744 |

O acaso, com três classes, é 33,3%.

A distância de 20 pontos entre os domínios é a limitação central do
modelo e precisa ser declarada: ele foi treinado majoritariamente com
foto de laboratório (folha arrancada, fundo uniforme, luz de estúdio) e
se saiu pior em foto de campo. Para efeito de comparação, a literatura
(HO-LAM; NGUYEN, 2026) reporta a mesma arquitetura MobileNetV2 caindo de
99,77% para **28,57%** ao ser aplicada ao PlantDoc.

**A comparação não é direta**, e o texto do TCC precisa dizer isso: aquele
estudo avalia transferência **sem nenhum ajuste** com imagem de campo,
enquanto o modelo aqui descrito foi ajustado com os dois domínios ao mesmo
tempo. O valor serve para dimensionar a severidade do deslocamento de
domínio, não como comparação de desempenho entre sistemas.

---

## 4. Métricas por classe

### Laboratório

| Classe | Suporte | Precisão | Revocação | F1 |
|---|---|---|---|---|
| Septoriose | 100 | 0,914 | 0,960 | 0,937 |
| Pinta-preta | 100 | 0,967 | 0,870 | 0,916 |
| Saudável | 100 | 0,952 | **1,000** | **0,976** |

### Campo

| Classe | Suporte | Precisão | Revocação | F1 |
|---|---|---|---|---|
| Septoriose | 10 | 0,800 | 0,800 | 0,800 |
| Pinta-preta | 9 | 0,600 | 0,667 | 0,632 |
| Saudável | 8 | 0,857 | 0,750 | 0,800 |

A pinta-preta é a classe mais difícil em campo, e é ela que puxa o F1
ponderado para baixo.

---

## 5. Matrizes de confusão

Linha é a classe verdadeira, coluna é a prevista pelo modelo.

### Laboratório (300 imagens)

| | Septoriose | Pinta-preta | Saudável |
|---|---|---|---|
| **Septoriose** | **96** | 3 | 1 |
| **Pinta-preta** | 9 | **87** | 4 |
| **Saudável** | 0 | 0 | **100** |

Nenhuma das 100 folhas sadias foi classificada como doente.

### Campo (27 imagens)

| | Septoriose | Pinta-preta | Saudável |
|---|---|---|---|
| **Septoriose** | **8** | 2 | 0 |
| **Pinta-preta** | 2 | **6** | 1 |
| **Saudável** | 0 | 2 | **6** |

Figuras correspondentes: `01-matriz-confusao-laboratorio` e
`02-matriz-confusao-campo`.

---

## 6. Falso positivo e falso negativo

Definições adotadas, porque com três classes o termo é ambíguo:

- **Falso negativo:** planta doente classificada como saudável. É o erro
  que mais custa ao produtor, porque manda ignorar uma lavoura doente.
- **Falso positivo:** planta sadia classificada como doente.
- **Doença trocada:** uma doença confundida com a outra. Não é nem um
  nem outro, e tem consequência agronômica diferente.

| Métrica | Meta | Laboratório | Campo |
|---|---|---|---|
| Falso negativo | < 10% | **2,5%** (5/200) | **5,3%** (1/19) |
| IC 95% | | 1,1% a 5,7% | 0,9% a 24,6% |
| Falso positivo | <= 15% | **0,0%** (0/100) | 25,0% (2/8) |
| IC 95% | | 0,0% a 3,7% | 7,1% a 59,1% |
| Doença trocada | sem meta | 6,0% (12/200) | 21,1% (4/19) |

**O falso negativo cumpre a meta nos dois domínios.**

**O falso positivo de campo é indeterminado, não reprovado.** São 2
erros em 8 imagens, e o intervalo de confiança vai de 7,1% a 59,1%. A
meta de 15% está dentro do intervalo, então os dados não permitem
afirmar nem que passou nem que falhou. Afirmar "25% de falso positivo"
seria estatisticamente incorreto com essa amostra.

Esse é o buraco que a coleta de campo precisa fechar: ela vai gerar
dezenas de capturas de planta sadia em condição real, que é exatamente
a amostra que falta.

**Em campo, o erro dominante não é confundir doente com sadia.** Dos 7
erros, 4 são doença trocada por doença e apenas 1 é falso negativo.
Agronomicamente isso é mais brando: septoriose e pinta-preta são
fúngicas e as recomendações que o sistema emite convergem (eliminar
restos de cultura, evitar plantio perto de lavoura infectada, consultar
o agrônomo). O produtor é levado à ação certa mesmo quando o nome está
errado.

---

## 7. O modelo aprendeu ou decorou?

Acurácia alta levanta a suspeita de memorização. Três medições
independentes foram feitas para responder.

### 7.1 Acurácia removendo imagens parecidas com o treino

Dizer "a imagem de teste não estava no treino" não basta: o PlantVillage
é montado a partir de poucas folhas fotografadas várias vezes. Para cada
imagem de teste foi calculada a distância de Hamming do dHash de 64 bits
até a imagem de treino mais parecida, e a acurácia foi recalculada
descartando as mais próximas.

| Subconjunto | n | Acertos | Acurácia |
|---|---|---|---|
| Laboratório, tudo | 300 | 283 | 94,3% |
| Laboratório, nenhuma a <= 4 bits | 299 | 282 | 94,3% |
| **Laboratório, nenhuma a <= 10 bits** | **274** | **258** | **94,2%** |

Removendo as 26 imagens mais parecidas com o treino, 8,7% do conjunto, a
acurácia caiu 0,1 ponto. Se o acerto viesse de memorização, remover
justamente as imagens memorizáveis derrubaria o número.

### 7.2 Generalização entre domínios

O modelo treinou majoritariamente com PlantVillage e mantém 74,1% no
PlantDoc, que é outro conjunto, de outros fotógrafos, com fotos de web.
A referência da literatura para esse salto é 28,57% (HO-LAM; NGUYEN, 2026), medida sem ajuste de domínio.

### 7.3 Grad-CAM

Os mapas de ativação do modelo em produção caem sobre a lesão, não sobre
o fundo nem sobre artefatos da foto. Em `septoria_01` a atenção se
concentra na região lesionada e ignora a régua vermelha ao lado, que
seria o atalho mais óbvio. Nas folhas sadias a ativação é difusa, como
esperado quando não há sintoma a localizar.

Figura correspondente: `06-gradcam-modelo-producao`.

### 7.4 Curva de treino

Treino e validação permanecem próximos as 14 épocas inteiras,
terminando em 94,0% e 92,0%. Dois pontos de diferença. Modelo que
memoriza abre essa distância.

Figura correspondente: `05-curva-de-treino-baseline`.

---

## 8. Comparação com o modelo anterior

Validação cruzada de 5 dobras sobre 3.577 imagens, cada imagem testada
exatamente uma vez por um modelo que nunca a viu, com comparação
**pareada** nas mesmas imagens de cada dobra.

| Domínio | Baseline anterior | Em produção | Ganho |
|---|---|---|---|
| Laboratório | 90,7% +- 0,2 | **95,3% +- 0,8** | +4,6 p.p. |
| Campo | 57,0% +- 4,7 | **74,0% +- 2,3** | +17,0 p.p. |

Venceu nas 5 dobras dos dois domínios: 10 comparações pareadas, 10
vitórias. Em campo também ficou mais estável, com metade do desvio.

Figura correspondente: `03-comparacao-por-dominio`.

### Uma tentativa que não funcionou

Ajustar apenas com foto de campo subia campo para 69,3% e **derrubava**
laboratório de 90,7% para 78,2%, com 495 das 1.100 pinta-pretas de
laboratório sendo chamadas de septoriose. Era troca, não melhora. Treinar
com os dois domínios juntos eliminou a troca.

---

## 9. Latência

### 9.1 Inferência, por etapa

240 amostras (6 imagens x 40 repetições), com aquecimento descartado.
Processador AMD Ryzen, Python 3.11.9, delegado XNNPACK ativo.

| Etapa | Média | p50 | p95 | p99 | Máx |
|---|---|---|---|---|---|
| Guarda de qualidade | 8,80 | 9,16 | 12,04 | 14,24 | 29,76 |
| Pré-processamento | 5,28 | 5,39 | 7,04 | 8,39 | 11,90 |
| Inferência TFLite | 13,69 | 13,29 | 15,29 | 20,24 | 28,40 |
| **Total** | **27,77** | **28,13** | **33,71** | **36,89** | **70,06** |

Valores em milissegundos. **Contra a meta de 500 ms, o p95 de 33,7 ms
passa com 466 ms de folga.**

Dois achados que valem comentário: a guarda de qualidade custa 8,8 ms,
cerca de um terço do total, o que quantifica o preço de uma decisão de
segurança; e decodificar e redimensionar a imagem pesa quase tanto
quanto rodar a rede, contrariando a intuição de que o modelo é o
gargalo.

### 9.2 Resposta da API em produção

10 medidas contra o Railway, após 2 descartes de aquecimento, imagem
média de 140,5 KB, zero falhas.

| Medida | Média | p50 | p95 | Máx |
|---|---|---|---|---|
| `GET /health` (piso de rede) | 388,3 | 364,4 | 602,4 | 602,4 |
| `POST /diagnostico` (ponta a ponta) | 1.323,6 | 1.362,4 | 1.578,2 | 1.578,2 |

Subtraindo o piso de rede, sobram cerca de 998 ms para processar a
captura. Como a inferência local custa 28 ms, **a maior parte desse
tempo é transporte de imagem**, não computação: subir 140 KB até o
Railway e, de lá, subir a mesma imagem para o Supabase Storage, que é um
segundo salto de rede.

Não há meta de tempo para esse número, e a justificativa é de projeto:
a captura é assíncrona, nenhum usuário espera a resposta, e a fila
offline absorve lentidão ou queda. O limite real é o timeout do
dispositivo, de 30 segundos, o que dá folga de 19 vezes.

---

## 10. Testes automatizados

160 testes no total, todos passando.

### Nuvem, 128 testes

| Arquivo | Testes | O que cobre |
|---|---|---|
| `test_cadastro_e_pareamento` | 17 | cadastro, vínculo de dispositivo, código de pareamento |
| `test_email_verificacao` | 17 | verificação por e-mail, reenvio, intervalo mínimo |
| `test_diagnostico` | 13 | o endpoint de captura, de ponta a ponta |
| `test_inference` | 11 | modelo, guarda de qualidade, limiares |
| `test_security` | 11 | senha, JWT, bloqueio por tentativas |
| `test_historico` | 9 | listagem de diagnósticos e leituras |
| `test_alertas_ambientais` | 8 | limiares de temperatura, umidade do ar e do solo |
| `test_alertas` | 7 | listagem e marcação de lido |
| `test_alertas_dispositivo` | 7 | alertas por dispositivo |
| `test_escopo` | 7 | RBAC por posse de dispositivo |
| `test_auth` | 6 | login, refresh, recuperação de senha |
| `test_dispositivos` | 6 | listagem e metadados |
| `test_health` | 4 | estado de banco e modelo |
| `test_usuarios` | 4 | perfil do usuário autenticado |
| `test_cors` | 1 | cabeçalhos de origem cruzada |

### Dispositivo, 32 testes

| Arquivo | Testes | O que cobre |
|---|---|---|
| `test_soil_moisture` | 7 | leitura do ADS1115, calibração, canal configurável |
| `test_led_flash` | 6 | acionamento do MOSFET |
| `test_dht22` | 5 | leitura de temperatura e umidade, tolerância a falha |
| `test_uploader` | 5 | envio, autenticação, reenvio idempotente |
| `test_config` | 4 | variáveis de ambiente e valores padrão |
| `test_offline_queue` | 3 | **retenção da fila quando a rede cai** |
| `test_compress` | 2 | compressão JPEG antes do envio |

---

## 11. Endpoints da API

16 rotas, todas em produção.

| Método | Rota | Autenticação |
|---|---|---|
| GET | `/health` | nenhuma |
| POST | `/auth/register` | nenhuma |
| POST | `/auth/login` | nenhuma |
| POST | `/auth/refresh` | token de refresh |
| POST | `/auth/verify-email` | nenhuma |
| POST | `/auth/resend-code` | nenhuma |
| POST | `/auth/forgot-password` | nenhuma |
| POST | `/auth/reset-password` | nenhuma |
| GET | `/usuarios/me` | JWT |
| GET | `/dispositivos` | JWT |
| POST | `/dispositivos/vincular` | JWT |
| **POST** | **`/diagnostico`** | **credencial do dispositivo** |
| GET | `/diagnosticos` | JWT |
| GET | `/leituras` | JWT |
| GET | `/alertas` | JWT |
| PATCH | `/alertas/{id}/lido` | JWT |

`POST /diagnostico` é o único chamado pelo dispositivo. Todos os demais
servem ao aplicativo.

---

## 12. Medições do dispositivo

Medidas no `ecovision-pi-01`, com o código do projeto.

### Eficácia do flash

| Métrica | Sem flash | Com flash |
|---|---|---|
| Iluminância (lux) | 3,89 | **36,5** (9,4x) |
| Ganho analógico da câmera | **16,0** (saturado) | 7,42 |

O ganho analógico é a evidência mais forte: sem flash a câmera
amplificava no máximo do sensor e ainda faltava luz; com flash ela
recuou sozinha para menos da metade.

Nota de método: o brilho médio da imagem **não serve** como métrica,
porque a exposição automática compensa e as duas ficam iguais. Foi assim
que a primeira medição concluiu, erradamente, que o flash não funcionava.

### Circuito do flash

```
corrente       = (5 V - 3,2 V) / 6,8 ohm = 265 mA
potência no R1 = 0,265^2 x 6,8           = 0,48 W
```

O resistor é de 2 W, então opera a 24% da capacidade. Um de 1/4 W estaria
a 192% e abriria com o tempo.

### Tempo de ciclo

| Condição | Ciclo | LED aceso |
|---|---|---|
| Cena escura, LED mal posicionado | 27 s | 27 s |
| LED junto da lente | 5,6 s | 5,6 s |
| Ciclo real disparado pelo cron | 8 s | 8 s |

Quem domina esse tempo é o autofoco, não o flash.

### Alimentação e imagens

| | |
|---|---|
| `vcgencmd get_throttled` após 1h27 de uso | `0x0`, nenhum evento de subtensão |
| Temperatura do SoC em repouso | 44,5 graus, sem dissipador |
| Tamanho das imagens, qualidade 70 | 204 KB a 718 KB |

Cena escura rende arquivo maior, porque o sensor compensa com ganho alto
e ruído não comprime.

---

## 13. Calibração do sensor de solo

Medida em 11/10/2026, sensor alimentado em 3,3 V, 40 amostras por ponto.

| Condição | Valor bruto | Tensão | Variação |
|---|---|---|---|
| Seco, suspenso no ar | 17.468 | 2,184 V | 102 |
| Submerso até a linha | 7.179 | 0,897 V | 11 |

Faixa útil de 10.289 pontos.

**Pendência declarada:** recalibrar com o sensor em terra, não em água.
Água pura é o extremo absoluto de saturação, então o extremo molhado
real será maior que 7.179, e é solo que o limiar de alerta usa.

---

## 14. Validação externa

6 imagens que não pertencem a nenhum dos conjuntos de treino ou teste,
avaliadas pela API real em produção.

| Imagem | Verdadeiro | Previsto | Confiança |
|---|---|---|---|
| `pinta_preta_01.jpg` | pinta-preta | pinta-preta | 0,807 |
| `pinta_preta_03.jpg` | pinta-preta | pinta-preta | 0,906 |
| `saudavel_01.jpg` | saudável | saudável | 0,717 |
| `saudavel_02.jpg` | saudável | saudável | 0,958 |
| `saudavel_03.jpg` | saudável | saudável | 0,957 |
| `septoria_01.jpg` | septoriose | septoriose | 0,977 |

**6 de 6**, contra 4 de 6 do modelo anterior. O intervalo de confiança
de 6/6 vai de 61,0% a 100%, ou seja, a amostra é pequena demais para
sustentar sozinha qualquer afirmação. Vale como confirmação, não como
métrica principal.

---

## 15. O que ainda não foi medido

Declarar isto é parte do resultado.

- **Desempenho em foto tirada pelo Raspberry Pi.** Nenhum conjunto usado
  aqui é isso: PlantVillage é folha arrancada em fundo uniforme,
  PlantDoc é foto de web, e a captura real fica entre os dois.
- **Falso positivo em campo com amostra suficiente.** Ver a seção 6.
- **Desempenho com a planta real na estufa**, ao longo de um ciclo.
- **Uptime do dispositivo** em operação contínua.
- **Tempo de carregamento das telas do aplicativo** com volume real de
  dados. A tela de Histórico gera uma URL assinada por imagem, e essa é
  a única latência que o produtor sente de fato.
- **Redução de custo com fungicida**, que é a hipótese econômica por trás
  do módulo financeiro. O módulo registra os gastos; medir o efeito exige
  um ciclo de safra com e sem o sistema.

---

## 16. Referências citadas neste documento

Todas verificadas na fonte original, não escritas de memória. A lista
completa, com o mapa de onde citar cada uma no texto do TCC, está em
[`material-pronto-para-o-tcc.docx`](material-pronto-para-o-tcc.docx),
Parte 5.

- GEIRHOS, R. et al. Shortcut learning in deep neural networks.
  *Nature Machine Intelligence*, v. 2, n. 11, p. 665-673, 2020.
- HO-LAM, N.-B.; NGUYEN, T.-A. TinyCNN: a 193K-parameter network for
  on-device plant disease detection, with a cross-dataset robustness
  diagnosis. [arXiv:2609.20290](https://arxiv.org/abs/2609.20290), 2026.
- HUGHES, D. P.; SALATHÉ, M. An open access repository of images on plant
  health to enable the development of mobile disease diagnostics.
  [arXiv:1511.08060](https://arxiv.org/abs/1511.08060), 2015.
- SANDLER, M. et al. MobileNetV2: inverted residuals and linear
  bottlenecks. In: *IEEE/CVF CVPR*, 2018. p. 4510-4520.
- SELVARAJU, R. R. et al. Grad-CAM: visual explanations from deep networks
  via gradient-based localization. In: *IEEE ICCV*, 2017. p. 618-626.
- SINGH, D. et al. PlantDoc: a dataset for visual plant disease detection.
  In: *ACM CoDS-COMAD*, 2020. p. 249-253. Licença CC BY 4.0.
- WILSON, E. B. Probable inference, the law of succession, and statistical
  inference. *Journal of the American Statistical Association*, v. 22,
  n. 158, p. 209-212, 1927.
- ZHOU, K. et al. Domain generalization: a survey. *IEEE TPAMI*, v. 45,
  n. 4, p. 4396-4415, 2023.
