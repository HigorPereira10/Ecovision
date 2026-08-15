"""
cloud/app/storage/supabase_storage.py

Integração com o Supabase Storage (bucket de objetos, S3-compatible),
(v3.0, Seção 4.2) para persistir as imagens capturadas pelo Pi.

Convenção de nomenclatura definida no Blueprint: bucket "ecovision-imagens",
caminho por dispositivo e timestamp: {device_id}/{timestamp}.jpg.

Responsabilidades quando implementado:
- Fazer upload da imagem já comprimida (150-250KB) recebida em memória.
- Retornar a URL/caminho a ser gravado no campo `caminho_arquivo` da
  tabela registros_imagem (app/db/models.py).

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py logo após a inferência,
  ANTES de a imagem ser descartada da memória (regra 4, Blueprint Seção 4.4).
"""

# from app.config import settings

# async def salvar_imagem(device_id: str, bytes_imagem: bytes) -> str:
#     """Faz upload para o bucket 'ecovision-imagens' e retorna a URL/caminho."""
#     raise NotImplementedError
