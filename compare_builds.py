#!/usr/bin/env python3
"""
Build Comparison Script
========================
Compares Earthshatter Berserker vs Facebreaker Luminary at similar budget tiers.
"""

import sys
sys.path.insert(0, '/Users/joecrawford/.hermes/profiles/bot-of-exile/scripts')

from pob_target_build_store import (
    TargetBuildStore,
    create_earthshatter_berserker_template,
    create_budget_version_template,
    create_earthshatter_berserker_mid_tier,
    create_facebreaker_luminary_budget,
    create_facebreaker_luminary_mid_tier,
    create_facebreaker_luminary_god_tier,
)


def estimate_build_cost(build) -> tuple[int, int]:
    """Estimate min/max cost of a build in divines."""
    total_min = 0
    total_max = 0
    
    for item in build.items:
        # Rough estimates based on notes
        notes = item.notes.lower()
        if "div" in notes:
            import re
            numbers = re.findall(r'~?(\d+)[-–]?(\d+)?\s*div', notes)
            for match in numbers:
                if match[1]:
                    total_min += int(match[0])
                    total_max += int(match[1])
                else:
                    total_min += int(match[0])
                    total_max += int(match[0])
    
    return total_min, total_max


def print_build_summary(build):
    """Print a formatted build summary."""
    min_cost, max_cost = estimate_build_cost(build)
    print(f"\n{'='*70}")
    print(f"  {build.name}")
    print(f"  ID: {build.id}")
    print(f"  Class: {build.character_class} / {build.ascendancy}")
    print(f"  Main Skill: {build.main_skill}")
    print(f"  Est. Cost: {min_cost}-{max_cost} div")
    print(f"  Tags: {', '.join(build.tags)}")
    print(f"{'='*70}")
    
    # Group items by type
    uniques = [i for i in build.items if i.target_unique_name]
    rares = [i for i in build.items if not i.target_unique_name]
    
    print(f"\n  Uniques ({len(uniques)}):")
    for item in uniques:
        print(f"    {item.slot}: {item.target_unique_name} ({item.target_mods[:2]})")
    
    print(f"\n  Key Rares ({len(rares)}):")
    for item in rares:
        if item.crafting_priority == "High" or item.crafting_priority == "Critical":
            print(f"    {item.slot}: {item.base_type} - {item.target_mods[:3]}")


def compare_budget_tiers():
    """Compare builds at similar budget tiers."""
    
    print("\n" + "="*80)
    print("  BUILD COMPARISON: Earthshatter Berserker vs Facebreaker Luminary")
    print("  Grouped by Budget Tier")
    print("="*80)
    
    # Budget Tier (~30-50 div)
    print("\n\n📦 BUDGET TIER (~30-50 div) - League Starter")
    print("-" * 60)
    
    berserker_budget = create_budget_version_template()
    luminary_budget = create_facebreaker_luminary_budget()
    
    print_build_summary(berserker_budget)
    print_build_summary(luminary_budget)
    
    print("\n  KEY DIFFERENCES (Budget):")
    print("  • Berserker: Self-sufficient, own warcries, 2H axe, Rage mechanic")
    print("  • Luminary: Requires Merc (Rallying Cry), Facebreakers + Shield, Block")
    print("  • Berserker: Resolute Technique via tree, 100% Overwhelm (Bastion Breaker)")
    print("  • Luminary: Resolute Technique keystone, Block + Armour, Glancing Blows")
    print("  • Luminary needs Flat Phys on Amulet (CRITICAL - ~10-20 div)")
    print("  • Luminary needs Merc survival (3.30: -60% merc res, but merc rarely dies)")
    
    # Mid Tier (~150-200 div)
    print("\n\n📦 MID TIER (~150-200 div) - Solid Endgame")
    print("-" * 60)
    
    berserker_mid = create_earthshatter_berserker_mid_tier()
    luminary_mid = create_facebreaker_luminary_mid_tier()
    
    print_build_summary(berserker_mid)
    print_build_summary(luminary_mid)
    
    print("\n  KEY DIFFERENCES (Mid):")
    print("  • Berserker: Echoes of Creation, Ashes, Mageblood, Circle of Guilt")
    print("  • Luminary: The Anvil, The Fourth Vow, Ralakesh's Impatience, Deep Breaths")
    print("  • Berserker: 1600+ pDPS axe, 3000+ armour, 100% Overwhelm")
    print("  • Luminary: Aegis/Anvil shield, Phys as Cold (Fourth Vow), Block cap")
    print("  • Both use: Mob Mentality clusters, Impossible Escape, Deep Breaths anoint")
    
    # God Tier (800+ div)
    print("\n\n📦 GOD TIER (800+ div) - Mirror Tier")
    print("-" * 60)
    
    berserker_god = create_earthshatter_berserker_template()
    luminary_god = create_facebreaker_luminary_god_tier()
    
    print_build_summary(berserker_god)
    print_build_summary(luminary_god)
    
    print("\n  KEY DIFFERENCES (God):")
    print("  • Berserker: Mirror-tier axe (1600+ pDPS), Ashes, Mageblood, Echoes")
    print("  • Luminary: Mirror-tier Facebreakers (+2 gems), Aegis Aurora, Watcher's Eye")
    print("  • Berserker: 100% Overwhelm, Rage mastery, 100% crit avoidance via RT")
    print("  • Luminary: Aegis Aurora (ES on block), Phys as Cold, Block cap, Watcher's Eye")


