"""Test script for TaskNetworkFlow validation."""

import sys
import os

# Adicionar o diretório edgesimpy-source ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from edge_sim_py import Simulator
from edge_sim_py.components import *

from models import Task, TaskStatus
from integration import TaskNetworkFlow


def test_task_network_flow():
    """Test TaskNetworkFlow with sample_dataset2.json."""
    # Definir resource management algorithm vazio
    def empty_resource_management(parameters):
        pass

    # Definir stopping criterion simples
    def simple_stopping_criterion(model):
        return model.schedule.steps >= 25

    simulator = Simulator(
        resource_management_algorithm=empty_resource_management,
        stopping_criterion=simple_stopping_criterion
    )
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)

    print("=== TESTE DE TASKNETWORKFLOW ===")

    # Selecionar componentes
    user = User.first()
    edge_servers = EdgeServer.all()
    if len(edge_servers) < 2:
        print("ERRO: Precisa de pelo menos 2 EdgeServers")
        return

    target_server = edge_servers[1]  # Usar segundo EdgeServer

    print(f"\n=== COMPONENTES SELECIONADOS ===")
    print(f"User ID: {user.id}")
    print(f"User BaseStation: {user.base_station.id if user.base_station else None}")
    print(f"User NetworkSwitch: {user.base_station.network_switch.id if user.base_station and user.base_station.network_switch else None}")
    print(f"Target EdgeServer ID: {target_server.id}")
    print(f"Target BaseStation: {target_server.base_station.id if target_server.base_station else None}")
    print(f"Target NetworkSwitch: {target_server.base_station.network_switch.id if target_server.base_station and target_server.base_station.network_switch else None}")

    # Criar Task com tamanho pequeno para teste rápido
    # 0.1 MB = 102.4 KB, com bandwidth 12.5 KB/tick -> ~8-9 steps
    task = Task(
        task_id=1,
        user=user,
        data_size_mb=0.1,  # Tamanho pequeno para teste
        cpu_cycles=1000.0,
        deadline_ms=1000.0,
        creation_time_s=0.0,
    )
    # Definir target_server manualmente (não está no construtor)
    task.target_server = target_server

    print(f"\n=== TASK CRIADA ===")
    print(f"Task ID: {task.task_id}")
    print(f"Data size: {task.data_size_mb} MB")
    print(f"Status inicial: {task.status}")

    # Criar TaskNetworkFlow
    print(f"\n=== CRIANDO TASKNETWORKFLOW ===")
    try:
        task_network_flow = TaskNetworkFlow(task=task, simulator=simulator)
        flow = task_network_flow.create_upload_flow()

        print(f"Flow criado com sucesso!")
        print(f"Flow ID: {flow.id}")
        print(f"Flow status: {flow.status}")
        print(f"Flow data_to_transfer: {flow.data_to_transfer}")
        print(f"Flow start: {flow.start}")
        print(f"Flow path: {[switch.id for switch in flow.path]}")
        print(f"Flow source: {flow.source.id if flow.source else None}")
        print(f"Flow target: {flow.target.id if flow.target else None}")

        print(f"\n=== STATUS APÓS CRIAÇÃO DO FLOW ===")
        print(f"Task status: {task.status}")
        print(f"Task transmission_start_time_s: {task.transmission_start_time_s}")

    except Exception as e:
        print(f"ERRO ao criar TaskNetworkFlow: {e}")
        return

    # Executar simulação até o flow terminar
    print(f"\n=== EXECUTANDO SIMULAÇÃO ===")
    max_steps = 30
    for i in range(max_steps):
        simulator.step()

        flow_info = task_network_flow.get_flow_info()
        print(f"\nStep {simulator.schedule.steps}:")
        print(f"  Flow status: {flow_info['status']}")
        print(f"  Flow data_to_transfer: {flow_info['data_to_transfer']}")
        print(f"  Flow bandwidth: {flow_info['bandwidth']}")
        print(f"  Task status: {task.status}")

        # Atualizar métricas quando flow terminar
        if flow_info['status'] == 'finished':
            task_network_flow.update_transmission_metrics()
            print(f"\n=== FLOW TERMINOU ===")
            print(f"Flow end: {flow_info['end']}")
            print(f"Task transmission_end_time_s: {task.transmission_end_time_s}")
            print(f"Task transmission_time_s: {task.transmission_time_s}")
            break
    else:
        print(f"\nAVISO: Flow não terminou em {max_steps} steps")

    # Resultado final
    print(f"\n=== RESULTADO FINAL ===")
    print(f"Task ID: {task.task_id}")
    print(f"User ID: {user.id}")
    print(f"Target EdgeServer ID: {target_server.id}")
    print(f"Source switch: {flow.source.id if flow.source else None}")
    print(f"Target switch: {target_server.base_station.network_switch.id if target_server.base_station and target_server.base_station.network_switch else None}")
    print(f"Path: {[switch.id for switch in flow.path]}")
    print(f"Data to transfer: {flow.data_to_transfer} KB (operational hypothesis)")
    print(f"Bandwidth efetiva: {list(flow.bandwidth.values())} KB/tick")
    print(f"Flow start: {flow.start}")
    print(f"Flow end: {flow.end}")
    if flow.end is not None:
        print(f"Transmission time (steps): {flow.end - flow.start}")
    print(f"Transmission time (seconds): {task.transmission_time_s}")
    print(f"Task status antes: CREATED")
    print(f"Task status depois: {task.status}")
    print(f"Simulator tick_duration: {simulator.tick_duration} segundos")

    # Validação
    print(f"\n=== VALIDAÇÃO ===")
    if flow.status == "finished":
        print("[OK] Flow terminou com sucesso")
    else:
        print(f"[FAIL] Flow não terminou (status: {flow.status})")

    if task.status == TaskStatus.TRANSMITTING:
        print("[OK] Task status em TRANSMITTING")
    else:
        print(f"[FAIL] Task status inesperado: {task.status}")

    if task.transmission_time_s is not None and task.transmission_time_s > 0:
        print(f"[OK] Transmission time calculado: {task.transmission_time_s}s")
    else:
        print("[FAIL] Transmission time não calculado")

    if flow.end is not None and flow.end - flow.start > 0:
        print(f"[OK] Duração coerente: {flow.end - flow.start} steps")
    else:
        print("[FAIL] Duração incoerente ou não terminou")


if __name__ == "__main__":
    # Mudar para o diretório edgesimpy-simulation
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    test_task_network_flow()
