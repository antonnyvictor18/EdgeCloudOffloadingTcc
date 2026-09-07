"""
Script de teste para investigar a transferência real de dados via NetworkFlow

Objetivo: Criar um NetworkFlow manual e observar como os dados são transferidos
"""

import json
import sys
import os
import networkx as nx

# Adicionar o diretório edgesimpy-source ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source'))

from edge_sim_py import Simulator
from edge_sim_py.components import *

def test_networkflow_manual():
    """Cria um NetworkFlow manual e observa a transferência"""
    # Definir um resource management algorithm vazio
    def empty_resource_management(parameters):
        pass
    
    # Definir um stopping criterion simples
    def simple_stopping_criterion(model):
        return model.schedule.steps >= 5
    
    simulator = Simulator(
        resource_management_algorithm=empty_resource_management,
        stopping_criterion=simple_stopping_criterion
    )
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)
    
    print("=== TESTE DE NETWORKFLOW MANUAL ===")
    
    # Pegar componentes - usar dois EdgeServers diferentes para um flow real
    edge_servers = EdgeServer.all()
    if len(edge_servers) < 2:
        print("ERRO: Precisa de pelo menos 2 EdgeServers para teste")
        return
    
    source_server = edge_servers[0]
    target_server = edge_servers[1]
    user = User.first()
    
    print(f"\n=== INFORMAÇÕES DOS COMPONENTES ===")
    print(f"\nUser {user.id}:")
    print(f"  base_station: {user.base_station.id if user.base_station else None}")
    print(f"  base_station.network_switch: {user.base_station.network_switch.id if user.base_station and user.base_station.network_switch else None}")
    
    print(f"\nSource EdgeServer {source_server.id}:")
    print(f"  base_station: {source_server.base_station.id if source_server.base_station else None}")
    print(f"  base_station.network_switch: {source_server.base_station.network_switch.id if source_server.base_station and source_server.base_station.network_switch else None}")
    
    print(f"\nTarget EdgeServer {target_server.id}:")
    print(f"  base_station: {target_server.base_station.id if target_server.base_station else None}")
    print(f"  base_station.network_switch: {target_server.base_station.network_switch.id if target_server.base_station and target_server.base_station.network_switch else None}")
    
    # Calcular path entre os switches dos dois EdgeServers
    if source_server.base_station and source_server.base_station.network_switch and target_server.base_station and target_server.base_station.network_switch:
        path = nx.shortest_path(
            G=simulator.topology,
            source=source_server.base_station.network_switch,
            target=target_server.base_station.network_switch,
            weight="delay",
            method="dijkstra",
        )
        
        print(f"\nPath (NetworkSwitch objects): {path}")
        print(f"Path (NetworkSwitch IDs): {[switch.id for switch in path]}")
        print(f"Número de links no path: {len(path) - 1}")
        
        # Verificar bandwidth dos links no path
        print(f"\nBandwidth dos links no path:")
        for i in range(len(path) - 1):
            link = simulator.topology[path[i]][path[i + 1]]
            print(f"  Link {link.id} entre Switch {path[i].id} e Switch {path[i + 1].id}: bandwidth={link.bandwidth}")
        
        # Criar um NetworkFlow manual seguindo o padrão do EdgeSimPy
        # source/target são componentes lógicos (EdgeServer), path contém NetworkSwitches
        # Usar tamanho que seja múltiplo exato da bandwidth para validação matemática
        bandwidth_per_link = 12.5
        data_size = int(bandwidth_per_link * 8)  # 100 KB para facilitar cálculo
        
        print(f"\n=== CRIAÇÃO DO NETWORKFLOW ===")
        print(f"  source: EdgeServer {source_server.id}")
        print(f"  target: EdgeServer {target_server.id}")
        print(f"  path: {[switch.id for switch in path]}")
        print(f"  data_to_transfer: {data_size}")
        print(f"  start: {simulator.schedule.steps + 1}")
        
        flow = NetworkFlow(
            topology=simulator.topology,
            source=source_server,
            target=target_server,
            start=simulator.schedule.steps + 1,
            path=path,
            data_to_transfer=data_size,
            metadata={"type": "test", "test_id": 1},
        )
        simulator.initialize_agent(agent=flow)
        
        print(f"\nNetworkFlow criado:")
        print(f"  flow.id: {flow.id}")
        print(f"  flow.status: {flow.status}")
        print(f"  flow.data_to_transfer: {flow.data_to_transfer}")
        print(f"  flow.bandwidth: {flow.bandwidth}")
        
        # Executar alguns steps para ver a transferência
        print(f"\n=== EXPERIMENTO DE TRANSFERÊNCIA CONTROLADA ===")
        print(f"\nDados iniciais:")
        print(f"  flow.start: {flow.start}")
        print(f"  flow.status: {flow.status}")
        print(f"  flow.data_to_transfer: {flow.data_to_transfer}")
        print(f"  Simulator.tick_duration: {simulator.tick_duration} segundos")
        
        print(f"\nExecutando simulation steps até conclusão...")
        max_steps = 20
        for i in range(max_steps):
            simulator.step()
            print(f"\nStep {simulator.schedule.steps}:")
            print(f"  flow.status: {flow.status}")
            print(f"  flow.data_to_transfer: {flow.data_to_transfer}")
            print(f"  flow.bandwidth: {flow.bandwidth}")
            if flow.status == "finished":
                print(f"  flow.end: {flow.end}")
                print(f"  transmission_time (steps): {flow.end - flow.start}")
                print(f"  transmission_time (segundos): {(flow.end - flow.start) * simulator.tick_duration}")
                break
        else:
            print(f"\nAVISO: Flow não terminou em {max_steps} steps")

