"""
cloud/app/api/routes/diagnostico.py

Endpoint principal de ingestão: POST /diagnostico
Recebe do Raspberry Pi (edge/) a imagem comprimida + leituras de sensores,
roda a inferência e persiste tudo no Supabase.

Fluxo completo, conforme Blueprint v3.0 Seção 4.2:
1. Autenticar a requisição via API Key estática (ver app/core/security.py).
2. Ler a imagem recebida em memória (BytesIO), nunca gravar em disco.
3. Redimensionar para 224x224, normalizar, rodar inferência TFLite
   (app/core/inference.py).
4. Fazer upload da imagem já comprimida para o Supabase Storage
   (app/storage/supabase_storage.py) e obter a URL/caminho.
5. Persistir no Supabase Postgres (app/db/models.py):
   - registros_imagem (com o caminho_arquivo retornado do Storage)
   - leituras_ambientais (temperatura, umidade do ar, umidade do solo)
   - diagnosticos (classe prevista, confiança)
   - alertas, se o diagnóstico exigir
6. Descartar o buffer da imagem da memória.

Relação com o resto do sistema:
- Único endpoint chamado pelo edge/src/upload/uploader.py.
- Depende de app/core/inference.py (modelo carregado em app/main.py no
  startup) e de app/storage/supabase_storage.py.
"""

# from fastapi import APIRouter, Depends, UploadFile
# from app.core.security import validar_api_key_dispositivo

# router = APIRouter()

# @router.post("/diagnostico")
# async def receber_diagnostico(...):
#     """Recebe imagem + leituras do dispositivo IoT e retorna o diagnóstico."""
#     raise NotImplementedError
