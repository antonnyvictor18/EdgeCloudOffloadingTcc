"""Test script for TaskScheduler integration with NetworkFlow upload."""

import sys
import os

# Adicionar o diretório edgesimpy-source ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from edge_sim_py import Simulator
from edge_sim_py.components import *

from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from integration import TaskSchedulerIntegration


def test_task_scheduler_with_network():
    """Test TaskScheduler with NetworkFlow upload integration."""
    # Definir resource management algorithm que usa TaskSchedulerIntegration
    def resource_management_algorithm(parameters):
        # A TaskSchedulerIntegration.step() será chamada aqui
        scheduler_integration.step()
        scheduler_integration.record_tick_metrics(task_a, task_b, target_server)

    # Definir stopping criterion simples
    def simple_stopping_criterion(model):
        return (
            task_a.status == TaskStatus.COMPLETED
            and task_b.status == TaskStatus.COMPLETED
        )

    # Criar simulador
    simulator = Simulator(
        resource_management_algorithm=resource_management_algorithm,
        stopping_criterion=simple_stopping_criterion
    )
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)

    print("=== TESTE DE INTEGRAÇÃO TASKSCHEDULER + NETWORKFLOW ===")

    # Selecionar EdgeServer
    edge_servers = EdgeServer.all()
    if len(edge_servers) < 1:
        print("ERRO: Precisa de pelo menos 1 EdgeServer")
        return

    target_server = edge_servers[0]
    user = User.first()

    print(f"\n=== COMPONENTES SELECIONADOS ===")
    print(f"User ID: {user.id}")
    print(f"Target EdgeServer ID: {target_server.id}")
    print(f"Target EdgeServer CPU: {target_server.cpu}")
    print(f"Target EdgeServer Memory: {target_server.memory} MB")

    # Criar TaskScheduler
    processing_rate = 500  # cycles/segundo
    task_scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate)

    # Criar TaskSchedulerIntegration
    scheduler_integration = TaskSchedulerIntegration(
        task_scheduler=task_scheduler,
        simulator=simulator
    )

    # Criar duas Tasks com dados para upload
    task_a = Task(
        task_id="task_a",
        user=user,
        data_size_mb=0.1,  # 102.4 KB, ~8 steps de upload
        cpu_cycles=1000,  # 2 segundos de execução
        deadline_ms=15000,  # 15 segundos
        creation_time_s=0.0,
        required_memory_mb=100,
    )
    task_a.target_server = target_server

    task_b = Task(
        task_id="task_b",
        user=user,
        data_size_mb=0.1,  # 102.4 KB, ~8 steps de upload
        cpu_cycles=500,   # 1 segundo de execução
        deadline_ms=15000,  # 15 segundos
        creation_time_s=0.0,
        required_memory_mb=100,
    )
    task_b.target_server = target_server

    print(f"\n=== TASKS CRIADAS ===")
    print(f"Task A: data_size_mb={task_a.data_size_mb}, cpu_cycles={task_a.cpu_cycles}, deadline={task_a.deadline_ms}ms")
    print(f"Task B: data_size_mb={task_b.data_size_mb}, cpu_cycles={task_b.cpu_cycles}, deadline={task_b.deadline_ms}ms")

    # Submeter Tasks para integração
    scheduler_integration.submit_task(task_a, target_server)
    scheduler_integration.submit_task(task_b, target_server)

    print(f"\n=== EXECUTANDO SIMULAÇÃO ===")
    print(f"Tick duration: {simulator.tick_duration} segundos")
    print(f"\n{'Step':<6} {'Time(s)':<10} {'Task A Status':<20} {'Task B Status':<20} {'Queue':<6} {'Current':<10}")
    print("-" * 90)

    # Executar simulação
    simulator.run_model()

    # Imprimir métricas coletadas
    print(f"\n=== MÉTRICAS POR TICK ===")
    for metrics in scheduler_integration.tick_metrics:
        print(f"Step {metrics.edge_sim_py_step}: Time={metrics.edge_sim_py_time:.1f}s, "
              f"Task A={metrics.task_a_status}, Task B={metrics.task_b_status}, "
              f"Queue={metrics.queue_size}, Current={metrics.current_task_id}")

    # Resultados finais das Tasks
    print(f"\n=== RESULTADOS FINAIS DAS TASKS ===")
    
    print(f"\nTask A:")
    print(f"  Status: {task_a.status}")
    print(f"  Creation: {task_a.creation_time_s}s")
    print(f"  Transmission Start: {task_a.transmission_start_time_s}s")
    print(f"  Transmission End: {task_a.transmission_end_time_s}s")
    print(f"  Transmission Time: {task_a.transmission_time_s}s")
    print(f"  Queue Enter: {task_a.queue_enter_time_s}s")
    print(f"  Queue Start: {task_a.queue_start_time_s}s")
    print(f"  Queue Time: {task_a.queue_time_s}s")
    print(f"  Execution Start: {task_a.execution_start_time_s}s")
    print(f"  Execution End: {task_a.execution_end_time_s}s")
    print(f"  Execution Time: {task_a.execution_time_s}s")
    print(f"  Completion: {task_a.completion_time_s}s")
    print(f"  Response Time: {task_a.response_time_s}s")
    print(f"  Deadline: {task_a.deadline_time_s}s")
    print(f"  Deadline Violation: {task_a.deadline_violation}")

    print(f"\nTask B:")
    print(f"  Status: {task_b.status}")
    print(f"  Creation: {task_b.creation_time_s}s")
    print(f"  Transmission Start: {task_b.transmission_start_time_s}s")
    print(f"  Transmission End: {task_b.transmission_end_time_s}s")
    print(f"  Transmission Time: {task_b.transmission_time_s}s")
    print(f"  Queue Enter: {task_b.queue_enter_time_s}s")
    print(f"  Queue Start: {task_b.queue_start_time_s}s")
    print(f"  Queue Time: {task_b.queue_time_s}s")
    print(f"  Execution Start: {task_b.execution_start_time_s}s")
    print(f"  Execution End: {task_b.execution_end_time_s}s")
    print(f"  Execution Time: {task_b.execution_time_s}s")
    print(f"  Completion: {task_b.completion_time_s}s")
    print(f"  Response Time: {task_b.response_time_s}s")
    print(f"  Deadline: {task_b.deadline_time_s}s")
    print(f"  Deadline Violation: {task_b.deadline_violation}")

    # Validações
    print(f"\n=== VALIDAÇÕES ===")
    
    validations = []
    
    # Validação 1: Tasks completaram
    if task_a.status == TaskStatus.COMPLETED:
        print("[OK] Task A completou")
        validations.append(True)
    else:
        print(f"[FAIL] Task A não completou (status: {task_a.status})")
        validations.append(False)
    
    if task_b.status == TaskStatus.COMPLETED:
        print("[OK] Task B completou")
        validations.append(True)
    else:
        print(f"[FAIL] Task B não completou (status: {task_b.status})")
        validations.append(False)
    
    # Validação 2: Upload antes de execução
    if task_a.execution_start_time_s is not None and task_a.transmission_end_time_s is not None:
        if task_a.execution_start_time_s >= task_a.transmission_end_time_s:
            print("[OK] Task A: execução começou após upload terminar")
            validations.append(True)
        else:
            print(f"[FAIL] Task A: execução começou antes do upload terminar "
                  f"(exec_start={task_a.execution_start_time_s}s, trans_end={task_a.transmission_end_time_s}s)")
            validations.append(False)
    
    if task_b.execution_start_time_s is not None and task_b.transmission_end_time_s is not None:
        if task_b.execution_start_time_s >= task_b.transmission_end_time_s:
            print("[OK] Task B: execução começou após upload terminar")
            validations.append(True)
        else:
            print(f"[FAIL] Task B: execução começou antes do upload terminar "
                  f"(exec_start={task_b.execution_start_time_s}s, trans_end={task_b.transmission_end_time_s}s)")
            validations.append(False)
    
    # Validação 3: FIFO funcionou
    if task_a.queue_time_s is not None and task_b.queue_time_s is not None:
        if task_a.queue_time_s <= task_b.queue_time_s:
            print("[OK] FIFO respeitado (Task A entrou na fila antes)")
            validations.append(True)
        else:
            print(f"[FAIL] FIFO não respeitado (Task A queue={task_a.queue_time_s}s, Task B queue={task_b.queue_time_s}s)")
            validations.append(False)
    
    # Validação 4: max_concurrent_tasks=1 funcionou
    queue_status = task_scheduler.get_queue_status(target_server)
    if queue_status["queue_size"] == 0:
        print("[OK] Fila vazia no final (max_concurrent_tasks=1 funcionou)")
        validations.append(True)
    else:
        print(f"[FAIL] Fila não vazia no final (size={queue_status['queue_size']})")
        validations.append(False)
    
    # Validação 5: EdgeSimPy é relógio mestre
    simulation_time_s = simulator.schedule.steps * simulator.tick_duration
    if task_a.completion_time_s <= simulation_time_s and task_b.completion_time_s <= simulation_time_s:
        print(
            f"[OK] Tempos derivados do EdgeSimPy "
            f"(simulação={simulation_time_s}s, A={task_a.completion_time_s}s, "
            f"B={task_b.completion_time_s}s)"
        )
        validations.append(True)
    else:
        print("[FAIL] Algum tempo de conclusão excede o relógio do EdgeSimPy")
        validations.append(False)

    # Validação 6: transmissão terminou antes da execução para ambas as Tasks
    for task_name, task in (("A", task_a), ("B", task_b)):
        if task.execution_start_time_s >= task.transmission_end_time_s:
            print(f"[OK] Task {task_name}: execução não ocorreu durante o upload")
            validations.append(True)
        else:
            print(f"[FAIL] Task {task_name}: execução ocorreu durante o upload")
            validations.append(False)

    # Validação 7: integração não mantém flows ativos após as Tasks terminarem
    if not scheduler_integration.active_network_flows:
        print("[OK] Nenhum NetworkFlow de Task permaneceu ativo")
        validations.append(True)
    else:
        print(f"[FAIL] Flows ainda ativos: {len(scheduler_integration.active_network_flows)}")
        validations.append(False)
    
    # Resumo
    print(f"\n=== RESUMO ===")
    passed = sum(validations)
    total = len(validations)
    print(f"Validações: {passed}/{total} passaram")
    
    if passed == total:
        print("\nIntegração TaskScheduler + NetworkFlow: SUCESSO")
    else:
        print(f"\nIntegração TaskScheduler + NetworkFlow: FALHOU ({total - passed} validações)")

    return passed == total


if __name__ == "__main__":
    # Mudar para o diretório edgesimpy-simulation
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    success = test_task_scheduler_with_network()
    sys.exit(0 if success else 1)
