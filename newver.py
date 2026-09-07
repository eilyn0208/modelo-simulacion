from datetime import datetime, timedelta
import math
import random

# PARÁMETROS GENERALES

BEATS_PER_HOUR = 120  # 1 beat = 30 seg, 120 beats = 1 hora
TOTAL_BEATS = 1200  # 10 horas * 120 beats (8:00 AM - 6:00 PM)

BASE_VOTERS_TARGET = 450
START_TIME = datetime.strptime("8:00 AM", "%I:%M %p")

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
    0.175,  # 5:00 - 6:00
]

CLIMA_EFFECTS = {
    "SOLEADO": 0.90,
    "NUBLADO": 1.10,
    "LLUVIA_LEVE": 0.85,
    "LLUVIA_MODERADA": 0.50,
}

CLIMA_TRANSITIONS = {
    "SOLEADO": (["SOLEADO", "NUBLADO", "LLUVIA_LEVE"], [0.75, 0.20, 0.05]),
    "NUBLADO": (["SOLEADO", "NUBLADO", "LLUVIA_LEVE", "LLUVIA_MODERADA"], [0.25, 0.50, 0.20, 0.05]),
    "LLUVIA_LEVE": (["SOLEADO", "NUBLADO", "LLUVIA_LEVE", "LLUVIA_MODERADA"], [0.10, 0.40, 0.35, 0.15]),
    "LLUVIA_MODERADA": (["NUBLADO", "LLUVIA_LEVE", "LLUVIA_MODERADA"], [0.20, 0.45, 0.35]),
}

PARTIDOS = ["Morena", "PAN", "PRI", "Movimiento Ciudadano", "Nulos", "Otros"]
PARTIDOS_PROBS = [0.4708, 0.1443, 0.1241, 0.0775, 0.0110, 0.1723]


def poisson_random(lam):
    if lam <= 0:
        return 0
    l_val = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l_val:
        k += 1
        p *= random.random()
    return k - 1


# DEFINICIÓN DE AGENTES

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

        mult_tiempo = random.uniform(1.3, 1.8) if self.es_prioridad else random.uniform(0.9, 1.1)

        self.t_llegada_seg = round(random.triangular(20, 70, 40) * mult_tiempo, 2)
        self.t_confirmacion_seg = round(random.triangular(30, 60, 40) * mult_tiempo, 2)
        self.t_votacion_seg = round(random.triangular(60, 240, 150) * mult_tiempo, 2)
        self.t_retirada_seg = round(random.triangular(15, 60, 30) * mult_tiempo, 2)

        self.beats_desplazamiento_llegada = max(0, math.floor(self.t_llegada_seg / 30))
        self.beat_llegada_cola = spawn_beat + self.beats_desplazamiento_llegada

    @property
    def beats_confirmacion(self):
        return max(1, math.ceil(self.t_confirmacion_seg / 30))

    @property
    def beats_votacion_total(self):
        # La casilla permanece ocupada durante el voto y la retirada del elector
        return max(1, math.ceil((self.t_votacion_seg + self.t_retirada_seg) / 30))

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

    def __init__(self, counter_id, prob_error=0.002):
        self.counter_id = counter_id
        self.prob_error = prob_error

    def contar(self, lista_votantes, lista_partidos):
        # Conteo boleta por boleta para mantener consistencia estricta
        conteo_partidos = {p: 0 for p in lista_partidos}
        total_votos_validos = 0
        votos_validos_reales = [v for v in lista_votantes if v.ine_valida]

        for voter in votos_validos_reales:
            partido_leido = voter.partido
            # Error de mala asignación boleta por boleta
            if random.random() < self.prob_error:
                partido_leido = random.choice([p for p in lista_partidos if p != voter.partido])
            conteo_partidos[partido_leido] += 1
            total_votos_validos += 1

        # Error en el registro de acceso de votantes totales
        total_personas = len(lista_votantes)
        if random.random() < (self.prob_error * 2):
            total_personas = max(total_votos_validos, total_personas + random.choice([-1, 1]))

        return {
            "total_personas": total_personas,
            "total_votos": total_votos_validos,
            "votos_partido": conteo_partidos,
        }


# ==============================================================================
# INICIALIZACIÓN DE LA SIMULACIÓN
# ==============================================================================
# Generación de la serie de tiempo climática con Markov
clima_por_hora = {}
estado_actual = random.choices(
    ["SOLEADO", "NUBLADO", "LLUVIA_LEVE", "LLUVIA_MODERADA"],
    weights=[0.7, 0.2, 0.08, 0.02],
    k=1
)[0]

for h in range(10):
    clima_por_hora[h] = estado_actual
    opciones, pesos = CLIMA_TRANSITIONS[estado_actual]
    estado_actual = random.choices(opciones, weights=pesos, k=1)[0]

