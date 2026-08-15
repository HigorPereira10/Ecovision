-- infra/supabase/schema.sql
--
-- Esqueleto do schema Postgres do Supabase, espelhando
-- cloud/app/db/models.py. Traz apenas os nomes de tabela já confirmados
-- no Tech Stack Blueprint v3.0 (Seções 4.2 e 4.4), colunas, tipos,
-- chaves estrangeiras e índices ficam como TODO até o grupo fechar o
-- schema fino em conjunto.
--
-- NÃO EXECUTAR: este arquivo é um esqueleto de discussão, não uma
-- migration pronta.

-- Uma captura do Pi. Campo caminho_arquivo é obrigatório (URL retornada
-- pelo Supabase Storage, bucket "ecovision-imagens", Blueprint Seção 4.2).
-- TODO: colunas (id, device_id, caminho_arquivo, criado_em, ...)
-- CREATE TABLE registros_imagem ( ... );

-- Temperatura/umidade do ar (DHT22) e umidade do solo (sensor capacitivo
-- + ADS1115), associadas a um registro/dispositivo.
-- TODO: colunas (id, registro_imagem_id ou device_id, temperatura_c,
--       umidade_ar_pct, umidade_solo_pct, criado_em, ...)
-- CREATE TABLE leituras_ambientais ( ... );

-- Resultado da inferência TFLite (classe prevista, confiança).
-- TODO: colunas (id, registro_imagem_id, classe_prevista, confianca, criado_em, ...)
-- CREATE TABLE diagnosticos ( ... );

-- Alertas derivados de diagnosticos e/ou leituras_ambientais fora da
-- faixa esperada. Produtor tem escrita limitada a marcar como lido (RBAC,
-- Blueprint Seção 4.3).
-- TODO: colunas (id, diagnostico_id ou leitura_id, tipo, lido, criado_em, ...)
-- CREATE TABLE alertas ( ... );

-- Usuários do dashboard (login do produtor). Senha SEMPRE com hash bcrypt
-- (nunca texto puro), papel para RBAC: 'produtor' ou 'administrador'.
-- TODO: colunas (id, email, senha_hash, papel, criado_em, ...)
-- CREATE TABLE usuarios ( ... );

-- Dispositivos IoT cadastrados, vínculo com o produtor dono e com a
-- API Key usada para autenticar as requisições do Pi (Blueprint Seção 4.3).
-- TODO: colunas (id, device_id, usuario_id, nome, api_key_hash, criado_em, ...)
-- CREATE TABLE dispositivos ( ... );
