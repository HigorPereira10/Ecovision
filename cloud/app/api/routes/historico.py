"""
cloud/app/api/routes/historico.py

Endpoints de consulta histórica: diagnósticos passados (com a URL da
imagem vinda do Supabase Storage) e leituras ambientais ao longo do
tempo, para as telas de Histórico/Diagnóstico do frontend.

Regra importante (Blueprint Seção 4.2, passo 5): o frontend NUNCA acessa
o Supabase diretamente. Este endpoint é quem busca os dados/URLs no
Supabase e devolve a resposta já pronta para exibição.

Relação com o resto do sistema:
- Consumido pelo frontend (app/) nas telas de diagnóstico e histórico.
- Depende de app/db/models.py (registros_imagem, leituras_ambientais,
  diagnosticos) e app/storage/supabase_storage.py (para resolver URLs
  de imagem, se necessário).
"""

# from fastapi import APIRouter

# router = APIRouter()

# TODO: GET /historico/diagnosticos: lista diagnósticos de um dispositivo
# TODO: GET /historico/leituras: série temporal de leituras ambientais
