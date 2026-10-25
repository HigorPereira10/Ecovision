# Depósito do conjunto de dados no Zenodo

> **DOI reservado em 25/10/2026: `10.5281/zenodo.23646357`**
> Rascunho salvo, ainda **não publicado**. Não apague o rascunho: o DOI
> reservado não é recuperável.
> Link: https://doi.org/10.5281/zenodo.23646357

O Manual do Conjunto Prototipado exige que os dados do projeto sejam
publicados no Zenodo e referenciados por identificador permanente (DOI).

**Estratégia: reservar o DOI agora, publicar o conteúdo depois da coleta
de campo.** O Zenodo permite reservar o identificador num rascunho, o que
deixa o Igor citar a referência antes de os dados existirem.

> **Ressalva do próprio Zenodo:** o DOI reservado não é garantido até a
> publicação e **não é recuperável se o rascunho for apagado**. Não apague
> o rascunho.

---

## Antes de qualquer coisa: faça o backup

Isso não tem relação com o Zenodo e é mais urgente que ele.

A pasta `ml/data/plantdoc_tomate/` está no `.gitignore` e existe **apenas
no disco de quem treinou**. O PlantDoc é público, mas **a nossa divisão
entre `train/` e `test/` não é**. Perder esse disco hoje significa não
conseguir reproduzir nenhuma métrica de campo do trabalho.

Compacte a pasta e guarde no Drive do grupo antes de seguir.

---

## Metadados do depósito

Preencher no formulário de upload do Zenodo. Os campos marcados com
**[CONFERIR]** dependem de decisão do grupo.

| Campo | Valor |
|---|---|
| Tipo de recurso | Dataset |
| Título | EcoVision: imagens de folhas de tomateiro e leituras ambientais para monitoramento fitossanitário em estufa |
| Autores | **[CONFERIR]** nomes completos e ordem dos quatro integrantes, mais a orientadora Stephany Mendes Oliveira |
| Afiliação | Universidade Paulista (UNIP), Ciência da Computação |
| Licença | **CC BY 4.0** |
| Idioma | Português |
| Versão | 1.0.0 |
| Palavras-chave | agricultura de precisão; visão computacional; Internet das Coisas; fitossanidade; tomate; Solanum lycopersicum |

### Por que CC BY 4.0

É a mesma licença do PlantDoc, de onde vem parte do conteúdo. Como ela
exige apenas atribuição, sem cláusula de compartilhamento igual, podemos
redistribuir a nossa divisão desde que a fonte original seja citada. Usar
a mesma licença evita incompatibilidade.

### Descrição sugerida

> Conjunto de dados produzido no âmbito do projeto EcoVision, sistema de
> monitoramento fitossanitário para cultivo protegido de tomate. Reúne
> imagens de folhas capturadas por dispositivo Raspberry Pi 3 Model B+ com
> iluminação própria, acompanhadas das leituras simultâneas de temperatura
> do ar, umidade relativa do ar e umidade do solo, além da divisão entre
> treino e teste utilizada na avaliação do classificador.
>
> As imagens de campo de terceiros incorporadas ao conjunto provêm do
> PlantDoc (SINGH et al., 2020), licenciado sob CC BY 4.0.

---

## O que depositar, e o que não depositar

| Conteúdo | Depositar? | Motivo |
|---|---|---|
| Fotos capturadas pelo Raspberry Pi | **Sim** | São originais e nossas. É o que torna o depósito valioso |
| Leituras de sensor correspondentes, em CSV | **Sim** | Dá contexto às imagens e permite reprodução |
| Nossa divisão do PlantDoc (`train/` e `test/`) | **Sim** | CC BY 4.0 permite, citando a fonte. É a parte insubstituível da reprodutibilidade |
| PlantVillage | **Não** | Cerca de 400 MB, público e amplamente espelhado. Basta citar |
| Modelo `.tflite` | Opcional | Já está versionado no repositório |

---

## Passo a passo

1. Compactar `ml/data/plantdoc_tomate/` e guardar no Drive. **Fazer hoje.**
2. ~~Criar conta no Zenodo.~~ **Feito** (login pelo GitHub).
3. ~~Abrir um upload novo, tipo Dataset.~~ **Feito.**
4. ~~Reservar o DOI.~~ **Feito:** `10.5281/zenodo.23646357`.
5. ~~Preencher título, autores, licença e descrição.~~ **Feito.**
6. ~~Subir arquivo provisório.~~ **Feito:** `zenodo-LEIAME.txt`.
7. ~~Salvar o rascunho.~~ **Feito em 25/10/2026.**
8. Entregar o DOI ao Igor. **Já consta no material pronto, Parte 5.**
9. Depois da coleta de campo: substituir os arquivos pelo conteúdo real e
   publicar.

---

## Como citar, depois de publicado

Formato ABNT, já com o DOI reservado:

> SOBRENOME, Nome et al. **EcoVision: imagens de folhas de tomateiro e
> leituras ambientais para monitoramento fitossanitário em estufa**.
> Zenodo, 2026. DOI: 10.5281/zenodo.23646357.

A citação entra no capítulo Material e Métodos, junto da descrição dos
conjuntos de dados, e na lista de Referências.

---

## Referências relacionadas

Declarar no campo "Related identifiers" do Zenodo, como `references`:

- SINGH, D. et al. PlantDoc: a dataset for visual plant disease detection.
  In: *ACM CoDS-COMAD*, 2020. p. 249-253. Licença CC BY 4.0.
- HUGHES, D. P.; SALATHÉ, M. An open access repository of images on plant
  health to enable the development of mobile disease diagnostics.
  [arXiv:1511.08060](https://arxiv.org/abs/1511.08060), 2015.
