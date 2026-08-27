"""
Diagnóstico da infraestrutura disponível no EdgeSimPy
Objetivo: Entender a infraestrutura sem executar placement, ML ou alterações
"""

import sys
import os

# Adicionando o diretório edgesimpy-source ao path para usar a versão local
edgesimpy_source = os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source')
sys.path.insert(0, edgesimpy_source)

from edge_sim_py import *


def print_edge_servers():
    """
    Imprime informações detalhadas sobre cada EdgeServer.
    """
    print("\n" + "="*60)
    print("EDGESERVERS")
    print("="*60)
    
    for server in EdgeServer.all():
        print(f"\nEdgeServer {server.id}:")
        print(f"  CPU: {server.cpu} (demand: {server.cpu_demand})")
        print(f"  Memory: {server.memory} (demand: {server.memory_demand})")
        print(f"  Disk: {server.disk} (demand: {server.disk_demand})")
        print(f"  Available: {server.available}")
        print(f"  BaseStation: {server.base_station}")
        print(f"  NetworkSwitch: {server.network_switch}")


def print_base_stations():
    """
    Imprime informações detalhadas sobre cada BaseStation.
    """
    print("\n" + "="*60)
    print("BASESTATIONS")
    print("="*60)
    
    for bs in BaseStation.all():
        print(f"\nBaseStation {bs.id}:")
        print(f"  Wireless Delay: {bs.wireless_delay}")
        print(f"  NetworkSwitch: {bs.network_switch}")
        print(f"  EdgeServers: {[f'EdgeServer_{es.id}' for es in bs.edge_servers]}")
        print(f"  Users: {[f'User_{u.id}' for u in bs.users]}")


def print_network_links():
    """
    Imprime informações detalhadas sobre cada NetworkLink.
    """
    print("\n" + "="*60)
    print("NETWORKLINKS")
    print("="*60)
    
    for link in NetworkLink.all():
        print(f"\nNetworkLink {link.id}:")
        print(f"  Nodes: {[f'{node.__class__.__name__}_{node.id}' for node in link.nodes]}")
        print(f"  Delay: {link.delay}")
        print(f"  Bandwidth: {link.bandwidth} (demand: {link.bandwidth_demand})")
        print(f"  Active Flows: {len(link.active_flows)}")
        print(f"  Active: {link.active}")


def print_users():
    """
    Imprime informações detalhadas sobre cada User.
    """
    print("\n" + "="*60)
    print("USERS")
    print("="*60)
    
    for user in User.all():
        print(f"\nUser {user.id}:")
        print(f"  BaseStation: {user.base_station}")
        print(f"  Applications: {[f'Application_{app.id}' for app in user.applications]}")
        print(f"  Delay SLAs: {user.delay_slas}")
        print(f"  Making Requests: {user.making_requests}")


def print_services():
    """
    Imprime informações detalhadas sobre cada Service.
    """
    print("\n" + "="*60)
    print("SERVICES")
    print("="*60)
    
    for service in Service.all():
        print(f"\nService {service.id}:")
        print(f"  CPU Demand: {service.cpu_demand}")
        print(f"  Memory Demand: {service.memory_demand}")
        print(f"  Server: {service.server}")
        print(f"  State: {service.state}")
        print(f"  Application: {service.application}")


def print_applications():
    """
    Imprime informações detalhadas sobre cada Application.
    """
    print("\n" + "="*60)
    print("APPLICATIONS")
    print("="*60)
    
    for app in Application.all():
        print(f"\nApplication {app.id}:")
        print(f"  Label: {app.label}")
        print(f"  Services: {[f'Service_{s.id}' for s in app.services]}")
        print(f"  Users: {[f'User_{u.id}' for u in app.users]}")


def print_infrastructure_summary():
    """
    Imprime um resumo tabular das relações na infraestrutura.
    """
    print("\n" + "="*60)
    print("RESUMO TABULAR - RELAÇÕES DE INFRAESTRUTURA")
    print("="*60)
    
    # Quais EdgeServers estão mais próximos de cada User?
    print("\n1. EdgeServers mais próximos de cada User:")
    for user in User.all():
        if user.base_station:
            closest_servers = user.base_station.edge_servers
            print(f"   User {user.id} -> BaseStation {user.base_station.id} -> EdgeServers: {[f'EdgeServer_{es.id}' for es in closest_servers]}")
    
    # Qual EdgeServer possui mais CPU disponível?
    print("\n2. EdgeServers com mais CPU disponível:")
    cpu_available = [(server.id, server.cpu - server.cpu_demand) for server in EdgeServer.all()]
    cpu_available.sort(key=lambda x: x[1], reverse=True)
    for server_id, cpu in cpu_available:
        print(f"   EdgeServer {server_id}: {cpu} CPU disponível")
    
    # Qual possui mais memória disponível?
    print("\n3. EdgeServers com mais memória disponível:")
    memory_available = [(server.id, server.memory - server.memory_demand) for server in EdgeServer.all()]
    memory_available.sort(key=lambda x: x[1], reverse=True)
    for server_id, memory in memory_available:
        print(f"   EdgeServer {server_id}: {memory} memória disponível")
    
    # Quais Users compartilham a mesma BaseStation?
    print("\n4. Users que compartilham a mesma BaseStation:")
    bs_users = {}
    for user in User.all():
        if user.base_station:
            bs_id = user.base_station.id
            if bs_id not in bs_users:
                bs_users[bs_id] = []
            bs_users[bs_id].append(user.id)
    
    for bs_id, user_ids in bs_users.items():
        print(f"   BaseStation {bs_id}: Users {[f'User_{uid}' for uid in user_ids]}")
    
    # Quais EdgeServers compartilham a mesma infraestrutura de rede?
    print("\n5. EdgeServers que compartilham a mesma infraestrutura de rede:")
    bs_servers = {}
    for server in EdgeServer.all():
        if server.base_station:
            bs_id = server.base_station.id
            if bs_id not in bs_servers:
                bs_servers[bs_id] = []
            bs_servers[bs_id].append(server.id)
    
    for bs_id, server_ids in bs_servers.items():
        print(f"   BaseStation {bs_id}: EdgeServers {[f'EdgeServer_{sid}' for sid in server_ids]}")


def main():
    """
    Função principal que carrega o dataset e imprime a infraestrutura.
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
    
    # Criar objeto Simulator sem algoritmo de resource management
    simulator = Simulator(
        tick_duration=1,
        tick_unit="seconds",
    )
    
    # Carregar dataset
    simulator.initialize(input_file=dataset_path)
    
    print(f"\n=== INFRAESTRUTURA CARREGADA ===")
    print(f"Total de EdgeServers: {EdgeServer.count()}")
    print(f"Total de BaseStations: {BaseStation.count()}")
    print(f"Total de NetworkLinks: {NetworkLink.count()}")
    print(f"Total de Users: {User.count()}")
    print(f"Total de Services: {Service.count()}")
    print(f"Total de Applications: {Application.count()}")
    
    # Imprimir informações detalhadas
    print_edge_servers()
    print_base_stations()
    print_network_links()
    print_users()
    print_services()
    print_applications()
    
    # Imprimir resumo tabular
    print_infrastructure_summary()


if __name__ == "__main__":
    main()
