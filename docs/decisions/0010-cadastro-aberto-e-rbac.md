# ADR 0010: Cadastro aberto, RBAC por posse de dispositivo e confirmação por e-mail

**Status:** Decidido e implementado (2026-10-10, confirmação por e-mail
em 2026-10-11). Aplica de verdade o RBAC que o
[ADR 0003](0003-autenticacao-dual.md) só declarava.

## Contexto

Até 2026-10-10 não existia cadastro. A única conta de produtor era
criada à mão por `cloud/scripts/seed_usuario_teste.py`, e a tela de
cadastro da Amanda, pronta no app, não tinha onde chamar. O sistema
estava fechado por acidente, não por decisão.

Ao abrir o cadastro, apareceu um problema que não existia antes:
**todas as rotas de consulta exigiam login mas devolviam os dados de
todos os dispositivos**. Com uma conta só, isso era inofensivo. Com
cadastro aberto, bastaria qualquer pessoa criar uma conta para ver a
estufa, as fotos, os diagnósticos e os alertas de outro produtor. A
abertura do cadastro e o filtro por dono **tinham que ser a mesma
entrega**, e foram.

## Decisão 1: cadastro é aberto

Qualquer pessoa pode criar conta em `POST /auth/register`.

O **papel é sempre `produtor`**, ignorando qualquer valor que venha no
corpo da requisição. Sem essa imposição, bastaria mandar
`papel: "administrador"` no JSON para ganhar acesso irrestrito a todas
as estufas do sistema. Administrador é concedido apenas por script, com
acesso ao banco.

## Decisão 2: o que cada conta enxerga é definido pela POSSE do aparelho

Implementado em `cloud/app/api/escopo.py`, consumido por
`/leituras`, `/diagnosticos`, `/alertas` e `/dispositivos`.

A cadeia de posse:

```
usuarios.id
  <- dispositivos.usuario_id
     (dispositivos.device_id == registros_imagem.device_id)
       <- leituras_ambientais / diagnosticos
          <- alertas
```

Uma conta nova não vê absolutamente nada até vincular um dispositivo
pelo código de pareamento ([ADR 0009](0009-credencial-por-dispositivo.md)).
Isso é o que torna o cadastro aberto seguro: criar conta é livre, mas o
acesso a dado exige provar posse física do equipamento.

Três distinções que o código faz e que importam:

| Caso | Retorno de `device_ids_visiveis` | Efeito |
|---|---|---|
| Administrador | `None` | Nenhum filtro aplicado, vê tudo |
| Produtor com dispositivos | lista com os `device_id` dele | Vê só os dele |
| Produtor sem nenhum dispositivo | lista **vazia** | Vê zero itens |

Confundir lista vazia com `None` seria a falha mais fácil de cometer
aqui, e ela entregaria o banco inteiro para qualquer conta recém-criada.

**Consequência operacional que precisa estar escrita:**
`registros_imagem.device_id` é uma string livre, sem chave estrangeira
para `dispositivos`. Uma captura cujo `device_id` não tenha linha em
`dispositivos`, ou cuja linha esteja sem dono, **não tem dono e fica
invisível para todo mundo**. O dado continua no banco, nenhuma tela
mostra. Para o Pi real aparecer, o `device_id` dele precisa estar
vinculado a um usuário.

## Decisão 3: alerta de outro dono responde 404, não 403

`PATCH /alertas/{id}/lido` num alerta que existe mas é de outro
produtor responde **404**, não 403.

403 significa "existe e você não pode", o que confirma a existência do
recurso. Testando ids em sequência, dá para contar quantos alertas o
sistema tem e inferir o movimento das outras estufas. 404 não entrega
nada.

## Decisão 4: o e-mail tem que ser confirmado

Pergunta do grupo, em 2026-10-11: "ao criar minha conta não pediu
nenhuma confirmação no e-mail, é bom manter isso?". Não era.

Sem confirmação, dois problemas:

1. Qualquer um enche a tabela `usuarios` com endereços inventados, e
   não há como distinguir cadastro real de lixo.
2. Quem digita o próprio e-mail errado fica **sem conta e sem como
   recuperá-la**, porque a recuperação de senha vai justamente para o
   endereço errado.

**Mecanismo:** código numérico de 6 dígitos, enviado por e-mail. O
login é recusado com 403 enquanto a conta não for confirmada, e a
mensagem só aparece **depois** de a senha conferir (avisar antes
revelaria que o e-mail existe para quem nem sabe a senha).

Seis dígitos são apenas um milhão de combinações, o que isoladamente
seria fraco. O que torna isso seguro é a soma de três limites:

| Limite | Valor |
|---|---|
| Validade | 15 minutos |
| Usos | 1 (pedir outro invalida o anterior) |
| Tentativas | 5, depois o código morre |

Resultado: 5 chances em 1 milhão.

**O código nunca aparece em nenhuma resposta da API, e no banco fica só
o hash bcrypt dele.** Se voltasse na resposta, bastaria abrir o
inspetor do navegador para ativar ou assumir a conta de qualquer pessoa.
Se ficasse em claro no banco, um vazamento entregaria contas. Há teste
automatizado para as duas coisas
(`cloud/tests/test_email_verificacao.py`).

