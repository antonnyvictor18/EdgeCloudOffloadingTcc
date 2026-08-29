"""
Diagnóstico de distância entre Users e EdgeServers
Objetivo: Calcular distância de rede usando a topologia real do EdgeSimPy
"""

import sys
import os
import networkx as nx

# Adicionando o diretório edgesimpy-source ao path para usar a versão local
edgesimpy_source = os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source')
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *


def calculate_network_distance(user_switch, edge_server_switch, topology):
    """
    Calcula a distância de rede entre dois NetworkSwitches usando a topologia.
    """
    try:
        # Usar nx.shortest_path com weight="delay" como o EdgeSimPy faz
        path = nx.shortest_path(
            G=topology,
            source=user_switch,
            target=edge_server_switch,
            weight="delay",
            method="dijkstra"
        )
        
        # Calcular delay total usando o método do EdgeSimPy
        path_delay = topology.calculate_path_delay(path=path)
        
        # Número de hops = número de links = len(path) - 1
        hops = len(path) - 1
        
        return {
            "path": path,
            "hops": hops,
            "delay": path_delay,
            "switch_sequence": [f"NetworkSwitch_{sw.id}" for sw in path]
        }
    except nx.NetworkXNoPath:
        return None


def print_user_edge_distances():
    """
    Imprime as distâncias entre cada User e cada EdgeServer.
    """
    print("\n" + "="*80)
    print("DISTÂNCIAS DE REDE: USERS × EDGESERVERS")
    print("="*80)
    
    topology = Topology.first()
    
    for user in User.all():
        print(f"\n{'='*80}")
        print(f"User {user.id}")
        print(f"{'='*80}")
        
        user_bs = user.base_station
        user_switch = user_bs.network_switch if user_bs else None
        user_sla = user.delay_slas.get(str(user.applications[0].id), "N/A") if user.applications else "N/A"
        
        print(f"BaseStation: {user_bs}")
        print(f"NetworkSwitch: {user_switch}")
        print(f"Delay SLA: {user_sla}ms")
        
        # EdgeServer diretamente associado à BaseStation
        local_edge_servers = user_bs.edge_servers if user_bs else []
        print(f"EdgeServers locais (na mesma BaseStation): {[f'EdgeServer_{es.id}' for es in local_edge_servers]}")
        
        # Calcular distâncias para todos os EdgeServers
        distances = []
        
        for edge_server in EdgeServer.all():
            edge_bs = edge_server.base_station
            edge_switch = edge_bs.network_switch if edge_bs else None
            
            if user_switch and edge_switch:
                distance_info = calculate_network_distance(user_switch, edge_switch, topology)
                
                if distance_info:
                    cpu_available = edge_server.cpu - edge_server.cpu_demand
                    memory_available = edge_server.memory - edge_server.memory_demand
                    
                    is_local = edge_server in local_edge_servers
                    
                    distances.append({
                        "edge_server": edge_server,
                        "edge_switch": edge_switch,
                        "edge_bs": edge_bs,
                        "hops": distance_info["hops"],
                        "delay": distance_info["delay"],
                        "switch_sequence": distance_info["switch_sequence"],
                        "cpu_available": cpu_available,
                        "memory_available": memory_available,
                        "is_local": is_local
                    })
        
        # Ordenar por delay (menor para maior)
        distances.sort(key=lambda x: x["delay"])
        
        print(f"\nEdgeServers ordenados por delay (menor para maior):")
        print(f"{'-'*80}")
        
        for i, dist in enumerate(distances):
            marker = "* MENOR DELAY" if i == 0 else ""
            local_marker = "[LOCAL]" if dist["is_local"] else ""
            
            print(f"\n{i+1}. EdgeServer_{dist['edge_server'].id} {local_marker} {marker}")
            print(f"   EdgeSwitch: {dist['edge_switch']}")
            print(f"   BaseStation: {dist['edge_bs']}")
            print(f"   Hops: {dist['hops']}")
            print(f"   Delay: {dist['delay']}ms")
            print(f"   Caminho: {' -> '.join(dist['switch_sequence'])}")
            print(f"   CPU disponível: {dist['cpu_available']}")
            print(f"   Memória disponível: {dist['memory_available']}")
            
            # Verificar se atende SLA
            if user_sla != "N/A":
                sla_status = "ATENDE SLA" if dist['delay'] <= user_sla else "NÃO ATENDE SLA"
                print(f"   Status SLA ({user_sla}ms): {sla_status}")


