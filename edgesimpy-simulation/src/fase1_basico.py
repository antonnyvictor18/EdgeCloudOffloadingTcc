from edge_sim_py import Simulator


def main():
    print("======================================")
    print("Fase 1 - Primeiro teste do simulador")
    print("======================================")

    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=lambda model: model.schedule.steps >= 10,
        resource_management_algorithm=lambda parameters: None,
    )

    print("Simulator criado com sucesso.")
    print("Iniciando simulação...")


if __name__ == "__main__":
    main()