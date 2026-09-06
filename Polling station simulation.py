from datetime import datetime, timedelta
import random

# ==========================================
# PARÁMETROS GENERALES
# ==========================================

TOTAL_BEATS = 600  # 10 horas * 60 minutos
BASE_VOTERS_TARGET = 450
START_TIME = datetime.strptime("8:00 AM", "%I:%M %p")

# Probabilidad base por hora (8:00 a 17:00)
PROB_HOUR = [
    0.15,   # 8:00 - 9:00
    0.175,  # 9:00 - 10:00
    0.125,  # 10:00 - 11:00
    0.075,  # 11:00 - 12:00
    0.025,  # 12:00 - 1:00
    0.025,  # 1:00 - 2:00
    0.025,  # 2:00 - 3:00
    0.075,  # 3:00 - 4:00
    0.15,   # 4:00 - 5:00
    0.175   # 5:00 - 6:00
]

# Tipo de clima, probabilidad de ocurrencia y efecto multiplicador
PROB_CLIMA = [
    ["SOLEADO", 0.80, 0.90],
    ["NUBLADO", 0.15, 1.10],
    ["LLUVIA_LEVE", 0.045, 0.85],
    ["LLUVIA_MODERADA", 0.005, 0.50]
]

clima_types = [item[0] for item in PROB_CLIMA]
clima_weights = [item[1] for item in PROB_CLIMA]
clima_effects = {item[0]: item[2] for item in PROB_CLIMA}

# Partidos políticos
PARTIDOS = ["Morena", "PAN", "PRI", "Movimiento Ciudadano", "Nulos", "Otros"]
PARTIDOS_PROBS = [0.4708, 0.1443, 0.1241, 0.0775, 0.0110, 0.1723]


# ==========================================
# DEFINICIÓN DE AGENTES
# ==========================================

class AgenteVotante:

    def __init__(self, voter_id, spawn_minute, time_str):
        self.voter_id = voter_id
        self.spawn_minute = spawn_minute
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
        self.current_voter = None
        self.is_busy = False
        self.time_remaining = 0


# Agentes Dummy
class AgenteMesaDirectiva:

    def __init__(self, agent_id, rol="Presidente"):
        self.agent_id = agent_id
        self.rol = rol
        self.is_busy = False
        self.current_voter = None


class AgenteObservador:

    def __init__(self, observer_id, organizacion="INE"):
        self.observer_id = observer_id
        self.organizacion = organizacion
        self.incidencias_reportadas = 0


# ==========================================
# INICIALIZACIÓN Y SIMULACIÓN
# ==========================================

# Instancias de prueba
mesa_ayudante = AgenteMesaDirectiva(agent_id=1, rol="Secretario")
observador = AgenteObservador(observer_id=1, organizacion="Observador Ciudadano")

# Determinar clima por bloque de 1 hora
clima_por_hora = {}
for h in range(10):
    clima_por_hora[h] = random.choices(clima_types, weights=clima_weights, k=1)[0]

voters_spawned = []
beat_logs = []
current_voter_id = 1

for beat in range(TOTAL_BEATS):
    hour_idx = beat // 60
    current_beat_time = START_TIME + timedelta(minutes=beat)
    time_label = current_beat_time.strftime("%I:%M %p").lstrip("0")

    clima_actual = clima_por_hora[hour_idx]
    efecto_clima = clima_effects[clima_actual]
    peso_hora = PROB_HOUR[hour_idx]

    # Probabilidad de spawn por beat
    prob_spawn_beat = (BASE_VOTERS_TARGET * peso_hora * efecto_clima) / 60.0

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
print("               REGISTRO BEAT A BEAT (GENERACIÓN DE AGENTES)")
print("=" * 80)

for beat, time_str, did_spawn, agent in beat_logs:
    if did_spawn:
        print(
            f"[Beat {beat:03d} | {time_str:>8}] -> ¡SPAWN! Agente ID: {agent.voter_id:<3} | "
            f"Partido: {agent.partido:<20} | INE Válida: {str(agent.ine_valida):<5} | "
            f"Prioridad: {agent.resumen_prioridades():<20} | "
            f"Tiempos(s) [Llegada: {agent.t_llegada_seg}, INE: {agent.t_confirmacion_seg}, "
            f"Voto: {agent.t_votacion_seg}, Salida: {agent.t_retirada_seg}]"
        )
    else:
        print(f"[Beat {beat:03d} | {time_str:>8}] -> Sin generación")

print("\n" + "=" * 80)
print("                          MÉTRICAS FINALES")
print("=" * 80)
print(f"Total de beats simulados: {TOTAL_BEATS}")
print(f"Total de agentes generados: {len(voters_spawned)}")
valid_ines = sum(1 for v in voters_spawned if v.ine_valida)
print(
    f"Votantes con INE válida: {valid_ines} ({(valid_ines/len(voters_spawned)*100) if voters_spawned else 0:.1f}%)"
)