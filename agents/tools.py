"""
Tool Creation System — Agents discover and craft tools from environmental resources.

Tool discovery follows a prerequisite graph: basic tools unlock advanced ones.
Tools improve agent efficiency and open new interaction possibilities.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import CuriosityAgent


@dataclass
class Tool:
    """A craftable tool with effects and prerequisites."""
    name: str
    description: str
    tier: int
    recipe: Dict[str, float]          # {resource: amount} required
    knowledge_prerequisites: List[str] # knowledge concepts needed
    tool_prerequisites: List[str]      # other tools needed to craft this
    effects: Dict[str, float]          # {skill_bonus: amount}
    durability: float = 100.0
    uses: int = 0

    def use(self) -> bool:
        """Use the tool, reducing durability. Returns False if broken."""
        self.uses += 1
        self.durability -= 2.0
        return self.durability > 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tier": self.tier,
            "description": self.description,
            "durability": round(self.durability, 1),
            "uses": self.uses,
            "effects": self.effects
        }


# ─── Tool Registry ────────────────────────────────────────────────────────────
TOOL_CATALOG: Dict[str, dict] = {
    # Tier 1 — Primitive
    "sharp_stone": {
        "description": "A sharp-edged stone for cutting",
        "tier": 1,
        "recipe": {"stone": 1.0},
        "knowledge_prerequisites": ["stone"],
        "tool_prerequisites": [],
        "effects": {"gathering": 0.1, "crafting": 0.05}
    },
    "wooden_club": {
        "description": "A heavy club for breaking rocks",
        "tier": 1,
        "recipe": {"wood": 2.0},
        "knowledge_prerequisites": ["wood"],
        "tool_prerequisites": [],
        "effects": {"gathering": 0.08, "building": 0.05}
    },
    "fire_stick": {
        "description": "A stick for starting fire",
        "tier": 1,
        "recipe": {"wood": 1.0},
        "knowledge_prerequisites": ["wood", "combustion"],
        "tool_prerequisites": [],
        "effects": {"crafting": 0.1, "science": 0.05}
    },
    "water_vessel": {
        "description": "A clay vessel for storing water",
        "tier": 1,
        "recipe": {"soil": 2.0, "water": 0.5},
        "knowledge_prerequisites": ["water", "soil"],
        "tool_prerequisites": [],
        "effects": {"gathering": 0.15}
    },

    # Tier 2 — Intermediate
    "stone_axe": {
        "description": "Sharp stone axe for cutting wood efficiently",
        "tier": 2,
        "recipe": {"stone": 2.0, "wood": 1.0},
        "knowledge_prerequisites": ["stone", "wood", "gravity"],
        "tool_prerequisites": ["sharp_stone"],
        "effects": {"gathering": 0.25, "building": 0.15}
    },
    "fire_torch": {
        "description": "A burning torch that reveals hidden resources",
        "tier": 2,
        "recipe": {"wood": 1.5, "fire": 0.5},
        "knowledge_prerequisites": ["combustion", "wood"],
        "tool_prerequisites": ["fire_stick"],
        "effects": {"exploration": 0.2, "science": 0.1}
    },
    "woven_basket": {
        "description": "Increases carrying capacity significantly",
        "tier": 2,
        "recipe": {"wood": 3.0},
        "knowledge_prerequisites": ["wood", "fermentation"],
        "tool_prerequisites": ["sharp_stone"],
        "effects": {"gathering": 0.3, "cooperation": 0.1}
    },
    "digging_stick": {
        "description": "For extracting root foods and soil",
        "tier": 2,
        "recipe": {"wood": 2.0, "stone": 0.5},
        "knowledge_prerequisites": ["soil", "food"],
        "tool_prerequisites": ["sharp_stone"],
        "effects": {"gathering": 0.2, "science": 0.05}
    },

    # Tier 3 — Advanced
    "metal_blade": {
        "description": "A sharp metal blade — foundation of metallurgy",
        "tier": 3,
        "recipe": {"metal": 2.0, "stone": 1.0, "fire": 1.0},
        "knowledge_prerequisites": ["metal", "combustion", "magnetism"],
        "tool_prerequisites": ["fire_torch", "stone_axe"],
        "effects": {"crafting": 0.4, "gathering": 0.3, "science": 0.15}
    },
    "crystal_lens": {
        "description": "Focuses light — enables observation and fire-starting",
        "tier": 3,
        "recipe": {"crystal": 1.5, "stone": 0.5},
        "knowledge_prerequisites": ["crystal", "electricity", "pressure"],
        "tool_prerequisites": ["sharp_stone"],
        "effects": {"science": 0.4, "exploration": 0.2}
    },
    "wooden_shelter": {
        "description": "A permanent structure for protection and community",
        "tier": 3,
        "recipe": {"wood": 8.0, "stone": 3.0},
        "knowledge_prerequisites": ["wood", "stone", "gravity", "erosion"],
        "tool_prerequisites": ["stone_axe", "wooden_club"],
        "effects": {"building": 0.5, "cooperation": 0.3, "teaching": 0.2}
    },
    "knowledge_tablet": {
        "description": "A stone tablet for recording knowledge — enables libraries",
        "tier": 3,
        "recipe": {"stone": 2.0, "crystal": 0.5},
        "knowledge_prerequisites": ["stone", "echo", "pressure"],
        "tool_prerequisites": ["sharp_stone", "crystal_lens"],
        "effects": {"teaching": 0.6, "science": 0.3, "cooperation": 0.2}
    },

    # Tier 4 — Civilization-level
    "forge": {
        "description": "A metal forge — enables mass production of tools",
        "tier": 4,
        "recipe": {"stone": 10.0, "metal": 5.0, "fire": 3.0},
        "knowledge_prerequisites": ["metal", "combustion", "magnetism", "electricity"],
        "tool_prerequisites": ["metal_blade", "wooden_shelter"],
        "effects": {"crafting": 0.8, "science": 0.4, "building": 0.5}
    },
    "windmill": {
        "description": "Captures wind energy — first renewable energy source",
        "tier": 4,
        "recipe": {"wood": 12.0, "stone": 6.0, "crystal": 1.0},
        "knowledge_prerequisites": ["wind", "pressure", "erosion", "gravity"],
        "tool_prerequisites": ["stone_axe", "metal_blade"],
        "effects": {"gathering": 0.6, "science": 0.5, "cooperation": 0.4}
    },
}


class ToolCrafter:
    """
    Manages tool discovery, crafting, and usage for agents.
    Tools are discovered when agents have sufficient knowledge and resources.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.world_tools_discovered: Dict[str, int] = {}  # tool_name -> first_discover_tick

    def can_craft(self, agent: "CuriosityAgent", tool_name: str) -> tuple:
        """Check if agent can craft a tool. Returns (bool, reason_str)."""
        if tool_name not in TOOL_CATALOG:
            return False, "unknown tool"
        spec = TOOL_CATALOG[tool_name]

        # Check knowledge prerequisites
        agent_concepts = set(agent.knowledge.keys())
        for prereq in spec["knowledge_prerequisites"]:
            if prereq not in agent_concepts:
                return False, f"missing knowledge: {prereq}"

        # Check tool prerequisites
        owned_tools = set(agent.inventory.keys())
        for tool_prereq in spec["tool_prerequisites"]:
            if tool_prereq not in owned_tools:
                return False, f"missing tool: {tool_prereq}"

        # Check resources
        for resource, amount in spec["recipe"].items():
            if agent.inventory.get(resource, 0) < amount:
                return False, f"insufficient {resource}"

        return True, "ok"

    def attempt_craft(self, agent: "CuriosityAgent", tool_name: str,
                      tick: int) -> Optional[Tool]:
        """Attempt to craft a tool. Returns Tool if successful."""
        ok, reason = self.can_craft(agent, tool_name)
        if not ok:
            return None

        spec = TOOL_CATALOG[tool_name]
        skill_factor = agent.skills.get("crafting", 0.1)
        success_prob = 0.4 + 0.5 * skill_factor + 0.1 * agent.creativity

        if self.rng.random() > success_prob:
            # Failed attempt — still consumes some resources
            for resource, amount in spec["recipe"].items():
                agent.inventory[resource] = max(0, agent.inventory.get(resource, 0) - amount * 0.3)
            return None

        # Consume resources
        for resource, amount in spec["recipe"].items():
            agent.inventory[resource] = max(0, agent.inventory.get(resource, 0) - amount)

        # Create tool
        tool = Tool(
            name=tool_name,
            description=spec["description"],
            tier=spec["tier"],
            recipe=spec["recipe"].copy(),
            knowledge_prerequisites=spec["knowledge_prerequisites"][:],
            tool_prerequisites=spec["tool_prerequisites"][:],
            effects=spec["effects"].copy()
        )

        # Apply skill bonuses
        for skill, bonus in spec["effects"].items():
            agent.improve_skill(skill, bonus * (0.5 + 0.5 * skill_factor))

        # Record in inventory
        agent.inventory[tool_name] = agent.inventory.get(tool_name, 0) + 1
        agent.tools_created += 1

        # Track world-first discoveries
        if tool_name not in self.world_tools_discovered:
            self.world_tools_discovered[tool_name] = tick

        # Gain knowledge about the tool
        agent.observe(f"tool_{tool_name}", 0.8, tick, "crafting")
        agent.improve_skill("crafting", 0.05)

        return tool

    def get_craftable_tools(self, agent: "CuriosityAgent") -> List[str]:
        """Return list of tools the agent can currently craft."""
        craftable = []
        for name in TOOL_CATALOG:
            ok, _ = self.can_craft(agent, name)
            if ok:
                craftable.append(name)
        return craftable

    def get_discoverable_tools(self, agent: "CuriosityAgent") -> List[str]:
        """Tools the agent is close to being able to craft (1-2 prerequisites missing)."""
        discoverable = []
        for name, spec in TOOL_CATALOG.items():
            if name in agent.inventory:
                continue
            agent_concepts = set(agent.knowledge.keys())
            missing_knowledge = [p for p in spec["knowledge_prerequisites"]
                                  if p not in agent_concepts]
            owned_tools = set(agent.inventory.keys())
            missing_tools = [p for p in spec["tool_prerequisites"]
                              if p not in owned_tools]
            total_missing = len(missing_knowledge) + len(missing_tools)
            if 0 < total_missing <= 2:
                discoverable.append(name)
        return discoverable

    def get_civilization_progress(self) -> dict:
        """Summarize tool discovery progress for the civilization."""
        by_tier = {}
        for name, spec in TOOL_CATALOG.items():
            t = spec["tier"]
            by_tier.setdefault(t, {"total": 0, "discovered": 0})
            by_tier[t]["total"] += 1
            if name in self.world_tools_discovered:
                by_tier[t]["discovered"] += 1
        return {
            "tools_discovered": list(self.world_tools_discovered.keys()),
            "total_tools": len(TOOL_CATALOG),
            "discovery_count": len(self.world_tools_discovered),
            "by_tier": by_tier
}
