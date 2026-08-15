# ADR 0003 — Autenticação dual (API Key + JWT/bcrypt)

**Status:** Decidido (Tech Stack Blueprint v3.0, Seção 4.3).

## Contexto

O TC1 e o Blueprint v2.0 propunham abordagens diferentes e incompatíveis
para autenticação.

## Decisão

Usar o mecanismo mais adequado para cada ponta, não o mesmo mecanismo
para as duas:

| Ponta | Mecanismo |
|---|---|
| Dispositivo IoT (Raspberry Pi → API) | API Key estática, em variável de ambiente, header `Authorization` |
| Dashboard (login do produtor) | JWT de curta duração (24h) + refresh token (30 dias) + senha com hash bcrypt |

## Motivo

Implementar JWT com rotação de chaves para autenticar 1 único dispositivo
é over-engineering: consome tempo de desenvolvimento sem agregar nota
acadêmica. Uma API Key simples é suficientemente segura para o escopo de
um protótipo de TCC. Já para o dashboard, JWT + bcrypt é barato de
implementar nativamente com FastAPI e demonstra domínio de segurança de
aplicações web na banca.

## RBAC

Mantido do TC1: papel **Produtor** (leitura dos próprios dispositivos,
escrita limitada a preferências/marcação de alertas como lidos) e papel
**Administrador** (CRUD completo, gestão de dispositivos e do modelo de IA).

## Implementação

- `cloud/app/core/security.py`
- `cloud/app/api/routes/auth.py`
