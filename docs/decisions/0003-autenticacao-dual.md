# ADR 0003: Autenticação dual (credencial de dispositivo + JWT/bcrypt)

**Status:** Decidido (Tech Stack Blueprint v3.0, Seção 4.3). A parte do
dispositivo IoT foi **substituída pelo [ADR 0009](0009-credencial-por-dispositivo.md)**
em 2026-10-10: a API Key única e global deixou de valer quando o
cadastro de produtores foi aberto. O princípio desta decisão (mecanismo
diferente para cada ponta) continua valendo, e é o que o 0009 preserva.

## Contexto

O TC1 e o Blueprint v2.0 propunham abordagens diferentes e incompatíveis
para autenticação.

## Decisão

Usar o mecanismo mais adequado para cada ponta, não o mesmo mecanismo
para as duas:

| Ponta | Mecanismo | Situação |
|---|---|---|
| Dispositivo IoT (Raspberry Pi → API) | ~~API Key estática única, em variável de ambiente~~ | **Superada:** hoje é credencial por dispositivo, ver [ADR 0009](0009-credencial-por-dispositivo.md) |
| Dashboard (login do produtor) | JWT de curta duração (24h) + refresh token (30 dias) + senha com hash bcrypt | **Vigente e implementada** |

## Motivo

Implementar JWT com rotação de chaves para autenticar 1 único dispositivo
é over-engineering: consome tempo de desenvolvimento sem agregar nota
acadêmica. Uma API Key simples é suficientemente segura para o escopo de
um protótipo de TCC. Já para o dashboard, JWT + bcrypt é barato de
implementar nativamente com FastAPI e demonstra domínio de segurança de
aplicações web na banca.

**Por que esse motivo caducou (e vale contar na banca):** a frase
"autenticar 1 único dispositivo" era a premissa inteira. Ela se
sustentava enquanto a única conta de produtor era semeada à mão por um
script. Quando `POST /auth/register` abriu o cadastro
([ADR 0010](0010-cadastro-aberto-e-rbac.md)), passaram a existir vários
produtores em potencial, e uma chave única significaria que qualquer um
com a chave poderia enviar captura como se fosse o dispositivo de
qualquer outro. A decisão não estava errada: a premissa dela mudou. Esse
é o tipo de rastro que um ADR existe para preservar.

## RBAC

Mantido do TC1: papel **Produtor** (leitura dos próprios dispositivos,
escrita limitada a preferências/marcação de alertas como lidos) e papel
**Administrador** (CRUD completo, gestão de dispositivos e do modelo de
IA).

Até 2026-10-10 isso era só uma coluna `papel` no banco, sem efeito
prático: todas as rotas de consulta devolviam os dados de todos os
dispositivos. A aplicação de verdade do RBAC, por posse de dispositivo,
está no [ADR 0010](0010-cadastro-aberto-e-rbac.md).

## Implementação

- `cloud/app/core/security.py` (JWT, bcrypt, força de senha)
- `cloud/app/api/routes/auth.py` (login, refresh, cadastro, códigos)
- `cloud/app/api/dispositivo_auth.py` (credencial do dispositivo, ADR 0009)
- `cloud/app/api/escopo.py` (filtro por dono, ADR 0010)
