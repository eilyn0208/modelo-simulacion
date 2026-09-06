from datetime import datetime, timedelta
import random

# PARÁMETROS GENERALES !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

BEATS_PER_HOUR = 120  # 2 beats * 60 minutos
TOTAL_BEATS = 1200  # 10 horas * 120 beats

BASE_VOTERS_TARGET = 450
START_TIME = datetime.strptime("8:00 AM", "%I:%M %p")

PROB_HOUR = [
    0.15,  # 8:00 - 9:00
    0.175,  # 9:00 - 10:00
    0.125,  # 10:00 - 11:00
    0.075,  # 11:00 - 12:00
    0.025,  # 12:00 - 1:00
    0.025,  # 1:00 - 2:00
    0.025,  # 2:00 - 3:00
    0.075,  # 3:00 - 4:00
    0.15,  # 4:00 - 5:00
    0.175,  # 5:00 - 6:00
]

PROB_CLIMA = [
    ["SOLEADO", 0.80, 0.90],
    ["NUBLADO", 0.15, 1.10],
    ["LLUVIA_LEVE", 0.045, 0.85],
    ["LLUVIA_MODERADA", 0.005, 0.50],
]

clima_types = [item[0] for item in PROB_CLIMA]
clima_weights = [item[1] for item in PROB_CLIMA]
clima_effects = {item[0]: item[2] for item in PROB_CLIMA}

PARTIDOS = ["Morena", "PAN", "PRI", "Movimiento Ciudadano", "Nulos", "Otros"]
PARTIDOS_PROBS = [0.4708, 0.1443, 0.1241, 0.0775, 0.0110, 0.1723]


# DEFINICIÓN DE AGENTES !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


class AgenteVotante:

    def __init__(self, voter_id, spawn_beat, time_str):
        self.voter_id = voter_id
        self.spawn_beat = spawn_beat
        self.spawn_time_str = time_str

        self.partido = random.choices(PARTIDOS, weights=PARTIDOS_PROBS, k=1)[0]
        self.ine_valida = random.random() < 0.95

        self.tercera_edad = random.random() < 0.185
        self.discapacidad = random.random() < random.uniform(0.01, 0.02)

        if not self.tercera_edad:
            self.embarazo = random.random() < random.uniform(0.02, 0.04)
        else:
            self.embarazo = False

        # Tiempos en segundos (Distribución triangular)
        self.t_llegada_seg = round(random.triangular(30, 60, 45), 2)
        self.t_confirmacion_seg = round(random.triangular(30, 45, 37.5), 2)
        self.t_votacion_seg = round(random.triangular(60, 300, 180), 2)
        self.t_retirada_seg = round(random.triangular(60, 120, 90), 2)

    def resumen_prioridades(self):
        prios = []
        if self.tercera_edad:
            prios.append("Tercera Edad")
        if self.discapacidad:
            prios.append("Discapacidad")
        if self.embarazo:
            prios.append("Embarazo")
        return ", ".join(prios) if prios else "Ninguna"


class AgenteRecipiente:

    def __init__(self, recipient_id):
        self.recipient_id = recipient_id


class AgenteContador:

    def __init__(self, counter_id):
        self.counter_id = counter_id


queue_ine = []
queue_ine_prioridad = []
queue_casilla = []

# INICIALIZACIÓN DE SIMULACIÓN !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

recipiente1 = AgenteRecipiente(recipient_id=1)
recipiente2 = AgenteRecipiente(recipient_id=2)
recipiente3 = AgenteRecipiente(recipient_id=3)

clima_por_hora = {}

for h in range(10):
    clima_por_hora[h] = random.choices(clima_types, weights=clima_weights, k=1)[0]

voters_spawned = []
beat_logs = []
current_voter_id = 1

for beat in range(TOTAL_BEATS):

    hour_idx = beat // BEATS_PER_HOUR
    current_beat_time = START_TIME + timedelta(seconds=beat * 30)
    time_label = current_beat_time.strftime("%I:%M:%S %p").lstrip("0")

    clima_actual = clima_por_hora[hour_idx]
    efecto_clima = clima_effects[clima_actual]
    peso_hora = PROB_HOUR[hour_idx]


    prob_spawn_beat = (BASE_VOTERS_TARGET * peso_hora * efecto_clima) / BEATS_PER_HOUR
    # best case: 450 * 0.175 * 1.1 / 120 = 0.721875
    # worst case: 450 * 0.025 * 0.5 / 120 = 0.046875

    spawned = random.random() < prob_spawn_beat

    if spawned:
        agent = AgenteVotante(current_voter_id, beat, time_label)
        voters_spawned.append(agent)
        current_voter_id += 1
        beat_logs.append((beat, time_label, True, agent))
    else:
        beat_logs.append((beat, time_label, False, None))


