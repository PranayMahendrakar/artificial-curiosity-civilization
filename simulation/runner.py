"""
simulation/runner.py

Main simulation orchestrator for the Artificial Curiosity Civilization.
Ties together World, CuriosityAgents, ToolCrafter, and CultureEngine
into a single step-based simulation loop with serializable state.
"""

from __future__ import annotations

import random
import time
import json
import copy
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

from engine.world import World, Cell, Biome, ResourceType
from agents.agent import CuriosityAgent, AgentAction
from agents.tools import ToolCrafter, ToolInstance
from civilization.culture import CultureEngine, Society


# ---------------------------------------------------------------------------
# Data containers for telemetry
# ---------------------------------------------------------------------------

@dataclass
class TickStats:
    """Statistics snapshot for a single simulation tick."""
    tick: int
    num_agents: int
    avg_curiosity: float
    avg_knowledge: float
    avg_energy: float
    tools_crafted: int
    discoveries: int
    milestone_count: int
    society_count: int
    total_resources: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationConfig:
    """Tunable hyper-parameters for the simulation."""
    # World
    world_width: int = 40
    world_height: int = 30
    seed: int = 42

    # Population
    initial_agents: int = 12
    max_agents: int = 80
    spawn_energy_threshold: float = 80.0
    spawn_probability: float = 0.04
    death_energy_threshold: float = 5.0

    # Dynamics
    energy_decay_per_tick: float = 0.8
    resource_regen_interval: int = 10
    culture_sync_interval: int = 5
    milestone_broadcast_radius: int = 8

    # Time
    max_ticks: int = 2000
    history_window: int = 500


# ---------------------------------------------------------------------------
# Simulation class
# ---------------------------------------------------------------------------

