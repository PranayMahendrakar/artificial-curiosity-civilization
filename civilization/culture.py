"""
Cultural Evolution System — Societies, knowledge sharing, and civilizational milestones.

Societies form when agents cluster and trust each other.
Knowledge spreads through social networks, mutating and evolving.
Milestones track the civilization's collective progress.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from agents.agent import CuriosityAgent


# ─── Society ──────────────────────────────────────────────────────────────────
@dataclass
class Society:
    """A cluster of cooperating agents — the basic unit of civilization."""
    id: int
    name: str
    founding_tick: int
    founder_id: int
    member_ids: Set[int] = field(default_factory=set)
    home_x: int = 0
    home_y: int = 0

    # Collective knowledge pool
    collective_knowledge: Dict[str, float] = field(default_factory=dict)
    shared_tools: List[str] = field(default_factory=list)
    structures: List[str] = field(default_factory=list)

    # Cultural traits (0-1)
    cooperation_level: float = 0.5
    knowledge_sharing_rate: float = 0.3
    innovation_rate: float = 0.2

    # History
    events: List[Dict] = field(default_factory=list)
    peak_size: int = 0
    total_discoveries: int = 0
    dissolved: bool = False

    def add_member(self, agent_id: int):
        self.member_ids.add(agent_id)
        self.peak_size = max(self.peak_size, len(self.member_ids))

    def remove_member(self, agent_id: int):
        self.member_ids.discard(agent_id)

    def pool_knowledge(self, agents: List["CuriosityAgent"]):
        """Merge individual agent knowledge into the collective pool."""
        for agent in agents:
            if agent.id not in self.member_ids:
                continue
            for concept, node in agent.knowledge.items():
                existing = self.collective_knowledge.get(concept, 0)
                self.collective_knowledge[concept] = max(existing, node.confidence)

    def get_culture_score(self) -> float:
        """Overall cultural advancement score."""
        return (len(self.collective_knowledge) * 0.4 +
                len(self.shared_tools) * 2.0 +
                len(self.structures) * 3.0 +
                self.cooperation_level * 10)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "size": len(self.member_ids),
            "peak_size": self.peak_size,
            "founding_tick": self.founding_tick,
            "collective_knowledge_count": len(self.collective_knowledge),
            "shared_tools": self.shared_tools,
            "structures": self.structures,
            "culture_score": round(self.get_culture_score(), 2),
            "cooperation_level": round(self.cooperation_level, 3),
            "innovation_rate": round(self.innovation_rate, 3),
            "total_discoveries": self.total_discoveries,
            "dissolved": self.dissolved
        }


# ─── Civilization Milestone ───────────────────────────────────────────────────
@dataclass
class Milestone:
    name: str
    description: str
    tick_achieved: int
    society_id: Optional[int]
    agent_ids: List[int]
    category: str  # "knowledge", "tool", "social", "structure"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "tick": self.tick_achieved,
            "category": self.category,
            "agents": self.agent_ids
        }


# ─── Knowledge Mutation ───────────────────────────────────────────────────────
class KnowledgeMutator:
    """Simulates knowledge mutation as it spreads — concepts evolve via
       telephone-game effects, gaining or losing nuance over generations."""

    MUTATION_RATE = 0.05

    def __init__(self, rng: random.Random):
        self.rng = rng

    def mutate_concept(self, concept: str, confidence: float) -> tuple:
        """Apply small random mutation to a concept during transmission."""
        if self.rng.random() < self.MUTATION_RATE:
            suffixes = ["_refined", "_basic", "_advanced", "_applied", "_theoretical"]
            new_concept = concept + self.rng.choice(suffixes)
            new_confidence = confidence * self.rng.uniform(0.6, 1.1)
            return new_concept, new_confidence
        return concept, confidence


# ─── Cultural Evolution Engine ────────────────────────────────────────────────
class CultureEngine:
    """
    Manages society formation, cultural evolution, and civilization milestones.
    Each tick, societies can grow, merge, split, or dissolve.
    Knowledge diffuses through social networks with mutation.
    """

    PROXIMITY_RADIUS = 3
    MIN_SOCIETY_SIZE = 3
    SOCIETY_FORMATION_TRUST = 0.6

    MILESTONE_DEFS = [
        {"name": "First Fire", "condition": "combustion", "category": "knowledge",
         "description": "Agents discover the phenomenon of combustion"},
        {"name": "Stone Age", "condition": "tool_sharp_stone", "category": "tool",
         "description": "First stone tool crafted"},
        {"name": "First Society", "condition": "society_formed", "category": "social",
         "description": "First cooperative society emerges"},
        {"name": "First Shelter", "condition": "tool_wooden_shelter", "category": "structure",
         "description": "First permanent structure built"},
        {"name": "Metallurgy", "condition": "tool_metal_blade", "category": "tool",
         "description": "First metal blade forged"},
        {"name": "Written Knowledge", "condition": "tool_knowledge_tablet", "category": "tool",
         "description": "Knowledge preserved on stone tablets"},
        {"name": "Industrial Age", "condition": "tool_forge", "category": "tool",
         "description": "First forge built — mass tool production begins"},
        {"name": "Energy Harnessing", "condition": "tool_windmill", "category": "structure",
         "description": "Renewable energy harnessed through windmill"},
        {"name": "Polymath", "condition": "agent_knowledge_50", "category": "knowledge",
         "description": "An agent achieves mastery of 50 knowledge concepts"},
        {"name": "Great Teacher", "condition": "agent_shared_20", "category": "social",
         "description": "An agent shares knowledge 20 times"},
    ]

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.societies: Dict[int, Society] = {}
        self._society_counter = 0
        self.milestones: List[Milestone] = []
        self._milestone_achieved: Set[str] = set()
        self.mutator = KnowledgeMutator(rng)
        self.tick = 0

    # ─── Society Management ────────────────────────────────────────
    def _next_society_id(self) -> int:
        self._society_counter += 1
        return self._society_counter

    def _generate_name(self) -> str:
        prefixes = ["Az", "Kar", "Sun", "Eld", "Vor", "Nim", "Osh", "Tyr"]
        suffixes = ["ari", "ona", "eld", "ith", "orn", "ath", "est", "ia"]
        return self.rng.choice(prefixes) + self.rng.choice(suffixes)

    def attempt_society_formation(
        self,
        agents: List["CuriosityAgent"],
        agent_positions: Dict[int, tuple]
    ) -> Optional[Society]:
        """Try to form a new society from nearby mutually-trusting agents."""
        if len(agents) < self.MIN_SOCIETY_SIZE:
            return None

        unaffiliated = [a for a in agents if a.alive and a.society_id is None]
        if len(unaffiliated) < self.MIN_SOCIETY_SIZE:
            return None

        # Find cluster of unaffiliated agents
        seed = self.rng.choice(unaffiliated)
        sx, sy = agent_positions.get(seed.id, (seed.x, seed.y))
        nearby = [a for a in unaffiliated
                  if abs(agent_positions.get(a.id, (a.x, a.y))[0] - sx) <= self.PROXIMITY_RADIUS
                  and abs(agent_positions.get(a.id, (a.x, a.y))[1] - sy) <= self.PROXIMITY_RADIUS
                  and seed.trust.get(a.id, 0) >= self.SOCIETY_FORMATION_TRUST]

        if len(nearby) < self.MIN_SOCIETY_SIZE - 1:
            return None

        society_id = self._next_society_id()
        society = Society(
            id=society_id,
            name=self._generate_name(),
            founding_tick=self.tick,
            founder_id=seed.id,
            home_x=sx, home_y=sy
        )
        members = [seed] + nearby[:self.MIN_SOCIETY_SIZE - 1]
        for agent in members:
            society.add_member(agent.id)
            agent.society_id = society_id

        self.societies[society_id] = society
        self._check_milestone("society_formed", self.tick, society_id, [a.id for a in members])
        return society

    def dissolve_dead_societies(self, agents: Dict[int, "CuriosityAgent"]):
        """Remove societies with fewer than MIN_SOCIETY_SIZE living members."""
        for sid, society in list(self.societies.items()):
            living = [mid for mid in society.member_ids
                      if mid in agents and agents[mid].alive]
            society.member_ids = set(living)
            if len(living) < 2 and not society.dissolved:
                society.dissolved = True

    # ─── Knowledge Diffusion ───────────────────────────────────────
    def diffuse_knowledge_in_societies(
        self,
        agents: Dict[int, "CuriosityAgent"]
    ):
        """Spread knowledge within societies, with occasional mutation."""
        for society in self.societies.values():
            if society.dissolved:
                continue
            members = [agents[mid] for mid in society.member_ids
                       if mid in agents and agents[mid].alive]
            if len(members) < 2:
                continue

            # Pool collective knowledge
            society.pool_knowledge(members)

            # Randomly diffuse subset of collective knowledge to members
            diff_rate = society.knowledge_sharing_rate
            for agent in members:
                for concept, conf in list(society.collective_knowledge.items()):
                    if concept not in agent.knowledge and self.rng.random() < diff_rate * 0.1:
                        mutated_concept, mutated_conf = self.mutator.mutate_concept(concept, conf)
                        agent.observe(mutated_concept, mutated_conf, self.tick, "cultural_diffusion")

            # Increase cooperation over time
            society.cooperation_level = min(1.0, society.cooperation_level + 0.0005 * len(members))

    # ─── Milestone Tracking ────────────────────────────────────────
    def _check_milestone(
        self,
        condition: str,
        tick: int,
        society_id: Optional[int],
        agent_ids: List[int]
    ):
        if condition in self._milestone_achieved:
            return
        for mdef in self.MILESTONE_DEFS:
            if mdef["condition"] == condition and mdef["name"] not in self._milestone_achieved:
                milestone = Milestone(
                    name=mdef["name"],
                    description=mdef["description"],
                    tick_achieved=tick,
                    society_id=society_id,
                    agent_ids=agent_ids,
                    category=mdef["category"]
                )
                self.milestones.append(milestone)
                self._milestone_achieved.add(mdef["name"])
                break

    def notify_knowledge_discovered(self, concept: str, tick: int,
                                    agent_id: int, society_id: Optional[int]):
        self._check_milestone(concept, tick, society_id, [agent_id])

    def notify_tool_crafted(self, tool_name: str, tick: int,
                            agent_id: int, society_id: Optional[int]):
        self._check_milestone(f"tool_{tool_name}", tick, society_id, [agent_id])
        # Update society shared tools
        if society_id and society_id in self.societies:
            society = self.societies[society_id]
            if tool_name not in society.shared_tools:
                society.shared_tools.append(tool_name)

    def notify_structure_built(self, structure: str, tick: int,
                               agent_id: int, society_id: Optional[int]):
        if society_id and society_id in self.societies:
            society = self.societies[society_id]
            if structure not in society.structures:
                society.structures.append(structure)

    def check_agent_milestones(self, agent: "CuriosityAgent"):
        """Check per-agent milestone conditions."""
        if len(agent.knowledge) >= 50:
            self._check_milestone("agent_knowledge_50", self.tick, agent.society_id, [agent.id])
        if agent.knowledge_shared >= 20:
            self._check_milestone("agent_shared_20", self.tick, agent.society_id, [agent.id])

    # ─── Main Step ─────────────────────────────────────────────────
    def step(self, agents: Dict[int, "CuriosityAgent"],
             agent_positions: Dict[int, tuple]):
        self.tick += 1
        agent_list = list(agents.values())

        # Try to form new societies every 20 ticks
        if self.tick % 20 == 0:
            self.attempt_society_formation(agent_list, agent_positions)

        # Diffuse knowledge within societies
        self.diffuse_knowledge_in_societies(agents)

        # Clean up dissolved societies
        self.dissolve_dead_societies(agents)

        # Check agent milestones
        for agent in agent_list:
            if agent.alive:
                self.check_agent_milestones(agent)

    def get_civilization_stats(self) -> dict:
        active = [s for s in self.societies.values() if not s.dissolved]
        total_members = sum(len(s.member_ids) for s in active)
        return {
            "total_societies": len(self.societies),
            "active_societies": len(active),
            "total_society_members": total_members,
            "milestones_achieved": len(self.milestones),
            "milestones": [m.to_dict() for m in self.milestones],
            "societies": [s.to_dict() for s in active],
        }
