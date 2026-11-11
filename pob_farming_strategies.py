#!/usr/bin/env python3
"""
PoB Farming Strategies — League-aware farming for PoE items and currency.

Updated for 3.30 Covens of Umbra:
- New league: Covens of Umbra (Fate selection, Wickerman/Viscera)
- Scarabs REMOVED → replaced by Threads (10 types)
- Frayed Thread currency
- Memory Threads → Memory Traces
- Shaped Regions reworked (10 types, one per Thread)
- New skills: Arcane Link, Fireball of Radiation
- Mirage as Core League
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
from pathlib import Path


# ─── League Constants ────────────────────────────────────────────────

CURRENT_LEAGUE = "3.30"
CURRENT_LEAGUE_NAME = "Covens of Umbra"
CURRENT_LEAGUE_MECHANIC = "Wickerman/Fate"

LEAGUE_ALIASES = {
    "3.30": ["3.30", "Covens of Umbra", "Wickerman", "Viscera", "Fate"],
    "3.29": ["3.29", "Necropolis", "Allflame", "Wildwood"],
    "3.28": ["3.28", "Affliction", "Wildwood", "Sanctum"],
    "3.27": ["3.27", "Trial of the Ancestors", "Ancestor"],
    "3.26": ["3.26", "Ancestor", "Kalandra", "Synthesis"],
}


def is_league_content(league_str: str, target_league: str = CURRENT_LEAGUE) -> bool:
    """Check if content applies to target league."""
    aliases = LEAGUE_ALIASES.get(target_league, [target_league])
    return any(alias.lower() in league_str.lower() for alias in aliases)


# ─── Enums ───────────────────────────────────────────────────────────

class FarmingMethod(Enum):
    """Farming method categories."""
    MAP_FARMING = "Map Farming"
    DELVE = "Delve"
    HEIST = "Heist"
    EXPEDITION = "Expedition"
    BLIGHT = "Blight"
    DELIRIUM = "Delirium"
    RITUAL = "Ritual"
    LEGION = "Legion"
    ABYSS = "Abyss"
    BREACH = "Breach"
    BETRAYAL = "Betrayal"
    BESTIARY = "Bestiary"
    ULTIMATUM = "Ultimatum"
    INCURSION = "Incursion"
    SANCTUM = "Sanctum"
    MIRAGE = "Mirage"
    KINGSMARCH = "Kingsmarch"
    COVENS_OF_UMBRA = "Covens of Umbra"
    BOSS_FARMING = "Boss Farming"
    SIMULACRUM = "Simulacrum"
    VAAL_SIDE_AREAS = "Vaal Side Areas"
    ESSENCE_FARMING = "Essence Farming"
    FOSSIL_FARMING = "Fossil Farming"
    SHAPED_REGIONS = "Shaped Regions"


class Applicability(Enum):
    """Strategy applicability status."""
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    OBSOLETE = "obsolete"


class CurrencyType(Enum):
    """Currency types for farming."""
    DIVINE = "Divine Orb"
    EXALTED = "Exalted Orb"
    CHAOS = "Chaos Orb"
    MIRROR = "Mirror of Kalandra"
    ANCIENT = "Ancient Orb"
    REGAL = "Regal Orb"
    VAAL = "Vaal Orb"
    ANCIENT_ORB = "Ancient Orb"
    THREAD = "Thread"  # NEW 3.30
    FRAYED_THREAD = "Frayed Thread"  # NEW 3.30
    VISCERA = "Viscera"  # NEW 3.30


# ─── Data Classes ────────────────────────────────────────────────────

@dataclass
class FarmingRequirement:
    """Requirements for a farming strategy."""
    atlas_completion: str = ""
    build_type: str = ""
    gear_level: str = ""
    league_mechanic: str = ""
    notes: str = ""


@dataclass
class EstimatedReturns:
    """Estimated returns per hour."""
    divine_per_hour: float = 0.0
    exalted_per_hour: float = 0.0
    chaos_per_hour: float = 0.0
    mirrors_per_hour: float = 0.0
    threads_per_hour: dict = field(default_factory=dict)  # NEW 3.30
    visera_per_hour: float = 0.0  # NEW 3.30
    artifacts_per_hour: float = 0.0
    logbooks_per_hour: float = 0.0
    relics_per_hour: float = 0.0
    oils_per_hour: float = 0.0
    fossils_per_hour: float = 0.0
    essences_per_hour: float = 0.0
    custom: dict = field(default_factory=dict)


@dataclass
class Investment:
    """Investment required for farming."""
    maps_per_hour: str = ""
    sextants_per_hour: str = ""
    scarabs_per_hour: str = ""  # DEPRECATED 3.30
    threads_per_hour: str = ""  # NEW 3.30
    waystones_per_hour: str = ""
    currency_cost: str = ""
    time_setup_minutes: int = 0


@dataclass
class FarmingStrategy:
    """Complete farming strategy definition."""
    name: str
    method: FarmingMethod
    mechanic: str
    league: str
    applicability: Applicability
    requirements: FarmingRequirement
    estimated_returns: EstimatedReturns
    investment: Investment
    source: str
    source_date: str
    league_tested: str
    confidence: float
    notes: str = ""
    priority: int = 999  # Lower = higher priority
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["method"] = self.method.value
        d["applicability"] = self.applicability.value
        return d
    
    @property
    def div_per_hour(self) -> float:
        return self.estimated_returns.divine_per_hour


# ─── Strategy Definitions ───────────────────────────────────────────

def build_strategies(league: str = CURRENT_LEAGUE) -> dict[str, FarmingStrategy]:
    """Build all farming strategies for a given league."""
    
    is_330 = league == "3.30"
    
    strategies = {}
    
    # ═══════════════════════════════════════════════════════════════════
    # CURRENCY FARMING (always included)
    # ═══════════════════════════════════════════════════════════════════
    
    strategies["divine_orbs"] = FarmingStrategy(
        name="Divine Orb Farming",
        method=FarmingMethod.MAP_FARMING,
        mechanic="Atlas Passive Tree + T16-17 Maps",
        league=league,
        applicability=Applicability.VERIFIED if is_330 else Applicability.NEEDS_REVIEW,
        requirements=FarmingRequirement(
            atlas_completion="80%+",
            build_type="Fast clear (10M+ DPS)",
            gear_level="T16+ maps sustainable",
            league_mechanic="Atlas Passives",
            notes="Atlas passives change per league; check current league tree"
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=3.0,
            chaos_per_hour=600,
            exalted_per_hour=5.0
        ),
        investment=Investment(
            maps_per_hour="50-80 maps/hr",
            sextants_per_hour="10-15c",
            threads_per_hour="8-12 Threads/hr" if is_330 else "",
            currency_cost="~50c/map sustained"
        ),
        source="pathofexile.com + community testing",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.95 if is_330 else 0.7,
        priority=1,
        notes="Primary div farming method. Optimize atlas for quantity/rarity passives."
    )
    
    strategies["exalted_orbs"] = FarmingStrategy(
        name="Exalted Orb Farming",
        method=FarmingMethod.BOSS_FARMING,
        mechanic="Endgame Bosses (Sirus, Maven, Eater/Exarch, Uber Bosses)",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Boss killer (30M+ DPS)",
            gear_level="Uber viable",
            notes="Exalt drops from bosses + Maven writs"
        ),
        estimated_returns=EstimatedReturns(
            exalted_per_hour=5.0,
            divine_per_hour=1.0,
            chaos_per_hour=200
        ),
        investment=Investment(
            currency_cost="Boss fragments (varies)",
            time_setup_minutes=30
        ),
        source="poe-vault.com + maxroll.gg",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.9,
        priority=2,
        notes="Combine with Maven invitations for extra drops"
    )
    
    strategies["chaos_orbs"] = FarmingStrategy(
        name="Chaos Orb Farming",
        method=FarmingMethod.MAP_FARMING,
        mechanic="Raw map drops + vendor recipes",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Any clear speed build",
            notes="Raw chaos from maps + 6-socket vendor recipe"
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=800,
            divine_per_hour=0.5
        ),
        investment=Investment(
            maps_per_hour="100+ maps/hr",
            currency_cost="Low (alchemy orbs)"
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.85,
        priority=3,
        notes="Good for early league; scales with clear speed"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # 3.30 COVENS OF UMBRA SPECIFIC
    # ═══════════════════════════════════════════════════════════════════
    
    if is_330:
        strategies["covens_of_umbra"] = FarmingStrategy(
            name="Covens of Umbra - Fate Selection & Wickerman",
            method=FarmingMethod.COVENS_OF_UMBRA,
            mechanic="Fate selection on bosses + Wickerman/Viscera",
            league=league,
            applicability=Applicability.VERIFIED,
            requirements=FarmingRequirement(
                build_type="Boss killer or fast mapper",
                league_mechanic="Covens of Umbra",
                notes="Select Fates to increase rewards/difficulty; place boss remains on Wickerman for Viscera"
            ),
            estimated_returns=EstimatedReturns(
                divine_per_hour=2.0,
                exalted_per_hour=3.0,
                chaos_per_hour=400,
                visera_per_hour=10.0,
                custom={"fate_rewards": "Variable by Fate choice"}
            ),
            investment=Investment(
                currency_cost="Map cost + Fate selection",
                time_setup_minutes=10
            ),
            source="pathofexile.com/covens + patch notes 3.30",
            source_date="2026-11-10",
            league_tested=league,
            confidence=0.85,
            priority=0,
            notes="NEW 3.30 league mechanic. Fates increase rewards AND difficulty. Viscera from Wickerman = unique boss powers."
        )
        
        strategies["threads_farming"] = FarmingStrategy(
            name="Thread Farming (replaces Scarabs)",
            method=FarmingMethod.SHAPED_REGIONS,
            mechanic="Shaped Regions + Thread drops (10 types)",
            league=league,
            applicability=Applicability.VERIFIED,
            requirements=FarmingRequirement(
                atlas_completion="60%+",
                league_mechanic="Shaped Regions / Threads",
                notes="10 Thread types: Abyss, Bestiary, Betrayal, Blight, Breach, Expedition, Incursion, Legion, Ritual, Ultimatum"
            ),
            estimated_returns=EstimatedReturns(
                threads_per_hour={
                    "Abyss": 8,
                    "Bestiary": 6,
                    "Betrayal": 5,
                    "Blight": 6,
                    "Breach": 7,
                    "Expedition": 5,
                    "Incursion": 5,
                    "Legion": 6,
                    "Ritual": 7,
                    "Ultimatum": 5,
                    "Frayed Thread": 10
                },
                divine_per_hour=1.5,
                chaos_per_hour=300
            ),
            investment=Investment(
                threads_per_hour="8-12 Threads/hr per map",
                maps_per_hour="30-50 maps/hr",
                currency_cost="Map cost + Waystones"
            ),
            source="patch notes 3.30 + community testing",
            source_date="2026-11-10",
            league_tested=league,
            confidence=0.9,
            priority=2,
            notes="Scarabs REMOVED in 3.30. Threads are the new map augmentation currency. Frayed Thread = random Thread or vendor for random Thread."
        )
        
        strategies["shaped_regions"] = FarmingStrategy(
            name="Shaped Region Objectives (Atlas Passive Progression)",
            method=FarmingMethod.SHAPED_REGIONS,
            mechanic="Complete Shaped Region objectives for free Thread scaling",
            league=league,
            applicability=Applicability.VERIFIED,
            requirements=FarmingRequirement(
                atlas_completion="40%+",
                league_mechanic="Shaped Regions",
                notes="10 Shaped Region types, one per Thread. Completing objectives increases free Thread count in all maps of that region."
            ),
            estimated_returns=EstimatedReturns(
                threads_per_hour={"scaling": "Infinite scaling per region"},
                divine_per_hour=2.0
            ),
            investment=Investment(
                maps_per_hour="20-30 maps/hr in shaped regions",
                currency_cost="Waystones + map sustain"
            ),
            source="patch notes 3.30",
            source_date="2026-11-10",
            league_tested=league,
            confidence=0.85,
            priority=3,
            notes="Core 3.30 Atlas progression. Regenerate Shaped Regions button when <10 on Atlas. Astrolabes add specific Shaped Region to specific map."
        )
        
        strategies["mirage_core"] = FarmingStrategy(
            name="Mirage (Now Core League Content)",
            method=FarmingMethod.MIRAGE,
            mechanic="Mirage encounters in maps",
            league=league,
            applicability=Applicability.VERIFIED,
            requirements=FarmingRequirement(
                league_mechanic="Mirage",
                notes="Mirage added as core content in 3.30. Memory Traces (was Memory Threads) for modifiers."
            ),
            estimated_returns=EstimatedReturns(
                divine_per_hour=1.0,
                chaos_per_hour=200,
                custom={"mirage_rewards": "Unique Mirage items"}
            ),
            investment=Investment(
                currency_cost="Map cost"
            ),
            source="patch notes 3.30",
            source_date="2026-11-10",
            league_tested=league,
            confidence=0.8,
            priority=5,
            notes="Mirage now spawns naturally in maps. Memory Traces altars for Rarity bonuses."
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # STABLE MECHANICS (exist across leagues)
    # ═══════════════════════════════════════════════════════════════════
    
    strategies["kingsmarch_daily"] = FarmingStrategy(
        name="Kingsmarch Daily (Settlers League Mechanic)",
        method=FarmingMethod.KINGSMARCH,
        mechanic="Kingsmarch town management + shipments",
        league=league,
        applicability=Applicability.VERIFIED if is_330 else Applicability.NEEDS_REVIEW,
        requirements=FarmingRequirement(
            league_mechanic="Kingsmarch (Settlers)",
            notes="Daily shipments, resource management, worker assignment"
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=2.0,
            chaos_per_hour=300,
            custom={"gold_per_hour": 50000, "artifact_chance": "Daily"}
        ),
        investment=Investment(
            time_setup_minutes=15,
            currency_cost="Initial town setup (~5-10 div)"
        ),
        source="patch notes 3.30 + community",
        source_date="2026-11-10",
        league_tested="3.30",
        confidence=0.9 if is_330 else 0.5,
        priority=2 if is_330 else 10,
        notes="Settlers/Kingsmarch from 3.29 continues in 3.30. Daily ~2 div/hr passive income once established."
    )
    
    strategies["heist_blueprints"] = FarmingStrategy(
        name="Heist Blueprints (Grand Heists)",
        method=FarmingMethod.HEIST,
        mechanic="Heist contracts + blueprints → Grand Heists",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Heist viable (movement speed, evasion)",
            notes="Contracts changed 3.25; blueprints for Grand Heists"
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=1.5,
            exalted_per_hour=3.0,
            chaos_per_hour=200,
            custom={"ring_bases_per_hour": 20, "replica_uniques": "Chance"}
        ),
        investment=Investment(
            currency_cost="Contract/blueprint cost + rogue gear",
            time_setup_minutes=20
        ),
        source="poe-vault.com + maxroll.gg",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.85,
        priority=4,
        notes="Best for ring bases, replica uniques, currency. Rogue leveling required."
    )
    
    strategies["sanctum_forbidden"] = FarmingStrategy(
        name="Sanctum / Forbidden Sanctum",
        method=FarmingMethod.SANCTUM,
        mechanic="Forbidden Sanctum runs → Relics, Ashes chance",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="High defense (max res, chaos res, phys reduction)",
            notes="3.28+ relic system. Need Sanctum keys."
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=1.0,
            exalted_per_hour=2.0,
            chaos_per_hour=150,
            relics_per_hour=5.0,
            custom={"ashes_chance": "Low per run"}
        ),
        investment=Investment(
            currency_cost="Sanctum keys (varies)",
            time_setup_minutes=30
        ),
        source="craftofexile.com + poe-vault.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=5,
        notes="High risk/reward. Relic crafting for endgame gear. Ashes of the Stars drop chance."
    )
    
    strategies["delirium_mirrors"] = FarmingStrategy(
        name="Delirium Mirrors (Simulacrum Splinters)",
        method=FarmingMethod.DELIRIUM,
        mechanic="Delirium mirrors in maps → Simulacrum splinters",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Delirium viable (clear speed + survivability)",
            notes="Reworked 3.26. Mirror mechanics changed."
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=1.5,
            chaos_per_hour=300,
            custom={"simulacrum_splinters_per_hour": 50}
        ),
        investment=Investment(
            currency_cost="Delirium orbs (if not natural spawn)",
            time_setup_minutes=10
        ),
        source="poe.fandom.com + community",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.85,
        priority=6,
        notes="Simulacrum wave 20-30 farming for cluster jewels, simulacrum splinters, Awakened gems."
    )
    
    strategies["simulacrum_wave30"] = FarmingStrategy(
        name="Simulacrum Wave 30 (Awakened Gems, Level 21)",
        method=FarmingMethod.SIMULACRUM,
        mechanic="Full Simulacrum clear to wave 30",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Simulacrum viable (30M+ DPS, high defense)",
            notes="Requires 300+ simulacrum splinters"
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=5.0,
            custom={"awakened_gems_per_run": "2-5", "level_21_gems": "Chance"}
        ),
        investment=Investment(
            currency_cost="300+ simulacrum splinters (~15-20 div)",
            time_setup_minutes=45
        ),
        source="maxroll.gg + community",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.9,
        priority=7,
        notes="Highest value per run but high entry cost. Awakened gems, level 21 gems, cluster jewels."
    )
    
    strategies["legion_emblems"] = FarmingStrategy(
        name="Legion Emblems (5-way Rotations)",
        method=FarmingMethod.LEGION,
        mechanic="5-way Legion emblem rotations",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Legion viable (AoE clear, freeze immune)",
            notes="5 emblems = 5-way. Timeless Jewels, cluster jewels, currency."
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=2.0,
            chaos_per_hour=400,
            custom={"timeless_jewels_per_hour": 3, "cluster_jewels_per_hour": 10}
        ),
        investment=Investment(
            currency_cost="5 emblems (~50-100c each)",
            time_setup_minutes=20
        ),
        source="poe-vault.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.85,
        priority=8,
        notes="Stable mechanic. Good for Timeless Jewels, cluster jewels, raw currency."
    )
    
    strategies["breachstones"] = FarmingStrategy(
        name="Breachstone Rotations (Pure Breachstones)",
        method=FarmingMethod.BREACH,
        mechanic="Pure Breachstone rotations (Chayula, Esh, Tul, Xoph, Uul-Netol)",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Breach viable (clear speed, breach resistance)",
            notes="Pure breachstones = double bosses = double splinters"
        ),
        estimated_returns=EstimatedReturns(
            divine_per_hour=1.5,
            chaos_per_hour=200,
            custom={"breach_splinters_per_hour": 200, "breach_uniques": "Chance"}
        ),
        investment=Investment(
            currency_cost="Pure breachstones (varies by type)",
            time_setup_minutes=15
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=9,
        notes="Chayula = most valuable (Breach uniques). Good for splinters + uniques."
    )
    
    strategies["abyssal_depths"] = FarmingStrategy(
        name="Abyssal Depths (Abyssal Jewels/Sockets)",
        method=FarmingMethod.ABYSS,
        mechanic="Abyss encounters → Abyssal Depths",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Fast clear for Abyss cracks",
            notes="Abyssal jewels, abyssal sockets on items"
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=300,
            custom={"abyssal_jewels_per_hour": 20, "abyssal_sockets": "Chance"}
        ),
        investment=Investment(
            currency_cost="Low (natural spawn or Abyssal Depths map)",
            time_setup_minutes=5
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.75,
        priority=10,
        notes="Low investment. Good for abyssal jewels + sockets on gear."
    )
    
    strategies["essence_farming"] = FarmingStrategy(
        name="Essence Farming (Memory + Corruption)",
        method=FarmingMethod.ESSENCE_FARMING,
        mechanic="Essence monsters + Memory corruption",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Essence viable",
            notes="Corrupted essences added 3.28. Memory for essence corruption."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=400,
            custom={"special_essences_per_hour": 10}
        ),
        investment=Investment(
            currency_cost="Essence map mods + Memory fragments",
            time_setup_minutes=15
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=11,
        notes="Special essences (Hysteria, Insanity, etc.) valuable for crafting."
    )
    
    strategies["fossil_farming"] = FarmingStrategy(
        name="Fossil Farming (Delve 200+)",
        method=FarmingMethod.FOSSIL_FARMING,
        mechanic="Delve depth 200+ → Fossil nodes",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Delve viable (darkness resist, movement)",
            notes="Sulphite cost varies. Depth 200+ for best fossils."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=500,
            custom={"pristine_fossils_per_hour": 30, "dense_fossils_per_hour": 20}
        ),
        investment=Investment(
            currency_cost="Sulphite + flares/dynamite",
            time_setup_minutes=30
        ),
        source="craftofexile.com + poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.85,
        priority=12,
        notes="Best for crafting bases. Pristine/Dense/Boundary/Faceted fossils high value."
    )
    
    strategies["ritual_vessels"] = FarmingStrategy(
        name="Ritual Vessels + Favours",
        method=FarmingMethod.RITUAL,
        mechanic="Ritual encounters → Vessels + Favours",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Ritual viable (survivability for re-rolls)",
            notes="Favours for Ritual uniques, omens, vessels"
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=300,
            custom={"favours_per_hour": 500, "vessels_per_hour": 5}
        ),
        investment=Investment(
            currency_cost="Ritual map mods",
            time_setup_minutes=10
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=13,
        notes="Omens valuable (Omen of Brilliance, etc.). Vessels for Ritual uniques."
    )
    
    strategies["ultimatum_inscribed"] = FarmingStrategy(
        name="Ultimatum Inscribed + Rare Rewards",
        method=FarmingMethod.ULTIMATUM,
        mechanic="Ultimatum encounters → Inscribed Ultimatums",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Ultimatum viable (DPS checks)",
            notes="Inscribed Ultimatums for rare rewards"
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=200,
            custom={"inscribed_per_hour": 3}
        ),
        investment=Investment(
            currency_cost="Ultimatum map mods",
            time_setup_minutes=10
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.75,
        priority=14,
        notes="Inscribed Ultimatums drop valuable uniques. High DPS checks."
    )
    
    strategies["expedition_logbooks"] = FarmingStrategy(
        name="Expedition Logbooks (Artifacts)",
        method=FarmingMethod.EXPEDITION,
        mechanic="Expedition encounters → Logbooks + Artifacts",
        league=league,
        applicability=Applicability.NEEDS_REVIEW,
        requirements=FarmingRequirement(
            build_type="Expedition viable (clear + explosives)",
            notes="Logbook drops changed 3.29. Verify current rates."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=300,
            artifacts_per_hour=15.0,
            logbooks_per_hour=5.0
        ),
        investment=Investment(
            currency_cost="Expedition map mods + explosives",
            time_setup_minutes=15
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested="3.29",
        confidence=0.4,
        priority=15,
        notes="Logbook drops rebalanced 3.29. Verify 3.30 rates. Artifacts for crafting."
    )
    
    strategies["blight_ravaged"] = FarmingStrategy(
        name="Blight Ravaged Maps (Oils)",
        method=FarmingMethod.BLIGHT,
        mechanic="Blighted/Ravaged Maps → Oils",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Blight viable (tower defense)",
            notes="Oil changes 3.28. Golden/ Silver oils valuable."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=400,
            oils_per_hour=50.0,
            custom={"golden_oils_per_hour": 5}
        ),
        investment=Investment(
            currency_cost="Blighted maps + tower upgrades",
            time_setup_minutes=20
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=16,
        notes="Golden/Silver oils for anointments. Blighted maps for oils + uniques."
    )
    
    strategies["betrayal_safehouse"] = FarmingStrategy(
        name="Betrayal Safehouse (Veiled Mods, Crafting)",
        method=FarmingMethod.BETRAYAL,
        mechanic="Betrayal encounters → Safehouse rewards",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Any clear speed",
            notes="Veiled mods for crafting. Catarina for unique drops."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=200,
            custom={"veiled_chaos_per_hour": 10, "catarina_chance": "Daily"}
        ),
        investment=Investment(
            currency_cost="Betrayal map mods",
            time_setup_minutes=10
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.75,
        priority=17,
        notes="Veiled Chaos Orbs for crafting. Safehouse rewards rotate."
    )
    
    strategies["bestiary_capture"] = FarmingStrategy(
        name="Bestiary Capture (Beasts, Fenumus, Craiceann)",
        method=FarmingMethod.BESTIARY,
        mechanic="Bestiary encounters → Beast capture",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Any clear speed",
            notes="Fenumus (Spider), Craiceann (Crab), Saqawine (Bird) for crafts"
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=200,
            custom={"fenumus_per_week": 1, "craiceann_per_week": 1}
        ),
        investment=Investment(
            currency_cost="Bestiary map mods + nets",
            time_setup_minutes=10
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.75,
        priority=18,
        notes="Aspect crafts (Aspect of the Spider, Crab, Avian). Menagerie management."
    )
    
    strategies["incursion_temple"] = FarmingStrategy(
        name="Incursion Temple (Alva, Double Corrupts)",
        method=FarmingMethod.INCURSION,
        mechanic="Incursion encounters → Temple upgrades",
        league=league,
        applicability=Applicability.VERIFIED,
        requirements=FarmingRequirement(
            build_type="Incursion viable (fast movement, clear)",
            notes="Double corrupt room = double corrupt items. Alva missions."
        ),
        estimated_returns=EstimatedReturns(
            chaos_per_hour=300,
            custom={"double_corrupt_chance": "Per temple"}
        ),
        investment=Investment(
            currency_cost="Incursion map mods",
            time_setup_minutes=10
        ),
        source="poe.fandom.com",
        source_date="2026-11-10",
        league_tested=league,
        confidence=0.8,
        priority=19,
        notes="Double corrupt room for double corrupted items. Valuable bases."
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # OBSOLETE / REMOVED (for reference)
    # ═══════════════════════════════════════════════════════════════════
    
    # Scarab farming - REMOVED in 3.30, kept for reference
    if not is_330:
        strategies["scarab_farming"] = FarmingStrategy(
            name="Scarab Farming (REMOVED in 3.30)",
            method=FarmingMethod.MAP_FARMING,
            mechanic="Scarabs (REMOVED - replaced by Threads)",
            league=league,
            applicability=Applicability.OBSOLETE,
            requirements=FarmingRequirement(
                notes="Scarabs removed in 3.30. Use Thread farming instead."
            ),
            estimated_returns=EstimatedReturns(),
            investment=Investment(),
            source="patch notes 3.30",
            source_date="2026-11-10",
            league_tested="3.29",
            confidence=0.0,
            priority=999,
            notes="OBSOLETE: Scarabs converted to Threads or Frayed Threads in 3.30."
        )
    
    return strategies


# ─── Applicability Verification ──────────────────────────────────────

REMOVED_MECHANICS = [
    "harvest",      # Removed 3.19
    "metamorph",    # Removed 3.10
    "synthesis",    # Removed 3.6
    "perandus",     # Removed
    "talisman",     # Removed
    "scarab",       # Removed 3.30 → Threads
]

CHANGED_MECHANICS = {
    "delirium": "Mirror mechanics changed in 3.26",
    "expedition": "Logbook drops changed in 3.29",
    "heist": "Contract/blueprint changes in 3.25",
    "blight": "Oil changes in 3.28",
    "sanctum": "Relic system added 3.28",
    "mirage": "Added as core content in 3.30",
    "shaped regions": "Shaped Regions reworked in 3.30",
}


def check_applicability(strategy: FarmingStrategy, target_league: str = CURRENT_LEAGUE) -> dict:
    """Return applicability verdict with reasoning."""
    mechanic = strategy.mechanic.lower()
    
    # Check for removed mechanics
    for removed in REMOVED_MECHANICS:
        if removed in mechanic:
            return {
                "applicable": False,
                "verified": False,
                "reason": f"{removed.title()} mechanic removed",
                "action": "exclude"
            }
    
    # Check for changed mechanics
    for key, note in CHANGED_MECHANICS.items():
        if key in mechanic:
            return {
                "applicable": True,
                "verified": False,
                "note": note,
                "action": "verify"
            }
    
    # New mechanic in current league
    if target_league in LEAGUE_ALIASES and any(alias.lower() in mechanic for alias in LEAGUE_ALIASES[target_league]):
        return {
            "applicable": True,
            "verified": True,
            "note": f"New {target_league} mechanic",
            "action": "prioritize"
        }
    
    return {
        "applicable": True,
        "verified": True,
        "note": "Mechanic stable",
        "action": "trust"
    }


def verify_strategy(strategy: FarmingStrategy, target_league: str = CURRENT_LEAGUE) -> dict:
    """Full verification of a farming strategy."""
    result = {
        "strategy": strategy.name,
        "target_league": target_league,
        "checks": {},
        "verdict": "unknown",
        "confidence": 0.0
    }
    
    # 1. Mechanic existence check
    applicability = check_applicability(strategy, target_league)
    result["checks"]["mechanic_exists"] = applicability.get("applicable", True)
    result["checks"]["applicability_note"] = applicability.get("note", "")
    
    # 2. Economy viability (div/hr > 0.5)
    if strategy.estimated_returns.divine_per_hour > 0:
        result["checks"]["economy_viable"] = strategy.estimated_returns.divine_per_hour >= 0.5
    else:
        result["checks"]["economy_viable"] = True  # Non-currency strategies
    
    # 3. Confidence threshold
    result["checks"]["confidence_ok"] = strategy.confidence >= 0.5
    
    # Aggregate verdict
    passed = sum(1 for v in result["checks"].values() if v is True)
    total = len([k for k in result["checks"] if k != "applicability_note"])
    result["confidence"] = passed / total if total > 0 else 0
    
    if result["confidence"] >= 0.75:
        result["verdict"] = "recommended"
    elif result["confidence"] >= 0.5:
        result["verdict"] = "verify_manually"
    else:
        result["verdict"] = "not_recommended"
    
    return result


# ─── Priority Sorting ────────────────────────────────────────────────

def sort_strategies_by_priority(strategies: dict[str, FarmingStrategy]) -> list[FarmingStrategy]:
    """Sort strategies by priority (lower = higher priority), then by div/hr * confidence."""
    sorted_strats = sorted(
        strategies.values(),
        key=lambda s: (s.priority, -s.div_per_hour * s.confidence)
    )
    return sorted_strats


# ─── Decision Matrix Integration ────────────────────────────────────

DECISION_MATRIX = {
    "Buy finished": "Cheap, high supply, low crafting cost",
    "Craft from base": "Expensive/rare, deterministic path exists",
    "Improve current": "Good base, 1-2 missing mods, Harvest available",
    "Farm it yourself": "League-specific drops, boss-exclusive, high drop rate content",
    "Farm currency → Buy": "Stable currency farms, volatile item prices",
}

# 3.30 specific: Farm it yourself for new league content
DECISION_MATRIX_330 = {
    **DECISION_MATRIX,
    "Farm it yourself (Covens)": "Fate selection rewards, Viscera from Wickerman",
    "Farm it yourself (Threads)": "Thread drops from Shaped Regions",
    "Farm it yourself (Mirage)": "Mirage unique rewards",
}


# ─── Budget Allocation (3.30 Earthshatter Berserker example) ────────

BUDGET_ALLOCATION_330 = {
    "helmet_enchant": {"budget_pct": 100, "divine": 20, "method": "BUY_FINISHED"},
    "weapon_1": {"budget_pct": 250, "divine": 50, "method": "FARM_CURRENCY_THEN_BUY"},
    "body_armour": {"budget_pct": 400, "divine": 80, "method": "FARM_CURRENCY_THEN_BUY"},
    "gloves": {"budget_pct": 150, "divine": 30, "method": "FARM_CURRENCY_THEN_BUY"},
    "boots": {"budget_pct": 125, "divine": 25, "method": "FARM_CURRENCY_THEN_BUY"},
    "ashes_of_the_stars": {"budget_pct": 750, "divine": 150, "method": "TRADE_ONLY"},
    "mageblood": {"budget_pct": 1000, "divine": 200, "method": "TRADE_ONLY"},
    "rings": {"budget_pct": 200, "divine": 40, "method": "FARM_CURRENCY_THEN_BUY"},
    "circle_of_guilt": {"budget_pct": 300, "divine": 60, "method": "TRADE_ONLY"},
    "echoes_of_creation": {"budget_pct": 200, "divine": 40, "method": "TRADE_ONLY"},
}


# ─── Main API ────────────────────────────────────────────────────────

def get_farming_strategies(
    target_items: list[str] | None = None,
    league: str = CURRENT_LEAGUE,
    include_currency: bool = True,
    min_confidence: float = 0.5
) -> dict[str, FarmingStrategy]:
    """
    Get farming strategies for target items.
    
    Args:
        target_items: List of target items (base types, unique names, etc.)
        league: Target league (default: CURRENT_LEAGUE)
        include_currency: Always include divine/exalted/chaos farming
        min_confidence: Minimum confidence threshold
    
    Returns:
        Dict of strategy_name -> FarmingStrategy
    """
    all_strategies = build_strategies(league)
    
    # Always include currency farming
    result = {}
    if include_currency:
        for key in ["divine_orbs", "exalted_orbs", "chaos_orbs"]:
            if key in all_strategies:
                result[key] = all_strategies[key]
    
    # Filter item-specific strategies
    if target_items:
        target_str = " ".join(str(t).lower() for t in target_items)
        for key, strategy in all_strategies.items():
            if key in ["divine_orbs", "exalted_orbs", "chaos_orbs"]:
                continue  # Already included
            # Match by strategy name or mechanic
            if any(t.lower() in strategy.name.lower() or t.lower() in strategy.mechanic.lower() 
                   for t in target_items):
                if strategy.confidence >= min_confidence:
                    result[key] = strategy
    
    # Apply applicability verification
    verified = {}
    for key, strategy in result.items():
        verification = verify_strategy(strategy, league)
        if verification["verdict"] in ["recommended", "verify_manually"]:
            verified[key] = strategy
    
    return verified


def get_farming_recommendation(
    target_items: list[str],
    league: str = CURRENT_LEAGUE,
    budget_divine: float = 0
) -> dict:
    """Get complete farming recommendation with decision matrix."""
    strategies = get_farming_strategies(target_items, league)
    sorted_strats = sort_strategies_by_priority(strategies)
    
    # Build recommendation
    primary = sorted_strats[0] if sorted_strats else None
    currency_farms = [s for s in sorted_strats if "orbs" in s.name.lower()]
    item_farms = [s for s in sorted_strats if "orbs" not in s.name.lower()]
    
    # Decision matrix
    decision_matrix = DECISION_MATRIX_330 if league == "3.30" else DECISION_MATRIX
    
    return {
        "league": league,
        "target_items": target_items,
        "budget_divine": budget_divine,
        "primary_strategy": primary.to_dict() if primary else None,
        "currency_farming": [s.to_dict() for s in currency_farms],
        "item_farming": [s.to_dict() for s in item_farms],
        "decision_matrix": decision_matrix,
        "budget_allocation": BUDGET_ALLOCATION_330 if league == "3.30" else {},
        "total_strategies": len(sorted_strats),
        "verified_count": len([s for s in sorted_strats if s.applicability == Applicability.VERIFIED])
    }


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="PoB Farming Strategies")
    parser.add_argument("--items", nargs="+", help="Target items to farm for")
    parser.add_argument("--league", default=CURRENT_LEAGUE, help="Target league")
    parser.add_argument("--budget", type=float, default=0, help="Budget in divine orbs")
    parser.add_argument("--list", action="store_true", help="List all strategies")
    parser.add_argument("--verify", action="store_true", help="Verify all strategies for league")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.list:
        strategies = build_strategies(args.league)
        for name, strat in sorted(strategies.items(), key=lambda x: x[1].priority):
            print(f"  [{strat.priority}] {strat.name} ({strat.method.value}) - {strat.applicability.value} - {strat.div_per_hour} div/hr")
        return
    
    if args.verify:
        strategies = build_strategies(args.league)
        for name, strat in strategies.items():
            verification = verify_strategy(strat, args.league)
            print(f"  {strat.name}: {verification['verdict']} (confidence: {verification['confidence']:.2f}) - {verification['checks'].get('applicability_note', '')}")
        return
    
    if args.items:
        recommendation = get_farming_recommendation(args.items, args.league, args.budget)
        if args.json:
            print(json.dumps(recommendation, indent=2, default=str))
        else:
            print(f"\n🎯 Farming Recommendation for {args.league}")
            print(f"Target: {', '.join(args.items)}")
            print(f"Budget: {args.budget} div\n")
            
            if recommendation["primary_strategy"]:
                ps = recommendation["primary_strategy"]
                print(f"Primary: {ps['name']} ({ps['div_per_hour']} div/hr)")
                print(f"  Method: {ps['method']}")
                print(f"  Returns: {ps['estimated_returns']}")
                print(f"  Investment: {ps['investment']}")
                print()
            
            print("Currency Farming:")
            for s in recommendation["currency_farming"]:
                print(f"  - {s['name']}: {s['estimated_returns'].get('divine_per_hour', 0)} div/hr")
            
            print("\nItem-Specific Farming:")
            for s in recommendation["item_farming"]:
                print(f"  - {s['name']}: {s['estimated_returns'].get('divine_per_hour', 0)} div/hr")
            
            print(f"\nTotal strategies: {recommendation['total_strategies']}")
            print(f"Verified: {recommendation['verified_count']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()