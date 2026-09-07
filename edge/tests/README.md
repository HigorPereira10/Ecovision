# edge/tests: Testes automatizados do software de borda

## Para quem nunca mexeu com testes automatizados: o que é isso?

Um "teste automatizado" é um pequeno programa que executa uma parte do
código sozinho, simulando uma situação real (ex.: "a internet caiu no
meio do envio da foto"), e confere se o resultado foi o esperado (ex.:
"a foto não pode ter sido apagada"). Em vez de uma pessoa testar
manualmente toda vez que o código muda, o computador testa em menos de
1 segundo, e avisa imediatamente se alguma alteração futura quebrar
algo que já funcionava.

Aqui eles servem principalmente para uma coisa: **provar, sem precisar
de nenhuma Raspberry Pi nem sensor físico em mãos, que a parte do
código que não depende de hardware (fila de fotos pendentes + envio
para a API) está correta.** As partes que só existem no hardware real
(câmera, sensores, LED) não têm como ser testadas aqui; essas só se
confirmam com a Pi montada.

## O que cada arquivo testa

- **`test_config.py`**: confere duas coisas: (1) que os caminhos de
  pastas (onde ficam as fotos pendentes, onde ficam os logs) sempre
  apontam para dentro da pasta `edge/` do projeto, não importa de onde
  o script é chamado (isso corrige um bug real que existia antes,
  onde o caminho podia "escorregar" dependendo de quem chamava o
  script); e (2) que o programa avisa claramente, e não trava de forma
  confusa, se esquecerem de configurar a URL da API ou a chave do
  dispositivo.

- **`test_compress.py`**: confere que a compressão de imagem (que
  reduz o tamanho da foto antes de mandar pela internet, já que a
  conexão na estufa pode ser fraca) realmente entrega um arquivo JPEG
  que abre sem erro, e que pedir mais qualidade de fato gera um
  arquivo maior, prova de que a compressão está sendo aplicada de
  verdade, não ignorada.

- **`test_offline_queue.py`**: testa o mecanismo que guarda fotos e
  leituras de sensores em disco quando a internet cai, para não perder
  nada, e depois libera esse espaço quando a entrega é confirmada.
  Simula: guardar duas capturas, conferir que as duas aparecem como
  pendentes, confirmar o envio de uma e checar que só ela (e só a
  imagem dela) desaparece, a outra continua intacta esperando sua vez.

- **`test_uploader.py`**: testa o envio das fotos pendentes para a
  API. Como o servidor da API (`cloud/`) ainda não está pronto, o
  teste "engana" o programa com uma conexão de internet falsa que a
  gente controla, simulando: sucesso no envio, falha de rede, a API
  recusando o pedido, e o caso raro de uma imagem já ter sido apagada
  antes da confirmação chegar. Em todos os casos de falha, a regra de
  ouro é: **nada pode ser apagado até a API confirmar que recebeu.**

## Por que alguns testes só rodam no WSL/Linux, e não no Windows

A fila de fotos pendentes usa um recurso do sistema chamado `fcntl`
("trava de arquivo") para evitar que o arquivo da fila seja corrompido
se duas coisas tentarem mexer nele ao mesmo tempo (ex.: uma nova foto
chegando enquanto o envio de outra está em andamento), o mesmo
tipo de proteção que a Raspberry Pi vai usar de verdade, rodando Linux.
O problema é que `fcntl` **só existe em Linux/Unix**, não existe no
Windows. Por isso:

- Rodando os testes direto no Windows, os testes de `config.py` e
  `compress.py` passam normalmente, e os de fila/upload são **pulados
  automaticamente** (aparecem como "skipped", não como erro), porque
  não faz sentido testar no Windows algo que só existe em Linux.
- Rodando dentro do **WSL (Windows Subsystem for Linux)**, que é um
  Linux de verdade rodando dentro do Windows, todos os testes rodam,
  incluindo os de fila/upload.

Não é preciso a Raspberry Pi física para isso, só precisa de um
Linux, e o WSL já serve.

## Como rodar

### Dentro do WSL/Ubuntu (recomendado, roda os 14 testes)

```bash
cd /mnt/c/Users/<seu-usuario>/.../Ecovision   # ajuste pro seu caminho
pip install -r edge/tests/requirements-test.txt
pytest edge/tests -v
```

### Direto no Windows (roda 6 dos 14, os que não dependem de fcntl)

```powershell
pip install -r edge/tests/requirements-test.txt
pytest edge/tests -v
```

## O que NÃO está coberto por esses testes (só dá pra confirmar na Pi física)

- Captura de foto pela câmera (Picamera2, autofoco).
- Leitura real dos sensores (DHT22, umidade do solo via ADS1115).
- Acionamento do Ring LED via MOSFET.
- O agendamento via `cron` rodando de verdade, ao longo de horas/dias.
