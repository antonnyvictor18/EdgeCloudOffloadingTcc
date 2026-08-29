"""Deterministic resource-aware placement policy for EdgeSimPy."""

from policies.latency_aware_placement import calculate_network_delay


def resource_aware_placement(parameters):
    """Place each pending service using the requested lexicographic priority."""
    from edge_sim_py import EdgeServer, Service, Topology

    topology = Topology.first()
    current_step = parameters.get("current_step", 0)
    print(f"\n=== ResourceAwarePlacement - Step {current_step} ===")

    for service in Service.all():
        if service.server is not None or service.being_provisioned:
            continue

        print(f"\nService {service.id}:")
        application = service.application
        if application is None or not application.users:
            print("  ERRO: Service sem Application ou User associado")
            continue

        user = application.users[0]
        application_id = str(application.id)
        sla = user.delay_slas.get(application_id, float("inf"))
        user_base_station = user.base_station
        user_switch = user_base_station.network_switch if user_base_station else None

        print(f"  User: {user.id}")
        print(f"  SLA: {sla}ms")
        if user_switch is None:
            print("  ERRO: User sem NetworkSwitch associado")
            continue

        valid_candidates = []
        for edge_server in EdgeServer.all():
            edge_base_station = edge_server.base_station
            edge_switch = edge_base_station.network_switch if edge_base_station else None
            if edge_switch is None:
                continue

            if not edge_server.has_capacity_to_host(service=service):
                print(f"  Edge {edge_server.id} -> INVALID (capacidade)")
                continue

            delay, hops, path = calculate_network_delay(user_switch, edge_switch, topology)
            if path is None or delay > sla:
                reason = "sem caminho" if path is None else f"SLA ({delay}ms > {sla}ms)"
                print(f"  Edge {edge_server.id} -> INVALID ({reason})")
                continue

            cpu_available = edge_server.cpu - edge_server.cpu_demand
            ram_available = edge_server.memory - edge_server.memory_demand
            candidate = {
                "edge_server": edge_server,
                "delay": delay,
                "hops": hops,
                "cpu_available": cpu_available,
                "ram_available": ram_available,
                "is_local": user_base_station == edge_base_station,
            }
            valid_candidates.append(candidate)
            print(
                f"  Edge {edge_server.id} -> delay={delay}ms, hops={hops}, "
                f"CPU={cpu_available}, RAM={ram_available}"
            )

        if not valid_candidates:
            print("  ERRO: Nenhum EdgeServer candidato válido")
            continue

        minimum_delay = min(candidate["delay"] for candidate in valid_candidates)
        tied_candidates = [candidate for candidate in valid_candidates if candidate["delay"] == minimum_delay]
        if len(tied_candidates) > 1:
            print("  Empate de delay.")
            if len({candidate["cpu_available"] for candidate in tied_candidates}) > 1:
                print("  Desempate por CPU disponível.")
            elif len({candidate["ram_available"] for candidate in tied_candidates}) > 1:
                print("  Desempate por RAM disponível.")
            else:
                print("  Desempate por menor ID.")

        valid_candidates.sort(
            key=lambda candidate: (
                candidate["delay"],
                -candidate["cpu_available"],
                -candidate["ram_available"],
                candidate["edge_server"].id,
            )
        )
        selected = valid_candidates[0]
        selected_edge = selected["edge_server"]
        print(f"  Selected -> Edge {selected_edge.id}")
        service.provision(target_server=selected_edge)