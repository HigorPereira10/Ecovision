# Railway: configuração do serviço

Notas de configuração do deploy do `cloud/` no Railway.app (Blueprint
v3.0, Fase 4). Este diretório documenta a configuração; não contém
segredos nem valores reais.

## O que roda no Railway (Blueprint Seção 4.1)

- FastAPI + Uvicorn com **1 worker apenas** + TFLite Runtime carregado em
  memória.
- Nada de dado de negócio, nenhuma imagem, nenhum log em disco, tudo
  isso fica no Supabase (ver `infra/supabase/`) ou é enviado via `stdout`.

## Configuração (a fazer no painel do Railway)

- **Root directory do serviço: NÃO definir** (deixar na raiz do
  repositório). Isto é o oposto do que este documento recomendava antes,
  e a correção é importante: quando o Railway recebe um root directory,
  ele baixa **somente** os arquivos daquela pasta, e diretórios irmãos
  ficam de fora. Como o modelo de IA vive em `ml/models/modelo.tflite`,
  irmão de `cloud/`, apontar a raiz para `cloud/` faria o modelo
  desaparecer do container. A API subiria normalmente e devolveria
  `"indisponivel"` em toda captura, sem erro visível, porque o
  carregador é tolerante a modelo ausente de propósito
  (`cloud/app/core/inference.py`). O Railway chama este caso de
  *shared monorepo* e recomenda exatamente isto.
- Start command e builder ficam versionados em `railway.json`, na raiz,
  em vez de configurados só no painel:
  `cd cloud && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
  (`$PORT` é injetado pelo Railway, nunca fixar um valor). As migrations
  rodam no start, então subir uma versão nova já aplica o schema.
- `requirements.txt` na raiz existe só para o Nixpacks reconhecer o
  projeto como Python (ele decide a linguagem olhando a raiz). Ele
  apenas reexporta `cloud/requirements.txt` com `-r`.
- `.python-version` fixa o Python em 3.11, a mesma versão usada no
  desenvolvimento, para o build não mudar de interpretador sozinho.
- Variáveis de ambiente: usar o template `infra/env/cloud.env.example`
  (preencher com os valores reais do Supabase e a `DEVICE_API_KEY`
  gerada, nunca commitar esses valores).
- Migração do banco: já embutida no start command acima. As migrations
  em `cloud/alembic/versions/` cobrem o schema atual
  (`registros_imagem`, `leituras_ambientais`, `diagnosticos`,
  `alertas`, `usuarios`, `dispositivos`).
- Runtime de IA: `cloud/requirements.txt` instala `ai-edge-litert`.
  Não trocar por `tflite-runtime` sem conferir a versão do Python: os
  wheels dele param no 3.11. Sem nenhum dos dois, o sintoma é o mesmo
  do root directory errado, diagnóstico `"indisponivel"` em silêncio.
- Depois do primeiro deploy, **conferir no log de startup** que não
  aparece `Modelo .tflite não encontrado`. É a forma mais rápida de
  saber se o modelo chegou ao container.
- Deploy automático: feito pela **integração nativa do Railway com o
  GitHub**, não por GitHub Actions. Em *Settings → Source*, a opção
  *Auto deploys when pushed to GitHub* publica sozinha a cada push na
  `main`.

  Isto diverge do Blueprint, que previa deploy via GitHub Actions. O
  motivo é que a integração nativa faz exatamente o mesmo com menos
  peça móvel: não exige guardar um token do Railway como secret do
  GitHub, e não há um segundo lugar para o pipeline quebrar. O
  `.github/workflows/deploy-railway.yml`, que nunca passou de um
  esqueleto com `echo`, foi removido em 2026-10-10 para não dar a
  impressão de que existe um pipeline de deploy que não existe.

- **Proteção contra subir código quebrado:** com auto-deploy ligado,
  um push com teste falhando iria direto para produção. Para evitar
  isso, ligue *Settings → Deploy → **Wait for CI***. Com essa opção, o
  Railway espera os checks do GitHub passarem antes de publicar, e
  `.github/workflows/tests.yml` (80 testes de `cloud/` e `edge/`) passa
  a ser o portão. Não exige Pull Request, então o fluxo de push direto
  na `main` continua valendo.

## Risco de timing (Blueprint Seção 4.5)

O free trial já foi consumido num projeto anterior. Em 2026-10-10 o
grupo assinou o **plano Hobby** (US$ 5/mês, cobrado como R$ 26,40),
o que elimina o risco de timing que esta seção descrevia: não há mais
relógio de 30 dias para sincronizar com a data da banca.

Mantido como histórico porque a decisão original de adiar a ativação
está registrada em `infra/calendar/sincronizacao.md` e no roadmap.
O que continua valendo: definir um teto de uso no painel (botão
*Set limits*), para erro de configuração não virar conta alta.
