from datetime import datetime, timedelta
import math
import random

# ==============================================================================
# PARÁMETROS GENERALES
# ==============================================================================
BEATS_PER_HOUR = 120  # 1 beat = 30 seg, 120 beats = 1 hora
TOTAL_BEATS = 1200  # 10 horas * 120 beats (8:00 AM - 6:00 PM)

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


# ==============================================================================
# DEFINICIÓN DE AGENTES
# ==============================================================================
class AgenteVotante:

    def __init__(self, voter_id, spawn_beat, time_str):
        self.voter_id = voter_id
        self.spawn_beat = spawn_beat
        self.spawn_time_str = time_str

        self.partido = random.choices(PARTIDOS, weights=PARTIDOS_PROBS, k=1)[0]
        self.ine_valida = random.random() < 0.95

        self.tercera_edad = random.random() < 0.185
        self.discapacidad = random.random() < random.uniform(0.01, 0.02)
        self.embarazo = (
            random.random() < random.uniform(0.02, 0.04)
            if not self.tercera_edad
            else False
        )
        self.es_prioridad = (
                self.tercera_edad or self.discapacidad or self.embarazo
        )

        # Tiempos continuos en segundos (Distribución triangular)
        self.t_llegada_seg = round(random.triangular(30, 60, 45), 2)
        self.t_confirmacion_seg = round(random.triangular(30, 45, 37.5), 2)
        self.t_votacion_seg = round(random.triangular(60, 300, 180), 2)
        self.t_retirada_seg = round(random.triangular(60, 120, 90), 2)

    @property
    def beats_confirmacion(self):
        return max(1, math.ceil(self.t_confirmacion_seg / 30))

    @property
    def beats_votacion(self):
        return max(1, math.ceil(self.t_votacion_seg / 30))

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
        self.busy_until_beat = -1

    def is_free(self, current_beat):
        return current_beat >= self.busy_until_beat


class AgenteCasilla:

    def __init__(self, casilla_id):
        self.casilla_id = casilla_id
        self.current_voter = None
        self.busy_until_beat = -1

    def is_free(self, current_beat):
        return current_beat >= self.busy_until_beat


class AgenteContador:

    def __init__(self, counter_id, prob_error=0.001):
        self.counter_id = counter_id
        self.prob_error = prob_error

    def _aplicar_posible_error(self, valor_real):
        # 0.1% de probabilidad de error (+1 o -1 con igual probabilidad)
        if random.random() < self.prob_error:
            error = random.choice([-1, 1])
            return max(0, valor_real + error)
        return valor_real

    def contar(self, lista_votantes, lista_partidos):
        # 1. Total de personas que llegaron
        total_personas_real = len(lista_votantes)
        total_personas_contado = self._aplicar_posible_error(total_personas_real)

        # 2. Total de votos emitidos (INE válida)
        votos_validos = [v for v in lista_votantes if v.ine_valida]
        total_votos_real = len(votos_validos)
        total_votos_contado = self._aplicar_posible_error(total_votos_real)

        # 3. Votos por partido
        votos_partido_contados = {}
        for partido in lista_partidos:
            real_partido = sum(1 for v in votos_validos if v.partido == partido)
            votos_partido_contados[partido] = self._aplicar_posible_error(real_partido)

        return {
            "total_personas": total_personas_contado,
            "total_votos": total_votos_contado,
            "votos_partido": votos_partido_contados,
        }


# ==============================================================================
# INICIALIZACIÓN DE LA SIMULACIÓN
# ==============================================================================
queue_ine = []
queue_ine_prioridad = []
queue_casilla = []
queue_casilla_prioridad = []

recipientes = [AgenteRecipiente(i + 1) for i in range(3)]
casillas = [AgenteCasilla(i + 1) for i in range(5)]
contadores = [AgenteContador(i + 1) for i in range(3)]

clima_por_hora = {
    h: random.choices(clima_types, weights=clima_weights, k=1)[0]
    for h in range(10)
}

voters_spawned = []
current_voter_id = 1
next_recipiente_prio = True
next_casilla_prio = True


