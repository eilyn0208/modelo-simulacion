# Simulacion de una casilla electoral
# Seccion 0956, Cajeme, Sonora. Eleccion federal 2 de junio de 2024.
#
# Agentes:
#   Votantes: llegan, se forman (fila normal o prioritaria), confirman ID,
#     votan y se retiran.
#   Recipientes: reciben a los votantes y verifican su identificacion.
#   Contadores: conteo final de los votos.
#
# Etapas y distribuciones (ver documento):
#   Llegada       0.5 - 1 min   triangular    volumen por hora: Poisson
#   Confirmacion  30 - 45 seg   triangular    5% no puede votar: binomial
#   Votacion      1 - 5 min     triangular    solo pasa si hay casilla vacia
#   Retirada      1 - 2 min     triangular
#
# Eventos externos: clima por hora (binomial) y hora del dia.
# Reloj: minutos desde las 8:00 am. Casilla cierra a las 18:00 (min 600).

import heapq
import math
import random
from collections import Counter

random.seed(6967)   # misma corrida cada vez que se ejecuta


# PARAMETROS
POSSIBLE_VOTERS = 426         # ver documento: tamano de muestra
CLOSING = 600                 # 18:00
NUM_RECIPIENTS = 2            # mesa de confirmacion
NUM_BOOTHS = 4                # casillas para votar

# asistencia por hora, de 8 am a 5 pm
HOUR_PCT = [15, 17.5, 12.5, 7.5, 2.5, 2.5, 2.5, 7.5, 15, 17.5]

# clima: (nombre, probabilidad, multiplicador de asistencia)
WEATHER = [("Soleado", 80, 0.90), ("Nublado", 15, 1.10),
           ("Lluvia leve", 4.5, 0.85), ("Lluvia moderada", 0.5, 0.50)]

P_REJECTED = 0.05             # casilla equivocada, INE invalida, etc.

PARTIES = ["Morena", "PAN", "MC", "PRI", "Nulo"]
PARTY_WEIGHTS = [40, 22, 22, 12, 4]


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def clock(t):
    h, m = divmod(int(t), 60)
    return f"{8 + h:02d}:{m:02d}"


# AGENTE VOTANTE
class VoterAgent:

    def __init__(self, voter_id, arrival_time):
        self.voter_id = voter_id
        self.arrival_time = arrival_time
        self.check_time = 0
        self.voting_time = 0
        self.exit_time = 0

        # condicion: define en que fila se forma
        self.is_senior = random.random() < 0.22
        self.age = random.randint(65, 90) if self.is_senior else random.randint(18, 64)
        self.is_pregnant = random.random() < 0.03
        self.has_disability = random.random() < 0.015
        self.priority = self.is_senior or self.is_pregnant or self.has_disability

        self.party = random.choices(PARTIES, weights=PARTY_WEIGHTS)[0]

    def voting_duration(self):
        d = random.triangular(1, 5)
        # entre mas edad, mas tarda en votar
        d *= 1 + sigmoid((self.age - 65) / 8)
        if self.has_disability or self.is_pregnant:
            d *= 1.5
        return d


# CREAR VOTANTES
# Cada hora: se sortea el clima y se generan las llegadas (Poisson).
event_queue = []
voters = []
weather_by_hour = []

for hour in range(10):
    weather, _, mult = random.choices(WEATHER, weights=[w[1] for w in WEATHER])[0]
    weather_by_hour.append(weather)

    expected = POSSIBLE_VOTERS * HOUR_PCT[hour] / 100 * mult
    t = hour * 60 + random.expovariate(expected / 60)
    while t < (hour + 1) * 60:
        voter = VoterAgent(len(voters) + 1, t)
        voters.append(voter)
        heapq.heappush(event_queue, (t, voter.voter_id, "ARRIVAL", voter))
        t += random.expovariate(expected / 60)

print("Clima por hora:")
for hour, w in enumerate(weather_by_hour):
    print(f"  {clock(hour * 60)}  {w}")
print(f"Votantes que llegan: {len(voters)}\n")


# SIMULACION
recipient_free_at = [0] * NUM_RECIPIENTS
booth_free_at = [0] * NUM_BOOTHS
urn = []
stats = Counter()
simulation_time = 0

while event_queue:
    event_time, _, event_type, voter = heapq.heappop(event_queue)
    simulation_time = event_time

    # LLEGADA: camina a la mesa y se forma
    if event_type == "ARRIVAL":
        if simulation_time >= CLOSING:
            stats["late"] += 1
            continue

        tag = " (fila prioritaria)" if voter.priority else ""
        print(f"{clock(simulation_time)}: Votante {voter.voter_id} llega{tag}")

        arrived_at_desk = simulation_time + random.triangular(0.5, 1)

        # prioritarios no hacen fila
        r = recipient_free_at.index(min(recipient_free_at))
        start = arrived_at_desk if voter.priority else max(arrived_at_desk, recipient_free_at[r])
        voter.check_time = start + random.triangular(0.5, 0.75)     # 30-45 seg
        recipient_free_at[r] = voter.check_time
        heapq.heappush(event_queue, (voter.check_time, voter.voter_id, "CHECK_ID", voter))

    # CONFIRMACION: pasa a votar o se retira
    elif event_type == "CHECK_ID":
        if random.random() < P_REJECTED:
            print(f"{clock(simulation_time)}: Votante {voter.voter_id} NO PUEDE VOTAR, se retira")
            stats["rejected"] += 1
            voter.exit_time = simulation_time + random.triangular(1, 2)
            heapq.heappush(event_queue, (voter.exit_time, voter.voter_id, "EXIT", voter))
            continue

        # solo pasa si hay casilla vacia
        b = booth_free_at.index(min(booth_free_at))
        start = max(simulation_time, booth_free_at[b])
        voter.voting_time = start + voter.voting_duration()
        booth_free_at[b] = voter.voting_time
        heapq.heappush(event_queue, (voter.voting_time, voter.voter_id, "VOTING", voter))

    # VOTACION: deposita y se retira
    elif event_type == "VOTING":
        urn.append(voter.party)
        stats["voted"] += 1
        print(f"{clock(simulation_time)}: Votante {voter.voter_id} vota")

        voter.exit_time = simulation_time + random.triangular(1, 2)
        heapq.heappush(event_queue, (voter.exit_time, voter.voter_id, "EXIT", voter))

    # RETIRADA
    elif event_type == "EXIT":
        print(f"{clock(simulation_time)}: Votante {voter.voter_id} se retira")


# CIERRE Y CONTEO
print("\n" + "=" * 40)
print(f"Cierre {clock(max(simulation_time, CLOSING))}")
print(f"Votos en urna: {len(urn)}")
for party, n in Counter(urn).most_common():
    print(f"  {party:8s} {n:4d}  {n / len(urn):6.1%}")
print(f"\nVotaron: {stats['voted']}   No pudieron votar: {stats['rejected']}   "
      f"Llegaron tarde: {stats['late']}")
