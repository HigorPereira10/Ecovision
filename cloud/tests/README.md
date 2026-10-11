# cloud/tests: Testes automatizados do backend

**121 testes.** Rodar: `pytest -q` dentro de `cloud/`.

## Para quem nunca mexeu com testes automatizados: o que é isso?

Ver a explicação completa em [`edge/tests/README.md`](../../edge/tests/README.md).
O resumo é: um pequeno programa que simula uma situação real (ex.: "a
Raspberry Pi mandou uma foto sem a credencial certa") e confere se o
sistema reage do jeito esperado, sem precisar de um Supabase real nem de
rede.

## Duas coisas que esta suíte garante e que não dá para testar à mão

**Isolamento entre produtores** (`test_escopo.py`). Conferir à mão que
uma conta não vê a estufa de outra exige criar duas contas, dois
dispositivos, capturas em cada um, e repetir isso em toda rota de
consulta. O teste faz isso em segundos, e é a única forma de garantir
que uma mudança futura não volte a devolver a tabela inteira.

**Que o código enviado por e-mail nunca escapa**
(`test_email_verificacao.py`). O teste confere que o código de 6 dígitos
não aparece em nenhuma resposta da API e que no banco fica só o hash
bcrypt. Se vazasse, bastaria abrir o inspetor do navegador para assumir
a conta de qualquer pessoa.

## O que cada arquivo testa

- **`test_security.py`**: JWT, bcrypt, regras de força de senha e a
  recusa de credencial errada ou ausente do dispositivo.

- **`test_escopo.py`**: o filtro por dono em todas as rotas de consulta.
  Inclui o caso que mais importa: produtor **sem** dispositivo vinculado
  vê zero itens, não a tabela toda.

- **`test_cadastro_e_pareamento.py`**: cadastro aberto com papel forçado
  para `produtor`, e o fluxo de reivindicar um dispositivo pelo código
  `ECO-XXXX-XXXX`.

- **`test_email_verificacao.py`**: confirmação de cadastro, reenvio de
  código com intervalo mínimo, recuperação de senha, e as proteções
  anti-enumeração (resposta idêntica para e-mail existente e
  inexistente).

- **`test_inference.py`**: confere que a inferência funciona com o
  modelo real carregado, e que **degrada para resultado "indisponivel"**
  em vez de travar quando o modelo não está presente. Também confere o
  pré-processamento: 224x224, e **pixels crus de 0 a 255**, que é o que
  este modelo específico exige (ver
  [ADR 0011](../../docs/decisions/0011-escopo-de-tres-classes.md)).

- **`test_diagnostico.py`**: o teste mais importante, simula de ponta a
  ponta exatamente o que a Raspberry Pi manda (mesmo formato que
  `edge/src/upload/uploader.py` já usa de verdade), sem precisar de um
  Supabase real rodando. Cobre: chave errada/ausente → recusado; envio
  correto → as 3 tabelas do banco são gravadas certinho e a resposta tem
  os dados certos; leitura de sensor que falhou na Pi (chega como campo
  ausente ou como a string `"None"`) → gravada como nula no banco, sem
  quebrar nada.

## Por que o Supabase Storage é sempre simulado nos testes

Não existe um projeto Supabase real disponível para os testes automáticos
usarem (e não seria uma boa prática mandar dados de teste pra lá mesmo se
existisse). Por isso, `test_diagnostico.py` troca temporariamente a função
`salvar_imagem` por uma versão falsa que só devolve um caminho de mentira,
sem nenhuma chamada de rede de verdade. Isso já foi validado à parte,
rodando o servidor real (`uvicorn`) e mandando uma requisição de verdade
do `edge/src/upload/uploader.py` contra ele, funcionou de ponta a ponta,
inclusive gravando no banco corretamente.

## Por que o banco de dados dos testes é SQLite, não Postgres

O Supabase usa Postgres de verdade em produção, mas os testes usam um
arquivo SQLite temporário no lugar (ver `cloud/tests/conftest.py`): mais
rápido, não precisa de credencial nenhuma, e as tabelas são as mesmas
(nenhum tipo específico de Postgres foi usado no schema, de propósito,
para isso funcionar).

## Por que a suíte NUNCA envia e-mail de verdade

Ela já enviou. A suíte lia o `cloud/.env` do desenvolvedor, encontrava
as credenciais do Brevo e mandava mensagens reais para caixas reais, a
cada execução, gastando a cota diária.

`conftest.py` agora força `BREVO_API_KEY`, `SMTP_HOST`, `SMTP_USUARIO`,
`SMTP_SENHA` e `EMAIL_REMETENTE` como vazios antes de qualquer teste
rodar. Os testes que precisam exercitar o envio substituem a função
`emails.enviar` por uma que captura a mensagem em memória. Ver
[ADR 0013](../../docs/decisions/0013-email-transacional-brevo.md).

## Como rodar

```bash
cd cloud
pip install -r requirements.txt -r tests/requirements-test.txt
pytest -q          # ou `pytest -v` para ver nome por nome
```

Os mesmos testes rodam na CI a cada push, e o Railway só publica depois
que eles passam ([ADR 0014](../../docs/decisions/0014-deploy-railway-e-gate-de-ci.md)).
