import heapq
import random

class VoteAgent:
    def __init__(self, voter_id):
        self.voter_id = voter_id
        self.arrival_time = 0
        self.check_time = 0
        self.voting_time = 0
        self.exit_time = 0


queue = []

num_de_votantes = 426
votantes = []

#Peso por hora
hour_weights = {
    8: 0.15,
    9: 0.175,
    10: 0.125,
    11: 0.075,
    12: 0.025,
    13: 0.025,
    14: 0.025,
    15: 0.075,
    16: 0.15,
    17: 0.175
}

# Probabilidad de clima
clima_types = [
    "SUNNY",
    "CLOUDY",
    "LIGHT_RAIN",
    "MODERATE_RAIN"
]

clima_probabilities = [
    0.80,
    0.15,
    0.045,
    0.005
]

# Asistencia con climas
clima_effect = {
    "SUNNY": 0.90,
    "CLOUDY": 1.10,
    "LIGHT_RAIN": 0.85,
    "MODERATE_RAIN": 0.50
}


hora_clima = {}

for hora in range(8, 18):

    clima = random.choices(
        clima_types,
        weights=clima_probabilities,
        k=1
    )[0]

    hora_clima[hora] = clima


for i in range(1, num_de_votantes + 1):

    #Seleccionar hora
    hora = random.choices(
        list(hour_weights.keys()),
        weights=list(hour_weights.values()),
        k=1
    )[0]

    #Clima en esa hora
    clima = hora_clima[hora]

    #El efecto del clima en la asistencia
    attendance_probability = clima_effect[clima]

    #Ver si los votantes asisten
    attends = random.random() < min(attendance_probability, 1.0)

    if attends:

        #Crear votante
        voter = VoteAgent(i)

        #LLegada al azar, entre 0 y 60 minutos
        minute = random.uniform(0, 60)

        #Convertir hora y minuto a tiempo de llegada en minutos desde las 8:00 a.m.
        tiempo_llegada = (hora - 8) * 60 + minute

        voter.tiempo_llegada = tiempo_llegada

        votantes.append(voter)

        # Crear la llegada
        llegada = (
            tiempo_llegada,
            "Llegada",
            voter
        )

        heapq.heappush(queue, llegada)