def show_farming_strategies():
    """Show farming strategies for each tier."""
    from pob_farming_strategies import get_farming_strategies, get_farming_recommendation
    
    print("\n\n📦 FARMING STRATEGIES BY TIER")
    print("="*80)
    
    tiers = [
        ("Budget (~50 div)", ["Facebreakers", "Fowlorn", "Deep Breaths", "Flat Phys Amulet"]),
        ("Mid (~200 div)", ["The Anvil", "The Fourth Vow", "Ralakesh's", "T1 Flat Phys Amulet"]),
        ("God (~800 div)", ["Aegis Aurora", "Mirror Facebreakers", "Watcher's Eye", "T1 Flat Phys Amulet"]),
    ]
    
    for tier_name, targets in tiers:
        print(f"\n  {tier_name}:")
        rec = get_farming_recommendation(targets, league="3.30")
        if rec["primary_strategy"]:
            ps = rec["primary_strategy"]
            print(f"    Primary: {ps['name']} ({ps['estimated_returns'].get('divine_per_hour', 0)} div/hr)")
            print(f"    Method: {ps['method']}")
            print(f"    Investment: {ps['investment'].get('currency_cost', 'N/A')}")
        
        for cf in rec["currency_farming"][:2]:
            print(f"    Currency: {cf['name']} ({cf['estimated_returns'].get('divine_per_hour', 0)} div/hr)")


if __name__ == "__main__":
    compare_budget_tiers()
    show_farming_strategies()
    
    print("\n\n" + "="*80)
    print("  RECOMMENDATION FOR 36/40 CHALLENGES")
    print("="*80)
    print("""
  For 36/40 challenges in 3.30 Covens of Umbra:
  
  🏆 RECOMMENDED: Earthshatter Berserker (Budget → Mid)
  
  Reasons:
  1. No merc dependency - merc AI can fail during challenges
  2. Higher single-target ceiling for Uber bosses (Sirus, Maven, Exarch/Eater)
  3. 100% Overwhelm trivializes high-armor pinnacle bosses
  4. Proven HCSSF viability (Ben hit 99 in 3 days self-found)
  5. Self-sufficient - no merc management during hectic challenge content
  
  Switch to Facebreaker Luminary if:
  • You want cheaper start (~30 div vs ~50 div for berserker budget)
  • You enjoy merc mechanics and auto warcrys
  • You prefer block + Resolute Technique playstyle
  • You want seamless swap from 2H axe leveling
  
  Budget Progression Path:
  Week 1-2:   Berserker Budget (~50 div) → Farm currency
  Week 3-4:   Berserker Mid (~200 div) → Push challenges
  Week 5+:    Optional swap to Luminary Mid if you prefer playstyle
""")


if __name__ == "__main__":
    compare_budget_tiers()