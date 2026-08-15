"""
cloud/app/db/models.py

Modelos ORM (SQLAlchemy) que espelham o schema do Supabase Postgres.

IMPORTANTE: decisão de grupo pendente: o Blueprint v3.0 cita os nomes
das tabelas de negócio (Seção 4.2 e 4.4) mas NÃO detalha todas as
colunas/relacionamentos. As classes abaixo são apenas placeholders com
os nomes já confirmados no Blueprint; colunas reais ficam como TODO até
o grupo fechar o schema (ver infra/supabase/schema.sql, que traz o
mesmo esqueleto em SQL para revisão conjunta).

Tabelas já citadas no Blueprint:
- registros_imagem: uma captura do Pi. Contém obrigatoriamente o campo
  `caminho_arquivo` (URL retornada pelo Supabase Storage, Seção 4.2/4.4).
- leituras_ambientais: temperatura, umidade do ar (DHT22), umidade do
  solo (sensor capacitivo + ADS1115), associadas a um registro/dispositivo.
- diagnosticos: resultado da inferência TFLite (classe prevista, confiança).
- alertas: derivados dos diagnósticos e/ou leituras fora da faixa esperada.
- (implícitas pelo RBAC da Seção 4.3, ainda não modeladas aqui):
  usuários (produtor/administrador, senha com hash bcrypt) e dispositivos
  (vínculo device <-> produtor, usado também para validar a API Key).

Relação com o resto do sistema:
- Consumido por todos os endpoints em app/api/routes/*.py via
  app/db/session.py.
- As migrations (cloud/alembic/) devem ser geradas a partir destas classes.
"""

# from sqlalchemy.orm import declarative_base

# Base = declarative_base()

# class RegistroImagem(Base):
#     """TODO: colunas a definir em grupo — inclui obrigatoriamente caminho_arquivo."""
#     __tablename__ = "registros_imagem"

# class LeituraAmbiental(Base):
#     """TODO: colunas a definir em grupo."""
#     __tablename__ = "leituras_ambientais"

# class Diagnostico(Base):
#     """TODO: colunas a definir em grupo."""
#     __tablename__ = "diagnosticos"

# class Alerta(Base):
#     """TODO: colunas a definir em grupo."""
#     __tablename__ = "alertas"

# class Usuario(Base):
#     """TODO: colunas a definir em grupo (RBAC: papel Produtor/Administrador)."""
#     __tablename__ = "usuarios"

# class Dispositivo(Base):
#     """TODO: colunas a definir em grupo (vínculo device <-> produtor)."""
#     __tablename__ = "dispositivos"
