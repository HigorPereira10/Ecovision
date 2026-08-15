"""
edge/src/sensors/dht22.py

Leitura do sensor DHT22 (temperatura/umidade do ar, protocolo 1-Wire),
via biblioteca Adafruit_DHT (Blueprint v3.0, Fase 1 e 2).

Precisão do sensor: ±0.5°C / ±2-5%RH. O BoM prevê 2 unidades (1 sobressalente).

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

# import Adafruit_DHT

# def ler_dht22(pino: int) -> dict:
#     """Retorna {'temperatura_c': float, 'umidade_ar_pct': float}."""
#     raise NotImplementedError