transit_voters = []  # Votantes que van en camino a la casilla
queue_ine = []
queue_ine_prioridad = []
queue_casilla = []
queue_casilla_prioridad = []

recipientes = [AgenteRecipiente(i + 1) for i in range(3)]
casillas = [AgenteCasilla(i + 1) for i in range(5)]
contadores = [AgenteContador(i + 1) for i in range(3)]

voters_spawned = []
current_voter_id = 1


def imprimir_estado_colas(beat_actual):

    tiempo_actual = START_TIME + timedelta(seconds=beat_actual * 30)
    hora_str = tiempo_actual.strftime("%I:%M %p").lstrip("0")
    h_idx = beat_actual // BEATS_PER_HOUR

    print("\n" + "-" * 80)
    print(f">>> [ESTADO HORARIO] Hora {h_idx:02d} | {hora_str} (Beat {beat_actual})")
    print("-" * 80)

    rec_status = [
        f"R{r.recipient_id}: [ID {r.current_voter.voter_id if r.current_voter else 'Libre'}]"
        for r in recipientes
    ]
    print(f"  Recipientes (Recepción) : {', '.join(rec_status)}")

    cas_status = [
        f"C{c.casilla_id}: [ID {c.current_voter.voter_id if c.current_voter else 'Libre'}]"
        for c in casillas
    ]
    print(f"  Casillas (Votación)     : {', '.join(cas_status)}")

    ids_ine = [v.voter_id for v in queue_ine]
    ids_ine_prio = [v.voter_id for v in queue_ine_prioridad]
    ids_casilla = [v.voter_id for v in queue_casilla]
    ids_casilla_prio = [v.voter_id for v in queue_casilla_prioridad]

    print(f"  En tránsito caminando   ({len(transit_voters):3d})")
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
    or len(transit_voters) > 0
    or len(queue_ine) > 0
    or len(queue_ine_prioridad) > 0
    or len(queue_casilla) > 0
    or len(queue_casilla_prioridad) > 0
    or any(not r.is_free(beat) for r in recipientes)
    or any(not c.is_free(beat) for c in casillas)
):
    if beat % BEATS_PER_HOUR == 0:
        imprimir_estado_colas(beat)

    hour_idx = min(beat // BEATS_PER_HOUR, 9)
    current_beat_time = START_TIME + timedelta(seconds=beat * 30)
    time_label = current_beat_time.strftime("%I:%M:%S %p").lstrip("0")

    # 1. FINALIZAR VOTACIONES EN CASILLAS
    for c in casillas:
        if c.current_voter and c.busy_until_beat <= beat:
            c.current_voter = None

    # 2. FINALIZAR VERIFICACIONES EN RECIPIENTES Y MOVER A CASILLAS
    for r in recipientes:
        if r.current_voter and r.busy_until_beat <= beat:
            voter = r.current_voter
            if voter.ine_valida:
                if voter.es_prioridad:
                    queue_casilla_prioridad.append(voter)
                else:
                    queue_casilla.append(voter)
            r.current_voter = None

    # 3. LLEGADA EFECTIVA DE VOTANTES EN TRÁNSITO A LAS COLAS INE
    agentes_que_llegan = [v for v in transit_voters if v.beat_llegada_cola <= beat]
    for agent in agentes_que_llegan:
        transit_voters.remove(agent)
        if agent.es_prioridad:
            queue_ine_prioridad.append(agent)
        else:
            queue_ine.append(agent)

    if beat < TOTAL_BEATS:
        clima_actual = clima_por_hora[hour_idx]
        efecto_clima = CLIMA_EFFECTS[clima_actual]
        peso_hora = PROB_HOUR[hour_idx]

        lambda_beat = (BASE_VOTERS_TARGET * peso_hora * efecto_clima) / BEATS_PER_HOUR
        num_llegadas = poisson_random(lambda_beat)

        for _ in range(num_llegadas):
            agent = AgenteVotante(current_voter_id, beat, time_label)
            voters_spawned.append(agent)
            current_voter_id += 1

            if agent.beat_llegada_cola == beat:
                if agent.es_prioridad:
                    queue_ine_prioridad.append(agent)
                else:
                    queue_ine.append(agent)
            else:
                transit_voters.append(agent)

            print(
                f"[Beat {beat:04d} | {time_label:>11}] -> ¡SPAWN! ID: {agent.voter_id:<3} | "
                f"Prio: {agent.resumen_prioridades():<20} | Caminata: {agent.t_llegada_seg}s | "
                f"INE: {agent.t_confirmacion_seg}s | Voto+Salida: {agent.t_votacion_seg + agent.t_retirada_seg}s"
            )

    # 5. ASIGNACIÓN A RECIPIENTES (Atención estocástica con sesgo prioritario 75/25)
    for r in recipientes:
        if r.is_free(beat) and (queue_ine or queue_ine_prioridad):
            elegir_prio = random.random() < 0.75 if (queue_ine and queue_ine_prioridad) else bool(queue_ine_prioridad)
            if elegir_prio and queue_ine_prioridad:
                voter_to_serve = queue_ine_prioridad.pop(0)
            elif queue_ine:
                voter_to_serve = queue_ine.pop(0)
            else:
                voter_to_serve = None

            if voter_to_serve:
                r.current_voter = voter_to_serve
                r.busy_until_beat = beat + voter_to_serve.beats_confirmacion

    # 6. ASIGNACIÓN A CASILLAS (Atención estocástica con sesgo prioritario 80/20)
    for c in casillas:
        if c.is_free(beat) and (queue_casilla or queue_casilla_prioridad):
            elegir_prio = random.random() < 0.80 if (queue_casilla and queue_casilla_prioridad) else bool(queue_casilla_prioridad)
            if elegir_prio and queue_casilla_prioridad:
                voter_to_vote = queue_casilla_prioridad.pop(0)
            elif queue_casilla:
                voter_to_vote = queue_casilla.pop(0)
            else:
                voter_to_vote = None

            if voter_to_vote:
                c.current_voter = voter_to_vote
                c.busy_until_beat = beat + voter_to_vote.beats_votacion_total

    beat += 1

imprimir_estado_colas(beat)

# ==============================================================================
# REPORTES FINALES
# ==============================================================================
print("=" * 80)
print("             REPORTE DE CLIMA POR HORA (CADENA DE MARKOV)")
print("=" * 80)
for h in range(10):
    hora_inicio = (START_TIME + timedelta(hours=h)).strftime("%I:%M %p")
    hora_fin = (START_TIME + timedelta(hours=h + 1)).strftime("%I:%M %p")
    clima = clima_por_hora[h]
    print(
        f"Hora {h+1:02d} [{hora_inicio} - {hora_fin}]: "
        f"Clima: {clima:<15} | Multiplicador: {CLIMA_EFFECTS[clima]:.2f}x | "
        f"Peso Base: {PROB_HOUR[h]*100:.1f}%"
    )

total_spawned_count = len(voters_spawned)
voters_by_hour = [0] * 10
for agent in voters_spawned:
    hour_index = min(agent.spawn_beat // BEATS_PER_HOUR, 9)
    voters_by_hour[hour_index] += 1

print("\n" + "=" * 80)
print("             DISTRIBUCIÓN REAL DE VOTANTES (POISSON)")
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
print(f"Total de beats corridos      : {beat} (finalizó a las {(START_TIME + timedelta(seconds=beat*30)).strftime('%I:%M:%S %p')})")
print(f"Total de agentes generados   : {total_spawned_count}")
valid_ines = sum(1 for v in voters_spawned if v.ine_valida)
print(
    f"Votantes con INE válida      : {valid_ines}"
    f" ({(valid_ines/total_spawned_count*100) if total_spawned_count else 0:.1f}%)"
)

conteo_votos = {partido: 0 for partido in PARTIDOS}
for agent in voters_spawned:
    if agent.ine_valida:
        conteo_votos[agent.partido] += 1

print("\n" + "=" * 80)
print("                     RESULTADOS REALES DE LA ELECCIÓN")
print("=" * 80)
votos_ordenados = sorted(conteo_votos.items(), key=lambda item: item[1], reverse=True)

for partido, votos in votos_ordenados:
    pct = (votos / valid_ines * 100) if valid_ines > 0 else 0.0
    barra = "█" * int(pct // 2)
    print(f"{partido:<22} | {votos:3d} votos ({pct:5.2f}%) | {barra}")

print("-" * 80)
print(f"Total de votos emitidos (INE válida): {valid_ines}")
print(f"Votos no emitidos (INE rechazada)  : {total_spawned_count - valid_ines}")

print("\n" + "=" * 80)
print("       ESCRUTINIO BOLETA POR BOLETA (AGENTES CONTADORES)")
print("=" * 80)

resultados_contadores = [c.contar(voters_spawned, PARTIDOS) for c in contadores]

for i, res in enumerate(resultados_contadores, start=1):
    print(f"\n--- Acta Contador #{i} ---")
    print(f"Total votantes registrados : {res['total_personas']}")
    print(f"Total boletas computadas   : {res['total_votos']}")
    print("Votos computados por partido:")
    for partido in PARTIDOS:
        votos_p = res["votos_partido"][partido]
        diff = votos_p - conteo_votos[partido]
        diff_str = f" ({diff:+d})" if diff != 0 else ""
        print(f"  - {partido:<22}: {votos_p:3d} votos{diff_str}")