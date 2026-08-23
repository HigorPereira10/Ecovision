# ADR 0006 — Recomendações de manejo por classe de diagnóstico

**Status:** Decidido (primeira versão — orientação geral, não prescrição
técnica; ver "Ressalva" abaixo).

## Contexto

O campo `diagnosticos.recomendacao` (`cloud/app/db/models.py`) existia
desde o schema inicial, mas só com 2 classes de exemplo, placeholder, em
`cloud/app/core/inference.py`. Faltava uma recomendação de verdade para
cada uma das classes que o modelo de IA vai prever.

As 10 classes usadas aqui são as do dataset público **PlantVillage**
(tomate) — o mesmo conjunto citado em `ml/README.md` ("Frankenstein
Cirúrgico", 10 classes, Mosaic Virus como classe minoritária). Não é uma
lista inventada: é o conjunto padrão de 9 doenças/pragas + saudável
amplamente usado em trabalhos de classificação de doenças de tomate.

## Ressalva importante

As recomendações abaixo são **orientação agronômica geral** (o que
fazer em termos amplos: melhorar ventilação, evitar molhar folhagem,
usar cultivar resistente, etc.), pesquisada em mais de uma fonte técnica
por classe. **Não são prescrição de produto comercial, dose ou
receituário agronômico** — isso exige responsabilidade técnica (RT) de
um engenheiro agrônomo e está fora do que um protótipo de TCC deve
oferecer como conselho definitivo. Cada recomendação no sistema termina
com uma frase padrão reforçando isso.

## Decisão

| Classe (PlantVillage) | Tipo | Severidade | Recomendação (resumo) | Fontes |
|---|---|---|---|---|
| Saudável | — | — | Nenhuma recomendação (sem alerta) | — |
| Requeima (*Phytophthora infestans*) | Fungo | **alta** — Embrapa: perda de até 100% da produção sem manejo | Favorecida por umidade >90% e 11-23°C. Aplicar fungicida preventivo quando o clima for favorável; evitar molhar a folhagem na irrigação; remover folhas/plantas afetadas. | [Embrapa – Requeima](https://www.embrapa.br/en/agencia-de-informacao-tecnologica/cultivos/tomate/producao/doencas-e-pragas/doencas/fungo/requeima), [Tofoli et al. – Controle da requeima com fungicidas](https://biologico.agricultura.sp.gov.br/uploads/docs/arq/V70_4/tofoli.pdf) |
| Pinta-preta (*Alternaria solani*) | Fungo | **media** — controlável com fungicida, progressão mais lenta | Pulverização preventiva com fungicida registrado; evitar cultivo perto de batata/solanáceas; preferir irrigação por gotejamento/sulco (não molhar folhagem). | [Embrapa – Pinta-preta](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/tomate/producao/doencas-e-pragas/doencas/fungo/pinta-preta), [Agrolink – Como controlar a pinta-preta](https://www.agrolink.com.br/culturas/tomate/informacoes-da-cultura/fitossanidade/como-controlar-a-pinta-preta--alternaria--no-tomateiro-_485615.html) |
| Mancha bacteriana (*Xanthomonas* spp.) | Bactéria | **alta** — sem cura para planta já infectada | Sem cura para planta já infectada. Usar sementes/mudas sadias, evitar molhar folhagem, rotacionar cultura, considerar cultivar resistente; bactericida à base de cobre pode reduzir disseminação. | [Embrapa – Mancha bacteriana](https://www.embrapa.br/en/busca-de-publicacoes/-/publicacao/882148/mancha-bacteriana-uma-atualizacao-para-o-sistema-de-producao-integrada-de-tomate-industria), [Revista Cultivar – Como controlar mancha bacteriana](https://revistacultivar.com.br/noticias/como-controlar-mancha-bacteriana-em-tomate) |
| Mofo de folha (*Passalora/Cladosporium fulvum*) | Fungo | **media** — controlável com ventilação/fungicida | Típico de estufa com umidade alta (75-90%, ótimo 85%). Melhorar ventilação/espaçamento para manter umidade do ar abaixo de 85%; estacar/podar; fungicida à base de cobre, clorotalonil ou mancozebe são opções registradas. | [Cornell Vegetables – Tomato Leaf Mold](https://www.vegetables.cornell.edu/pest-management/disease-factsheets/tomato-leaf-mold/), [PNW Handbooks – Tomato Leaf Mold](https://pnwhandbooks.org/plantdisease/host-disease/tomato-solanum-lycopersicum-leaf-mold) |
| Septoriose (*Septoria lycopersici*) | Fungo | **alta** — Embrapa: perdas de até 100% e morte da planta em casos graves | Mais comum em épocas quentes/chuvosas. Usar sementes/mudas sadias, eliminar restos de cultura e plantas voluntárias, evitar plantio perto de lavoura antiga/infectada, aplicar fungicida quando necessário. | [Embrapa – Capítulo Septoriose (133 Hortaliças)](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1117733/1/CLV19011.pdf), [Agrolink – Como controlar a septoriose](https://www.agrolink.com.br/culturas/tomate/informacoes-da-cultura/fitossanidade/como-controlar-a-septoriose---mancha-de-septoria-no-tomateiro--septoria-lycopersici--_486101.html) |
| Ácaro-rajado (*Tetranychus urticae*) | Praga (não fungo) | **media** — controlável biologicamente | Monitorar a face inferior das folhas; controle biológico (ácaros predadores) é recomendado a partir de ~5 ácaros por folíolo. | [Embrapa – Estratégias de controle do ácaro-rajado](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/577395/1/IwassakiEstrategias.pdf), [Revista Cultivar – Tetranychus urticae](https://revistacultivar.com.br/fitossanidade/tetranychus-urticae) |
| Mancha-alvo (*Corynespora cassiicola*) | Fungo | **media** — controlável com fungicida/cultivar resistente | Favorecida por umidade do ar >80%, 18-21°C e ≥12h de folha molhada. Remover folhas com sintomas; preferir cultivar resistente; fungicida à base de estrobirulina em rotação é uma opção. | [SciELO – Manejo da mancha-de-Corynespora no tomate](https://www.scielo.br/j/tpp/a/PRCHQKry3cdLtsGMJVjw5pP/?lang=pt), [Embrapa – Eficiência de fungicidas para mancha-alvo](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1154756/1/Circ-Tec-194.pdf) |
| Vira-cabeça / Geminivírus (transmitido pela mosca-branca) | Vírus | **alta** — sem cura, só controle do vetor | Sem cura — foco no controle do vetor: mudas em ambiente protegido, eliminar plantas daninhas hospedeiras, controle químico da mosca-branca, remover plantas infectadas e restos de cultura. | [Embrapa – Mosca-branca](https://www.embrapa.br/en/agencia-de-informacao-tecnologica/cultivos/tomate/producao/doencas-e-pragas/pragas/mosca-branca), [Embrapa – Manejo Integrado da Mosca-Branca](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/782604/4/ct70.pdf) |
| Mosaico-do-tomateiro (ToMV) | Vírus | **alta** — sem cura | Sem cura — transmitido por semente e contato mecânico (mãos/ferramentas). Priorizar cultivar resistente, usar semente certificada, higienizar mãos/ferramentas entre plantas. | [Embrapa – Doenças causadas por vírus](https://www.embrapa.br/en/web/hortalicas/tomate-de-mesa/doencas-causadas-por-virus), [Embrapa – Novo método (RNAi) para viroses](https://www.embrapa.br/en/busca-de-noticias/-/noticia/48515931/novo-metodo-funciona-como-vacina-para-controle-de-viroses-em-tomateiro) |

Severidade usada em `alertas.severidade` (`cloud/app/db/models.py`),
mesma escala do risco ambiental ([ADR 0005](0005-limiares-ambientais.md)):
**alta** = sem cura ou risco de perda total documentado pela fonte;
**media** = tratamento/controle disponível, progressão mais lenta.

Todas as recomendações de doença/praga terminam com o texto fixo:
*"Consulte um engenheiro agrônomo para definir produto e dosagem
específicos."*

## Combinação com alerta ambiental (ADR 0005)

Quando um alerta de doença e um alerta ambiental ocorrem no mesmo ciclo
de captura, a recomendação da doença é complementada citando a causa
ambiental correlata (ex.: mofo de folha detectado + alerta de umidade
do ar alta no mesmo ciclo → a mensagem reforça que reduzir a umidade do
ar contribui pro controle). Isso é só lógica de regra simples (checar
se ambos os alertas existem no mesmo ciclo), não é fusão de modelo — a
imagem e os sensores continuam sendo avaliados de forma independente
(ver `cloud/README.md`, "Papel desta camada").

## Implementação

- `cloud/app/core/inference.py` (`_CLASSES_PLACEHOLDER` → tabela
  completa das 10 classes, `RECOMENDACAO_PADRAO_DOENCA`)
- `cloud/app/api/routes/diagnostico.py` (combinação com alerta ambiental)

## Pendências

- Confirmar que a lista de classes acima bate **exatamente** com a
  ordem/nomes de saída do modelo `.tflite` real quando `ml/` entregar o
  treino — o índice de cada classe (`argmax`) precisa corresponder à
  posição certa nesta tabela, ou a recomendação sai trocada.
