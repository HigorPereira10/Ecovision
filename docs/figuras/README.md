# Figuras

Diagramas, fotos do protótipo, resultados do modelo e telas do aplicativo.
Os diagramas e gráficos têm a versão editável em SVG ao lado do PNG.

## Arquitetura

| Arquivo | Conteúdo |
|---|---|
| `arquitetura-cinco-camadas` | Arquitetura do sistema em cinco camadas, da aquisição no campo à consulta pelo produtor |
| `arquitetura-cinco-camadas-interface` | A mesma arquitetura, com a camada 5 denominada "Interface com o usuário" |
| `pipeline-captura-ao-diagnostico` | Fluxo de processamento, da captura no dispositivo à exibição no aplicativo |
| `diagrama-casos-de-uso` | Diagrama de casos de uso do sistema |
| `diagrama-de-classes` | Diagrama de classes das entidades de domínio e dos serviços da nuvem |
| `modelo-entidade-relacionamento` | Modelo entidade-relacionamento do banco de dados |

## Hardware

| Arquivo | Conteúdo |
|---|---|
| `esquematico-eletronico` | Esquema de ligações do dispositivo de campo |
| `conjunto-prototipado.jpeg` | Raspberry Pi 3 Model B+, protoboard com o conversor ADS1115 e o sensor DHT22 |
| `instalacao-em-operacao.png` | Dispositivo instalado sobre o tomateiro, em operação |

## Modelo

| Arquivo | Conteúdo |
|---|---|
| `distribuicao-imagens-publicas` | Distribuição das imagens de treino das bases públicas, por classe e por domínio |
| `curvas-treino-modelo-base` | Curvas de acurácia e de perda durante o treinamento do modelo base |
| `distribuicao-janelas-dominio-proprio` | Janelas rotuladas no domínio próprio, por enquadramento (o enquadramento F foi retido para teste) |
| `matriz-confusao-laboratorio` | Matriz de confusão do modelo de três classes em imagens de laboratório (300 amostras de teste) |
| `matriz-confusao-campo` | Matriz de confusão do modelo de três classes em imagens de campo (27 amostras de teste) |
| `comparacao-por-dominio` | Acurácia do modelo base e do modelo ajustado em dois domínios; as barras de erro indicam o desvio padrão entre as cinco dobras da validação cruzada |
| `matriz-confusao-dominio-proprio` | Matriz de confusão do modelo em produção no enquadramento retido; as linhas são as duas classes rotuladas e as colunas, as quatro que o modelo pode responder |
| `comparacao-tres-quatro-classes` | Classificação das mesmas janelas pelo modelo de três classes e pelo modelo em produção |
| `gradcam-dominio-proprio` | Mapas de ativação Grad-CAM do modelo em produção no enquadramento retido |

## Aplicativo

| Arquivo | Conteúdo |
|---|---|
| `apresentacao` | Tela de apresentação |
| `cadastro` | Cadastro |
| `pareamento` | Vínculo do dispositivo por código |
| `recuperacao-senha` | Recuperação de senha |
| `perfil-dispositivo` | Perfil, dispositivo vinculado e limiares de alerta (e-mail ocultado) |
| `inicio-situacao-sanitaria` | Início: distribuição dos diagnósticos recentes |
| `inicio-condicoes-estufa` | Início: séries de umidade do ar, temperatura e umidade do solo com as linhas de referência |
| `alertas` | Alertas |
| `historico-distribuicao` | Histórico: distribuição dos diagnósticos por classe |
| `diagnostico-saudavel` | Diagnóstico: folha sadia |
| `diagnostico-estresse` | Diagnóstico: estresse foliar |
| `diagnostico-septoriose` | Diagnóstico: septoriose |
| `diagnostico-pinta-preta` | Diagnóstico: pinta-preta |
| `financeiro.jpg` | Módulo de registro de despesas |

As telas de septoriose e pinta-preta foram capturadas com o modelo de três
classes, sobre a planta que o modelo em produção classifica como estresse
foliar; elas ilustram o formato da recomendação de cada doença, e não um
diagnóstico confirmado.
