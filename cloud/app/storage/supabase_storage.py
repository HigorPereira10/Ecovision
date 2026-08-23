"""
cloud/app/storage/supabase_storage.py

Integração com o Supabase Storage (bucket de objetos, S3-compatible),
(v3.0, Seção 4.2) para persistir as imagens capturadas pelo Pi.

Convenção de nomenclatura definida no Blueprint: bucket "ecovision-imagens",
caminho por dispositivo e timestamp: {device_id}/{timestamp}.jpg.

Decisão de design: salvar_imagem() retorna o CAMINHO dentro do bucket,
não uma URL resolvida — a escolha entre signed URL e bucket público
(infra/supabase/storage_policies.md, ainda em aberto) fica pro código
que LÊ a imagem depois (dashboard), sem acoplar essa decisão a este
módulo nem exigir mudança de schema quando ela for tomada.

Relação com o resto do sistema:
- Chamado por app/api/routes/diagnostico.py logo após a inferência,
  ANTES de a imagem ser descartada da memória (regra 4, Blueprint Seção 4.4).
"""

from supabase import Client, create_client

from app.config import settings

_cliente: Client | None = None


def _obter_cliente() -> Client:
    global _cliente
    if _cliente is None:
        _cliente = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _cliente


async def salvar_imagem(device_id: str, timestamp: str, bytes_imagem: bytes) -> str:
    """Faz upload para o bucket configurado e retorna o caminho salvo
    (ex.: "pi-teste/2026-08-22T10-00-00.jpg"). O nome do arquivo troca
    ':' por '-' porque ':' não é seguro em paths de object storage."""
    nome_arquivo = f"{timestamp.replace(':', '-')}.jpg"
    caminho = f"{device_id}/{nome_arquivo}"

    cliente = _obter_cliente()
    cliente.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        caminho,
        bytes_imagem,
        {"content-type": "image/jpeg"},
    )
    return caminho