class Simulation:
    """
    Top-level simulation controller.

    Usage
    -----
    >>> sim = Simulation(SimulationConfig(seed=7))
    >>> sim.run(200)          # run 200 ticks
    >>> state = sim.get_state()
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self._rng = random.Random(self.config.seed)

        # Core subsystems
        self.world = World(
            width=self.config.world_width,
            height=self.config.world_height,
            seed=self.config.seed,
        )
        self.culture_engine = CultureEngine()

        # Agent registry
        self.agents: Dict[str, CuriosityAgent] = {}
        self._next_agent_id = 0

        # Time-series history (ring-buffer)
        self.history: deque[TickStats] = deque(maxlen=self.config.history_window)

        # Global counters
        self.tick: int = 0
        self.total_tools_crafted: int = 0
        self.total_discoveries: int = 0
        self.event_log: List[str] = []

        # Seed initial population
        self._spawn_initial_agents()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _spawn_initial_agents(self) -> None:
        """Place the founding agents at random walkable cells."""
        walkable = [
            (x, y)
            for y in range(self.config.world_height)
            for x in range(self.config.world_width)
            if self.world.grid[y][x].biome != Biome.OCEAN
        ]
        positions = self._rng.sample(walkable, min(self.config.initial_agents, len(walkable)))
        for pos in positions:
            self._create_agent(pos)

    def _create_agent(self, position: Tuple[int, int], parent: Optional[CuriosityAgent] = None) -> CuriosityAgent:
        """Instantiate a new agent and register it."""
        agent_id = f"A{self._next_agent_id:04d}"
        self._next_agent_id += 1
        agent = CuriosityAgent(
            agent_id=agent_id,
            position=list(position),
            world_width=self.config.world_width,
            world_height=self.config.world_height,
        )
        if parent is not None:
            # Inherit a fraction of parent knowledge
            for k, v in list(parent.knowledge_base.items())[:5]:
                agent.knowledge_base[k] = v * 0.6
        self.agents[agent_id] = agent
        return agent

    # ------------------------------------------------------------------
    # Core step logic
    # ------------------------------------------------------------------

    def step(self) -> TickStats:
        """Advance the simulation by one tick and return statistics."""
        self.tick += 1
        discoveries_this_tick = 0
        tools_this_tick = 0

        # --- Shuffle agent order for fairness ---
        agent_list = list(self.agents.values())
        self._rng.shuffle(agent_list)

        dead_ids: List[str] = []

        for agent in agent_list:
            if agent.energy <= self.config.death_energy_threshold:
                dead_ids.append(agent.agent_id)
                continue

            # Energy decay
            agent.energy -= self.config.energy_decay_per_tick

            # --- Agent decision ---
            nearby_agents = self._get_nearby_agents(agent, radius=3)
            cell = self.world.grid[agent.position[1]][agent.position[0]]
            action = agent.decide(cell, nearby_agents)

            # --- Execute action ---
            discoveries_this_tick += self._execute_action(agent, action, cell, nearby_agents)

            # --- Tool crafting opportunity ---
            if self._rng.random() < 0.08 and agent.energy > 40:
                tool = ToolCrafter.attempt_craft(agent, cell)
                if tool:
                    agent.inventory.append(tool)
                    tools_this_tick += 1
                    self.total_tools_crafted += 1
                    self._log(f"{agent.agent_id} crafted {tool.name} at tick {self.tick}")

        # --- Reap dead agents ---
        for aid in dead_ids:
            self._log(f"{aid} perished at tick {self.tick}")
            del self.agents[aid]

        # --- Spawning ---
        if len(self.agents) < self.config.max_agents:
            self._maybe_spawn()

        # --- World regeneration ---
        if self.tick % self.config.resource_regen_interval == 0:
            self.world.regenerate_resources()

        # --- Culture sync ---
        if self.tick % self.config.culture_sync_interval == 0:
            self._sync_culture()

        self.total_discoveries += discoveries_this_tick

        # --- Snapshot stats ---
        stats = self._snapshot(discoveries_this_tick)
        self.history.append(stats)
        return stats

    def _execute_action(self, agent: CuriosityAgent, action: AgentAction,
                        cell: Cell, nearby_agents: List[CuriosityAgent]) -> int:
        """Carry out the chosen action and return number of new discoveries."""
        discoveries = 0

        if action == AgentAction.EXPLORE:
            # Move to an adjacent cell
            nx, ny = self._random_step(agent)
            target_cell = self.world.grid[ny][nx]
            if target_cell.biome != Biome.OCEAN:
                agent.position = [nx, ny]
                novelty = agent.perceive(target_cell)
                if novelty > 0.5:
                    discoveries += 1
                    self.total_discoveries += 0  # counted upstream

        elif action == AgentAction.FORAGE:
            # Harvest food/water from cell
            gained = self.world.harvest(agent.position[0], agent.position[1], agent)
            agent.energy = min(100.0, agent.energy + gained)

        elif action == AgentAction.STUDY:
            # Deep observation — big curiosity reward
            agent.study(cell)
            discoveries += 1

        elif action == AgentAction.SHARE:
            # Knowledge transfer to a nearby agent
            if nearby_agents:
                partner = self._rng.choice(nearby_agents)
                agent.share_knowledge(partner)

        elif action == AgentAction.REST:
            agent.energy = min(100.0, agent.energy + 5.0)

        elif action == AgentAction.MIGRATE:
            # Larger move
            dx = self._rng.randint(-4, 4)
            dy = self._rng.randint(-4, 4)
            nx = max(0, min(self.config.world_width - 1, agent.position[0] + dx))
            ny = max(0, min(self.config.world_height - 1, agent.position[1] + dy))
            if self.world.grid[ny][nx].biome != Biome.OCEAN:
                agent.position = [nx, ny]

        return discoveries

    def _random_step(self, agent: CuriosityAgent) -> Tuple[int, int]:
        """Return a valid adjacent cell coordinate."""
        dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        self._rng.shuffle(dirs)
        for dx, dy in dirs:
            nx = agent.position[0] + dx
            ny = agent.position[1] + dy
            if 0 <= nx < self.config.world_width and 0 <= ny < self.config.world_height:
                return nx, ny
        return agent.position[0], agent.position[1]

    def _get_nearby_agents(self, agent: CuriosityAgent, radius: int) -> List[CuriosityAgent]:
        """Return agents within Manhattan distance radius (excluding self)."""
        ax, ay = agent.position
        return [
            a for a in self.agents.values()
            if a.agent_id != agent.agent_id
            and abs(a.position[0] - ax) + abs(a.position[1] - ay) <= radius
        ]

    def _maybe_spawn(self) -> None:
        """Potentially reproduce a high-energy agent."""
        candidates = [
            a for a in self.agents.values()
            if a.energy >= self.config.spawn_energy_threshold
        ]
        if candidates and self._rng.random() < self.config.spawn_probability:
            parent = self._rng.choice(candidates)
            parent.energy -= 30.0
            child_pos = self._random_step(parent)
            child = self._create_agent(child_pos, parent=parent)
            self._log(f"{child.agent_id} born from {parent.agent_id} at tick {self.tick}")

    def _sync_culture(self) -> None:
        """Update the culture engine with current agent population."""
        self.culture_engine.update(list(self.agents.values()), self.tick)

    # ------------------------------------------------------------------
    # Batch run
    # ------------------------------------------------------------------

    def run(self, ticks: int = 100, verbose: bool = False) -> List[TickStats]:
        """Run the simulation for *ticks* steps, returning all stats."""
        results: List[TickStats] = []
        for _ in range(ticks):
            if len(self.agents) == 0:
                self._log("All agents perished — resetting population.")
                self._spawn_initial_agents()
            stats = self.step()
            results.append(stats)
            if verbose and self.tick % 50 == 0:
                print(f"Tick {self.tick:4d} | Agents: {stats.num_agents:3d} | "
                      f"Curiosity: {stats.avg_curiosity:.2f} | "
                      f"Knowledge: {stats.avg_knowledge:.2f} | "
                      f"Milestones: {stats.milestone_count}")
        return results

    # ------------------------------------------------------------------
    # State serialisation
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the simulation state."""
        return {
            "tick": self.tick,
            "config": asdict(self.config),
            "agents": [
                {
                    "id": a.agent_id,
                    "position": a.position,
                    "energy": round(a.energy, 2),
                    "curiosity": round(a.curiosity_level, 2),
                    "knowledge_count": len(a.knowledge_base),
                    "tool_count": len(a.inventory),
                    "skills": list(a.skills.keys()),
                }
                for a in self.agents.values()
            ],
            "history": [s.to_dict() for s in self.history],
            "event_log": self.event_log[-100:],
            "culture": {
                "societies": len(self.culture_engine.societies),
                "milestones": len(self.culture_engine.milestones),
                "milestone_names": [m.name for m in self.culture_engine.milestones[-10:]],
            },
            "totals": {
                "tools_crafted": self.total_tools_crafted,
                "discoveries": self.total_discoveries,
            },
            "world_summary": self.world.get_summary() if hasattr(self.world, "get_summary") else {},
        }

    def get_history_dataframe_data(self) -> Dict[str, List]:",
        """Return history as column-oriented dict (easy to feed into pandas/plotly)."""
        cols: Dict[str, List] = defaultdict(list)
        for s in self.history:
            d = s.to_dict()
            for k, v in d.items():
                cols[k].append(v)
        return dict(cols)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        self.event_log.append(msg)
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-800:]

    def _snapshot(self, discoveries_this_tick: int) -> TickStats:
        """Compute a TickStats for the current tick."""
        agents = list(self.agents.values())
        n = len(agents)
        if n == 0:
            return TickStats(
                tick=self.tick, num_agents=0,
                avg_curiosity=0.0, avg_knowledge=0.0, avg_energy=0.0,
                tools_crafted=self.total_tools_crafted,
                discoveries=self.total_discoveries,
                milestone_count=len(self.culture_engine.milestones),
                society_count=len(self.culture_engine.societies),
                total_resources=self.world.count_resources(),
            )
        return TickStats(
            tick=self.tick,
            num_agents=n,
            avg_curiosity=sum(a.curiosity_level for a in agents) / n,
            avg_knowledge=sum(len(a.knowledge_base) for a in agents) / n,
            avg_energy=sum(a.energy for a in agents) / n,
            tools_crafted=self.total_tools_crafted,
            discoveries=self.total_discoveries,
            milestone_count=len(self.culture_engine.milestones),
            society_count=len(self.culture_engine.societies),
            total_resources=self.world.count_resources(),
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Artificial Curiosity Civilization simulation.")
    parser.add_argument("--ticks", type=int, default=500, help="Number of simulation ticks")
    parser.add_argument("--agents", type=int, default=12, help="Initial agent count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--width", type=int, default=40, help="World width")
    parser.add_argument("--height", type=int, default=30, help="World height")
    parser.add_argument("--output", type=str, default=None, help="Save final state to JSON file")
    args = parser.parse_args()

    cfg = SimulationConfig(
        seed=args.seed,
        world_width=args.width,
        world_height=args.height,
        initial_agents=args.agents,
        max_ticks=args.ticks,
    )

    print(f"Starting simulation: {args.ticks} ticks, {args.agents} agents, seed={args.seed}")
    start = time.time()
    sim = Simulation(cfg)
    sim.run(args.ticks, verbose=True)
    elapsed = time.time() - start

    print(f"\nSimulation complete in {elapsed:.1f}s")
    final = sim.get_state()
    print(f"Final agents: {final['totals']}")
    print(f"Culture: {final['culture']}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(final, f, indent=2)
        print(f"State saved to {args.output}")
