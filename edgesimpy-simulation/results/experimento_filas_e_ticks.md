# Estudo Fatorial: Resolução Temporal (Tick) × Disciplina de Fila × Política de Destino

Avaliação conduzida sobre o **mesmo workload representativo congelado de 20 tasks**
(10 rótulos analíticos Edge, 10 Cloud) executando Edge (`NetworkFlow` + `TaskScheduler` a 12 GHz)
e Cloud (`CloudExecutor` lógico com WAN por-Task a 60 GHz) no mesmo relógio do EdgeSimPy.

## 1. Desenho Experimental (Passos A → B → C)

1. **Passo A — Resolução Temporal (`tick_duration_s`):**
   - `1.0 s`: configuração padrão do tutorial EdgeSimPy (`link.bandwidth = 12.5 MB/tick`).
   - `0.1 s` (100 ms): `configure_simulator_tick_resolution` reescala cada link para
     `1.25 MB/tick`, mantendo a vazão física invariante em **12.5 MB/s (100 Mbps)** e
     eliminando o pedágio artificial de 1 s por task na fila de CPU.
2. **Passo B — Disciplina de Fila Local (`queue_policy`):**
   - `FIFO`: ordem de chegada na fila de execução.
   - `SJF` (*Shortest Job First*): menor `cpu_cycles` primeiro (ótimo para tempo médio de fila).
   - `EDF` (*Earliest Deadline First*): menor `deadline_time_s` primeiro — incorpora no
     escalonador local o atributo `DeadlineMs` que não faz parte das 6 features do classificador ML.
   - `LLF` (*Least Laxity First*): menor folga `(deadline_time_s - t_atual) - tempo_exec_estimado`.
   - `EDF_FEASIBLE` (*Feasibility-Aware EDF*): prioriza por EDF apenas tarefas que ainda podem
     cumprir o deadline (`t_atual + exec <= deadline`); tarefas cujo deadline já expirou no upload
     ('tasks zumbis') são rebaixadas para o fim da fila e atendidas em *best-effort* via SJF.
3. **Passo C — Política de Destino (Offloading):**
   - `AlwaysEdge`, `AlwaysCloud`, `RandomDestination` (5 seeds), `Oracle`, `MLP` (`MLP_final_6`), `WiSARD` (`WISARD_FINAL_6`).

---

## 2. Efeito do Passo A: Resolução Temporal (`tick = 1.0 s` vs `tick = 0.1 s`, sob FIFO)

| Política | E/C | Compl. 1.0s (s) | Compl. 0.1s (s) | Fila 1.0s (s) | Fila 0.1s (s) | Viol. 1.0s | Viol. 0.1s |
|---|---:|---:|---:|---:|---:|---:|---:|
| AlwaysEdge | 20/0 | 11.60 | 5.48 | 5.50 | 0.53 | 80% | 60% |
| AlwaysCloud | 0/20 | 13.75 | 6.33 | 6.40 | 0.44 | 100% | 40% |
| RandomDestination | 8.4/11.6 | 8.52 | 4.20 | 3.22 | 0.25 | 81% | 39% |
| Oracle | 10/10 | 7.80 | 3.55 | 3.20 | 0.30 | 90% | 45% |
| MLP | 11/9 | 7.25 | 3.23 | 2.95 | 0.30 | 80% | 40% |
| WiSARD | 12/8 | 7.40 | 3.75 | 2.40 | 0.11 | 75% | 50% |

### Decomposição Edge vs Cloud sob `FIFO` (`tick = 1.0 s` → `tick = 0.1 s`)

| Política | Edge fila 1.0s→0.1s (s) | Edge compl. 1.0s→0.1s (s) | Cloud fila 1.0s→0.1s (s) | Cloud compl. 1.0s→0.1s (s) | Cloud viol. 1.0s→0.1s |
|---|---:|---:|---:|---:|---:|
| AlwaysEdge | 5.50 → 0.53 | 11.60 → 5.48 | - → - | - → - | - → - |
| AlwaysCloud | - → - | - → - | 6.40 → 0.44 | 13.75 → 6.33 | 100% → 40% |
| RandomDestination | 2.05 → 0.25 | 6.64 → 3.65 | 3.85 → 0.22 | 9.50 → 4.41 | 85% → 31% |
| Oracle | 1.90 → 0.14 | 9.10 → 6.25 | 4.50 → 0.46 | 6.50 → 0.86 | 80% → 20% |
| MLP | 2.09 → 0.18 | 8.27 → 5.22 | 4.00 → 0.43 | 6.00 → 0.79 | 78% → 22% |
| WiSARD | 2.00 → 0.02 | 8.67 → 5.42 | 3.00 → 0.25 | 5.50 → 1.23 | 62% → 38% |

---

## 3. Efeito dos Passos B & C: Política de Destino × Disciplina de Fila (em `tick = 0.1 s`)

### 3.1 Tempo Médio de Conclusão (`mean_completion_time_s`, em segundos)

| Política de Destino | FIFO (s) | SJF (s) | EDF (s) | LLF (s) | EDF_FEASIBLE (s) | Melhor disciplina |
|---|---:|---:|---:|---:|---:|---|
| AlwaysEdge | 5.485 | 5.295 | 5.335 | 5.530 | 5.500 | **SJF** (5.295 s) |
| AlwaysCloud | 6.335 | 6.210 | 6.260 | 6.260 | 6.275 | **SJF** (6.210 s) |
| RandomDestination | 4.203 | 4.152 | 4.180 | 4.189 | 4.191 | **SJF** (4.152 s) |
| Oracle | 3.555 | 3.475 | 3.525 | 3.525 | 3.530 | **SJF** (3.475 s) |
| MLP | 3.225 | 3.145 | 3.195 | 3.195 | 3.200 | **SJF** (3.145 s) |
| WiSARD | 3.745 | 3.720 | 3.725 | 3.725 | 3.725 | **SJF** (3.720 s) |

