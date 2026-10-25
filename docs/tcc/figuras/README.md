# Figuras do TCC

Cada figura existe em dois formatos. Use o **PNG** para colar no Word
(300 dpi, já no tamanho certo) e guarde o **SVG** para quem precisar
reeditar sem perder qualidade.

Os dados por trás das figuras 1 a 6 estão em
[`../resultados-medidos.md`](../resultados-medidos.md), com os valores
em tabela para o texto corrido.

## Onde cada uma entra

| Arquivo | Capítulo sugerido | O que mostra |
|---|---|---|
| `01-matriz-confusao-laboratorio` | Resultados | 300 imagens retidas, 94,3%, F1 0,943. A linha "Saudável" é 0 / 0 / 100 |
| `02-matriz-confusao-campo` | Resultados | 27 imagens retidas, 74,1%, F1 0,744 |
| `03-comparacao-por-dominio` | Resultados | Baseline contra o modelo atual, validação cruzada de 5 dobras |
| `04-distribuicao-das-imagens` | Material e Métodos | 1.100 por classe em laboratório contra 137/79/60 em campo |
| `05-curva-de-treino-baseline` | Material e Métodos | 14 épocas, treino e validação em painéis separados |
| `06-gradcam-modelo-producao` | Resultados | Onde o modelo olha para decidir, nas 6 imagens de validação externa |
| `07-pipeline-captura-ao-diagnostico` | Material e Métodos | Fluxo real, da captura no Pi até a tela do aplicativo |
| `08-mer-banco-de-dados` | Material e Métodos | As 8 tabelas, com chaves, cardinalidades e a cadeia de posse |
| `09-diagrama-de-classes` | Material e Métodos | Entidades e serviços implementados, e o que caiu em relação ao TC1 |
| **`16-app-telas-conjunto`** | Resultados ou Material e Métodos | **As seis telas do aplicativo em grade 3x2, já montada e rotulada de (a) a (f). É este arquivo que vai no TCC** |
| `10` a `15` | (avulsos) | As mesmas seis telas, uma por arquivo, para quem precisar usar só uma |

## Três figuras que substituem material desatualizado

**`09-diagrama-de-classes`** substitui a Figura 2 antiga. Aquela trazia
`classificarMultimodal()`, `Produtor.receberAlerta()` e
`notificacao_ativa`, que nunca foram implementados. A nova traz o que
existe e declara, num quadro à parte, o que foi removido e por quê.

**`07-pipeline-captura-ao-diagnostico`** substitui a Figura 4 antiga,
que afirmava "cruza imagem com dados ambientais" e terminava num
"dashboard". Não há fusão multimodal, não há dashboard, e a ordem das
etapas estava trocada: a classificação acontece **antes** do envio ao
Storage, e a guarda de qualidade acontece antes de tudo.

**`08-mer-banco-de-dados`** substitui os Quadros 4 a 9. Aqueles
descreviam 6 tabelas com chaves UUID, uma tabela `produtores` e uma
`resultados_classificacao`. O sistema tem 8 tabelas, chaves inteiras
autoincremento, `usuarios` e `diagnosticos`.

## As telas do aplicativo

São seis capturas reais do aparelho, já tratadas: a barra de status do
Android e a barra de gestos foram removidas, e os endereços de e-mail
pessoais foram substituídos por `produtor@ecovision.app`, porque o
trabalho é público.

**Para o TCC, use `16-app-telas-conjunto.png`.** A grade de 3 por 2 com
os rótulos já está dentro da imagem, então basta inserir uma figura. Os
arquivos `10` a `15` existem para o caso de uma tela precisar aparecer
sozinha.

Faltam quatro telas (Início, Diagnóstico, Histórico e Alertas), porque
só fazem sentido com dados reais. Elas entram depois da coleta de campo.

## Como regerar

As figuras 1 a 5 saem de scripts sobre os dados de avaliação; a 6 exige
TensorFlow para calcular os gradientes; as 7 a 9 são SVG escrito à mão,
convertido para PNG com um navegador em modo headless.

Se precisar mexer, o caminho mais curto é editar o SVG direto (figuras
7 a 9) ou pedir a regeração com os dados novos (figuras 1 a 6), porque
todos os números vêm de `../resultados-medidos.md`.

## Paleta

As cores seguem a mesma convenção do diagrama de arquitetura em
`docs/architecture/diagramas/`: laranja para a camada de borda,
verde-azulado para a nuvem e índigo para o aplicativo. Nos gráficos, a
dupla azul e laranja foi verificada para daltonismo e para contraste, e
as matrizes de confusão usam um matiz só, porque codificam intensidade
e não categoria.
