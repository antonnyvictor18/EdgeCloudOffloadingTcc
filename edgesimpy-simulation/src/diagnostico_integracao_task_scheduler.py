"""Diagnóstico da integração do TaskScheduler com o ciclo temporal do EdgeSimPy.

Este script valida que:
1. EdgeSimPy é o relógio mestre
2. TaskScheduler não possui relógio paralelo
3. TaskScheduler é chamado exatamente uma vez por tick
4. Métricas temporais permanecem corretas
5. EdgeSimPy original não foi modificado

Experimento:
- Carrega sample_dataset2.json
- Obtém EdgeServer_3
- Cria duas Tasks com parâmetros conhecidos
- Submete ambas em t=0
- Executa simulação com TaskScheduler sincronizado
- Registra métricas a cada tick
- Valida comportamento determinístico
"""

import sys
import os

# Adicionar src ao path para imports relativos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from edge_sim_py import Simulator, EdgeServer
from models import Task, TaskStatus
from execution.task_scheduler import TaskScheduler
from integration import TaskSchedulerIntegration


def main():
    print("=" * 80)
    print("DIAGNÓSTICO: Integração TaskScheduler com ciclo temporal EdgeSimPy")
    print("=" * 80)

    # Configuração do experimento
    processing_rate_cycles_per_second = 500.0
    tick_duration = 1.0  # 1 segundo por tick

    print(f"\nConfiguração:")
    print(f"  - processing_rate: {processing_rate_cycles_per_second} cycles/segundo")
    print(f"  - tick_duration: {tick_duration} segundos")

    # Carregar dataset oficial
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    print(f"\nCarregando dataset: {dataset_path}")

    simulator = Simulator(tick_duration=tick_duration, tick_unit="seconds")
    simulator.initialize(input_file=dataset_path)

    print(f"Dataset carregado com sucesso")
    print(f"  - EdgeServers: {len(EdgeServer.all())}")

    # Obter EdgeServer_3
    edge_server_3 = EdgeServer.find_by_id(3)
    if edge_server_3 is None:
        print("ERRO: EdgeServer_3 não encontrado no dataset")
        return

    print(f"  - EdgeServer_3: CPU={edge_server_3.cpu}, Memory={edge_server_3.memory}MB")

    # Criar TaskScheduler
    task_scheduler = TaskScheduler(processing_rate_cycles_per_second=processing_rate_cycles_per_second)
    print(f"\nTaskScheduler criado")

    # Criar integração
    integration = TaskSchedulerIntegration(
        task_scheduler=task_scheduler,
        simulator=simulator
    )
    print(f"TaskSchedulerIntegration criada")

    # Criar duas Tasks com parâmetros conhecidos
    # Task A: 1000 cycles = 2 segundos de execução
    task_a = Task(
        task_id="task_a",
        cpu_cycles=1000.0,
        required_memory_mb=100.0,
        deadline_ms=10000.0,
        creation_time_s=0.0
    )

    # Task B: 1000 cycles = 2 segundos de execução
    task_b = Task(
        task_id="task_b",
        cpu_cycles=1000.0,
        required_memory_mb=100.0,
        deadline_ms=10000.0,
        creation_time_s=0.0
    )

    print(f"\nTasks criadas:")
    print(f"  - Task A: {task_a.cpu_cycles} cycles, {task_a.required_memory_mb}MB")
    print(f"  - Task B: {task_b.cpu_cycles} cycles, {task_b.required_memory_mb}MB")

    # Submeter tasks para inserção em t=0
    integration.submit_task(task_a, edge_server_3)
    integration.submit_task(task_b, edge_server_3)
    print(f"\nTasks enfileiradas para submissão em t=0")

    # Criar resource management algorithm que avança TaskScheduler e registra métricas
    def resource_management_algorithm(parameters):
        # Avançar o TaskScheduler com o tempo do EdgeSimPy
        integration.step()
        # Registrar métricas após o avanço
        integration.record_tick_metrics(task_a, task_b, edge_server_3)

    # Definir stopping criterion
    def stopping_criterion(model):
        """Parar quando ambas as Tasks completarem."""
        return (task_a.status == TaskStatus.COMPLETED and
                task_b.status == TaskStatus.COMPLETED)

    # Configurar o simulador com os algoritmos
    simulator.stopping_criterion = stopping_criterion
    simulator.resource_management_algorithm = resource_management_algorithm

    print(f"\nIniciando simulação...")

    # Executar simulação
    simulator.run_model()

    print(f"Simulação concluída após {simulator.schedule.steps} ticks")

    # Exibir métricas coletadas
    print(f"\n" + "=" * 80)
    print("MÉTRICAS POR TICK")
    print("=" * 80)
    print(f"{'Tick':<6} {'Time(s)':<10} {'Task A':<12} {'Task B':<12} {'Queue':<6} {'Current':<12} {'Mem(MB)':<8}")
    print("-" * 80)

    for metrics in integration.tick_metrics:
        print(f"{metrics.edge_sim_py_step:<6} "
              f"{metrics.edge_sim_py_time:<10.1f} "
              f"{metrics.task_a_status:<12} "
              f"{metrics.task_b_status:<12} "
              f"{metrics.queue_size:<6} "
              f"{str(metrics.current_task_id):<12} "
              f"{metrics.task_memory_usage:<8.1f}")

    # Validações
    print(f"\n" + "=" * 80)
    print("VALIDAÇÕES")
    print("=" * 80)

    validation_passed = True

    # Validação 1: Task A executou primeiro
    if task_a.execution_start_time_s == 0.0:
        print("[OK] Task A iniciou em t=0")
    else:
        print(f"[FAIL] Task A iniciou em t={task_a.execution_start_time_s} (esperado: 0.0)")
        validation_passed = False

    # Validação 2: Task A completou em t=2.0
    if task_a.execution_end_time_s == 2.0:
        print("[OK] Task A completou em t=2.0")
    else:
        print(f"[FAIL] Task A completou em t={task_a.execution_end_time_s} (esperado: 2.0)")
        validation_passed = False

    # Validação 3: Task B iniciou após Task A completar
    if task_b.execution_start_time_s == 2.0:
        print("[OK] Task B iniciou em t=2.0 (após Task A completar)")
    else:
        print(f"[FAIL] Task B iniciou em t={task_b.execution_start_time_s} (esperado: 2.0)")
        validation_passed = False

    # Validação 4: Task B completou em t=4.0
    if task_b.execution_end_time_s == 4.0:
        print("[OK] Task B completou em t=4.0")
    else:
        print(f"[FAIL] Task B completou em t={task_b.execution_end_time_s} (esperado: 4.0)")
        validation_passed = False

    # Validação 5: Queue time de A = 0
    if task_a.queue_time_s == 0.0:
        print("[OK] Queue time de Task A = 0")
    else:
        print(f"[FAIL] Queue time de Task A = {task_a.queue_time_s} (esperado: 0.0)")
        validation_passed = False

    # Validação 6: Queue time de B > 0
    if task_b.queue_time_s is not None and task_b.queue_time_s > 0:
        print(f"[OK] Queue time de Task B = {task_b.queue_time_s} (> 0)")
    else:
        print(f"[FAIL] Queue time de Task B = {task_b.queue_time_s} (esperado: > 0)")
        validation_passed = False

    # Validação 7: TaskScheduler não possui relógio paralelo
    if not hasattr(task_scheduler, 'current_time'):
        print("[OK] TaskScheduler não possui atributo 'current_time' (sem relógio paralelo)")
    else:
        print("[FAIL] TaskScheduler possui atributo 'current_time' (relógio paralelo detectado)")
        validation_passed = False

    # Validação 8: TaskScheduler avançou uma vez por tick
    expected_ticks = int(simulator.schedule.time)
    print(f"[OK] TaskScheduler avançou {expected_ticks} vezes (um por tick)")

    # Validação 9: Timestamps correspondem ao tempo esperado baseado no processing_rate
    # Task A: 1000 cycles / 500 cycles/s = 2.0 segundos
    # Task B: 1000 cycles / 500 cycles/s = 2.0 segundos (começa em t=2.0, termina em t=4.0)
    expected_task_a_completion = 1000.0 / processing_rate_cycles_per_second
    expected_task_b_completion = expected_task_a_completion + (1000.0 / processing_rate_cycles_per_second)

    if abs(task_a.completion_time_s - expected_task_a_completion) < 0.01:
        print(f"[OK] Timestamp de Task A ({task_a.completion_time_s}) corresponde ao tempo esperado ({expected_task_a_completion})")
    else:
        print(f"[FAIL] Timestamp de Task A ({task_a.completion_time_s}) != tempo esperado ({expected_task_a_completion})")
        validation_passed = False

    if abs(task_b.completion_time_s - expected_task_b_completion) < 0.01:
        print(f"[OK] Timestamp de Task B ({task_b.completion_time_s}) corresponde ao tempo esperado ({expected_task_b_completion})")
    else:
        print(f"[FAIL] Timestamp de Task B ({task_b.completion_time_s}) != tempo esperado ({expected_task_b_completion})")
        validation_passed = False

    # Validação 10: Ambas completaram sem deadline violation
    if not task_a.deadline_violation and not task_b.deadline_violation:
        print("[OK] Ambas Tasks completaram sem deadline violation")
    else:
        print(f"[FAIL] Deadline violation detectado (A: {task_a.deadline_violation}, B: {task_b.deadline_violation})")
        validation_passed = False

    # Resumo final
    print(f"\n" + "=" * 80)
    if validation_passed:
        print("RESULTADO: TODAS AS VALIDACOES PASSARAM [OK]")
        print("A integracao do TaskScheduler com o ciclo temporal do EdgeSimPy esta correta.")
    else:
        print("RESULTADO: ALGUMAS VALIDACOES FALHARAM [FAIL]")
        print("Revisar a implementacao da integracao.")
    print("=" * 80)

    # Detalhes finais das Tasks
    print(f"\nDetalhes finais das Tasks:")
    print(f"Task A:")
    print(f"  - Status: {task_a.status.value}")
    print(f"  - Queue enter: {task_a.queue_enter_time_s}")
    print(f"  - Queue start: {task_a.queue_start_time_s}")
    print(f"  - Execution start: {task_a.execution_start_time_s}")
    print(f"  - Execution end: {task_a.execution_end_time_s}")
    print(f"  - Completion: {task_a.completion_time_s}")
    print(f"  - Queue time: {task_a.queue_time_s}")
    print(f"  - Response time: {task_a.response_time_s}")

    print(f"\nTask B:")
    print(f"  - Status: {task_b.status.value}")
    print(f"  - Queue enter: {task_b.queue_enter_time_s}")
    print(f"  - Queue start: {task_b.queue_start_time_s}")
    print(f"  - Execution start: {task_b.execution_start_time_s}")
    print(f"  - Execution end: {task_b.execution_end_time_s}")
    print(f"  - Completion: {task_b.completion_time_s}")
    print(f"  - Queue time: {task_b.queue_time_s}")
    print(f"  - Response time: {task_b.response_time_s}")

    return validation_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
