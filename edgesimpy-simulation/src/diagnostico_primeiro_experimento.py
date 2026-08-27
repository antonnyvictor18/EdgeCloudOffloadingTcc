"""Diagnóstico observacional de 10 passos do EdgeSimPy 1.1.0."""

from copy import deepcopy
from pathlib import Path

from edge_sim_py import Application, EdgeServer, NetworkFlow, Service, Simulator, User


NUMBER_OF_STEPS = 10


def resource_management_noop(parameters: dict) -> None:
    """Mantém o experimento observacional: não faz placement nem migração."""


def collect_snapshot(model: Simulator) -> dict:
    """Coleta somente atributos expostos pelos componentes do EdgeSimPy."""
    # Identifica os usuários que estão fazendo alguma requisição neste passo.
    requesting_users = []
    for user in User.all():
        if any(user.making_requests.get(str(app.id), {}).get(str(model.schedule.steps), False) for app in user.applications):
            requesting_users.append(user.id)

    # Registra o servidor atualmente associado a cada Service; None significa sem servidor.
    service_servers = {service.id: service.server.id if service.server else None for service in Service.all()}

    # Copia os delays mantidos por cada User para preservar o snapshot do passo.
    user_delays = {user.id: deepcopy(user.delays) for user in User.all()}

    # Conta NetworkFlows cujo status ainda é active.
    active_flows = sum(flow.status == "active" for flow in NetworkFlow.all())

    return {
        "step": model.schedule.steps,
        "time": model.schedule.time,
        "users": User.count(),
        "applications": Application.count(),
        "services": Service.count(),
        "edge_servers": EdgeServer.count(),
        "network_flows": NetworkFlow.count(),
        "requesting_users": requesting_users,
        "service_servers": service_servers,
        "user_delays": user_delays,
        "active_flows": active_flows,
    }


def format_snapshot(snapshot: dict) -> str:
    """Formata um snapshot para leitura no terminal."""
    return (
        f"passo={snapshot['step']} tempo={snapshot['time']}s | "
        f"Users={snapshot['users']} Applications={snapshot['applications']} "
        f"Services={snapshot['services']} EdgeServers={snapshot['edge_servers']} "
        f"NetworkFlows={snapshot['network_flows']} ativos={snapshot['active_flows']} | "
        f"requesting_users={snapshot['requesting_users']} | "
        f"service_servers={snapshot['service_servers']} | "
        f"delays={snapshot['user_delays']}"
    )


def main() -> None:
    dataset_path = Path(__file__).resolve().parents[1] / "tutorials" / "datasets" / "sample_dataset2.json"
    snapshots = []

    def stopping_criterion(model: Simulator) -> bool:
        # run_model chama este critério depois de monitorar cada passo; assim o décimo snapshot é pós-passo.
        snapshots.append(collect_snapshot(model))
        return model.schedule.steps >= NUMBER_OF_STEPS

    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=stopping_criterion,
        resource_management_algorithm=resource_management_noop,
        dump_interval=float("inf"),
    )
    simulator.initialize(input_file=str(dataset_path))

    print(f"Dataset: {dataset_path}")
    print("Diagnóstico observacional iniciado")
    simulator.run_model()

    for snapshot in snapshots:
        print(format_snapshot(snapshot))

    print("\nResumo")
    print(f"passos executados: {len(snapshots)}")
    print(f"tempo final: {simulator.schedule.time}s")
    print(f"flows totais criados: {NetworkFlow.count()}")
    print(f"flows ativos no final: {snapshots[-1]['active_flows'] if snapshots else 0}")
    print(f"servidores dos Services no final: {snapshots[-1]['service_servers'] if snapshots else {}}")


if __name__ == "__main__":
    main()