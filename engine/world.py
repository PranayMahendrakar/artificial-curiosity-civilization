"""
World Engine — Procedurally generated environment for the Curiosity Civilization.
The World is a 2D grid of Cells, each with physics properties, resources,
and phenomena that agents can discover and interact with.
"""

from __future__ import annotations
import random
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum, auto


# ─── Enums ────────────────────────────────────────────────────────────────────
class Biome(Enum):
    PLAINS   = "plains"
    FOREST   = "forest"
    MOUNTAIN = "mountain"
    DESERT   = "desert"
    OCEAN    = "ocean"
    TUNDRA   = "tundra"


class ResourceType(Enum):
    WOOD      = "wood"
    STONE     = "stone"
    FIRE      = "fire"
    WATER     = "water"
    FOOD      = "food"
    METAL     = "metal"
    CRYSTAL   = "crystal"
    SOIL      = "soil"
    WIND      = "wind"


class Phenomenon(Enum):
    """Natural phenomena agents can observe and learn from."""
    GRAVITY     = "gravity"
    COMBUSTION  = "combustion"
    MAGNETISM   = "magnetism"
    ELECTRICITY = "electricity"
    PRESSURE    = "pressure"
    EROSION     = "erosion"
    FERMENTATION = "fermentation"
    ECHO        = "echo"


# ─── Cell ─────────────────────────────────────────────────────────────────────
@dataclass
class Cell:
    """A single grid cell in the World."""
    x: int
    y: int
    biome: Biome = Biome.PLAINS
    elevation: float = 0.0
    temperature: float = 20.0
    moisture: float = 0.5
    resources: Dict[ResourceType, float] = field(default_factory=dict)
    phenomena: Set[Phenomenon] = field(default_factory=set)
    agent_ids: List[int] = field(default_factory=list)
    structures: List[str] = field(default_factory=list)
    pollution: float = 0.0
    fertility: float = 1.0

    def resource_count(self) -> int:
        return sum(1 for v in self.resources.values() if v > 0)

    def is_habitable(self) -> bool:
        return (self.biome != Biome.OCEAN and
                self.elevation < 0.9 and
                self.temperature > -10 and
                self.pollution < 0.8)

    def extract_resource(self, rtype: ResourceType, amount: float) -> float:
        """Extract up to amount of a resource, returns actual extracted."""
        available = self.resources.get(rtype, 0.0)
        extracted = min(available, amount)
        self.resources[rtype] = available - extracted
        return extracted

    def deposit_resource(self, rtype: ResourceType, amount: float):
        self.resources[rtype] = self.resources.get(rtype, 0.0) + amount

    def to_dict(self) -> dict:
        return {
            "x": self.x, "y": self.y,
            "biome": self.biome.value,
            "elevation": round(self.elevation, 3),
            "temperature": round(self.temperature, 1),
            "resources": {r.value: round(v, 2) for r, v in self.resources.items() if v > 0.01},
            "phenomena": [p.value for p in self.phenomena],
            "agents": len(self.agent_ids),
            "structures": self.structures[:]
        }


# ─── Physics Engine ───────────────────────────────────────────────────────────
class PhysicsEngine:
    """
    Simulates physical laws in the world.
    Each tick, physics rules apply: resource regeneration, weather, diffusion.
    """

    REGEN_RATES = {
        ResourceType.WOOD:   0.02,
        ResourceType.FOOD:   0.05,
        ResourceType.WATER:  0.03,
        ResourceType.STONE:  0.001,
        ResourceType.WIND:   0.10,
        ResourceType.SOIL:   0.01,
    }

    BIOME_RESOURCES = {
        Biome.PLAINS:   [ResourceType.FOOD, ResourceType.SOIL, ResourceType.WIND],
        Biome.FOREST:   [ResourceType.WOOD, ResourceType.FOOD, ResourceType.WATER],
        Biome.MOUNTAIN: [ResourceType.STONE, ResourceType.METAL, ResourceType.CRYSTAL],
        Biome.DESERT:   [ResourceType.STONE, ResourceType.WIND, ResourceType.CRYSTAL],
        Biome.OCEAN:    [ResourceType.WATER, ResourceType.FOOD],
        Biome.TUNDRA:   [ResourceType.STONE, ResourceType.WATER],
    }

    BIOME_PHENOMENA = {
        Biome.PLAINS:   {Phenomenon.GRAVITY, Phenomenon.PRESSURE},
        Biome.FOREST:   {Phenomenon.GRAVITY, Phenomenon.FERMENTATION, Phenomenon.ECHO},
        Biome.MOUNTAIN: {Phenomenon.GRAVITY, Phenomenon.ECHO, Phenomenon.EROSION},
        Biome.DESERT:   {Phenomenon.GRAVITY, Phenomenon.ELECTRICITY, Phenomenon.PRESSURE},
        Biome.OCEAN:    {Phenomenon.PRESSURE, Phenomenon.EROSION},
        Biome.TUNDRA:   {Phenomenon.GRAVITY, Phenomenon.MAGNETISM},
    }

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.tick = 0

    def step(self, cells: Dict[Tuple[int, int], Cell]):
        """Advance physics by one tick."""
        self.tick += 1
        season_factor = 0.8 + 0.4 * math.sin(self.tick * math.pi / 50)

        for cell in cells.values():
            if cell.biome == Biome.OCEAN:
                continue

            # Resource regeneration
            for rtype in self.BIOME_RESOURCES.get(cell.biome, []):
                rate = self.REGEN_RATES.get(rtype, 0.01)
                cap = 10.0 * cell.fertility * season_factor
                current = cell.resources.get(rtype, 0.0)
                if current < cap:
                    delta = rate * (1 - current / cap) * cell.fertility
                    cell.resources[rtype] = current + delta

            # Random fire ignition in forests
            if cell.biome == Biome.FOREST and self.rng.random() < 0.0002:
                cell.resources[ResourceType.FIRE] = cell.resources.get(ResourceType.FIRE, 0) + 2.0
                cell.phenomena.add(Phenomenon.COMBUSTION)
                cell.resources[ResourceType.WOOD] = max(0, cell.resources.get(ResourceType.WOOD, 0) - 1)

            # Fire decay
            if ResourceType.FIRE in cell.resources and cell.resources[ResourceType.FIRE] > 0:
                cell.resources[ResourceType.FIRE] *= 0.85
                if cell.resources[ResourceType.FIRE] < 0.05:
                    cell.resources[ResourceType.FIRE] = 0
                    cell.phenomena.discard(Phenomenon.COMBUSTION)

            # Temperature variation
            base_temp = 30 - cell.elevation * 25
            cell.temperature = base_temp + 5 * math.sin(self.tick * math.pi / 100) + self.rng.gauss(0, 1)

            # Pollution decay
            cell.pollution = max(0, cell.pollution - 0.001)


