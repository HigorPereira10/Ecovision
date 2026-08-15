"""
ml/src/dataset/frankenstein_compose.py

Estratégia "Frankenstein Cirúrgico" (Blueprint v3.0, Fase 3), o
principal argumento de originalidade acadêmica do dataset:

1. Aplicar `rembg` (remoção de fundo) SOMENTE nas 6 classes do
   PlantVillage identificadas como de baixo risco de corrosão de
   segmentação (não em todas as classes, decisão deliberada).
2. Compor as folhas recortadas sobre fundos reais de estufa,
   fotos de fundo real, não sintéticas 
   (Aqui podemos tirar fotos do vaso que vamos plantar os pés de tomate).
3. Fundir o resultado com o Mendeley Tomato Disease Dataset (~4k
   imagens já em ambiente real, sem necessidade de composição).

IMPORTANTE (Pontos de Atenção do Blueprint): esse pipeline leva 4-8h
para ~7k imagens. Executar UMA VEZ, salvar o resultado (ex.: Google
Drive (lik ta no readme)) e reutilizar, nunca gerar on-the-fly a cada treino.

Relação com o resto do sistema:
- Consome a saída de ml/src/dataset/download.py.
- Alimenta ml/src/dataset/augmentation.py e, por fim,
  ml/src/training/train.py.
"""

# CLASSES_BAIXO_RISCO_SEGMENTACAO = [
#     # TODO: listar as 6 classes definidas para aplicação de rembg
# ]

# def aplicar_rembg_seletivo(imagens_plantvillage, classes: list) -> None:
#     """Remove fundo apenas nas classes de baixo risco de corrosão de segmentação."""
#     raise NotImplementedError

# def compor_sobre_fundos_reais(folhas_recortadas, fundos_estufa) -> None:
#     """Compõe as folhas recortadas sobre fundos reais de estufa."""
#     raise NotImplementedError

# def fundir_com_mendeley(dataset_composto, dataset_mendeley) -> None:
#     """Funde o resultado da composição com o Mendeley Tomato Disease Dataset."""
#     raise NotImplementedError
