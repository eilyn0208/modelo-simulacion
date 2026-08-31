# Simulation of a polling station
# ----------------------------------------
# We consider that a voter passes through three main stages:
#
# 1. Arrival:
#    Includes the arrival time and the time spent waiting in line.
#
# 2. Voting:
#    Includes ID validation time, ballot receiving time, voting time,
#    and indelible ink application time.
#
# 3. Exit:
#    Includes the time required for the voter to leave the polling station.
#
# *Note that each stage requires calculating its corresponding time.


# heapq is used to implement a priority queue that manages
# all simulation events in chronological order.
import heapq
import random

from datetime import datetime, timedelta
import time

# ---------------------------------------
# VOTER AGENT
# ---------------------------------------
# In the object definition, you can see the time attributes associated with each stage.

total_turns = 600 # unidades de tiempo (10 horas / 60 minutos)
turn = 0
current_time = datetime.strptime("8:00 AM", "%I:%M %p")
simulation_ended = False

class VoterAgent:

   def __init__(self, voter_id):
       self.voter_id = voter_id
       self.arrival_time = 0
       self.check_time = 0
       self.voting_time = 0
       self.exit_time = 0

while simulation_ended == False:

   formatted_time = current_time.strftime("%I:%M %p").lstrip("0")
   print(f"Turn {turn}: {formatted_time}")

   current_time += timedelta(minutes=1)
   turn += 1

   if turn >= total_turns:
       simulation_ended = True
       print("Simulation ended.")


# ---------------------------------------
# EVENT QUEUE
# ---------------------------------------

event_queue = []


# ---------------------------------------
# CREATE VOTERS
# Before the simulation starts
# ---------------------------------------

# I consider 5 voters, you have to use a more sophisticated method (e.g., a sample)
#vBefore simulation I create the agents.
number_of_voters = 5
voters = []

arrival_time = 0

for i in range(1, number_of_voters + 1):

    # Create voter
    voter = VoterAgent(i)

    # Time between two consecutive voters
    # Average = 4 minutes
    interarrival_time = random.expovariate(1 / 4)

    # Accumulated arrival time
    arrival_time += interarrival_time

    voter.arrival_time = arrival_time

    voters.append(voter)

    # Create ARRIVAL event
    # An event is created as a tuple
    event = (arrival_time, "ARRIVAL", voter)

    # Insert event into Event Queue
    # When an event is inserted, heapq automatically organizes the Event Queue
    # according to the event time.

    # The event with the smallest event_time has the highest priority
    # and is processed first.
    heapq.heappush(event_queue, event)


# Initial Input Data for the Simulation
# - VoterAgents
# - ARRIVAL events for each voter

# ---------------------------------------
# SIMULATION
# ---------------------------------------

simulation_time = 0

while event_queue:

    # POP next event
    # Remember that the event with the smallest event_time has the highest priority
    # and is processed first.
    # Here we extract the element from the QUEUE_events
    event_time, event_type, voter = heapq.heappop(event_queue)

    # Advance simulation clock
    # We are responsible for managing the simulation clock.
    simulation_time = event_time



    # -----------------------------------
    # ARRIVAL
    # -----------------------------------


    if event_type == "ARRIVAL":

        print(
            f"Time {simulation_time:.2f}: "
            f"Voter {voter.voter_id} ARRIVES"
        )

        # El evento que sigue a ARRIVAL es CHECK_ID, asi que aqui va el
        # retraso de la etapa ARRIVAL -> CHECK_ID (fila + revision del ID).
        # Revisar el ID es rapido: entre 1 y 3 minutos.
        # TU BUSCA LA MEJOR FUNCION ESTADISTICA
        check_delay = random.randint(1, 3)

        voter.check_time = simulation_time + check_delay

        # Create CHECK_ID event
        # By creating this event, we move the voter
        # to the next stage CHECK_ID.
        new_event = (
            voter.check_time,
            "CHECK_ID",
            voter
        )

        # Insert CHECK_ID event
        # heapq inserts the event in the appropriate chronological order based on event_time.
        heapq.heappush(event_queue, new_event)



    # -----------------------------------
    # CHECK ID
    # -----------------------------------

    elif event_type == "CHECK_ID":

        print(
            f"Time {simulation_time:.2f}: "
            f"Voter {voter.voter_id} ID IS CHECKED"
        )

        valid = random.random() >= 0.5

        if valid:
            # Recuerda que VOTING involucra varias actividades (recibir la
            # boleta, votar, tinta indeleble), por eso el retraso es grande.
            # TU BUSCA LA MEJOR FUNCION ESTADISTICA
            voting_delay = random.randint(10, 30)

            voter.voting_time = simulation_time + voting_delay

            new_event = (
                voter.voting_time,
                "VOTING",
                voter
            )

        else:
            # ID invalido: el votante NO vota, pero igual se va.
            # Si no le creamos evento, desaparece de la simulacion.
            print(
                f"Time {simulation_time:.2f}: "
                f"Voter {voter.voter_id} IS REJECTED (invalid ID)"
            )

            exit_delay = random.randint(1, 3)

            voter.exit_time = simulation_time + exit_delay

            new_event = (
                voter.exit_time,
                "EXIT",
                voter
            )

        heapq.heappush(event_queue, new_event)


    # -----------------------------------
    # VOTING
    # -----------------------------------

    elif event_type == "VOTING":

        print(
            f"Time {simulation_time:.2f}: "
            f"Voter {voter.voter_id} VOTES"
        )

        # Retraso de la etapa VOTING -> EXIT
        exit_delay = random.randint(5, 12)

        voter.exit_time = simulation_time + exit_delay

        new_event = (
            voter.exit_time,
            "EXIT",
            voter
        )

        heapq.heappush(event_queue, new_event)


    # -----------------------------------
    # EXIT
    # -----------------------------------

    elif event_type == "EXIT":

        print(
            f"Time {simulation_time:.2f}: "
            f"Voter {voter.voter_id} EXITS"
        )
