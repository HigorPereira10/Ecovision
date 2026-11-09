# cloud

API do EcoVision, desenvolvida com FastAPI e hospedada no Railway. Recebe
as capturas e as leituras dos dispositivos, executa a classificação das
imagens, grava os dados no PostgreSQL e as imagens no Supabase Storage, e
atende o aplicativo.

## Responsabilidades

- Autenticar os dispositivos, cada um com credencial própria, e os
  produtores, com JWT de acesso (24 h), token de renovação (30 dias) e
  senha com hash bcrypt.
- Verificar a qualidade de cada captura, recortá-la em janelas de 896
  pixels com passo de 448 e classificar cada janela com o modelo
  MobileNetV2 em TensorFlow Lite. O diagnóstico da captura é a classe mais
  severa cuja fração de janelas atinge 20%.
- Avaliar as leituras ambientais por regras de limiar e gerar alertas.
- Restringir toda consulta aos dispositivos vinculados à conta.

## Endpoints

| Método | Rota | Autenticação | Finalidade |
|---|---|---|---|
| GET | `/health` | nenhuma | Estado do serviço, do banco e do modelo; 503 se o banco não responder |
| POST | `/auth/register` | nenhuma | Cadastro de produtor, com confirmação por e-mail |
| POST | `/auth/verify-email` | nenhuma | Confirmação da conta pelo código de 6 dígitos |
| POST | `/auth/resend-code` | nenhuma | Reenvio do código, com intervalo mínimo de 60 s |
| POST | `/auth/login` | nenhuma | Emissão dos tokens; conta não confirmada recebe 403 |
| POST | `/auth/forgot-password` | nenhuma | Envio do código de redefinição de senha |
| POST | `/auth/reset-password` | nenhuma | Definição de nova senha |
| POST | `/auth/refresh` | token de renovação | Renovação da sessão |
| GET | `/usuarios/me` | token | Dados do produtor |
| GET | `/dispositivos` | token | Dispositivos do produtor, com estado calculado |
| POST | `/dispositivos/vincular` | token | Vínculo de dispositivo pelo código `ECO-XXXX-XXXX` |
| POST | `/diagnostico` | credencial do dispositivo | Captura e leituras: classificação, armazenamento e alertas |
| POST | `/leituras` | credencial do dispositivo | Leituras de 15 minutos, sem foto |
| GET | `/diagnosticos` | token | Histórico de diagnósticos, com URL assinada da imagem |
| GET | `/leituras` | token | Série temporal dos sensores |
| GET | `/alertas` | token | Alertas do produtor, incluindo o de dispositivo inativo |
| PATCH | `/alertas/{id}/lido` | token | Marcação de alerta como lido |

## Comportamentos relevantes

- **Idempotência:** o reenvio de uma captura com a mesma
  `idempotency_key` devolve o diagnóstico existente, sem duplicar
  registros.
- **Validação antes do upload:** imagem corrompida (422), imagem acima de
  5 MB (413) e leituras inválidas são recusadas antes de qualquer
  gravação no Storage.
- **Imagem inadequada:** capturas escuras ou sem textura são armazenadas
  sem diagnóstico, com um alerta de verificação do equipamento.
- **Degradação controlada:** sem o arquivo do modelo, a API inicia e
  responde com resultado provisório; sem serviço de e-mail configurado,
  as contas são criadas já verificadas. Os dois casos são registrados no
  log.
- **Anti-enumeração:** login e recuperação de senha respondem de forma
  idêntica, inclusive no tempo de resposta, exista ou não a conta.

## Banco de dados

O esquema é definido em `app/db/models.py` e aplicado pelas migrações do
Alembic em `alembic/versions/`.

| Tabela | Conteúdo |
|---|---|
| `registros_imagem` | Capturas recebidas e caminho da imagem no bucket |
| `leituras_ambientais` | Leituras dos sensores, com ou sem foto associada |
| `diagnosticos` | Classe, confiança e recomendação de cada captura |
| `alertas` | Alertas de diagnóstico, ambientais e de equipamento |
| `usuarios` | Contas de produtor e administrador |
| `dispositivos` | Dispositivos, credenciais (hash) e vínculo com a conta |
| `tentativas_login` | Bloqueio temporário por tentativas sucessivas |
| `codigos_email` | Códigos de confirmação e de redefinição (hash) |

As imagens ficam no bucket privado `ecovision-imagens`, em
`{device_id}/{timestamp}.jpg`, e são entregues ao aplicativo por URLs
assinadas com validade de 1 hora.

## Estrutura

```
cloud/
├── app/
│   ├── main.py          # aplicação FastAPI e rota /health
│   ├── config.py        # configuração por variáveis de ambiente
│   ├── api/             # rotas, autenticação de dispositivo e escopo por dono
│   ├── core/            # inferência, janelas, alertas, segurança e e-mail
│   ├── db/              # modelos SQLAlchemy, sessão e schemas Pydantic
│   └── storage/         # integração com o Supabase Storage
├── alembic/             # migrações do banco
├── scripts/             # provisionamento de dispositivos e contas de teste
└── tests/               # testes automatizados (ver tests/README.md)
```

`app/core/` não depende do banco, o que permite testar as regras de
negócio isoladamente; o acesso a dados fica em `app/api/` e `app/db/`.

## Execução local

```bash
cd cloud
pip install -r requirements.txt
cp ../infra/env/cloud.env.example .env      # preencher as variáveis
alembic upgrade head
python -m scripts.seed_usuario_teste        # conta de teste
python -m scripts.provisionar_dispositivo <device_id> "<nome>"
uvicorn app.main:app --reload
```

O script de provisionamento exibe a credencial do dispositivo uma única
vez; o banco guarda somente o hash. Os testes rodam com `pytest -q`.

## Implantação no Railway

- O serviço usa a raiz do repositório, sem diretório raiz configurado,
  porque o modelo em `ml/models/` precisa estar no contêiner.
- O comando de inicialização está em `railway.json`: aplica as migrações
  e inicia o Uvicorn com um único processo, já que cada processo carrega
  o interpretador do modelo em memória.
- O `requirements.txt` da raiz apenas reexporta `cloud/requirements.txt`,
  para que o Nixpacks reconheça o projeto como Python; `.python-version`
  fixa o Python 3.11.
- As variáveis de ambiente seguem `infra/env/cloud.env.example`.
- O runtime de inferência é o `ai-edge-litert`; o pacote `tensorflow`
  completo não deve ser instalado, pois excede a memória do plano.
- A publicação é automática a cada push na `main`, condicionada à
  aprovação dos testes do GitHub Actions (opção *Wait for CI*).
