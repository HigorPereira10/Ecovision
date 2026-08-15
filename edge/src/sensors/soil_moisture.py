"""
edge/src/sensors/soil_moisture.py

Leitura do sensor capacitivo de umidade do solo, via ADC ADS1115
(I2C, 16-bit), o Pi Zero não tem ADC nativo, por isso o ADS1115 é
obrigatório (Blueprint v3.0, Fase 1).

Sensor capacitivo foi escolhido (não resistivo) por evitar corrosão por
eletrólise em uso contínuo no solo úmido.

Relação com o resto do sistema:
- Chamado por edge/src/main.py em cada ciclo de captura.
- A leitura resultante entra no pacote enviado para o endpoint
  /diagnostico e é persistida na tabela leituras_ambientais
  (cloud/app/db/models.py).
"""

# import board
# import busio
# from adafruit_ads1x15.analog_in import AnalogIn
# import adafruit_ads1x15.ads1115 as ADS

# def ler_umidade_solo() -> float:
#     """Lê o canal analógico do sensor de solo via ADS1115 e retorna um percentual."""
#     raise NotImplementedError
