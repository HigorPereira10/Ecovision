# Supabase Storage: bucket `ecovision-imagens`

Componente adicionado nesta revisão do Blueprint (v3.0, Seção 4.2),
não existia no Blueprint v2.0, apesar da tabela `registros_imagem` já
prever o campo `caminho_arquivo`.

## Configuração planejada (TODO: a fazer no console do Supabase)

- Nome do bucket: `ecovision-imagens`.
- Convenção de caminho: `{device_id}/{timestamp}.jpg` (facilita auditoria
  e possível reuso do dataset de campo em retreino futuro do modelo).
- Acesso: apenas a API (backend, via `SUPABASE_SERVICE_ROLE_KEY`) escreve
  no bucket. O frontend nunca acessa o Supabase diretamente, sempre via
  API (Blueprint Seção 4.2, passo 5).
- Política de leitura das imagens exibidas no dashboard: TODO: decidir
  entre URLs assinadas (signed URLs, mais restritivo) ou bucket com
  leitura pública somente das imagens (mais simples, mas expõe dados de
  produtores publicamente se a URL vazar). Isso é uma decisão de grupo
  ainda em aberto, não coberta em detalhe pelo Blueprint v3.0.

## Relação com o resto do sistema

- Escrito por `cloud/app/storage/supabase_storage.py`.
- URL resultante gravada no campo `caminho_arquivo` de `registros_imagem`
  (ver `infra/supabase/schema.sql` e `cloud/app/db/models.py`).
