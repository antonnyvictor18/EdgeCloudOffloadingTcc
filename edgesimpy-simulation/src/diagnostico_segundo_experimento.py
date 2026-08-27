"""
Diagnóstico do segundo experimento - Reproduzindo placement do tutorial EdgeSimPy
Objetivo: Reproduzir APENAS o comportamento de placement do tutorial oficial
"""

import sys
import os

# Adicionando o diretório edgesimpy-source ao path para usar a versão local
edgesimpy_source = os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source')
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *


def placement_algorithm(parameters):
    """
    Algoritmo de placement equivalente ao do tutorial (First-Fit).
    Itera sobre serviços e provisiona no primeiro servidor com capacidade.
    """
    from edge_sim_py import NetworkFlow
    
    current_step = parameters.get("current_step", 0)
    
    print(f"\n=== Placement Algorithm - Step {current_step} ===")
    
    for service in Service.all():
        # Não migrar serviços que já estão sendo migrados
        if service.server == None and not service.being_provisioned:
            # Iterar sobre servidores para encontrar um host adequado
            for edge_server in EdgeServer.all():
                # Verificar se o servidor tem recursos suficientes
                if edge_server.has_capacity_to_host(service=service):
                    # Iniciar o provisionamento do serviço no servidor
                    service.provision(target_server=edge_server)
                    print(f"  Service {service.id} -> {edge_server}")
                    # Após iniciar o provisionamento, passar para o próximo serviço
                    break
    
    # Imprimir estado dos NetworkFlows após placement
    total_flows = NetworkFlow.count()
    active_flows = len([f for f in NetworkFlow.all() if f.status == "active"])
    
    if total_flows > 0:
        flow_types = {}
        finished_flows = 0
        for flow in NetworkFlow.all():
            flow_type = flow.metadata.get("type", "unknown")
            flow_types[flow_type] = flow_types.get(flow_type, 0) + 1
            if flow.status == "finished":
                finished_flows += 1
        
        print(f"  NetworkFlows: total={total_flows}, active={active_flows}, finished={finished_flows}")
        print(f"  Flow types: {flow_types}")
    else:
        print(f"  NetworkFlows: total={total_flows}, active={active_flows}")


def stopping_criterion(model: object):
    """
    Critério de parada: simulação continua até que todos os serviços estejam provisionados.
    """
    provisioned_services = 0
    for service in Service.all():
        if service.server != None:
            provisioned_services += 1
    return provisioned_services == Service.count()


def print_step_info():
    """
    Imprime informações detalhadas sobre o estado atual da simulação.
    """
    from edge_sim_py import NetworkFlow
    
    # Obter o step atual do simulador
    simulator = Simulator.all()[0] if Simulator.count() > 0 else None
    step = simulator.schedule.steps if simulator else 0
    time = step * 1  # tick_duration = 1 segundo
    
    print(f"\n=== Step {step} (Time: {time}s) ===")
    
    # Informações de cada serviço
    for service in Service.all():
        print(f"Service {service.id}: server={service.server}, being_provisioned={service.being_provisioned}")
    
    # Informações sobre NetworkFlows
    total_flows = NetworkFlow.count()
    active_flows = len([f for f in NetworkFlow.all() if f.status == "active"])
    
    if total_flows > 0:
        flow_types = {}
        finished_flows = 0
        for flow in NetworkFlow.all():
            flow_type = flow.metadata.get("type", "unknown")
            flow_types[flow_type] = flow_types.get(flow_type, 0) + 1
            if flow.status == "finished":
                finished_flows += 1
        
        print(f"NetworkFlows: total={total_flows}, active={active_flows}, finished={finished_flows}")
        print(f"Flow types: {flow_types}")
    else:
        print(f"NetworkFlows: total={total_flows}, active={active_flows}")


def print_final_results():
    """
    Imprime os resultados finais da simulação.
    """
    from edge_sim_py import NetworkFlow
    
    print("\n" + "="*60)
    print("RESULTADOS FINAIS")
    print("="*60)
    
    # Servidor final de cada serviço
    print("\nServidor final de cada Service:")
    for service in Service.all():
        print(f"  Service {service.id}: {service.server}")
    
    # Duração da simulação
    simulator = Simulator.all()[0] if Simulator.count() > 0 else None
    if simulator:
        final_step = simulator.schedule.steps
        duration = final_step * 1  # tick_duration = 1 segundo
        print(f"\nDuração da simulação: {duration}s ({final_step} steps)")
    
    # Informações sobre NetworkFlows
    total_flows = NetworkFlow.count()
    print(f"\nQuantidade total de flows: {total_flows}")
    
    if total_flows > 0:
        flow_types = {}
        for flow in NetworkFlow.all():
            flow_type = flow.metadata.get("type", "unknown")
            flow_types[flow_type] = flow_types.get(flow_type, 0) + 1
        print(f"Tipos de flows criados: {flow_types}")
    
    # Métricas de provisionamento disponíveis
    print("\nMétricas de provisionamento por Service:")
    for service in Service.all():
        metrics = service.collect()
        print(f"  Service {service.id}:")
        for key, value in metrics.items():
            print(f"    {key}: {value}")


def main():
    """
    Função principal que configura e executa a simulação.
    """
    # Caminho para o dataset
    dataset_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'tutorials', 
        'datasets', 
        'sample_dataset2.json'
    )
    
    print(f"Usando dataset: {dataset_path}")
    print(f"Dataset existe: {os.path.exists(dataset_path)}")
    
    # Criar objeto Simulator
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=stopping_criterion,
        resource_management_algorithm=placement_algorithm,
    )
    
    # Carregar dataset
    simulator.initialize(input_file=dataset_path)
    
    print(f"\n=== INÍCIO DA SIMULAÇÃO ===")
    print(f"Total de Services: {Service.count()}")
    print(f"Total de EdgeServers: {EdgeServer.count()}")
    
    # Executar simulação
    simulator.run_model()
    
    # Imprimir resultados finais
    print_final_results()


if __name__ == "__main__":
    main()
