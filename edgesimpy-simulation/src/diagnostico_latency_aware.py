"""
Diagnóstico da política LatencyAwarePlacement
Objetivo: Avaliar a primeira política determinística de placement baseada em latência
"""

import sys
import os
import networkx as nx

# Adicionando o diretório edgesimpy-source ao path para usar a versão local
edgesimpy_source = os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source')
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *

# Importar política diretamente do arquivo
import importlib.util
spec = importlib.util.spec_from_file_location("latency_aware_placement", 
    os.path.join(os.path.dirname(__file__), 'policies', 'latency_aware_placement.py'))
latency_aware_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latency_aware_module)

latency_aware_placement = latency_aware_module.latency_aware_placement
calculate_network_delay = latency_aware_module.calculate_network_delay


def stopping_criterion(model: object):
    """
    Critério de parada: simulação continua até que todos os serviços estejam provisionados.
    """
    provisioned_services = 0
    for service in Service.all():
        if service.server != None:
            provisioned_services += 1
    return provisioned_services == Service.count()


def collect_results():
    """
    Coleta os resultados finais da simulação.
    """
    from edge_sim_py import NetworkFlow
    
    results = []
    
    for service in Service.all():
        application = service.application
        user = application.users[0] if application and application.users else None
        
        if not user:
            continue
        
        # Calcular delay final
        user_base_station = user.base_station
        user_switch = user_base_station.network_switch if user_base_station else None
        
        edge_server = service.server
        edge_base_station = edge_server.base_station if edge_server else None
        edge_switch = edge_base_station.network_switch if edge_base_station else None
        
        delay = 0
        hops = 0
        is_local = False
        
        if user_switch and edge_switch:
            topology = Topology.first()
            delay, hops, _ = calculate_network_delay(user_switch, edge_switch, topology)
            is_local = user_base_station == edge_base_station
        
        # Obter SLA
        application_id = str(application.id)
        sla = user.delay_slas.get(application_id, float('inf'))
        
        # Capacidade disponível
        cpu_available = edge_server.cpu - edge_server.cpu_demand if edge_server else 0
        ram_available = edge_server.memory - edge_server.memory_demand if edge_server else 0
        
        # Tempo de provisionamento
        metrics = service.collect()
        last_migration = metrics.get("Last Migration", {})
        provisioning_time = 0
        if last_migration:
            start = last_migration.get("start", 0)
            end = last_migration.get("end", 0)
            provisioning_time = end - start
        
        # NetworkFlows
        total_flows = NetworkFlow.count()
        
        results.append({
            'user_id': user.id,
            'service_id': service.id,
            'edge_server_id': edge_server.id if edge_server else None,
            'local_offload': 'LOCAL' if is_local else 'OFFLOAD',
            'hops': hops,
            'delay': delay,
            'sla': sla,
            'cpu_available': cpu_available,
            'ram_available': ram_available,
            'provisioning_time': provisioning_time,
            'total_flows': total_flows
        })
    
    return results


def print_results_table(results):
    """
    Imprime a tabela de resultados.
    """
    print("\n" + "="*100)
    print("TABELA DE RESULTADOS - LatencyAwarePlacement")
    print("="*100)
    
    header = f"{'User':<6} | {'Service':<8} | {'Edge escolhido':<14} | {'Local/Offload':<13} | {'Hops':<5} | {'Delay':<6} | {'SLA':<6} | {'CPU disp':<10} | {'RAM disp':<10} | {'Provisionamento':<15}"
    print(header)
    print("-" * len(header))
    
    for result in results:
        user_str = f"User_{result['user_id']}"
        service_str = f"Service_{result['service_id']}"
        edge_str = f"Edge_{result['edge_server_id']}" if result['edge_server_id'] else "N/A"
        delay_str = f"{result['delay']}ms"
        sla_str = f"{result['sla']}ms"
        provision_str = f"{result['provisioning_time']}s"
        
        row = f"{user_str:<6} | {service_str:<8} | {edge_str:<14} | {result['local_offload']:<13} | {result['hops']:<5} | {delay_str:<6} | {sla_str:<6} | {result['cpu_available']:<10} | {result['ram_available']:<10} | {provision_str:<15}"
        print(row)


def main():
    """
    Função principal que executa o experimento com LatencyAwarePlacement.
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
    
    # Criar objeto Simulator com LatencyAwarePlacement
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
        stopping_criterion=stopping_criterion,
        resource_management_algorithm=latency_aware_placement,
    )
    
    # Carregar dataset
    simulator.initialize(input_file=dataset_path)
    
    print(f"\n=== INÍCIO DA SIMULAÇÃO ===")
    print(f"Total de Services: {Service.count()}")
    print(f"Total de EdgeServers: {EdgeServer.count()}")
    print(f"Política: LatencyAwarePlacement")
    
    # Executar simulação
    simulator.run_model()
    
    # Coletar resultados
    results = collect_results()
    
    # Imprimir tabela de resultados
    print_results_table(results)
    
    # Imprimir resumo
    print("\n" + "="*100)
    print("RESUMO")
    print("="*100)
    
    local_count = sum(1 for r in results if r['local_offload'] == 'LOCAL')
    offload_count = sum(1 for r in results if r['local_offload'] == 'OFFLOAD')
    
    print(f"Services com acesso LOCAL: {local_count}")
    print(f"Services com OFFLOAD: {offload_count}")
    
    sla_met_count = sum(1 for r in results if r['delay'] <= r['sla'])
    sla_violated_count = sum(1 for r in results if r['delay'] > r['sla'])
    
    print(f"Services que atendem SLA: {sla_met_count}")
    print(f"Services que violam SLA: {sla_violated_count}")
    
    avg_provisioning_time = sum(r['provisioning_time'] for r in results) / len(results)
    print(f"Tempo médio de provisionamento: {avg_provisioning_time:.2f}s")


if __name__ == "__main__":
    main()