def imprimir_estado_colas(beat_actual):
    tiempo_actual = START_TIME + timedelta(seconds=beat_actual * 30)
    hora_str = tiempo_actual.strftime("%I:%M %p").lstrip("0")
    h_idx = beat_actual // BEATS_PER_HOUR

    print("\n" + "-" * 80)
    print(f">>> [ESTADO HORARIO] Hora {h_idx:02d} | {hora_str} (Beat {beat_actual})")
    print("-" * 80)

    # Estado de recipientes
    rec_status = [
        f"R{r.recipient_id}: [ID {r.current_voter.voter_id if r.current_voter else 'Libre'}]"
        for r in recipientes
    ]
    print(f"  Recipientes (Recepción) : {', '.join(rec_status)}")

    # Estado de casillas
    cas_status = [
        f"C{c.casilla_id}: [ID {c.current_voter.voter_id if c.current_voter else 'Libre'}]"
        for c in casillas
    ]
    print(f"  Casillas (Votación)     : {', '.join(cas_status)}")

    # Estado de las 4 colas
    ids_ine = [v.voter_id for v in queue_ine]
    ids_ine_prio = [v.voter_id for v in queue_ine_prioridad]
    ids_casilla = [v.voter_id for v in queue_casilla]
    ids_casilla_prio = [v.voter_id for v in queue_casilla_prioridad]

    print(f"  Queue INE               ({len(ids_ine):3d}): {ids_ine if ids_ine else 'Vacía'}")
    print(f"  Queue INE Prioridad     ({len(ids_ine_prio):3d}): {ids_ine_prio if ids_ine_prio else 'Vacía'}")
    print(f"  Queue Casilla           ({len(ids_casilla):3d}): {ids_casilla if ids_casilla else 'Vacía'}")
    print(f"  Queue Casilla Prioridad ({len(ids_casilla_prio):3d}): {ids_casilla_prio if ids_casilla_prio else 'Vacía'}")
    print("-" * 80 + "\n")


# ==============================================================================
# CICLO PRINCIPAL DE SIMULACIÓN (BEATS)
# ==============================================================================
beat = 0

print("=" * 80)
print("              INICIO DE LA SIMULACIÓN (REGISTRO BEAT A BEAT)")
print("=" * 80)

