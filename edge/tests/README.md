# edge/tests

Testes automatizados do software do dispositivo (32 testes). O hardware
(câmera, GPIO, I2C e DHT22) é simulado, então a suíte roda fora do
Raspberry Pi.

| Arquivo | Testes | O que verifica |
|---|---|---|
| `test_config.py` | 4 | Caminhos ancorados na pasta `edge/` e erro claro quando falta configuração |
| `test_compress.py` | 2 | Recompressão JPEG válida e efeito da qualidade |
| `test_dht22.py` | 5 | Leitura do DHT22 e tolerância a falhas pontuais |
| `test_soil_moisture.py` | 7 | Leitura do ADS1115, conversão pela calibração e seleção de canal |
| `test_led_flash.py` | 6 | Acionamento do LED pelo MOSFET |
| `test_offline_queue.py` | 3 | Retenção das capturas na fila local até a confirmação do envio |
| `test_uploader.py` | 5 | Envio, falhas de rede, recusa da API e reenvio idempotente |

A fila local usa `fcntl`, disponível apenas em Linux. No Windows, os 8
testes de `test_offline_queue.py` e `test_uploader.py` são ignorados; use
WSL ou Linux para rodar a suíte completa.

## Execução

```bash
pip install -r edge/tests/requirements-test.txt
python -m pytest edge/tests -q
```

`edge/requirements.txt` não é necessário para os testes: ele inclui
pacotes que só se instalam no Raspberry Pi, como `RPi.GPIO`.
