-- infra/supabase/schema.sql
--
-- Schema Postgres do Supabase, espelhando cloud/app/db/models.py. A
-- fonte de verdade real é cloud/alembic/versions/0001_schema_inicial.py
-- (é o que de fato roda via `alembic upgrade head`). Este arquivo é uma
-- cópia de leitura fácil para revisão/discussão em grupo, sem precisar
-- abrir o código Python.
--
-- Escopo desta rodada (combinado com o grupo): só o caminho do
-- dispositivo. registros_imagem, leituras_ambientais e diagnosticos
-- são de fato gravadas por POST /diagnostico. alertas, usuarios e
-- dispositivos já têm o schema fechado (para o dashboard não exigir
-- migration nova depois), mas ficam vazias/não usadas até o login do
-- produtor (app/) ser implementado.

-- Uma captura do Pi. caminho_arquivo guarda só o CAMINHO dentro do
-- bucket "ecovision-imagens" (ex. "pi-teste/2026-08-22T10-00-00.jpg"),
-- não a URL resolvida. A escolha entre signed URL e bucket público
-- (ver storage_policies.md, ainda em aberto) fica pro lado que LÊ a
-- imagem depois. capturado_em é o timestamp que o Pi mandou; criado_em
-- é quando a API recebeu (podem divergir bastante: a fila offline do
-- edge/ pode entregar horas depois de a foto ter sido tirada).
CREATE TABLE registros_imagem (
    id               SERIAL PRIMARY KEY,
    device_id        TEXT NOT NULL,
    -- UUID gerado pelo edge/ na captura, usado pra detectar reenvios
    -- duplicados (ver cloud/app/api/routes/diagnostico.py).
    idempotency_key  TEXT NOT NULL UNIQUE,
    caminho_arquivo  TEXT NOT NULL,
    capturado_em     TIMESTAMPTZ NOT NULL,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_registros_imagem_device_id ON registros_imagem (device_id);
CREATE INDEX ix_registros_imagem_idempotency_key ON registros_imagem (idempotency_key);

-- Temperatura/umidade do ar (DHT22) e umidade do solo (sensor
-- capacitivo + ADS1115), 1:1 com uma captura (o Pi manda os dois
-- juntos no mesmo ciclo). Colunas nullable porque edge/src/main.py já
-- tolera falha de leitura de sensor sem abortar a captura da foto.
CREATE TABLE leituras_ambientais (
    id                 SERIAL PRIMARY KEY,
    registro_imagem_id INTEGER NOT NULL UNIQUE REFERENCES registros_imagem(id),
    temperatura_c      REAL,
    umidade_ar_pct     REAL,
    umidade_solo_pct   REAL,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Resultado da inferência TFLite. classe_prevista fica "indisponivel"
-- e confianca 0.0 enquanto o modelo real (ml/) não existir; ver
-- cloud/app/core/inference.py.
CREATE TABLE diagnosticos (
    id                 SERIAL PRIMARY KEY,
    registro_imagem_id INTEGER NOT NULL UNIQUE REFERENCES registros_imagem(id),
    classe_prevista    TEXT NOT NULL,
    confianca          REAL NOT NULL,
    recomendacao       TEXT,
    criado_em          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Login do dashboard (produtor/administrador). Schema pronto nesta
-- rodada; sem uso até o login (JWT/bcrypt) ser implementado.
CREATE TABLE usuarios (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,
    papel       TEXT NOT NULL, -- 'produtor' | 'administrador'
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_usuarios_email ON usuarios (email);

-- Vínculo device_id <-> produtor dono. Schema pronto nesta rodada; a
-- autenticação do Pi continua sendo a API Key global (ADR 0003), não
-- depende desta tabela ainda.
CREATE TABLE dispositivos (
    id          SERIAL PRIMARY KEY,
    device_id   TEXT NOT NULL UNIQUE,
    usuario_id  INTEGER REFERENCES usuarios(id),
    nome        TEXT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_dispositivos_device_id ON dispositivos (device_id);

-- Alertas derivados de diagnósticos e/ou leituras fora da faixa
-- esperada. severidade ('alta' | 'media') vem de app/core/inference.py
-- (doença) ou app/core/alertas_ambientais.py (ambiental); ver
-- docs/decisions/0005 e 0006 para a origem de cada valor.
CREATE TABLE alertas (
    id             SERIAL PRIMARY KEY,
    diagnostico_id INTEGER REFERENCES diagnosticos(id),
    leitura_id     INTEGER REFERENCES leituras_ambientais(id),
    titulo         TEXT NOT NULL,
    descricao      TEXT NOT NULL,
    severidade     TEXT NOT NULL, -- 'alta' | 'media'
    lido           BOOLEAN NOT NULL DEFAULT false,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);
