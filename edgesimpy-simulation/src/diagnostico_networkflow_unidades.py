"""
Script de diagnóstico para investigar unidades de NetworkFlow no EdgeSimPy 1.1.0

Objetivo: Investigar as unidades de:
- ContainerLayer.size
- NetworkLink.bandwidth  
- NetworkFlow.data_to_transfer
- NetworkFlow.start/end
- Simulator.tick_duration
"""

import json
import sys
import os

# Adicionar o diretório edgesimpy-source ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'edgesimpy-source'))

from edge_sim_py import Simulator
from edge_sim_py.components import *

def investigar_dataset():
    """Investiga os valores do sample_dataset2.json"""
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    print("=== INVESTIGAÇÃO DO DATASET ===")
    print(f"\nContainerLayer sizes (primeiros 5):")
    for layer in data["ContainerLayer"][:5]:
        print(f"  Layer {layer['attributes']['id']}: size={layer['attributes']['size']}")
    
    print(f"\nNetworkLink bandwidth (primeiros 5):")
    for link in data["NetworkLink"][:5]:
        print(f"  Link {link['attributes']['id']}: bandwidth={link['attributes']['bandwidth']}, delay={link['attributes']['delay']}")
    
    print(f"\nService states (primeiros 5):")
    for service in data["Service"][:5]:
        print(f"  Service {service['attributes']['id']}: state={service['attributes']['state']}")
    
    print(f"\nEdgeServer disk (primeiros 5):")
    for server in data["EdgeServer"][:5]:
        print(f"  EdgeServer {server['attributes']['id']}: disk={server['attributes']['disk']}")

def investigar_simulacao():
    """Carrega o dataset e investiga a simulação"""
    simulator = Simulator()
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)
    
    print("\n=== INVESTIGAÇÃO DA SIMULAÇÃO ===")
    print(f"Simulator.tick_duration: {simulator.tick_duration} segundos")
    print(f"Simulator.tick_unit: (definido no construtor, padrão 'seconds')")
    
    print(f"\nNetworkLinks na topologia:")
    for link in NetworkLink.all()[:5]:
        print(f"  Link {link.id}: bandwidth={link.bandwidth}, delay={link.delay}")
    
    print(f"\nContainerLayers:")
    for layer in ContainerLayer.all()[:5]:
        print(f"  Layer {layer.id}: size={layer.size}")
    
    print(f"\nServices:")
    for service in Service.all()[:5]:
        print(f"  Service {service.id}: state={service.state}")
    
    print(f"\nEdgeServers:")
    for server in EdgeServer.all()[:5]:
        print(f"  EdgeServer {server.id}: disk={server.disk}")

def investigar_path_example():
    """Investiga um exemplo de path na topologia"""
    simulator = Simulator()
    dataset_path = "tutorials/datasets/sample_dataset2.json"
    simulator.initialize(input_file=dataset_path)
    
    print("\n=== EXEMPLO DE PATH ===")
    
    # Pegar o primeiro User e primeiro EdgeServer
    user = User.first()
    edge_server = EdgeServer.first()
    
    print(f"User {user.id}:")
    print(f"  coordinates: {user.coordinates}")
    print(f"  base_station: {user.base_station.id if user.base_station else None}")
    if user.base_station:
        print(f"  base_station.network_switch: {user.base_station.network_switch.id if user.base_station.network_switch else None}")
    
    print(f"\nEdgeServer {edge_server.id}:")
    print(f"  coordinates: {edge_server.coordinates}")
    print(f"  base_station: {edge_server.base_station.id if edge_server.base_station else None}")
    if edge_server.base_station:
        print(f"  base_station.network_switch: {edge_server.base_station.network_switch.id if edge_server.base_station.network_switch else None}")
    
    # Calcular path entre os switches
    if user.base_station and user.base_station.network_switch and edge_server.base_station and edge_server.base_station.network_switch:
        import networkx as nx
        path = nx.shortest_path(
            G=simulator.topology,
            source=user.base_station.network_switch,
            target=edge_server.base_station.network_switch,
            weight="delay",
            method="dijkstra",
        )
        print(f"\nPath (NetworkSwitch IDs): {[switch.id for switch in path]}")
        print(f"Path length: {len(path)} switches")

if __name__ == "__main__":
    # Mudar para o diretório edgesimpy-simulation
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    
    investigar_dataset()
    investigar_simulacao()
    investigar_path_example()
