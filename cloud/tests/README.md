# cloud/tests: Testes automatizados do backend

## Para quem nunca mexeu com testes automatizados: o que é isso?

Ver a explicação completa em [`edge/tests/README.md`](../../edge/tests/README.md).
O resumo é: um pequeno programa que simula uma situação real (ex.: "a
Raspberry Pi mandou uma foto sem a API Key certa") e confere se o sistema
reage do jeito esperado, sem precisar de um Supabase real nem de rede.

## O que cada arquivo testa

- **`test_security.py`**: confere que a API só aceita requisições do
  dispositivo com a API Key certa; chave errada ou ausente é sempre
  recusada.

- **`test_inference.py`**: confere que a etapa de inferência (a parte
  que "olha" a foto e tenta identificar a doença) funciona mesmo sem um
  modelo de IA real disponível ainda (o time de ML ainda não entregou o
  `.tflite` treinado), a API devolve um resultado "indisponível" em vez
  de travar. Também confere que o pré-processamento da imagem (redimensionar
  para 224×224) gera o formato certo para alimentar qualquer modelo TFLite
  no futuro.

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

## Como rodar

```bash
cd cloud
pip install -r requirements.txt -r tests/requirements-test.txt
pytest tests -v
```