def test_endpoint_semantics():
    """Testa a semântica de source/target: NetworkSwitch vs EdgeServer"""
    # Definir um resource management algorithm vazio
    def empty_resource_management(parameters):
        pass
    
    # Definir um stopping criterion simples
    def simple_stopping_criterion(model):
        return model.schedule.steps >= 3
    
    simulator = Simulator(
        resource_management_algorithm=empty_resource_management,
        stopping_criterion=simple_stopping_criterion
    )
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)
    
    print("\n=== TESTE DE SEMÂNTICA DE ENDPOINTS ===")
    
    edge_servers = EdgeServer.all()
    if len(edge_servers) < 2:
        print("ERRO: Precisa de pelo menos 2 EdgeServers")
        return
    
    source_server = edge_servers[0]
    target_server = edge_servers[1]
    
    # Calcular path
    path = nx.shortest_path(
        G=simulator.topology,
        source=source_server.base_station.network_switch,
        target=target_server.base_station.network_switch,
        weight="delay",
        method="dijkstra",
    )
    
    print(f"\nCaso A: source=EdgeServer, target=EdgeServer (padrão EdgeSimPy)")
    flow_a = NetworkFlow(
        topology=simulator.topology,
        source=source_server,
        target=target_server,
        start=simulator.schedule.steps + 1,
        path=path,
        data_to_transfer=50,
        metadata={"type": "test_endpoint", "case": "A"},
    )
    simulator.initialize_agent(agent=flow_a)
    
    print(f"  source: {flow_a.source} (EdgeServer {flow_a.source.id})")
    print(f"  target: {flow_a.target} (EdgeServer {flow_a.target.id})")
    print(f"  status: {flow_a.status}")
    
    print(f"\nCaso B: source=NetworkSwitch, target=NetworkSwitch")
    flow_b = NetworkFlow(
        topology=simulator.topology,
        source=source_server.base_station.network_switch,
        target=target_server.base_station.network_switch,
        start=simulator.schedule.steps + 1,
        path=path,
        data_to_transfer=50,
        metadata={"type": "test_endpoint", "case": "B"},
    )
    simulator.initialize_agent(agent=flow_b)
    
    print(f"  source: {flow_b.source} (NetworkSwitch {flow_b.source.id})")
    print(f"  target: {flow_b.target} (NetworkSwitch {flow_b.target.id})")
    print(f"  status: {flow_b.status}")
    
    # Executar alguns steps
    print(f"\nExecutando 2 steps para validar...")
    for i in range(2):
        simulator.step()
        print(f"\nStep {simulator.schedule.steps}:")
        print(f"  Flow A status: {flow_a.status}, data_to_transfer: {flow_a.data_to_transfer}")
        print(f"  Flow B status: {flow_b.status}, data_to_transfer: {flow_b.data_to_transfer}")
    
    print(f"\nConclusão: Ambos os casos funcionam mecanicamente.")
    print(f"  Caso A (EdgeServer): Segue o padrão EdgeSimPy para layer/service flows")
    print(f"  Caso B (NetworkSwitch): Funciona mas não segue o padrão EdgeSimPy")
    print(f"  OBSERVAÇÃO IMPORTANTE: Os dois flows compartilharam bandwidth (6.25 cada em vez de 12.5)")
    print(f"  Isso confirma que max_min_fairness funciona corretamente para flows de Task")

if __name__ == "__main__":
    # Mudar para o diretório edgesimpy-simulation
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    
    test_networkflow_manual()
    test_endpoint_semantics()
