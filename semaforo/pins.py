"""
Mapeamento dos pinos em modo BCM (numeração GPIO da Raspberry Pi).

Constantes conforme as tabelas do enunciado: semáforos, pedestres, buzzer e sensores.
"""

import os

# Modelo 1 — três saídas (LEDs) para verde, amarelo e vermelho (cruzamento 1).

M1_LED_VERDE = 17
M1_LED_AMARELO = 18
M1_LED_VERMELHO = 23

# Pedestres: nível baixo em repouso; acionamento com pulso em nível alto.
# Tabela do trabalho: pedestre principal do M1 no GPIO 1. Em várias placas o pino 1
# está reservado (HAT / I2C) e não pode ser usado; nesse caso ajuste via ambiente.
# Para forçar o GPIO 1 quando o hardware permitir: export FSE_PIN_M1_PED_PRINCIPAL=1
M1_BOTAO_PED_PRINCIPAL = int(os.environ.get("FSE_PIN_M1_PED_PRINCIPAL", "27"))
M1_BOTAO_PED_CRUZAMENTO = 12

# Modelo 2 — três saídas que codificam o estado do semáforo (cruzamento 2).

M2_BIT0 = 24
M2_BIT1 = 8
M2_BIT2 = 7

# Pedestres do modelo 2 (um por via do cruzamento).
M2_BOTAO_PED_PRINCIPAL = 25
M2_BOTAO_PED_CRUZAMENTO = 22

# Periféricos no modo distribuído — buzzer e entradas de sensores.

# Buzzer (saída). Altere se o laboratório usar outro pino.
BUZZER = 16

# Sensores (entradas digitais; conferir a montagem).
# Presença / passagem 1 e 2
SENSOR_PRESENCA_PASSAGEM_1 = 5
SENSOR_PRESENCA_PASSAGEM_2 = 6
# Velocidade / presença / passagem 1 e 2
SENSOR_VELO_PRES_PASS_1 = 13
SENSOR_VELO_PRES_PASS_2 = 19
