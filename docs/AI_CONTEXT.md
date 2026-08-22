# AI context pack — EdgeCloudOffloadingTcc

## 1. Project goal
Undergraduate TCC studying Edge/Cloud offloading decisions using traditional baselines and ML, with EdgeSimPy added as a more realistic simulation/evaluation layer.

## 2. Existing C# side
Known structure from the project:
- dataset/feature representation around `OffloadingSample`;
- analytical simulation around `EdgeCloudSimulator`;
- evaluation around `Evaluator`;
- strategies include Random, Fixed Rule, Simple Heuristic, WiSARD and MLP.

Known feature concepts:
- CpuCycles
- TaskSizeMB
- DeadlineMs
- LatencySensitivity
- RequiredMemoryMB
- Edge CPU utilization
- Edge memory utilization
- Edge queue
- bandwidth
- network latency
- Cloud CPU utilization
- Cloud queue

The current analytical model uses these variables to estimate Edge/Cloud response time and produce a preferred destination/label.

## 3. Main methodological risk
The ML model may learn to reproduce labels produced by the analytical simulator that is also used for evaluation. This is acceptable as a baseline experiment but creates a circularity limitation.

The EdgeSimPy layer should therefore be used as an independent environmental validation layer.

## 4. Preferred architecture
C#:
dataset + existing policies + training

Interface:
CSV/JSON contract

Python:
EdgeSimPy scenario + policy execution + system metrics

Output:
CSV/JSON results + plots

## 5. Current EdgeSimPy state
Installed:
`edge_sim_py 1.1.0`

Known commit:
`76eb5ead74596bb4240759fa4336f1d6f190c70a`

Available components observed:
Application, BaseStation, EdgeServer, NetworkFlow, NetworkLink, NetworkSwitch, Service, Simulator, Topology, User, power models, mobility/access patterns, placement and flow-scheduling modules.

Local tutorial data:
- `tutorials/datasets/sample_dataset1.json`
- `tutorials/datasets/sample_dataset2.json`

## 6. Immediate learning phase
Current phase is Phase 1.

Goal:
- understand official dataset structure;
- load an official dataset;
- instantiate Simulator;
- run a short simulation;
- inspect entity counts/relationships;
- understand service placement and network flows.

Do not integrate C# or ML until this works.

## 7. EdgeSimPy concepts
Input JSON has two conceptual groups:
- attributes: intrinsic state/capacity/parameters;
- relationships: associations between entities.

Physical layer examples:
User, BaseStation, NetworkSwitch, NetworkLink, EdgeServer.

Logical layer:
Application, Service, container entities.

Management:
service placement, migration, network-flow scheduling, maintenance/resource-management logic.

Dynamic communication:
NetworkFlow.

## 8. Useful research questions
Examples:
- Does ML-based offloading reduce latency under load?
- Which policy best balances latency and energy?
- How robust are policies when bandwidth or Edge capacity changes?
- What happens when multiple Edge servers compete for workloads?
- Does mobility degrade the policy?

## 9. Experimental progression
1. official dataset smoke test
2. reduced scenario
3. one workload/task type
4. controlled Edge vs Cloud
5. concurrent workload
6. dynamic network
7. multiple Edge servers
8. policy comparison
9. ML integration
10. energy and optional mobility
11. repeated runs/statistics

## 10. Reproducibility
Always record:
- software versions;
- Git commit;
- scenario configuration;
- random seed;
- workload;
- policy;
- date/time if needed;
- output artifact.

## 11. Official reference
EdgeSimPy paper:
Paulo S. Souza, Tiago Ferreto, Rodrigo N. Calheiros.
"EdgeSimPy: Python-Based Modeling and Simulation of Edge Computing Resource Management Policies."
Future Generation Computer Systems, 148, 446–459, 2023.
DOI: https://doi.org/10.1016/j.future.2023.06.013

Use the official project/documentation for API claims.
