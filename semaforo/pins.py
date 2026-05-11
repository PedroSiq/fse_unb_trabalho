"""Mapeamento BCM dos pinos conforme tabelas da especificação."""

# Modelo 1 — 3 LEDs (Cruzamento 1) → diagrama: “Sinal de Trânsito 1 e 3”
M1_LED_VERDE = 17
M1_LED_AMARELO = 18
M1_LED_VERMELHO = 23

# Modelo 1 — botões pedestre (normalmente baixo, pulso alto ~200 ms)
M1_BOTAO_PED_PRINCIPAL = 1
M1_BOTAO_PED_CRUZAMENTO = 12

# Modelo 2 — saída 3 bits (Cruzamento 2) → diagrama: “Sinal de Trânsito 2 e 4”
M2_BIT0 = 24
M2_BIT1 = 8
M2_BIT2 = 7

# Modelo 2 — botões pedestre
M2_BOTAO_PED_PRINCIPAL = 25
M2_BOTAO_PED_CRUZAMENTO = 22

# Buzzer (saída dedicada no servidor distribuído — ajuste ao hardware)
BUZZER = 16

# Sensores (entradas digitais; BCM livres — conferir fiação)
# Presença/passagem 1 e 2
SENSOR_PRESENCA_PASSAGEM_1 = 5
SENSOR_PRESENCA_PASSAGEM_2 = 6
# Velocidade / presença / passagem 1 e 2
SENSOR_VELO_PRES_PASS_1 = 13
SENSOR_VELO_PRES_PASS_2 = 19
