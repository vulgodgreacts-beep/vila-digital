"""
Ponto de entrada da simulação.

    python main.py --ticks 12
    python main.py --ticks 30 --delay 1.5 --incident-chance 0.4
"""

import argparse

from dotenv import load_dotenv

from core.simulation import Simulation

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Vila Digital com agentes de IA")
    parser.add_argument("--ticks", type=int, default=12, help="Quantos passos de tempo simular")
    parser.add_argument("--delay", type=float, default=0.0, help="Pausa em segundos entre ticks")
    parser.add_argument(
        "--incident-chance", type=float, default=0.25,
        help="Chance (0 a 1) de uma ocorrência nova a cada tick",
    )
    parser.add_argument(
        "--ticks-por-dia", type=int, default=8,
        help="Quantos ticks formam um dia (no fim de cada dia há o balanço)",
    )
    args = parser.parse_args()

    sim = Simulation(
        ticks_por_dia=args.ticks_por_dia,
        incident_chance=args.incident_chance,
    )
    sim.run(ticks=args.ticks, delay=args.delay)


if __name__ == "__main__":
    main()
