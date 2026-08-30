# EdgeCloudOffloadingTcc

Projeto acadêmico de TCC para comparação de estratégias de decisão de task offloading em ambientes Edge-Cloud, combinando simulação analítica em C#/.NET 10 e validação independente com EdgeSimPy 1.1.0.

## Visão geral do projeto

Este projeto possui duas camadas complementares que não devem ser mescladas:

### Camada C# (Simulador Analítico)
- Gerador de dataset sintético com 15.000 amostras
- Simulador analítico Edge-Cloud com modelo de latência
- Cinco estratégias de decisão: Random, Fixed Rule, Heuristic, WiSARD, MLP
- Avaliação de métricas de classificação e desempenho
- Geração automática de gráficos e relatórios

### Camada Python (EdgeSimPy)
- EdgeSimPy 1.1.0 como ambiente de simulação de infraestrutura
- Modelo de Task independente com ciclo de vida temporal completo
- Políticas de placement: FirstFit, LatencyAware, ResourceAware
- TaskScheduler com filas FIFO por EdgeServer
- Validação independente das decisões de offloading

**Arquitetura proposta:** C# (dataset/políticas) → contrato CSV/JSON → EdgeSimPy (simulação realista) → resultados sistêmicos

## Como executar

### C# (Simulador Analítico)

Instale o .NET 10 SDK e execute:

```bash
dotnet build EdgeCloudOffloadingTcc.csproj
dotnet run --project EdgeCloudOffloadingTcc.csproj
```

Para gerar um número específico de amostras:

```bash
dotnet run --project EdgeCloudOffloadingTcc.csproj 20000
```

**Arquivos gerados:**
- `Dataset/dataset.csv` - dataset completo
- `Dataset/train.csv` - conjunto de treinamento
- `Dataset/test.csv` - conjunto de teste
- `Charts/*.png` - gráficos de resultados
- `Reports/final-report.md` - relatório automático

### Python/EdgeSimPy

Navegue para o diretório `edgesimpy-simulation` e use o ambiente virtual:

```bash
cd edgesimpy-simulation
.venv\Scripts\python.exe src\diagnostico_primeiro_experimento.py
.venv\Scripts\python.exe src\comparar_politicas_isoladas.py
```

**Scripts disponíveis:**
- `src/diagnostico_primeiro_experimento.py` - teste básico do Simulator
- `src/diagnostico_infraestrutura.py` - auditoria da infraestrutura
- `src/diagnostico_distancia_users_edges.py` - análise de latência de rede
- `src/diagnostico_latency_aware.py` - política LatencyAwarePlacement
- `src/diagnostico_resource_aware.py` - política ResourceAwarePlacement
- `src/diagnostico_task_scheduler.py` - validação do TaskScheduler
- `src/test_task_scheduler.py` - testes obrigatórios A-E do TaskScheduler

## Estratégias implementadas

### Lado C# (Offloading)
- **Random Decision** - baseline aleatório
- **Fixed Rule** - regra baseada em limiar de CPU
- **Simple Heuristic** - heurística ponderada com múltiplas variáveis
- **WiSARD** - rede neural sem peso implementada didaticamente
- **MLP** - perceptron multicamadas em C# puro

### Lado Python (Placement)
- **FirstFit** - baseline determinístico
- **LatencyAwarePlacement** - escolhe menor delay que atenda SLA
- **ResourceAwarePlacement** - desempata por delay, CPU, RAM, ID

## Status do EdgeSimPy (Fases concluídas)

### ✅ Fases 0-5 concluídas (28/08/2026)
- **Fase 0:** Ambiente e instalação do EdgeSimPy 1.1.0
- **Fase 1:** Dataset oficial e infraestrutura
- **Fase 2:** Ciclo do Simulator e scheduler
- **Fase 3:** Políticas de placement (FirstFit, LatencyAware, ResourceAware)
- **Fase 4:** Auditoria de provisionamento
- **Fase 5:** Modelo temporal de Tasks (Task, TaskStatus, TaskExecutor, TaskQueue, TaskScheduler)

### 🔵 Fase 6 - Atual
- Integração do TaskScheduler ao ciclo temporal do EdgeSimPy
- Ainda sem NetworkFlow para dados de Task, Cloud, ML ou offloading completo

### ⏳ Fases futuras
- NetworkFlow para transmissão de dados de Task
- Representação de Cloud
- Integração C# ↔ Python (contrato CSV/JSON)
- Políticas ML (WiSARD, MLP) conectadas ao EdgeSimPy
- Mobilidade e experimentos de estresse

## Documentação técnica

### Contexto geral
- [AI_CONTEXT.md](docs/AI_CONTEXT.md) - pacote de contexto para IA
- [CONTEXTO_MESTRE_EDGESIMPY_TCC.md](docs/CONTEXTO_MESTRE_EDGESIMPY_TCC.md) - contexto de continuidade
- [EDGE_SIM_PY_PHASES.md](docs/EDGE_SIM_PY_PHASES.md) - lista resumida de fases

### Histórico e detalhes
- [HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md](docs/HISTORICO_EVOLUCAO_EDGESIMPY_TCC.md) - log detalhado de experimentos
- [APRESENTACAO_ORIENTADOR_EDGESIMPY.md](docs/APRESENTACAO_ORIENTADOR_EDGESIMPY.md) - roteiro de apresentação

### Guias didáticos
- [GUIA_DIDATICO_TCC.md](GUIA_DIDATICO_TCC.md) - guia completo do projeto
- [ARTIGO_TCC_COMPLETO.md](ARTIGO_TCC_COMPLETO.md) - artigo completo do TCC

## Observações importantes

### Reprodutibilidade
- O projeto C# evita dependências externas (NuGet) para facilitar execução em ambientes sem restore de pacotes
- Experimentos EdgeSimPy são isolados em processos separados para evitar estado global compartilhado
- Seeds e parâmetros são documentados para reprodutibilidade

### Separação metodológica
- O simulador C# gera rótulos analíticos que podem sofrer de circularidade se usados para avaliação
- O EdgeSimPy serve como camada de validação independente para quebrar essa circularidade
- O modelo de Task é mantido independente do EdgeSimPy até decisão explícita de integração

### Cuidados com unidades
- Lado C#: milissegundos para deadline, MB para tamanho
- Lado Python: segundos para tempo (igual ao `tick_unit="seconds"` do EdgeSimPy)
- Conversão explícita: `deadline_time_s = creation_time_s + deadline_ms / 1000`

## Próximos passos recomendados

1. Concluir Fase 6: integrar TaskScheduler ao ciclo temporal do EdgeSimPy
2. Implementar NetworkFlow para transmissão de dados de Task
3. Adicionar representação de Cloud
4. Criar contrato CSV/JSON entre C# e Python
5. Conectar políticas ML (WiSARD, MLP) ao EdgeSimPy
6. Realizar experimentos comparativos completos
7. Escrever metodologia e resultados finais do TCC

## Ambiente de desenvolvimento

### Requisitos
- .NET 10 SDK
- Python 3.x
- EdgeSimPy 1.1.0 (commit 76eb5ead74596bb4240759fa4336f1d6f190c70a)
- NetworkX (dependência do EdgeSimPy)

### Validação
- C#: `dotnet build EdgeCloudOffloadingTcc.csproj`
- EdgeSimPy: `edgesimpy-simulation\.venv\Scripts\python.exe edgesimpy-simulation\src\diagnostico_primeiro_experimento.py`
