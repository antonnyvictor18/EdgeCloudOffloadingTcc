from edge_sim_py import Simulator, Service


def main():
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=lambda model: all(
            service.server is not None
            for service in Service.all()
        ),
        resource_management_algorithm=lambda parameters: None,
    )

    simulator.initialize(
        input_file="scenarios/sample_dataset1.json"
    )

    print("Cenário carregado com sucesso!")

    simulator.run_model()

    print("Simulação finalizada.")


if __name__ == "__main__":
    main()