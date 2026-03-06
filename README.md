<div align="center">

# 🧠 Artificial Curiosity Civilization

**An artificial life simulation where AI agents evolve knowledge through curiosity,**
**explore environments, invent tools, cooperate, and build an emergent civilization.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![ALife](https://img.shields.io/badge/Research-Artificial%20Life-purple)](https://alife.org)

</div>

---

## 🌍 Overview

Artificial Curiosity Civilization is an agent-based simulation inspired by Artificial Life research.
Agents are equipped with an **intrinsic curiosity drive** — they prefer to explore novel states,
discover physics, craft tools, and share knowledge with peers.
Over time, societies form, culture evolves, and civilizational milestones emerge organically.

> *"Intelligence is not just solving problems — it is being relentlessly drawn to interesting ones."*

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗺 **Procedural World** | Multi-biome terrain with dynamic resources, temperature, elevation, phenomena |
| 🧬 **Curiosity-Driven Agents** | ICM-inspired intrinsic motivation, novelty detection, knowledge base growth |
| 🔧 **Tool Creation** | 4-tier tool catalog; agents discover and craft tools from environmental resources |
| 🤝 **Cooperation** | Knowledge sharing, joint exploration, coalition formation |
| 🏛 **Cultural Evolution** | Societies, milestones, knowledge mutation, cross-generational inheritance |
| 📊 **Live Dashboard** | Streamlit app with world map, time-series metrics, agent table, event log |
| 💾 **State Export** | Full JSON serialization of the simulation state at any tick |

---

## 🏗 Architecture

```
artificial-curiosity-civilization/
├── engine/
│   └── world.py          # World, Cell, Biome, ResourceType, PhysicsEngine
├── agents/
│   ├── agent.py          # CuriosityAgent — curiosity, knowledge base, skills
│   └── tools.py          # ToolCrafter, TOOL_CATALOG (16 tools, 4 tiers)
├── civilization/
│   └── culture.py        # CultureEngine, Society, Milestone, KnowledgeMutator
├── simulation/
│   └── runner.py         # Simulation orchestrator — step(), run(), get_state()
├── app.py                # Streamlit visualization dashboard
└── requirements.txt
```

### Component Relationships

```
Simulation (runner.py)
  ├── World (engine/world.py)
  │     ├── Grid of Cells with Biomes
  │     ├── Resource management
  │     └── PhysicsEngine (phenomena)
  ├── CuriosityAgents[] (agents/agent.py)
  │     ├── Intrinsic curiosity score
  │     ├── Knowledge base dict
  │     ├── Inventory of ToolInstances
  │     └── decide() → AgentAction
  ├── ToolCrafter (agents/tools.py)
  │     └── attempt_craft(agent, cell) → ToolInstance?
  └── CultureEngine (civilization/culture.py)
        ├── Society formation
        ├── Milestone detection
        └── Knowledge mutation & inheritance
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/PranayMahendrakar/artificial-curiosity-civilization.git
cd artificial-curiosity-civilization
pip install -r requirements.txt
```

### 2. Launch the Dashboard

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### 3. Run CLI Simulation

```bash
python -m simulation.runner --ticks 500 --agents 20 --seed 42 --output state.json
```

---

## 🧬 Agent Design

Each `CuriosityAgent` has:

- **Curiosity Level** — continuously updated based on information gain vs prediction error
- **Knowledge Base** — a dictionary of discovered facts, weighted by confidence
- **Skill System** — agents develop specialised skills (foraging, exploration, crafting, diplomacy)
- **Inventory** — crafted tools that boost efficiency or unlock new actions
- **Decision Engine** — weighs actions by expected curiosity reward + survival needs

### Action Space

| Action | Effect |
|--------|--------|
| `EXPLORE` | Move to adjacent cell, gain novelty reward |
| `FORAGE` | Harvest resources, restore energy |
| `STUDY` | Deep observation, big knowledge gain |
| `SHARE` | Transfer knowledge to nearby agent |
| `REST` | Recover energy |
| `MIGRATE` | Large-distance relocation |

---

## 🔧 Tool System

Tools are organized in **4 discovery tiers**:

| Tier | Examples | Requirements |
|------|----------|--------------|
| 1 — Primitive | Stone Blade, Torch, Basket | Basic resources (stone, wood) |
| 2 — Crafted | Bow, Kiln, Compass | Tier-1 tools + more resources |
| 3 — Advanced | Smelter, Loom, Aqueduct | Tier-2 mastery + cooperation |
| 4 — Civilizational | Observatory, Library, Computing Engine | Full society + milestones |

---

## 🏛 Cultural Evolution

The `CultureEngine` tracks:

- **Societies** — groups of nearby agents that share knowledge and norms
- **Milestones** — automatic detection of civilizational achievements (e.g. *"First Fire"*, *"Written Language"*)
- **Knowledge Mutation** — accumulated knowledge drifts and recombines across generations
- **Inheritance** — offspring agents inherit a fraction of parent knowledge and skills

---

## 📊 Dashboard

The Streamlit dashboard provides:

- **World Map** — biome heatmap with live agent positions, colour-coded by curiosity
- **Metrics Panel** — tick count, agent population, discoveries, tools crafted, milestones, societies
- **Time-Series Charts** — agents, curiosity, knowledge, and energy over time
- **Cultural Progress** — milestone and tool discovery timelines
- **Agent Details Table** — sortable agent stats
- **Event Log** — timestamped simulation events
- **Export** — download full simulation state as JSON

---

## ⚙️ Configuration

Tune simulation parameters via `SimulationConfig`:

```python
from simulation.runner import Simulation, SimulationConfig

cfg = SimulationConfig(
    world_width=50,
    world_height=40,
    seed=123,
    initial_agents=20,
    max_agents=100,
    spawn_probability=0.05,
    energy_decay_per_tick=0.6,
    culture_sync_interval=3,
)
sim = Simulation(cfg)
sim.run(1000, verbose=True)
```

---

## 🔬 Research Context

This project draws on several active research areas:

- **Intrinsic Motivation / ICM** — [Pathak et al., 2017](https://arxiv.org/abs/1705.05363): Curiosity-driven Exploration by Self-Supervised Prediction
- **Artificial Life** — [Langton, 1986](https://www.sciencedirect.com/science/article/pii/0167278987900422): Studying life-as-it-could-be
- **Cultural Evolution** — [Henrich, 2016](https://press.princeton.edu/books/paperback/9780691175959/the-secret-of-our-success): Cumulative cultural learning in human societies
- **Emergent Complexity** — [Holland, 1995](https://www.amazon.com/Hidden-Order-Adaptation-Helix-Book/dp/0201407930): Hidden Order — How Adaptation Builds Complexity

---

## 🗺 Roadmap

- [ ] Neural network curiosity model (replacing heuristic)
- [ ] Genetic algorithm for agent brain evolution
- [ ] Inter-civilization conflict and diplomacy
- [ ] Language emergence via symbol grounding
- [ ] 3D world rendering with Three.js
- [ ] Multi-GPU parallel simulation

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Made with 🧠 curiosity and ❤️ by <a href="https://github.com/PranayMahendrakar">PranayMahendrakar</a>
</div>