while (
        beat < TOTAL_BEATS
        or len(queue_ine) > 0
        or len(queue_ine_prioridad) > 0
        or len(queue_casilla) > 0
        or len(queue_casilla_prioridad) > 0
        or any(not r.is_free(beat) for r in recipientes)
        or any(not c.is_free(beat) for c in casillas)
):
    # Snapshot por hora
    if beat % BEATS_PER_HOUR == 0:
        imprimir_estado_colas(beat)

    hour_idx = min(beat // BEATS_PER_HOUR, 9)
    current_beat_time = START_TIME + timedelta(seconds=beat * 30)
    time_label = current_beat_time.strftime("%I:%M:%S %p").lstrip("0")

    # 1. FINALIZAR VOTACIONES EN CASILLAS
    for c in casillas:
        if c.current_voter and c.busy_until_beat == beat:
            c.current_voter = None

    # 2. FINALIZAR VERIFICACIONES EN RECIPIENTES Y MOVER A CASILLAS
    for r in recipientes:
        if r.current_voter and r.busy_until_beat == beat:
            voter = r.current_voter
            if voter.ine_valida:
                if voter.es_prioridad:
                    queue_casilla_prioridad.append(voter)
                else:
                    queue_casilla.append(voter)
            r.current_voter = None

    # 3. SPAWN DE NUEVOS VOTANTES (Solo durante los 1200 beats reglamentarios)
    if beat < TOTAL_BEATS:
        clima_actual = clima_por_hora[hour_idx]
        efecto_clima = clima_effects[clima_actual]
        peso_hora = PROB_HOUR[hour_idx]

        prob_spawn_beat = (
                                  BASE_VOTERS_TARGET * peso_hora * efecto_clima
                          ) / BEATS_PER_HOUR

        if random.random() < prob_spawn_beat:
            agent = AgenteVotante(current_voter_id, beat, time_label)
            voters_spawned.append(agent)
            current_voter_id += 1

            if agent.es_prioridad:
                queue_ine_prioridad.append(agent)
                dest = "Queue INE Prio"
            else:
                queue_ine.append(agent)
                dest = "Queue INE"

            print(
                f"[Beat {beat:04d} | {time_label:>11}] -> ¡SPAWN! ID: {agent.voter_id:<3} | "
                f"Destino: {dest:<14} | Partido: {agent.partido:<20} | INE: {str(agent.ine_valida):<5} | "
                f"Prioridad: {agent.resumen_prioridades():<20} | Tiempos(s) [Llegada: {agent.t_llegada_seg}, "
                f"INE: {agent.t_confirmacion_seg}, Voto: {agent.t_votacion_seg}, Salida: {agent.t_retirada_seg}]"
            )

    # 4. ASIGNACIÓN A RECIPIENTES (Alternancia 1 a 1)
    for r in recipientes:
        if r.is_free(beat) and (queue_ine or queue_ine_prioridad):
            voter_to_serve = None
            if (next_recipiente_prio and queue_ine_prioridad) or (not queue_ine and queue_ine_prioridad):
                voter_to_serve = queue_ine_prioridad.pop(0)
                next_recipiente_prio = False
            elif queue_ine:
                voter_to_serve = queue_ine.pop(0)
                next_recipiente_prio = True

            if voter_to_serve:
                r.current_voter = voter_to_serve
                r.busy_until_beat = beat + voter_to_serve.beats_confirmacion

    # 5. ASIGNACIÓN A CASILLAS (Alternancia 1 a 1)
    for c in casillas:
        if c.is_free(beat) and (queue_casilla or queue_casilla_prioridad):
            voter_to_vote = None
            if (next_casilla_prio and queue_casilla_prioridad) or (not queue_casilla and queue_casilla_prioridad):
                voter_to_vote = queue_casilla_prioridad.pop(0)
                next_casilla_prio = False
            elif queue_casilla:
                voter_to_vote = queue_casilla.pop(0)
                next_casilla_prio = True

            if voter_to_vote:
                c.current_voter = voter_to_vote
                c.busy_until_beat = beat + voter_to_vote.beats_votacion

    beat += 1

# Snapshot final al concluir toda la jornada extendida
imprimir_estado_colas(beat)

# ==============================================================================
# REPORTES FINALES
# ==============================================================================
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

total_spawned_count = len(voters_spawned)
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
print(f"Total de beats reglamentarios: {TOTAL_BEATS} (hasta las 6:00 PM)")
print(f"Total de beats reales corridos: {beat} (finalizó a las {(START_TIME + timedelta(seconds=beat*30)).strftime('%I:%M:%S %p')})")
print(f"Total de agentes generados: {total_spawned_count}")
valid_ines = sum(1 for v in voters_spawned if v.ine_valida)
print(
    f"Votantes con INE válida: {valid_ines}"
    f" ({(valid_ines/total_spawned_count*100) if total_spawned_count else 0:.1f}%)"
)

conteo_votos = {partido: 0 for partido in PARTIDOS}
for agent in voters_spawned:
    if agent.ine_valida:
        conteo_votos[agent.partido] += 1

print("\n" + "=" * 80)
print("                     RESULTADOS DE LA ELECCIÓN")
print("=" * 80)
votos_ordenados = sorted(conteo_votos.items(), key=lambda item: item[1], reverse=True)

for partido, votos in votos_ordenados:
    pct = (votos / valid_ines * 100) if valid_ines > 0 else 0.0
    barra = "█" * int(pct // 2)
    print(f"{partido:<22} | {votos:3d} votos ({pct:5.2f}%) | {barra}")

print("-" * 80)
print(f"Total de votos emitidos (INE válida): {valid_ines}")
votos_descartados = total_spawned_count - valid_ines
print(f"Votos no emitidos (INE rechazada)  : {votos_descartados}")

# ==============================================================================
# CONTEO INDEPENDIENTE DE AGENTES CONTADORES (CON 0.1% PROBABILIDAD DE ERROR)
# ==============================================================================
print("\n" + "=" * 80)
print("               CONTEO INDEPENDIENTE DE LOS AGENTES CONTADORES")
print("=" * 80)

resultados_contadores = [c.contar(voters_spawned, PARTIDOS) for c in contadores]

for i, res in enumerate(resultados_contadores, start=1):
    print(f"\n--- Agente Contador #{i} ---")
    print(f"Total de personas contadas : {res['total_personas']}")
    print(f"Total de votos contados    : {res['total_votos']}")
    print("Votos por partido:")
    for partido in PARTIDOS:
        print(f"  - {partido:<22}: {res['votos_partido'][partido]:3d} votos")