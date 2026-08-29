"""Launch and compare isolated FirstFit, LatencyAware and ResourceAware runs."""

import json
import os
import subprocess
import sys


def main():
    source_dir = os.path.dirname(__file__)
    results_dir = os.path.join(os.path.dirname(source_dir), "results", "isolated_sample_dataset2")
    os.makedirs(results_dir, exist_ok=True)
    python_executable = sys.executable
    runner = os.path.join(source_dir, "executar_politica_isolada.py")
    policies = ["FirstFit", "LatencyAware", "ResourceAware"]
    results = {}

    for policy in policies:
        output_path = os.path.join(results_dir, f"{policy}.json")
        completed = subprocess.run(
            [python_executable, runner, policy, output_path],
            check=True,
            capture_output=True,
            text=True,
        )
        print(completed.stdout, end="")
        with open(output_path, "r", encoding="utf-8") as result_file:
            results[policy] = json.load(result_file)

    print("\n=== COMPARAÇÃO ISOLADA ===")
    for policy, result in results.items():
        provisioning = {item["service"]: item["provisioning_time_s"] for item in result["services"]}
        servers = {item["service"]: item["server"] for item in result["services"]}
        print(
            f"{policy}: steps={result['simulation_steps']}, flows={result['total_network_flows']}, "
            f"servers={servers}, provisioning={provisioning}"
        )

    print("\n=== SERVICES 5 E 6 ===")
    for policy, result in results.items():
        services = {item["service"]: item for item in result["services"]}
        print(
            f"{policy}: Service 5={services[5]['provisioning_time_s']}s, "
            f"Service 6={services[6]['provisioning_time_s']}s"
        )

    print("\n=== MUDANÇAS DE SERVIDOR ===")
    baseline = {item["service"]: item["server"] for item in results["LatencyAware"]["services"]}
    for policy in ["FirstFit", "ResourceAware"]:
        current = {item["service"]: item["server"] for item in results[policy]["services"]}
        changes = [f"Service {service}: Edge {baseline[service]} -> Edge {current[service]}" for service in baseline if baseline[service] != current[service]]
        print(f"{policy} vs LatencyAware: {', '.join(changes) if changes else 'nenhuma'}")


if __name__ == "__main__":
    main()