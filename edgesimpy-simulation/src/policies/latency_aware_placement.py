"""
Política LatencyAwarePlacement para EdgeSimPy
Objetivo: Escolher EdgeServer com menor delay que atenda SLA e capacidade
"""

import networkx as nx


def calculate_network_delay(user_switch, edge_server_switch, topology):
    """
    Calcula o delay de rede entre dois NetworkSwitches.
    """
    try:
        path = nx.shortest_path(
            G=topology,
            source=user_switch,
            target=edge_server_switch,
            weight="delay",
            method="dijkstra"
        )
        path_delay = topology.calculate_path_delay(path=path)
        hops = len(path) - 1
        return path_delay, hops, path
    except nx.NetworkXNoPath:
        return float('inf'), float('inf'), None


def latency_aware_placement(parameters):
    """
    Política de placement baseada em latência.
    Para cada Service, escolhe o EdgeServer com menor delay que atenda SLA e capacidade.
    """
    from edge_sim_py import Service, EdgeServer, Topology, NetworkFlow
    
    topology = Topology.first()
    current_step = parameters.get("current_step", 0)
    
    print(f"\n=== LatencyAwarePlacement - Step {current_step} ===")
    
    for service in Service.all():
        # Apenas Services não provisionados
        if service.server is None and not service.being_provisioned:
            print(f"\nService {service.id}:")
            
            # Obter User associado ao Service
            application = service.application
            if not application or not application.users:
                print(f"  ERRO: Service sem Application ou User associado")
                continue
            
            user = application.users[0]  # No nosso cenário, 1 User por Application
            print(f"  User: {user.id}")
            
            # Obter SLA do User
            application_id = str(application.id)
            sla = user.delay_slas.get(application_id, float('inf'))
            print(f"  SLA: {sla}ms")
            
            # Obter switches do User e EdgeServers
            user_base_station = user.base_station
            user_switch = user_base_station.network_switch if user_base_station else None
            
            if not user_switch:
                print(f"  ERRO: User sem NetworkSwitch associado")
                continue
            
            # Construir lista de candidatos
            candidates = []
            
            for edge_server in EdgeServer.all():
                edge_base_station = edge_server.base_station
                edge_switch = edge_base_station.network_switch if edge_base_station else None
                
                if not edge_switch:
                    continue
                
                # Verificar capacidade
                if not edge_server.has_capacity_to_host(service=service):
                    continue
                
                # Calcular delay de rede
                delay, hops, path = calculate_network_delay(user_switch, edge_switch, topology)
                
                if delay == float('inf'):
                    continue
                
                # Verificar se atende SLA
                meets_sla = delay <= sla
                
                candidates.append({
                    'edge_server': edge_server,
                    'delay': delay,
                    'hops': hops,
                    'meets_sla': meets_sla,
                    'is_local': user_base_station == edge_base_station
                })
                
                status = "VALID" if meets_sla else "INVALID (SLA)"
                print(f"  Candidate EdgeServer {edge_server.id}: {delay}ms -> {status}")
            
            # Escolher melhor candidato
            if not candidates:
                print(f"  ERRO: Nenhum EdgeServer candidato válido")
                continue
            
            # Priorizar candidatos que atendem SLA, depois menor delay
            valid_candidates = [c for c in candidates if c['meets_sla']]
            
            if valid_candidates:
                # Escolher menor delay entre válidos
                valid_candidates.sort(key=lambda x: x['delay'])
                selected = valid_candidates[0]
                print(f"  Selected: EdgeServer {selected['edge_server'].id} (atende SLA)")
            else:
                # Fallback: menor delay mesmo não atendendo SLA
                candidates.sort(key=lambda x: x['delay'])
                selected = candidates[0]
                print(f"  Selected: EdgeServer {selected['edge_server'].id} (NÃO atende SLA - fallback)")
            
            # Provisionar o Service
            service.provision(target_server=selected['edge_server'])