### 3.2 Tempo Médio de Fila (`mean_queue_time_s`, em segundos)

| Política de Destino | FIFO (s) | SJF (s) | EDF (s) | LLF (s) | EDF_FEASIBLE (s) | Redução SJF vs FIFO |
|---|---:|---:|---:|---:|---:|---:|
| AlwaysEdge | 0.530 | 0.340 | 0.380 | 0.575 | 0.545 | +35.8% |
| AlwaysCloud | 0.440 | 0.315 | 0.365 | 0.365 | 0.380 | +28.4% |
| RandomDestination | 0.245 | 0.194 | 0.222 | 0.231 | 0.233 | +20.8% |
| Oracle | 0.300 | 0.220 | 0.270 | 0.270 | 0.275 | +26.7% |
| MLP | 0.295 | 0.215 | 0.265 | 0.265 | 0.270 | +27.1% |
| WiSARD | 0.115 | 0.090 | 0.095 | 0.095 | 0.095 | +21.7% |

### 3.3 Taxa de Violação de Deadline (`deadline_violation_rate`)

| Política de Destino | FIFO | SJF | EDF | LLF | EDF_FEASIBLE |
|---|---:|---:|---:|---:|---:|
| AlwaysEdge | 60.0% | 55.0% | 65.0% | 65.0% | 50.0% |
| AlwaysCloud | 40.0% | 35.0% | 30.0% | 30.0% | 30.0% |
| RandomDestination | 39.0% | 36.0% | 36.0% | 36.0% | 35.0% |
| Oracle | 45.0% | 40.0% | 35.0% | 35.0% | 35.0% |
| MLP | 40.0% | 35.0% | 30.0% | 30.0% | 30.0% |
| WiSARD | 50.0% | 45.0% | 40.0% | 40.0% | 40.0% |

---

## 4. Comparação com `tick = 1.0 s`: Por que a resolução temporal destrava as disciplinas de fila

| Política (tick = 1.0 s) | FIFO compl. / fila / viol. | SJF compl. / fila / viol. | EDF compl. / fila / viol. | LLF compl. / fila / viol. | EDF_FEASIBLE compl. / fila / viol. |
|---|---:|---:|---:|---:|---:|
| AlwaysEdge | 11.60s / 5.50s / 80% | 11.60s / 5.50s / 95% | 11.60s / 5.50s / 95% | 11.60s / 5.50s / 95% | 11.60s / 5.50s / 90% |
| AlwaysCloud | 13.75s / 6.40s / 100% | 13.75s / 6.40s / 95% | 13.75s / 6.40s / 100% | 13.75s / 6.40s / 100% | 13.75s / 6.40s / 100% |
| RandomDestination | 8.52s / 3.22s / 81% | 8.52s / 3.22s / 89% | 8.52s / 3.22s / 95% | 8.52s / 3.22s / 95% | 8.52s / 3.22s / 80% |
| Oracle | 7.80s / 3.20s / 90% | 7.80s / 3.20s / 95% | 7.80s / 3.20s / 100% | 7.80s / 3.20s / 100% | 7.80s / 3.20s / 80% |
| MLP | 7.25s / 2.95s / 80% | 7.25s / 2.95s / 85% | 7.25s / 2.95s / 95% | 7.25s / 2.95s / 95% | 7.25s / 2.95s / 65% |
| WiSARD | 7.40s / 2.40s / 75% | 7.40s / 2.40s / 85% | 7.40s / 2.40s / 95% | 7.40s / 2.40s / 95% | 7.40s / 2.40s / 60% |

## 5. Principais Conclusões para o TCC

1. **Efeito dramático da resolução temporal (Passo A):**
   - Com `tick = 1.0 s`, cada task na fila pagava no mínimo 1 s inteiro de servidor, mesmo
     quando sua execução durava `0.02–0.15 s` no Cloud (60 GHz) ou `0.1–0.6 s` no Edge (12 GHz).
   - Ao reduzir o tick para `0.1 s` (mantendo a vazão da rede em 12.5 MB/s = 100 Mbps), a fila
     Cloud cai de **3–6 s para frações de segundo**, derrubando as violações de deadline do Cloud
     e revelando a verdadeira vantagem de capacidade (60 GHz + WAN dedicada por task).
2. **Interação entre resolução temporal e políticas de fila (Passos A + B):**
   - Em `tick = 1.0 s`, trocar `FIFO` por `SJF` quase não altera o tempo de fila porque quase
     todas as tasks são arredondadas para 1 tick (1 s) de ocupação de CPU.
   - Em `tick = 0.1 s`, as durações de CPU se diferenciam (1 a 7 ticks de 0.1 s): **SJF reduz
     consistentemente o tempo médio de fila e de conclusão**, enquanto **EDF/LLF reordenam
     tasks urgentes usando `DeadlineMs`**.
3. **Gargalo residual no caminho Edge (rede compartilhada vs fila de CPU):**
   - Para tasks enviadas ao Edge num burst simultâneo (`t = 0`), os 10–12 fluxos concorrem
     simultaneamente pelo link LAN de 12.5 MB/s (`max_min_fairness`). Como muitas tasks
     terminam o upload em instantes próximos ou já chegam após estourar deadlines sub-segundo,
     a disciplina da fila de CPU atua apenas **após** o término do upload.
   - Isso demonstra um achado sistêmico central do EdgeSimPy que o modelo analítico C# não
     captura: **sob rajadas de dados grandes, o gargalo no Edge desloca-se da fila de CPU
     para o compartilhamento de banda de rede (NetworkFlow)**.
