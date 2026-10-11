# ADR 0013: E-mail transacional pela API HTTP do Brevo

**Status:** Decidido e em produção (2026-10-11).

## Contexto

A confirmação de cadastro e a recuperação de senha
([ADR 0010](0010-cadastro-aberto-e-rbac.md)) dependem de enviar e-mail.
A primeira implementação usou SMTP com uma conta Gmail dedicada
(`app.ecovision@gmail.com`), e **funcionava perfeitamente na máquina de
desenvolvimento**.

Em produção, não. O cadastro levava 21,8 segundos e estourava o limite
de 10 segundos do app, e o produtor via "fetch failed" sem nenhuma pista
do motivo.

Causa: **o Railway bloqueia as portas de e-mail (25, 465, 587 e 2525)**
nos planos Free, Trial e Hobby, para impedir que spammers abusem dos IPs
do datacenter. O projeto está no Hobby. Nenhuma configuração de SMTP
resolveria, porque o problema não é a configuração: é a porta estar
fechada na saída.

A própria documentação do Railway recomenda serviços com API HTTP como
alternativa, porque usam a porta 443, que não é bloqueada.

## Decisão

Enviar e-mail pela **API HTTP do Brevo** (`api.brevo.com`, porta 443),
com SMTP mantido apenas como caminho de fallback para desenvolvimento
local.

A ordem importa e está no código: se `BREVO_API_KEY` existe, usa Brevo;
senão, se `SMTP_*` existe, usa SMTP; senão, não envia e devolve `False`.

Resultado medido: 21,8 segundos (timeout) com SMTP em produção, contra
**0,78 a 1,9 segundo** com a API HTTP.

## Por que Brevo e não Resend

Os planos gratuitos de serviço de e-mail transacional costumam exigir um
**domínio verificado** para enviar a terceiros. O EcoVision não tem
domínio próprio. Sem domínio, o Resend entrega apenas no endereço do
dono da conta, o que impediria o resto do grupo (e qualquer produtor de
teste) de receber qualquer coisa.

O Brevo aceita verificar apenas um endereço **remetente** e enviar para
qualquer destinatário, com 300 e-mails por dia no plano gratuito. Para
um TCC, 300 por dia é folgado.

Essa cota é o motivo do intervalo mínimo de 60 segundos no reenvio de
código (ver [ADR 0010](0010-cadastro-aberto-e-rbac.md)): sem trava, um
botão de "reenviar" esgotaria a cota do dia em segundos.

## Três decisões pequenas dentro desta

**`urllib` da biblioteca padrão, não `requests`.** O Blueprint é
restritivo com dependências no deploy (a RAM do Railway é o limite real
do projeto), e uma única chamada HTTP não justifica um pacote novo.

**Timeout de 8 segundos.** O envio acontece **dentro** da requisição de
cadastro, e o app desiste em 10 (`EXPO_PUBLIC_API_TIMEOUT`). Com o
limite anterior de 20s, uma porta bloqueada pendurava o cadastro além do
tempo do app. Melhor desistir rápido do e-mail e liberar a conta.

**`enviar()` devolve `False` em vez de levantar exceção.** Uma falha de
e-mail não pode derrubar a requisição que estava em andamento. Quem
chama decide o que fazer, e em `POST /auth/register` isso significa criar
a conta **já verificada**, com erro no log, em vez de prender o produtor
numa conta que ele nunca conseguiria confirmar.

**O corpo do erro do Brevo vai para o log.** Ele diz a causa real
(chave inválida, remetente não verificado, cota estourada). Sem isso no
log, descobrir o motivo de um e-mail não ter saído vira adivinhação.

## Armadilha encontrada no caminho

A suíte de testes estava **enviando e-mail de verdade**: ela lia o
`cloud/.env` do desenvolvedor, encontrava as credenciais e mandava. Cada
execução completa gastava cota e entregava mensagens reais em caixas
reais.

Corrigido em `cloud/tests/conftest.py`, que agora força
`BREVO_API_KEY`, `SMTP_HOST`, `SMTP_USUARIO`, `SMTP_SENHA` e
`EMAIL_REMETENTE` como vazios antes de qualquer teste rodar. Os testes
que precisam exercitar o envio substituem a função `emails.enviar` por
uma que captura a mensagem em memória.

## Implementação

- `cloud/app/core/emails.py`
- `cloud/app/config.py` (`BREVO_API_KEY`, `remetente`, `email_configurado`)
- `cloud/tests/conftest.py` (bloqueio de envio real nos testes)

## Pendências

- O remetente é um Gmail enviando via Brevo, então a primeira mensagem
  tende a cair no spam. Instruir quem testar a marcar como "não é spam".
  Resolver de verdade exigiria domínio próprio com SPF e DKIM.
