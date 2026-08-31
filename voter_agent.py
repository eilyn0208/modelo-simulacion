import random


class VoterAgent:

    def __init__(self, voter_id, party=None):
        self.voter_id = voter_id

        # Preferencia electoral
        self.party = party

        # 95% de probabilidad de tener una INE válida
        self.ine_valid = random.random() < 0.95

        # 10% de probabilidad de necesitar atención prioritaria
        self.priority = random.random() < 0.10

        # Tiempos de las etapas
        self.arrival_time = 0
        self.check_time = 0
        self.voting_time = 0
        self.exit_time = 0

        # Estado inicial
        self.state = "SPAWNED"