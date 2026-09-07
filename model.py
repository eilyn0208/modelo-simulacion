"""Versión Mesa de 'Polling station simulation.py'. Misma lógica, mismos parámetros.

1 step() = 1 beat = 30 seg. Correr directo: python3 model.py
Servir a Unity: python3 server.py
"""
from datetime import datetime, timedelta
import math

import mesa

# PARÁMETROS GENERALES
BEATS_PER_HOUR = 120
TOTAL_BEATS = 1200
BASE_VOTERS_TARGET = 450
START_TIME = datetime.strptime("8:00 AM", "%I:%M %p")

PROB_HOUR = [0.15, 0.175, 0.125, 0.075, 0.025, 0.025, 0.025, 0.075, 0.15, 0.175]

PROB_CLIMA = [
    ["SOLEADO", 0.80, 0.90],
    ["NUBLADO", 0.15, 1.10],
    ["LLUVIA_LEVE", 0.045, 0.85],
    ["LLUVIA_MODERADA", 0.005, 0.50],
]
clima_types = [c[0] for c in PROB_CLIMA]
clima_weights = [c[1] for c in PROB_CLIMA]
clima_effects = {c[0]: c[2] for c in PROB_CLIMA}

PARTIDOS = ["Morena", "PAN", "PRI", "Movimiento Ciudadano", "Nulos", "Otros"]
PARTIDOS_PROBS = [0.4708, 0.1443, 0.1241, 0.0775, 0.0110, 0.1723]


# AGENTES
class AgenteVotante(mesa.Agent):
    def __init__(self, model, voter_id, spawn_beat, time_str):
        super().__init__(model)
        rnd = model.random
        self.voter_id = voter_id
        self.spawn_beat = spawn_beat
        self.spawn_time_str = time_str
        self.estado = "queue_ine"  # queue_ine | queue_ine_prio | recipiente:N | queue_casilla | queue_casilla_prio | casilla:N | salida | rechazado

        self.partido = rnd.choices(PARTIDOS, weights=PARTIDOS_PROBS, k=1)[0]
        self.ine_valida = rnd.random() < 0.95
        self.tercera_edad = rnd.random() < 0.185
        self.discapacidad = rnd.random() < rnd.uniform(0.01, 0.02)
        self.embarazo = rnd.random() < rnd.uniform(0.02, 0.04) if not self.tercera_edad else False
        self.es_prioridad = self.tercera_edad or self.discapacidad or self.embarazo

        self.t_llegada_seg = round(rnd.triangular(30, 60, 45), 2)
        self.t_confirmacion_seg = round(rnd.triangular(30, 45, 37.5), 2)
        self.t_votacion_seg = round(rnd.triangular(60, 300, 180), 2)
        self.t_retirada_seg = round(rnd.triangular(60, 120, 90), 2)

    @property
    def beats_confirmacion(self):
        return max(1, math.ceil(self.t_confirmacion_seg / 30))

    @property
    def beats_votacion(self):
        return max(1, math.ceil(self.t_votacion_seg / 30))

    def resumen_prioridades(self):
        p = []
        if self.tercera_edad: p.append("Tercera Edad")
        if self.discapacidad: p.append("Discapacidad")
        if self.embarazo: p.append("Embarazo")
        return ", ".join(p) if p else "Ninguna"

    def to_dict(self):
        return {
            "id": self.voter_id,
            "estado": self.estado,
            "partido": self.partido,
            "ine_valida": self.ine_valida,
            "prioridad": self.es_prioridad,
            "spawn_beat": self.spawn_beat,
        }


class AgenteEstacion(mesa.Agent):
    """Recipiente (verifica INE) o Casilla (vota). Misma mecánica: ocupado hasta un beat."""

    def __init__(self, model, station_id, tipo):
        super().__init__(model)
        self.station_id = station_id
        self.tipo = tipo  # "recipiente" | "casilla"
        self.current_voter = None
        self.busy_until_beat = -1

    def is_free(self, beat):
        return beat >= self.busy_until_beat

    def to_dict(self):
        return {"id": self.station_id, "votante": self.current_voter.voter_id if self.current_voter else None}


class AgenteContador(mesa.Agent):
    def __init__(self, model, counter_id, prob_error=0.001):
        super().__init__(model)
        self.counter_id = counter_id
        self.prob_error = prob_error

    def _err(self, v):
        if self.model.random.random() < self.prob_error:
            return max(0, v + self.model.random.choice([-1, 1]))
        return v

    def contar(self, votantes):
        validos = [v for v in votantes if v.ine_valida]
        return {
            "total_personas": self._err(len(votantes)),
            "total_votos": self._err(len(validos)),
            "votos_partido": {p: self._err(sum(1 for v in validos if v.partido == p)) for p in PARTIDOS},
        }