# ─── World ────────────────────────────────────────────────────────────────────
class World:
    """
    The simulation world — a grid of Cells with a physics engine.
    Generates biomes using coherent noise, populates resources and phenomena.
    """

    def __init__(self, width: int = 40, height: int = 30, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.cells: Dict[Tuple[int, int], Cell] = {}
        self.physics = PhysicsEngine(self.rng)
        self.tick = 0
        self.events: List[Dict] = []
        self._generate()

    def _noise(self, x: float, y: float, scale: float = 0.1) -> float:
        """Simple pseudo-noise for terrain generation."""
        v = (math.sin(x * scale * 7.3 + 1.7) * math.cos(y * scale * 5.1 + 2.3) +
             math.sin(x * scale * 3.1 + y * scale * 2.7) * 0.5)
        return (v + 1.5) / 3.0

    def _generate(self):
        """Procedurally generate the world using noise-based terrain."""
        physics = PhysicsEngine(self.rng)

        for y in range(self.height):
            for x in range(self.width):
                elevation = self._noise(x, y, scale=0.15)
                moisture  = self._noise(x + 100, y + 100, scale=0.12)
                temperature_base = 30 - elevation * 30 - abs(y - self.height / 2) * 0.5

                biome = self._classify_biome(elevation, moisture, temperature_base)

                cell = Cell(
                    x=x, y=y,
                    biome=biome,
                    elevation=elevation,
                    temperature=temperature_base,
                    moisture=moisture,
                    fertility=moisture * (1 - abs(elevation - 0.3)),
                )

                # Populate initial resources
                for rtype in physics.BIOME_RESOURCES.get(biome, []):
                    base = self.rng.uniform(0.5, 5.0)
                    cell.resources[rtype] = base * cell.fertility

                # Add phenomena
                cell.phenomena = physics.BIOME_PHENOMENA.get(biome, set()).copy()

                # Special: rare crystals on mountains
                if biome == Biome.MOUNTAIN and self.rng.random() < 0.15:
                    cell.resources[ResourceType.CRYSTAL] = self.rng.uniform(1, 4)

                # Special: metal veins
                if biome == Biome.MOUNTAIN and self.rng.random() < 0.1:
                    cell.resources[ResourceType.METAL] = self.rng.uniform(0.5, 3)
                    cell.phenomena.add(Phenomenon.MAGNETISM)

                self.cells[(x, y)] = cell

    def _classify_biome(self, elevation: float, moisture: float, temp: float) -> Biome:
        if elevation > 0.75:
            return Biome.MOUNTAIN
        if elevation < 0.2:
            return Biome.OCEAN
        if temp < 0:
            return Biome.TUNDRA
        if moisture < 0.25:
            return Biome.DESERT
        if moisture > 0.6 and temp > 10:
            return Biome.FOREST
        return Biome.PLAINS

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        return self.cells.get((x % self.width, y % self.height))

    def get_neighbors(self, x: int, y: int, radius: int = 1) -> List[Cell]:
        neighbors = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                c = self.get_cell(x + dx, y + dy)
                if c:
                    neighbors.append(c)
        return neighbors

    def step(self):
        """Advance world by one tick."""
        self.tick += 1
        self.physics.step(self.cells)

    def add_event(self, event_type: str, data: dict):
        self.events.append({"tick": self.tick, "type": event_type, **data})
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

    def get_stats(self) -> dict:
        habitable = sum(1 for c in self.cells.values() if c.is_habitable())
        total_resources = {}
        biome_counts = {}
        for cell in self.cells.values():
            b = cell.biome.value
            biome_counts[b] = biome_counts.get(b, 0) + 1
            for rtype, amt in cell.resources.items():
                key = rtype.value
                total_resources[key] = total_resources.get(key, 0) + amt
        return {
            "tick": self.tick,
            "total_cells": len(self.cells),
            "habitable_cells": habitable,
            "biome_distribution": biome_counts,
            "total_resources": {k: round(v, 1) for k, v in total_resources.items()},
        }