def print_conceptual_table():
    """
    Gera tabela conceitual completa com todas as métricas.
    """
    print("\n" + "="*80)
    print("TABELA CONCEITUAL: USERS × EDGESERVERS")
    print("="*80)
    
    topology = Topology.first()
    
    # Cabeçalho da tabela
    header = f"{'User':<6} | {'User BS':<12} | {'User Switch':<16} | {'SLA':<6} | {'EdgeServer':<12} | {'Edge Switch':<16} | {'Hops':<5} | {'Delay':<6} | {'CPU disp':<9} | {'RAM disp':<9} | {'Status':<12}"
    print(header)
    print("-" * len(header))
    
    for user in User.all():
        user_bs = user.base_station
        user_switch = user_bs.network_switch if user_bs else None
        user_sla = user.delay_slas.get(str(user.applications[0].id), "N/A") if user.applications else "N/A"
        local_edge_servers = user_bs.edge_servers if user_bs else []
        
        # Calcular distâncias para todos os EdgeServers
        distances = []
        
        for edge_server in EdgeServer.all():
            edge_bs = edge_server.base_station
            edge_switch = edge_bs.network_switch if edge_bs else None
            
            if user_switch and edge_switch:
                distance_info = calculate_network_distance(user_switch, edge_switch, topology)
                
                if distance_info:
                    cpu_available = edge_server.cpu - edge_server.cpu_demand
                    memory_available = edge_server.memory - edge_server.memory_demand
                    is_local = edge_server in local_edge_servers
                    
                    sla_status = "ATENDE" if user_sla != "N/A" and distance_info["delay"] <= user_sla else "NÃO ATENDE"
                    local_status = "LOCAL" if is_local else "OFFLOAD"
                    
                    distances.append({
                        "edge_server": edge_server,
                        "edge_switch": edge_switch,
                        "hops": distance_info["hops"],
                        "delay": distance_info["delay"],
                        "cpu_available": cpu_available,
                        "memory_available": memory_available,
                        "sla_status": sla_status,
                        "local_status": local_status
                    })
        
        # Ordenar por delay
        distances.sort(key=lambda x: x["delay"])
        
        # Imprimir linhas da tabela
        for dist in distances:
            user_str = f"User_{user.id}"
            user_bs_str = f"BS_{user_bs.id}" if user_bs else "N/A"
            user_switch_str = f"Switch_{user_switch.id}" if user_switch else "N/A"
            sla_str = f"{user_sla}ms" if user_sla != "N/A" else "N/A"
            edge_server_str = f"Edge_{dist['edge_server'].id}"
            edge_switch_str = f"Switch_{dist['edge_switch'].id}"
            
            row = f"{user_str:<6} | {user_bs_str:<12} | {user_switch_str:<16} | {sla_str:<6} | {edge_server_str:<12} | {edge_switch_str:<16} | {dist['hops']:<5} | {dist['delay']:<6} | {dist['cpu_available']:<9} | {dist['memory_available']:<9} | {dist['sla_status']} ({dist['local_status']})"
            print(row)


def main():
    """
    Função principal que carrega o dataset e calcula distâncias.
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
    
    # Criar objeto Simulator sem executar simulação
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
    )
    
    # Carregar dataset
    simulator.initialize(input_file=dataset_path)
    
    print(f"\n=== TOPOLOGIA CARREGADA ===")
    print(f"Total de Users: {User.count()}")
    print(f"Total de EdgeServers: {EdgeServer.count()}")
    print(f"Total de NetworkSwitches: {NetworkSwitch.count()}")
    
    # Imprimir distâncias detalhadas
    print_user_edge_distances()
    
    # Imprimir tabela conceitual
    print_conceptual_table()


if __name__ == "__main__":
    main()
