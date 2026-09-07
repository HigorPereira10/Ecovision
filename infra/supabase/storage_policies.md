# Supabase Storage: bucket `ecovision-imagens`

Componente adicionado nesta revisão do Blueprint (v3.0, Seção 4.2),
não existia no Blueprint v2.0, apesar da tabela `registros_imagem` já
prever o campo `caminho_arquivo`.

## Configuração (confirmada no projeto Supabase real)

- Nome do bucket: `ecovision-imagens`. **Criado e confirmado** (bucket
  privado, `public: false`).
- Convenção de caminho: `{device_id}/{timestamp}.jpg` (facilita auditoria
  e possível reuso do dataset de campo em retreino futuro do modelo).
- Acesso: apenas a API (backend, via `SUPABASE_SERVICE_ROLE_KEY`) escreve
  no bucket. O frontend nunca acessa o Supabase diretamente, sempre via
  API (Blueprint Seção 4.2, passo 5).
- Política de leitura das imagens exibidas no dashboard: **decidido,
  manter privado + URLs assinadas (signed URLs)**, não expor o bucket
  publicamente. Motivo: as fotos mostram a lavoura/estufa do produtor
  (dado sensível), o caminho `{device_id}/{timestamp}.jpg` é previsível
  (facilitaria adivinhar URLs de outros dispositivos num bucket
  público), e signed URLs expiram/podem ser revogadas, ao contrário de
  um link público que vaza para sempre. Como o frontend já é obrigado a
  passar pela API mesmo (regra acima), gerar a signed URL ali não é
  esforço extra real. **Ainda não implementado**: a função de gerar a
  signed URL em `cloud/app/storage/supabase_storage.py` e o consumo dela
  em `cloud/app/api/routes/historico.py` (hoje um esqueleto/TODO) ficam
  para quando a tela de histórico do app for construída de verdade.

## Relação com o resto do sistema

- Escrito por `cloud/app/storage/supabase_storage.py`.
- URL resultante gravada no campo `caminho_arquivo` de `registros_imagem`
  (ver `infra/supabase/schema.sql` e `cloud/app/db/models.py`).
