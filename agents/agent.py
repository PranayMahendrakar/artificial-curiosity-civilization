"""
Curiosity Agent — Core autonomous agent for the Artificial Curiosity Civilization.
Agents explore environments with intrinsic motivation (ICM-inspired curiosity),
build knowledge bases, improve skills, use tools, and teach each other.
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from collections import deque


@dataclass
class KnowledgeNode:
    """A single piece of discovered knowledge."""
    concept: str
    confidence: float = 0.5
    discovery_tick: int = 0
    source: str = "observation"
    connections: List[str] = field(default_factory=list)
    times_applied: int = 0

    def reinforce(self, amount: float = 0.05):
        self.confidence = min(1.0, self.confidence + amount)
        self.times_applied += 1

    def decay(self, rate: float = 0.001):
        self.confidence = max(0.0, self.confidence - rate)

    def to_dict(self) -> dict:
        return {"concept": self.concept, "confidence": round(self.confidence, 3),
                "source": self.source, "applied": self.times_applied}


@dataclass
class Memory:
    """Episodic memory entry."""
    tick: int
    event: str
    location: Tuple[int, int]
    reward: float
    novelty: float
    agents_present: List[int] = field(default_factory=list)


class AgentState(Enum):
    EXPLORING   = "exploring"
    GATHERING   = "gathering"
    CRAFTING    = "crafting"
    TEACHING    = "teaching"
    LEARNING    = "learning"
    RESTING     = "resting"
    SOCIALIZING = "socializing"
    BUILDING    = "building"


class CuriosityAgent:
    """
    Intrinsically motivated agent that builds knowledge through exploration.

    Core curiosity mechanism:
        novelty(cell) = spatial_novelty + resource_novelty + phenomenon_novelty
        action = softmax_sample(novelty_scores * personality_weights)
    """

    _id_counter = 0
    CURIOSITY_DECAY = 0.002
    NOVELTY_THRESHOLD = 0.2

    def __init__(self, x: int, y: int, seed: int = 0,
                 generation: int = 0, parent_id: Optional[int] = None):
        CuriosityAgent._id_counter += 1
        self.id = CuriosityAgent._id_counter
        self.x = x
        self.y = y
        self.generation = generation
        self.parent_id = parent_id
        self.rng = random.Random(seed + self.id)

        # Vitals
        self.energy: float = 80.0 + self.rng.uniform(-10, 10)
        self.age: int = 0
        self.lifespan: int = self.rng.randint(300, 600)
        self.alive: bool = True

        # Personality traits (0-1, Beta-distributed for diversity)
        self.curiosity_trait: float = self.rng.betavariate(2, 2)
        self.sociability:     float = self.rng.betavariate(2, 2)
        self.creativity:      float = self.rng.betavariate(2, 2)
        self.patience:        float = self.rng.betavariate(2, 2)

        # State machine
        self.state: AgentState = AgentState.EXPLORING
        self.current_curiosity: float = self.curiosity_trait

        # Knowledge base (concept -> KnowledgeNode)
        self.knowledge: Dict[str, KnowledgeNode] = {}
        self.memory: deque = deque(maxlen=200)
        self.visited_cells: Dict[Tuple[int, int], int] = {}
        self.inventory: Dict[str, float] = {}

        # Skills (0-1, improve with practice)
        self.skills: Dict[str, float] = {
            "exploration": self.rng.uniform(0.1, 0.4),
            "crafting":    self.rng.uniform(0.0, 0.3),
            "teaching":    self.rng.uniform(0.1, 0.3),
            "building":    self.rng.uniform(0.0, 0.3),
            "gathering":   self.rng.uniform(0.1, 0.4),
            "science":     self.rng.uniform(0.0, 0.2),
            "cooperation": self.rng.uniform(0.1, 0.4),
        }

        # Social graph
        self.known_agents: Set[int] = set()
        self.trust: Dict[int, float] = {}
        self.society_id: Optional[int] = None

        # Cumulative stats
        self.discoveries: int = 0
        self.tools_created: int = 0
        self.structures_built: int = 0
        self.knowledge_shared: int = 0
        self.total_reward: float = 0.0
        self.children: List[int] = []

    # ─── Curiosity & Novelty ──────────────────────────────────────────
    def novelty_of(self, cell_key: Tuple[int, int],
                   cell_resources: dict, cell_phenomena: set) -> float:
        visit_count = self.visited_cells.get(cell_key, 0)
        spatial_novelty = 1.0 / (1.0 + math.log1p(visit_count))

        unknown_resources = sum(1 for r in cell_resources if r not in self.knowledge)
        resource_novelty = min(1.0, unknown_resources * 0.3)

        unknown_phenomena = sum(1 for p in cell_phenomena if p not in self.knowledge)
        phenomenon_novelty = min(1.0, unknown_phenomena * 0.5)

        raw = (spatial_novelty * 0.4 + resource_novelty * 0.35 + phenomenon_novelty * 0.25)
        return raw * self.curiosity_trait

    def update_curiosity(self, novelty: float):
        self.current_curiosity = min(
            1.0,
            self.current_curiosity * (1 - self.CURIOSITY_DECAY) + novelty * 0.3
        )

    # ─── Learning ──────────────────────────────────────────────────
    def observe(self, observation: str, confidence: float,
                tick: int, source: str = "observation") -> bool:
        """Observe and record knowledge. Returns True if new discovery."""
        if observation in self.knowledge:
            self.knowledge[observation].reinforce()
            return False
        self.knowledge[observation] = KnowledgeNode(
            concept=observation,
            confidence=confidence * (0.7 + 0.3 * self.skills["science"]),
            discovery_tick=tick,
            source=source
        )
        self.discoveries += 1
        return True

    def learn_from_agent(self, teacher: CuriosityAgent, tick: int) -> List[str]:
        """Social learning: receive knowledge from a teacher agent."""
        if not teacher.knowledge:
            return []
        trust_factor = self.trust.get(teacher.id, 0.5)
        shareable = [k for k, v in teacher.knowledge.items()
                     if v.confidence > 0.4 and k not in self.knowledge]
        n_share = max(1, int(len(shareable) * 0.2 * trust_factor))
        to_share = self.rng.sample(shareable, min(n_share, len(shareable)))
        gained = []
        for concept in to_share:
            node = teacher.knowledge[concept]
            self.knowledge[concept] = KnowledgeNode(
                concept=concept,
                confidence=node.confidence * trust_factor * 0.8,
                discovery_tick=tick,
                source=f"teacher_{teacher.id}"
            )
            gained.append(concept)
            teacher.knowledge_shared += 1
        self.trust[teacher.id] = min(1.0, trust_factor + 0.05)
        teacher.trust[self.id] = min(1.0, teacher.trust.get(self.id, 0.5) + 0.05)
        return gained

    def improve_skill(self, skill: str, amount: float = 0.01):
        if skill in self.skills:
            current = self.skills[skill]
            self.skills[skill] = min(1.0, current + amount * (1 - current))

    # ─── Inventory ─────────────────────────────────────────────────
    def pickup(self, item: str, amount: float):
        self.inventory[item] = self.inventory.get(item, 0) + amount

    def has_items(self, items: Dict[str, float]) -> bool:
        return all(self.inventory.get(k, 0) >= v for k, v in items.items())

    def consume_items(self, items: Dict[str, float]):
        for k, v in items.items():
            self.inventory[k] = max(0, self.inventory.get(k, 0) - v)

    # ─── Decision Making ───────────────────────────────────────────
    def decide_state(self, neighbors_occupied: bool, can_craft: bool) -> AgentState:
        """Behavioral state selection based on needs and curiosity."""
        if self.energy < 15:
            return AgentState.RESTING
        if can_craft and self.creativity > 0.5 and self.rng.random() < 0.25:
            return AgentState.CRAFTING
        if neighbors_occupied and self.sociability > 0.4 and self.rng.random() < 0.3:
            if self.knowledge and self.rng.random() < self.skills["teaching"]:
                return AgentState.TEACHING
            return AgentState.SOCIALIZING
        total_items = sum(self.inventory.values())
        if total_items > 20 and self.rng.random() < self.skills["building"]  * 0.5:
            return AgentState.BUILDING
        if self.current_curiosity > self.NOVELTY_THRESHOLD:
            return AgentState.EXPLORING
        return AgentState.GATHERING

    def choose_move(self, valid_positions: List[Tuple[int, int]],
                    novelty_scores: Dict[Tuple[int, int], float]) -> Tuple[int, int]:
        """Softmax-weighted curiosity-driven movement."""
        if not valid_positions:
            return (self.x, self.y)
        scores = [novelty_scores.get(pos, 0.1) + 0.01 for pos in valid_positions]
        temp = 0.5 + (1 - self.curiosity_trait) * 0.5
        max_s = max(scores)
        exp_s = [math.exp((s - max_s) / temp) for s in scores]
        total = sum(exp_s)
        probs = [e / total for e in exp_s]
        r = self.rng.random()
        cumulative = 0.0
        for pos, prob in zip(valid_positions, probs):
            cumulative += prob
            if r <= cumulative:
                return pos
        return valid_positions[-1]

    # ─── Vitals ────────────────────────────────────────────────────
    def step_vitals(self):
        self.age += 1
        cost_map = {
            AgentState.RESTING:    -2.5,
            AgentState.EXPLORING:   0.5,
            AgentState.GATHERING:   0.4,
            AgentState.CRAFTING:    1.2,
            AgentState.TEACHING:    0.5,
            AgentState.LEARNING:    0.3,
            AgentState.SOCIALIZING: 0.2,
            AgentState.BUILDING:    1.5,
        }
        cost = cost_map.get(self.state, 0.5)
        self.energy = max(0.0, min(100.0, self.energy - cost))

        # Eat from inventory
        food = self.inventory.get("food", 0)
        if food > 0 and self.energy < 70:
            eat = min(food, 5.0)
            self.energy = min(100, self.energy + eat * 1.5)
            self.inventory["food"] = food - eat

        # Knowledge decay (forgetting curve)
        for node in self.knowledge.values():
            node.decay(0.0005)

        if self.energy <= 0 or self.age >= self.lifespan:
            self.alive = False

    def mark_visited(self, x: int, y: int):
        key = (x, y)
        self.visited_cells[key] = self.visited_cells.get(key, 0) + 1

    def record_memory(self, event: str, reward: float, novelty: float, others: list = None):
        self.memory.append(Memory(tick=self.age, event=event, location=(self.x, self.y),
                                  reward=reward, novelty=novelty, agents_present=others or []))
        self.total_reward += reward

    # ─── Stats ─────────────────────────────────────────────────────
    def knowledge_score(self) -> float:
        return sum(n.confidence for n in self.knowledge.values())

    def exploration_coverage(self) -> int:
        return len(self.visited_cells)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pos": [self.x, self.y],
            "generation": self.generation,
            "age": self.age,
            "lifespan": self.lifespan,
            "energy": round(self.energy, 1),
            "alive": self.alive,
            "state": self.state.value,
            "curiosity": round(self.current_curiosity, 3),
            "knowledge_count": len(self.knowledge),
            "knowledge_score": round(self.knowledge_score(), 2),
            "exploration_coverage": self.exploration_coverage(),
            "skills": {k: round(v, 3) for k, v in self.skills.items()},
            "inventory": {k: round(v, 1) for k, v in self.inventory.items() if v > 0.01},
            "discoveries": self.discoveries,
            "tools_created": self.tools_created,
            "structures_built": self.structures_built,
            "knowledge_shared": self.knowledge_shared,
            "total_reward": round(self.total_reward, 2),
            "children": self.children,
            "society_id": self.society_id,
            "known_agents": list(self.known_agents),
            "personality": {
                "curiosity_trait": round(self.curiosity_trait, 2),
                "sociability":     round(self.sociability, 2),
                "creativity":      round(self.creativity, 2),
                "patience":        round(self.patience, 2),
            }
        }