**Degradação proposital:** sem e-mail configurado no servidor, a conta
nasce **já verificada**, com erro no log. Criá-la bloqueada seria pior:
o produtor ficaria preso numa conta que ninguém consegue confirmar,
porque o e-mail nunca sairia. Mesma filosofia de
`app/core/inference.py`: dependência externa ausente degrada o
comportamento, não derruba o sistema.

**Reenvio (`POST /auth/resend-code`, 2026-10-11):** sem ele, um e-mail
que caísse no spam e fosse apagado deixava a conta inacessível para
sempre, porque o login recusa quem não confirmou e o cadastro recusa o
e-mail por já existir. O reenvio tem intervalo mínimo de 60 segundos,
que não é proteção contra invasão (o reenvio só manda e-mail para o
próprio dono do endereço) e sim proteção de **recurso**: a cota gratuita
do Brevo é de 300 e-mails por dia, e um botão sem trava esgotaria a cota
do dia em segundos, derrubando o cadastro de todo mundo.

## Decisão 5: recuperação de senha pelo mesmo mecanismo

Pedido do grupo: "não dá para colocar um token aleatório enviado para a
conta de e-mail, com muita segurança, para não deixar o token à mostra
num Ctrl+Shift+I?".

Mesma estrutura do código de confirmação, com dois cuidados extras:

- `POST /auth/forgot-password` responde **exatamente a mesma coisa**
  para e-mail cadastrado e inexistente, incluindo o mesmo corpo de
  resposta. Diferenciar permitiria descobrir quais endereços têm conta
  só testando valores, o que anularia a proteção anti-enumeração que o
  login já tem.
- A nova senha passa pelas **mesmas regras de força** do cadastro. Sem
  isso, a recuperação viraria um atalho para contornar a exigência de
  senha forte.

## Decisão 6: regras de senha e trava de tentativas

Cinco regras, todas verificadas no servidor (o app mostra o checklist,
mas quem decide é a API):

mínimo de 8 caracteres, uma maiúscula, uma minúscula, um número, um
símbolo. Mais um limite de **72 bytes**, porque o bcrypt recusa entradas
maiores e, sem checar, o cadastro viraria erro 500 que qualquer pessoa
poderia disparar sem autenticação.

A API devolve **todas** as regras que falharam de uma vez, não a
primeira, para o app marcar o checklist inteiro em vez de fazer o
produtor descobrir uma por tentativa.

**Trava de força bruta:** 5 tentativas erradas, 15 minutos de bloqueio.
O contador é indexado pelo **e-mail digitado**, exista a conta ou não.
Indexar só por conta existente faria o 429 ("muitas tentativas")
aparecer apenas para e-mails cadastrados, o que transformaria a própria
trava num detector de contas.

## Decisão 7: tempo de resposta também não pode vazar

A proteção anti-enumeração do login era só aparente. O `or` em
curto-circuito pulava a verificação bcrypt quando o e-mail não existia,
e a resposta voltava em cerca de 0,39s contra 0,65s para e-mail
cadastrado. **Cronometrando as respostas, dava para descobrir quais
e-mails têm conta, mesmo com a mensagem idêntica.**

Corrigido com `HASH_DESCARTAVEL` (`cloud/app/core/security.py`): quando
o e-mail não existe, o bcrypt roda contra um hash descartável, gastando
o mesmo tempo.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Cadastro fechado, contas criadas por script | Não se defende na banca: um sistema para produtores em que o produtor não consegue criar conta |
| Cadastro por convite | Resolve o lixo no banco, mas exige um fluxo de administração que ninguém vai operar num TCC |
| Link mágico no e-mail em vez de código | Link em app mobile exige deep link configurado e quebra se o e-mail abrir no navegador do desktop; código de 6 dígitos funciona em qualquer combinação |
| RBAC por "organização" ou "fazenda" | Camada de modelagem a mais para um protótipo com um Pi; posse direta do aparelho resolve o mesmo problema |

## Implementação

- `cloud/app/api/escopo.py` (filtro por dono)
- `cloud/app/api/routes/auth.py` (cadastro, códigos, trava, recuperação)
- `cloud/app/core/security.py` (força de senha, `HASH_DESCARTAVEL`)
- `cloud/app/core/emails.py` (envio, ver [ADR 0013](0013-email-transacional-brevo.md))
- `cloud/alembic/versions/0005_*` (`tentativas_login`), `0007_*` (`usuarios.email_verificado`, `codigos_email`)
- `app/src/screens/CadastroScreen.tsx`, `VerificarEmailScreen.tsx`, `RecuperarSenhaScreen.tsx`
- Testes: `cloud/tests/test_escopo.py`, `test_cadastro_e_pareamento.py`, `test_email_verificacao.py`

## Pendências

- As contas existentes antes da migration 0007 foram marcadas como
  verificadas (`email_verificado = true`). Elas nunca passaram por
  confirmação de e-mail, e isso é intencional: bloqueá-las
  retroativamente trancaria as contas de teste do grupo.