# MODELO
class CasillaModel(mesa.Model):
    def __init__(self, n_recipientes=3, n_casillas=5, n_contadores=3, voters_target=BASE_VOTERS_TARGET, seed=None):
        super().__init__(rng=seed)
        self.voters_target = voters_target
        self.beat = 0
        self.next_voter_id = 1
        self.next_recipiente_prio = True
        self.next_casilla_prio = True

        self.queue_ine, self.queue_ine_prio = [], []
        self.queue_casilla, self.queue_casilla_prio = [], []

        self.recipientes = [AgenteEstacion(self, i + 1, "recipiente") for i in range(n_recipientes)]
        self.casillas = [AgenteEstacion(self, i + 1, "casilla") for i in range(n_casillas)]
        self.contadores = [AgenteContador(self, i + 1) for i in range(n_contadores)]
        self.votantes = []
        self.clima_por_hora = {h: self.random.choices(clima_types, weights=clima_weights, k=1)[0] for h in range(10)}
        self.running = True

    # helpers
    def time_label(self, fmt="%I:%M:%S %p"):
        return (START_TIME + timedelta(seconds=self.beat * 30)).strftime(fmt).lstrip("0")

    def _pick(self, prio_q, normal_q, flag_name):
        flag = getattr(self, flag_name)
        if (flag and prio_q) or (not normal_q and prio_q):
            setattr(self, flag_name, False)
            return prio_q.pop(0)
        if normal_q:
            setattr(self, flag_name, True)
            return normal_q.pop(0)
        return None

    def _pendiente(self):
        return (self.queue_ine or self.queue_ine_prio or self.queue_casilla or self.queue_casilla_prio
                or any(not r.is_free(self.beat) for r in self.recipientes)
                or any(not c.is_free(self.beat) for c in self.casillas))

    # un beat
    def step(self):
        beat = self.beat
        hour_idx = min(beat // BEATS_PER_HOUR, 9)
        spawned = None

        # 1. Terminan votaciones
        for c in self.casillas:
            if c.current_voter and c.busy_until_beat == beat:
                c.current_voter.estado = "salida"
                c.current_voter = None

        # 2. Terminan verificaciones -> a casilla
        for r in self.recipientes:
            if r.current_voter and r.busy_until_beat == beat:
                v = r.current_voter
                if v.ine_valida:
                    if v.es_prioridad:
                        self.queue_casilla_prio.append(v); v.estado = "queue_casilla_prio"
                    else:
                        self.queue_casilla.append(v); v.estado = "queue_casilla"
                else:
                    v.estado = "rechazado"
                r.current_voter = None

        # 3. Spawn
        if beat < TOTAL_BEATS:
            efecto = clima_effects[self.clima_por_hora[hour_idx]]
            p = self.voters_target * PROB_HOUR[hour_idx] * efecto / BEATS_PER_HOUR
            if self.random.random() < p:
                spawned = AgenteVotante(self, self.next_voter_id, beat, self.time_label())
                self.next_voter_id += 1
                self.votantes.append(spawned)
                if spawned.es_prioridad:
                    self.queue_ine_prio.append(spawned); spawned.estado = "queue_ine_prio"
                else:
                    self.queue_ine.append(spawned)

        # 4. Recipientes
        for r in self.recipientes:
            if r.is_free(beat):
                v = self._pick(self.queue_ine_prio, self.queue_ine, "next_recipiente_prio")
                if v:
                    r.current_voter = v
                    r.busy_until_beat = beat + v.beats_confirmacion
                    v.estado = f"recipiente:{r.station_id}"

        # 5. Casillas
        for c in self.casillas:
            if c.is_free(beat):
                v = self._pick(self.queue_casilla_prio, self.queue_casilla, "next_casilla_prio")
                if v:
                    c.current_voter = v
                    c.busy_until_beat = beat + v.beats_votacion
                    v.estado = f"casilla:{c.station_id}"

        self.beat += 1
        self.running = self.beat < TOTAL_BEATS or self._pendiente()
        return spawned

    # JSON para Unity
    def estado(self):
        return {
            "beat": self.beat,
            "hora": self.time_label(),
            "running": self.running,
            "clima": self.clima_por_hora[min(self.beat // BEATS_PER_HOUR, 9)],
            "queue_ine": [v.voter_id for v in self.queue_ine],
            "queue_ine_prio": [v.voter_id for v in self.queue_ine_prio],
            "queue_casilla": [v.voter_id for v in self.queue_casilla],
            "queue_casilla_prio": [v.voter_id for v in self.queue_casilla_prio],
            "recipientes": [r.to_dict() for r in self.recipientes],
            "casillas": [c.to_dict() for c in self.casillas],
            "votantes": [v.to_dict() for v in self.votantes],
        }

    def resultados(self):
        validos = [v for v in self.votantes if v.ine_valida]
        votos = {p: sum(1 for v in validos if v.partido == p) for p in PARTIDOS}
        return {
            "beats": self.beat,
            "hora_fin": self.time_label(),
            "total_agentes": len(self.votantes),
            "ine_valida": len(validos),
            "votos": votos,
            "clima_por_hora": self.clima_por_hora,
            "contadores": [c.contar(self.votantes) for c in self.contadores],
        }


if __name__ == "__main__":
    import json
    m = CasillaModel()
    while m.running:
        m.step()
    print(json.dumps(m.resultados(), indent=2, ensure_ascii=False))
