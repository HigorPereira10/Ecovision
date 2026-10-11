# ADR 0009: Credencial por dispositivo e pareamento por código

**Status:** Decidido e implementado (2026-10-10). Substitui a parte de
dispositivo IoT do [ADR 0003](0003-autenticacao-dual.md).

## Contexto

O [ADR 0003](0003-autenticacao-dual.md) escolheu uma API Key **estática
e global** para o Raspberry Pi, e a justificativa estava escrita com
todas as letras: "implementar JWT com rotação de chaves para autenticar
1 único dispositivo é over-engineering".

Essa frase era verdadeira e deixou de ser. Enquanto a única conta de
produtor era semeada à mão por `scripts/seed_usuario_teste.py`, havia
literalmente um dispositivo e um usuário, e uma chave no `.env` resolvia.
Quando `POST /auth/register` abriu o cadastro
([ADR 0010](0010-cadastro-aberto-e-rbac.md)), a premissa caiu e dois
problemas apareceram ao mesmo tempo:

1. **Impersonação de dispositivo.** `POST /diagnostico` recebe o
   `device_id` no corpo da requisição e a chave no header. Com uma chave
   única, qualquer um que a possuísse poderia enviar uma captura
   declarando o `device_id` de outra pessoa, ou seja, **injetar um
   diagnóstico falso de doença na estufa alheia**. Como o app mostra
   esse diagnóstico e gera alerta a partir dele, isso não é incômodo
   teórico: é fazer o produtor pulverizar fungicida por causa de uma
   foto que ele nunca tirou.
2. **Raio de alcance de um vazamento.** A mesma chave vive no `.env` de
   todo Pi. Um aparelho roubado ou um cartão SD lido compromete a frota
   inteira, e não existe como revogar um sem revogar todos.

Havia ainda um terceiro problema, de produto e não de segurança: nada
ligava um dispositivo a um dono. Sem esse vínculo, o filtro por posse do
ADR 0010 não teria em que se apoiar.

## Decisão

**Cada dispositivo tem o próprio segredo.** `dispositivos.chave_hash`
guarda o hash bcrypt dele. O segredo em claro existe em exatamente dois
lugares: na saída do script de provisionamento, uma única vez, e no
`.env` daquele Pi. **Nunca no banco.** Se o banco vazar, as credenciais
não servem para nada, pela mesma razão que `usuarios.senha_hash` existe
em vez da senha.

**A posse física é a prova de propriedade.** O provisionamento gera
também um código de pareamento no formato `ECO-XXXX-XXXX`, para ser
colado numa etiqueta no aparelho. O produtor digita esse código no app
(`POST /dispositivos/vincular`) e o dispositivo passa a ser dele.

Três propriedades do código, que são o que o tornam seguro:

| Propriedade | Motivo |
|---|---|
| Só funciona enquanto `usuario_id` for nulo | Reivindicar um aparelho que já tem dono é impossível, e o código perde todo o valor no instante em que é usado |
| Alfabeto sem `O`, `I`, `L`, `0` e `1` | O código é lido de uma etiqueta e digitado à mão; `ECO-O0I1-...` geraria suporte eterno por erro de leitura |
| Gerado com `secrets`, não com `random` | `random` é previsível a partir de saídas anteriores, e isso aqui é credencial |

**O dispositivo nasce sem dono, de propósito.** Quem o vincula é o
produtor, com o código. É exatamente isso que torna seguro deixar o
cadastro aberto: criar conta é livre, mas a conta não enxerga dado algum
até provar que tem o equipamento na mão.

## Transição, e por que ela existe

A chave global **continua sendo aceita**, num ramo de código marcado com
comentário explícito em `cloud/app/api/dispositivo_auth.py`, e cada uso
dela grava um aviso no log com o `device_id` que a usou.

Isso não é indecisão: é para não derrubar um Pi em campo no segundo em
que o deploy sobe. O aparelho está dentro de uma estufa, e um deploy que
exigisse provisionamento simultâneo deixaria a captura parada até alguém
ir fisicamente até lá. Quando todos os Pis estiverem provisionados, basta
apagar o ramo marcado, e os avisos no log são justamente como se descobre
que ainda falta algum.

## Dois detalhes de implementação que não são detalhe

**`secrets.compare_digest` em vez de `==`.** Comparar credencial com `==`
sai no primeiro caractere diferente, e o tempo de resposta vaza quantos
caracteres iniciais estavam certos. Com tempo suficiente, isso permite
descobrir a chave caractere por caractere.

**A comparação é feita em BYTES, não em texto.** `compare_digest` recusa
strings com caracteres não-ASCII levantando `TypeError`, que escaparia da
função como erro 500. Como a credencial vem de fora, qualquer pessoa
derrubaria a rota mandando um acento no header. `.encode("utf-8")` nas
duas pontas resolve.

**A mensagem de erro é a mesma** para `device_id` inexistente e para
segredo errado. Diferenciar permitiria descobrir quais `device_id`
existem, só testando valores.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Manter a chave global e validar `device_id` contra um cadastro | Não resolve nada: quem tem a chave global tem a chave de todos, e só precisaria descobrir um `device_id` válido, que é um nome curto e adivinhável |
| mTLS (certificado por dispositivo) | Tecnicamente superior e proporcional a uma frota de verdade. Para um Pi em TCC, significa gerenciar uma CA, distribuir e renovar certificados; custo alto, ganho zero na nota |
| JWT emitido para o dispositivo | Teria que ser renovado, e um Pi que fica horas sem rede (é o caso, existe fila offline) perderia a janela de renovação justamente quando mais precisa enviar |

## Implementação

- `cloud/app/api/dispositivo_auth.py` (autenticação)
- `cloud/app/core/security.py` (`gerar_segredo_dispositivo`, `gerar_codigo_pareamento`)
- `cloud/app/api/routes/dispositivos.py` (`POST /dispositivos/vincular`)
- `cloud/scripts/provisionar_dispositivo.py` (gera segredo e código)
- `cloud/alembic/versions/0005_*` (colunas `chave_hash`, `codigo_pareamento`, `pareado_em`)
- `app/src/screens/VincularDispositivoScreen.tsx` (tela do produtor)

## Pendências

- Remover o ramo de transição da chave global depois que todos os
  dispositivos estiverem provisionados.
- O fluxo de pareamento tem teste automatizado
  (`cloud/tests/test_cadastro_e_pareamento.py`), mas **nunca foi
  exercitado por uma pessoa de verdade no app**. Fazer isso antes da
  banca.
