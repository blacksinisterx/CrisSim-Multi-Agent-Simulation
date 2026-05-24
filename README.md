# CrisisSim 🚨
**Agentic AI for Disaster Response using LLM-based Planning**

> Simulating multi-agent earthquake response with ReAct, Chain-of-Thought, and Reflexion reasoning frameworks.

---

## Overview

CrisisSim is a Mesa-based simulation environment for evaluating LLM-driven disaster response. Heterogeneous agents (drones, medics, trucks) coordinate to rescue survivors, suppress fires, and clear rubble-blocked roads in post-earthquake scenarios. Three reasoning strategies are benchmarked across 45 simulation runs (3 maps × 3 strategies × 5 seeds).

**Authors:** Aiza Ali  
**Course:** Agentic AI  

---

## Features

- **Three LLM Planning Strategies:** ReAct, Chain-of-Thought (CoT), and Reflexion
- **Multi-provider LLM support:** Gemini 2.5 Flash, Groq (LLaMA 3.1), Ollama (local)
- **Realistic operational constraints:** battery management, hospital triage queues, medic carrying mechanics
- **Dynamic environment:** aftershocks, fire spread with wind effects, probabilistic rubble generation
- **Advanced GUI:** real-time charts, per-agent status panels, strategy indicator
- **Comprehensive logging:** all agent actions, environmental changes, and LLM decisions

---

## Agent Types

| Agent | Capabilities | Constraints |
|-------|-------------|-------------|
| **Drone** | `scout_area` (radius 3), `charge_battery` | Limited battery; must recharge at depot |
| **Medic** | `rescue_survivor` (≤1 cell), `move` | Carries 1 survivor; 50% speed when transporting |
| **Truck** | `extinguish_fire` (≤2 cells), `clear_rubble` (≤1 cell) | Fuel constraints; variable clearing rate |

---

## Planning Strategies

### ReAct (Reasoning and Acting)
Iterative observe → reason → act → reflect loop. Up to 5 reasoning steps per tick.
- ✅ Highest rescue efficiency, dynamic re-prioritization
- ⚠️ Higher API call count, more JSON schema violations

### Chain-of-Thought (CoT)
Structured 6-step reasoning: Situation Analysis → Agent Assessment → Task Prioritization → Distance Validation → Command Generation → Confidence Assessment.
- ✅ Most consistent output, lowest invalid JSON rate
- ⚠️ Less adaptive to unexpected events

### Reflexion
Memory-augmented self-critique. Reviews past failures before planning; up to 3 refinement iterations per tick.
- ✅ Improves over time; learns optimal hospital routing and battery planning
- ⚠️ Benefits require multiple runs to manifest; higher memory overhead

---

## Results Summary

| Strategy | Rescued (mean) | Deaths (mean) | Avg Rescue Time | Invalid JSON |
|----------|---------------|---------------|-----------------|--------------|
| **ReAct** | **2.27** | 18.47 | 88.95 s | 4.67 |
| Reflexion | 1.87 | 18.13 | 103.29 s | 2.60 |
| CoT | 1.20 | 18.67 | 121.48 s | **1.53** |

Results across 45 runs (3 maps × 3 strategies × 5 seeds). ReAct achieves the highest rescue count; CoT is the most reliable.

---

## Maps

| Map | Grid | Survivors | Fires | Rubble |
|-----|------|-----------|-------|--------|
| `small` | 20×20 | 15 | 2 | 3 |
| `medium` | 20×20 | 20 | 3 | 3 |
| `hard` | 20×20 | 25 | 3 | 3 |

---

## Setup

### Prerequisites
- Python 3.9+
- Mesa agent-based modeling framework
- API key for Gemini or Groq (or Ollama running locally)

### Installation

```bash
git clone https://github.com/<your-repo>/crisissim.git
cd crisissim
pip install -r requirements.txt
```

### Configuration

Copy and edit the config file:

```bash
cp config.example.yaml config.yaml
```

Set your API keys and preferred provider:

```yaml
provider: gemini          # gemini | groq | ollama
strategy: react           # react | cot | reflexion
map: small                # small | medium | hard
seeds: [42, 123, 456, 789, 999]
```

Or configure via environment variables:

```bash
export GEMINI_API_KEY=your_key_here
export GROQ_API_KEY=your_key_here
```

---

## Running the Simulation

### Single run (with GUI)
```bash
python run_sim.py --map small --strategy react --seed 42
```

### Full experimental suite (all 45 runs)
```bash
python run_experiments.py --maps small medium hard \
                          --strategies react cot reflexion \
                          --seeds 42 123 456 789 999
```

### Headless mode
```bash
python run_sim.py --map hard --strategy reflexion --seed 999 --no-gui
```

---

## LLM Configuration

### Gemini 2.5 Flash (default)
```python
GEMINI_CONFIG = {
    "model": "gemini-2.5-flash",
    "temperature": 0.1,
    "max_output_tokens": 1536,
}
```

### Groq (LLaMA 3.1 8B)
```python
GROQ_CONFIG = {
    "model": "llama-3.1-8b-instant",
    "temperature": 0.1,
    "max_completion_tokens": 1536,
    "response_format": {"type": "json_object"},
}
```

### Ollama (local)
```python
OLLAMA_CONFIG = {
    "model": "hermes3:8b",
    "host": "http://localhost:11434",
    "temperature": 0.1,
    "num_predict": 400,
}
```

---

## Action Schema

All LLM outputs must conform to this JSON schema:

```json
{
  "commands": [
    {
      "agent": "16",
      "action": "rescue_survivor",
      "target": [6, 8]
    }
  ],
  "strategy": "brief plan description"
}
```

Invalid JSON triggers automatic re-prompting with error details. ~85% of failures are recovered within one retry.

---

## Project Structure

```
crisissim/
├── agents/
│   ├── drone.py
│   ├── medic.py
│   └── truck.py
├── environment/
│   ├── world.py
│   ├── hospital.py
│   └── aftershock.py
├── planners/
│   ├── react.py
│   ├── cot.py
│   └── reflexion.py
├── maps/
│   ├── map_small.yaml
│   ├── map_medium.yaml
│   └── map_hard.yaml
├── gui/
│   └── dashboard.py
├── performance_config.py
├── run_sim.py
├── run_experiments.py
└── requirements.txt
```

---

## Key Design Decisions

- **Temperature 0.1** across all providers — prioritizes deterministic, valid JSON over creative variation
- **Schema enforcement** — invalid outputs re-prompted with error context; hallucinated agent IDs/positions caught by a validation pipeline (95% catch rate)
- **Token budget** — ~10,000 tokens per run; state summarization keeps context window manageable
- **Planning overhead** — LLM strategies add ~2–3 s per tick vs. rule-based baselines; acceptable given 20–40% rescue efficiency gains

---

## Limitations

- Computational overhead makes sub-second real-time deployment difficult without infrastructure investment
- Reflexion's learning benefits require multiple runs; less useful for novel, one-shot scenarios
- Occasional hallucinations (non-existent agent IDs, out-of-bounds coordinates) require robust post-processing
- API costs may be prohibitive for resource-constrained organizations at scale

---

## References

1. Yao et al. "ReAct: Synergizing Reasoning and Acting in Language Models." arXiv:2210.03629 (2022)
2. Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning." arXiv:2303.11366 (2023)
3. Wei et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." NeurIPS 35 (2022)
4. Kazil et al. "Mesa: An Agent-Based Modeling Framework." PSF (2020)