# ==========================================
# REPORTE FINAL
# ==========================================

print("=" * 80)
print("                      REPORTE DE CLIMA POR HORA")
print("=" * 80)

for h in range(10):
    hora_inicio = (START_TIME + timedelta(hours=h)).strftime("%I:%M %p")
    hora_fin = (START_TIME + timedelta(hours=h + 1)).strftime("%I:%M %p")
    clima = clima_por_hora[h]
    print(
        f"Hora {h+1:02d} [{hora_inicio} - {hora_fin}]: "
        f"Clima: {clima:<15} | Multiplicador: {clima_effects[clima]:.2f}x | "
        f"Peso Asistencia: {PROB_HOUR[h]*100:.1f}%"
    )

print("\n" + "=" * 80)
print("          REGISTRO BEAT A BEAT (INTERVALOS DE 30 SEGUNDOS)")
print("=" * 80)

for beat, time_str, did_spawn, agent in beat_logs:
    if did_spawn:
        print(
            f"[Beat {beat:04d} | {time_str:>11}] -> ¡SPAWN! ID: {agent.voter_id:<3} |"
            f" Partido: {agent.partido:<20} | INE: {str(agent.ine_valida):<5} |"
            f" Prioridad: {agent.resumen_prioridades():<20} | Tiempos(s) [Llegada:"
            f" {agent.t_llegada_seg}, INE: {agent.t_confirmacion_seg}, Voto:"
            f" {agent.t_votacion_seg}, Salida: {agent.t_retirada_seg}]"
        )
    else:
        print(f"[Beat {beat:04d} | {time_str:>11}] -> Sin generación")

# ----------------------------------------------------
# DISTRIBUCIÓN HORARIA DE VOTANTES GENERADOS
# ----------------------------------------------------
total_spawned_count = len(voters_spawned)

# Conteo por hora según el beat de spawn
voters_by_hour = [0] * 10
for agent in voters_spawned:
    hour_index = agent.spawn_beat // BEATS_PER_HOUR
    voters_by_hour[hour_index] += 1

print("\n" + "=" * 80)
print("             DISTRIBUCIÓN DE VOTANTES GENERADOS POR HORA")
print("=" * 80)
for h in range(10):
    hora_inicio = (START_TIME + timedelta(hours=h)).strftime("%I:%M %p")
    hora_fin = (START_TIME + timedelta(hours=h + 1)).strftime("%I:%M %p")
    count = voters_by_hour[h]
    pct = (count / total_spawned_count * 100) if total_spawned_count > 0 else 0.0
    print(
        f"Hora {h+1:02d} [{hora_inicio:>8} - {hora_fin:>8}]: {count:3d} votantes"
        f" ({pct:5.2f}% del total)"
    )

print("\n" + "=" * 80)
print("                          MÉTRICAS FINALES")
print("=" * 80)
print(f"Total de beats simulados: {TOTAL_BEATS}")
print(f"Total de agentes generados: {total_spawned_count}")
valid_ines = sum(1 for v in voters_spawned if v.ine_valida)
print(
    f"Votantes con INE válida: {valid_ines}"
    f" ({(valid_ines/total_spawned_count*100) if total_spawned_count else 0:.1f}%)"
)

# Inicializar conteo en 0 para cada partido
conteo_votos = {partido: 0 for partido in PARTIDOS}

# Contar únicamente los votos de agentes cuya credencial fue válida
for agent in voters_spawned:
    if agent.ine_valida:
        conteo_votos[agent.partido] += 1

print("\n" + "=" * 80)
print("                     RESULTADOS DE LA ELECCIÓN")
print("=" * 80)

# Ordenar los resultados de mayor a menor número de votos
votos_ordenados = sorted(conteo_votos.items(), key=lambda item: item[1], reverse=True)

for partido, votos in votos_ordenados:
    pct = (votos / valid_ines * 100) if valid_ines > 0 else 0.0
    barra = "█" * int(pct // 2)  # Barra visual proporcional (máx 50 caracteres)
    print(f"{partido:<22} | {votos:3d} votos ({pct:5.2f}%) | {barra}")

print("-" * 80)
print(f"Total de votos emitidos (INE válida): {valid_ines}")
votos_descartados = total_spawned_count - valid_ines
print(f"Votos no emitidos (INE rechazada)  : {votos_descartados}")