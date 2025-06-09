"""
Final Fantasy XI game data configuration for the marketplace bot.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Zone configurations with their subcategories and items
ZONE_DATA = {
    "sky": {
        "display_name": "Sky",
        "description": "Tu'Lia and related sky zones",
        "subcategories": {
            "All Sky Gods": {
                "display_name": "All Sky Gods",
                "items": [
                    "All Items",
                    "Shura Zunari Kabuto",
                    "Shura Haidate",
                    "Shura Togi",
                    "Shura Tegoshi",
                    "Shura Sune-ate",
                    "Haubergeon",
                    "Byakko's Haidate",
                    "Suzaku's Sune-ate",
                    "Genbu's Shield",
                    "Seiryu's Kote",
                    "Peacock Charm",
                    "Peacock Amulet",
                    "Speed Belt",
                    "Justice Badge",
                    "Fortitude Torque",
                    "Hope Torque",
                    "Faith Torque"
                ]
            },
            "Kirin": {
                "display_name": "Kirin",
                "items": [
                    "All Items",
                    "Shining Cloth",
                    "Kirin's Osode",
                    "Kirin's Pole",
                    "Neptunal Abjuration: Head",
                    "Neptunal Abjuration: Body",
                    "Neptunal Abjuration: Hands",
                    "Neptunal Abjuration: Legs",
                    "Neptunal Abjuration: Feet",
                    "Dryadic Abjuration: Head",
                    "Dryadic Abjuration: Body",
                    "Dryadic Abjuration: Hands",
                    "Dryadic Abjuration: Legs",
                    "Dryadic Abjuration: Feet",
                    "Earthen Abjuration: Head",
                    "Earthen Abjuration: Body",
                    "Earthen Abjuration: Hands",
                    "Earthen Abjuration: Legs",
                    "Earthen Abjuration: Feet"
                ]
            },
            "Suzaku": {
                "display_name": "Suzaku",
                "items": [
                    "All Items",
                    "Suzaku's Sune-ate",
                    "Crimson Blade",
                    "Peacock Charm",
                    "Suzaku Feather"
                ]
            },
            "Seiryu": {
                "display_name": "Seiryu",
                "items": [
                    "All Items",
                    "Seiryu's Kote",
                    "Cobalt Blade",
                    "Peacock Amulet",
                    "Seiryu Seal"
                ]
            },
            "Genbu": {
                "display_name": "Genbu",
                "items": [
                    "All Items",
                    "Genbu's Shield",
                    "Amber Blade",
                    "Speed Belt",
                    "Genbu Shell"
                ]
            },
            "Byakko": {
                "display_name": "Byakko",
                "items": [
                    "All Items",
                    "Byakko's Haidate",
                    "White Blade",
                    "Justice Badge",
                    "Byakko Fur"
                ]
            }
        }
    },
    
    "sea": {
        "display_name": "Sea",
        "description": "Sea Serpent Grotto and Limbus zones",
        "subcategories": {
            "All Sea Gods": {
                "display_name": "All Sea Gods",
                "items": [
                    "All Items",
                    "Novio Earring",
                    "Brutal Earring",
                    "Suppanomimi",
                    "Ethereal Earring",
                    "Magnetic Earring",
                    "Hollow Earring",
                    "Infernal Earring",
                    "Coral Earring",
                    "Hope Torque",
                    "Faith Torque",
                    "Fortitude Torque"
                ]
            },
            "Jailer of Hope": {
                "display_name": "Jailer of Hope",
                "items": [
                    "All Items",
                    "Hope Torque",
                    "Novio Earring",
                    "Brutal Earring",
                    "Hope's Bane"
                ]
            },
            "Jailer of Justice": {
                "display_name": "Jailer of Justice",
                "items": [
                    "All Items",
                    "Suppanomimi",
                    "Ethereal Earring",
                    "Justice Torque"
                ]
            },
            "Jailer of Faith": {
                "display_name": "Jailer of Faith",
                "items": [
                    "All Items",
                    "Faith Torque",
                    "Magnetic Earring",
                    "Hollow Earring"
                ]
            },
            "Jailer of Fortitude": {
                "display_name": "Jailer of Fortitude",
                "items": [
                    "All Items",
                    "Fortitude Torque",
                    "Infernal Earring",
                    "Coral Earring"
                ]
            },
            "Absolute Virtue": {
                "display_name": "Absolute Virtue",
                "items": [
                    "All Items",
                    "Virtue Stone",
                    "Neptunal Abjuration: Head",
                    "Neptunal Abjuration: Body",
                    "Neptunal Abjuration: Hands",
                    "Neptunal Abjuration: Legs",
                    "Neptunal Abjuration: Feet"
                ]
            }
        }
    },
    
    "dynamis": {
        "display_name": "Dynamis",
        "description": "Dynamis zones and currency farming",
        "subcategories": {
            "All Dynamis": {
                "display_name": "All Dynamis Zones",
                "items": [
                    "All Items",
                    "Ancient Currency",
                    "Relic Armor",
                    "Relic Weapons",
                    "Dynamis Currency",
                    "100 Byne Bills",
                    "1 Montiont Silverpiece",
                    "1 Ranperre's Goldpiece",
                    "1 Lungo-Nango Jadeshell"
                ]
            },
            "Dynamis - Bastok": {
                "display_name": "Dynamis - Bastok",
                "items": [
                    "All Items",
                    "Relic Armor +1",
                    "Hydra Corps",
                    "Hydra Salade",
                    "Hydra Brayettes",
                    "Hydra Moufles",
                    "Hydra Sollerets",
                    "100 Byne Bills",
                    "Ancient Currency"
                ]
            },
            "Dynamis - San d'Oria": {
                "display_name": "Dynamis - San d'Oria",
                "items": [
                    "All Items",
                    "Relic Armor +1",
                    "Crusader's Armor",
                    "Temple Crown",
                    "Temple Cyclas",
                    "Temple Gloves",
                    "Temple Hose",
                    "Temple Gaiters",
                    "1 Montiont Silverpiece",
                    "Ancient Currency"
                ]
            },
            "Dynamis - Windurst": {
                "display_name": "Dynamis - Windurst",
                "items": [
                    "All Items",
                    "Relic Armor +1",
                    "Sorcerer's Petasos",
                    "Sorcerer's Coat",
                    "Sorcerer's Gloves",
                    "Sorcerer's Tonban",
                    "Sorcerer's Sabots",
                    "1 Ranperre's Goldpiece",
                    "Ancient Currency"
                ]
            },
            "Dynamis - Jeuno": {
                "display_name": "Dynamis - Jeuno",
                "items": [
                    "All Items",
                    "Relic Armor +1",
                    "Relic Weapons",
                    "Apocalypse",
                    "Ragnarok",
                    "Redemption",
                    "Spharai",
                    "Mandau",
                    "Excalibur",
                    "1 Lungo-Nango Jadeshell",
                    "Ancient Currency"
                ]
            }
        }
    },
    
    "limbus": {
        "display_name": "Limbus",
        "description": "Limbus zones and Homam/Nashira gear",
        "subcategories": {
            "All Limbus": {
                "display_name": "All Limbus Zones",
                "items": [
                    "All Items",
                    "Homam Gear",
                    "Nashira Gear",
                    "Ancient Beastcoin",
                    "Limbus Chips",
                    "Temenos Chips",
                    "Apollyon Chips"
                ]
            },
            "Temenos": {
                "display_name": "Temenos",
                "items": [
                    "All Items",
                    "Homam Zucchetto",
                    "Homam Corazza",
                    "Homam Manopolas",
                    "Homam Cosciales",
                    "Homam Gambieras",
                    "Ancient Beastcoin",
                    "Temenos Orb"
                ]
            },
            "Apollyon": {
                "display_name": "Apollyon",
                "items": [
                    "All Items",
                    "Nashira Turban",
                    "Nashira Manteel",
                    "Nashira Gages",
                    "Nashira Seraweels",
                    "Nashira Crackows",
                    "Ancient Beastcoin",
                    "Apollyon Orb"
                ]
            },
            "Omega": {
                "display_name": "Omega",
                "items": [
                    "All Items",
                    "Omega's Eye",
                    "Homam Gear",
                    "Nashira Gear",
                    "Ancient Beastcoin"
                ]
            },
            "Ultima": {
                "display_name": "Ultima",
                "items": [
                    "All Items",
                    "Ultima's Cerebrum",
                    "Homam Gear",
                    "Nashira Gear",
                    "Ancient Beastcoin"
                ]
            }
        }
    },
    
    "others": {
        "display_name": "Others",
        "description": "Other endgame content and miscellaneous items",
        "subcategories": {
            "Einherjar": {
                "display_name": "Einherjar",
                "items": [
                    "All Items",
                    "Odin's Gear",
                    "Freyr's Gear",
                    "Gleipnir",
                    "Gungnir",
                    "Defending Ring",
                    "Amanomurakumo"
                ]
            },
            "Salvage": {
                "display_name": "Salvage",
                "items": [
                    "All Items",
                    "Usukane Gear",
                    "Serafim Gear",
                    "Morrigan Gear",
                    "Skadi Gear",
                    "35 Piece",
                    "15 Piece",
                    "Alexandrite"
                ]
            },
            "ZNMs": {
                "display_name": "Zeni Notorious Monsters",
                "items": [
                    "All Items",
                    "Tier I ZNM Pops",
                    "Tier II ZNM Pops",
                    "Tier III ZNM Pops",
                    "Pandemonium Key",
                    "ZNM Gear",
                    "Zeni"
                ]
            },
            "HNMs": {
                "display_name": "High Notorious Monsters",
                "items": [
                    "All Items",
                    "Ridill",
                    "Kraken Club",
                    "Haubergeon",
                    "Adaman Hauberk",
                    "Defending Ring",
                    "Herald's Gaiters",
                    "Crimson Cuisses"
                ]
            },
            "Crafting": {
                "display_name": "Crafting Materials",
                "items": [
                    "All Items",
                    "HQ Synthesis Materials",
                    "Rare Gems",
                    "Alexandrite",
                    "Damascus Ingot",
                    "Wootz Ore",
                    "Voidstone",
                    "Dragon Heart"
                ]
            },
            "Currency": {
                "display_name": "Currency Items",
                "items": [
                    "All Items",
                    "Ancient Currency",
                    "Dynamis Currency",
                    "Imperial Standing",
                    "Assault Points",
                    "Zeni",
                    "Therion Ichor",
                    "Allied Notes"
                ]
            },
            "Misc": {
                "display_name": "Miscellaneous",
                "items": [
                    "All Items",
                    "Rare/Ex Gear",
                    "Testimony Items",
                    "Key Items",
                    "Consumables",
                    "Furniture",
                    "Chocobo Items"
                ]
            }
        }
    }
}

# Listing type configurations
LISTING_TYPES = {
    "WTS": {
        "display_name": "Want to Sell",
        "emoji": "🔸",
        "color": 0xF59E0B,  # Amber
        "description": "Items you want to sell"
    },
    "WTB": {
        "display_name": "Want to Buy", 
        "emoji": "🔹",
        "color": 0x3B82F6,  # Blue
        "description": "Items you want to buy"
    }
}

# Time zone configurations
TIMEZONE_DATA = {
    "GMT": {
        "display_name": "GMT/UTC",
        "description": "Greenwich Mean Time / Coordinated Universal Time",
        "offset": 0
    },
    "EU": {
        "display_name": "EU (CET/CEST)",
        "description": "Central European Time",
        "offset": 1
    },
    "NA": {
        "display_name": "NA (EST/PST)",
        "description": "North American Time Zones",
        "offset": -5  # EST as default
    },
    "JST": {
        "display_name": "JST",
        "description": "Japan Standard Time",
        "offset": 9
    }
}

# Reputation role thresholds
REPUTATION_THRESHOLDS = {
    "trusted_trader": {
        "min_rating": 4.5,
        "min_count": 10,
        "role_name": "Trusted Trader",
        "color": 0x10B981,  # Green
        "description": "Highly trusted community member"
    },
    "verified_trader": {
        "min_rating": 4.0,
        "min_count": 5,
        "role_name": "Verified Trader",
        "color": 0x3B82F6,  # Blue
        "description": "Verified community trader"
    },
    "restricted_trader": {
        "max_rating": 2.5,
        "min_count": 3,
        "role_name": "Restricted Trader",
        "color": 0xEF4444,  # Red
        "description": "Limited marketplace access"
    }
}

def get_zone_subcategories(zone: str) -> List[str]:
    """Get subcategories for a specific zone."""
    try:
        zone_lower = zone.lower()
        if zone_lower in ZONE_DATA:
            return list(ZONE_DATA[zone_lower]["subcategories"].keys())
        
        logger.warning(f"Zone not found: {zone}")
        return []
        
    except Exception as e:
        logger.error(f"Error getting subcategories for zone {zone}: {e}")
        return []

def get_subcategory_items(zone: str, subcategory: str) -> List[str]:
    """Get items for a specific subcategory within a zone."""
    try:
        zone_lower = zone.lower()
        if zone_lower in ZONE_DATA:
            subcategories = ZONE_DATA[zone_lower]["subcategories"]
            if subcategory in subcategories:
                return subcategories[subcategory]["items"]
        
        logger.warning(f"Subcategory not found: {zone}/{subcategory}")
        return []
        
    except Exception as e:
        logger.error(f"Error getting items for {zone}/{subcategory}: {e}")
        return []

def get_all_zones() -> List[str]:
    """Get list of all available zones."""
    try:
        return list(ZONE_DATA.keys())
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return []

def get_zone_display_name(zone: str) -> str:
    """Get display name for a zone."""
    try:
        zone_lower = zone.lower()
        if zone_lower in ZONE_DATA:
            return ZONE_DATA[zone_lower]["display_name"]
        return zone.title()
    except Exception as e:
        logger.error(f"Error getting display name for zone {zone}: {e}")
        return zone.title()

def get_zone_description(zone: str) -> str:
    """Get description for a zone."""
    try:
        zone_lower = zone.lower()
        if zone_lower in ZONE_DATA:
            return ZONE_DATA[zone_lower]["description"]
        return f"Content from {zone.title()}"
    except Exception as e:
        logger.error(f"Error getting description for zone {zone}: {e}")
        return f"Content from {zone.title()}"

def validate_zone_subcategory_item(zone: str, subcategory: str, item: str) -> bool:
    """Validate that a zone/subcategory/item combination exists."""
    try:
        items = get_subcategory_items(zone, subcategory)
        return item in items or item == "All Items"
    except Exception as e:
        logger.error(f"Error validating zone/subcategory/item: {e}")
        return False

def get_listing_type_config(listing_type: str) -> Dict[str, any]:
    """Get configuration for a listing type."""
    try:
        if listing_type in LISTING_TYPES:
            return LISTING_TYPES[listing_type]
        
        logger.warning(f"Unknown listing type: {listing_type}")
        return {
            "display_name": listing_type,
            "emoji": "📋",
            "color": 0x6B7280,
            "description": f"{listing_type} listings"
        }
    except Exception as e:
        logger.error(f"Error getting listing type config: {e}")
        return {}

def get_reputation_role_config(reputation_avg: float, reputation_count: int) -> Optional[Dict[str, any]]:
    """Get appropriate reputation role configuration based on stats."""
    try:
        for role_key, config in REPUTATION_THRESHOLDS.items():
            min_rating = config.get("min_rating", 0)
            max_rating = config.get("max_rating", 5)
            min_count = config.get("min_count", 0)
            
            if (reputation_count >= min_count and 
                min_rating <= reputation_avg <= max_rating):
                return config
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting reputation role config: {e}")
        return None

def search_items(query: str, zone: str = None) -> List[Dict[str, str]]:
    """Search for items across zones or within a specific zone."""
    try:
        results = []
        query_lower = query.lower()
        
        zones_to_search = [zone.lower()] if zone else ZONE_DATA.keys()
        
        for zone_key in zones_to_search:
            if zone_key not in ZONE_DATA:
                continue
                
            zone_data = ZONE_DATA[zone_key]
            
            for subcat_name, subcat_data in zone_data["subcategories"].items():
                for item in subcat_data["items"]:
                    if query_lower in item.lower():
                        results.append({
                            "item": item,
                            "zone": zone_key,
                            "subcategory": subcat_name,
                            "zone_display": zone_data["display_name"]
                        })
        
        # Remove duplicates and sort
        unique_results = []
        seen = set()
        for result in results:
            key = (result["item"], result["zone"], result["subcategory"])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return sorted(unique_results, key=lambda x: x["item"])
        
    except Exception as e:
        logger.error(f"Error searching items: {e}")
        return []

def get_popular_items(zone: str = None, limit: int = 10) -> List[str]:
    """Get list of popular/commonly traded items."""
    try:
        # This would ideally be based on actual marketplace data
        # For now, return some commonly sought items
        popular_items = [
            "Haubergeon",
            "Ridill", 
            "Kraken Club",
            "Hope Torque",
            "Brutal Earring",
            "Novio Earring",
            "Suppanomimi",
            "Homam Corazza",
            "Nashira Manteel",
            "Ancient Currency",
            "Shura Zunari Kabuto",
            "Kirin's Osode",
            "Defending Ring",
            "Peacock Charm",
            "Justice Badge"
        ]
        
        if zone:
            # Filter items relevant to the zone
            zone_items = []
            for subcat_data in ZONE_DATA.get(zone.lower(), {}).get("subcategories", {}).values():
                zone_items.extend(subcat_data.get("items", []))
            
            # Return popular items that exist in this zone
            filtered_items = [item for item in popular_items if item in zone_items]
            return filtered_items[:limit]
        
        return popular_items[:limit]
        
    except Exception as e:
        logger.error(f"Error getting popular items: {e}")
        return []

# Configuration validation
def validate_ffxi_data_integrity():
    """Validate the integrity of FFXI data configuration."""
    try:
        errors = []
        
        # Check that all zones have required fields
        for zone_key, zone_data in ZONE_DATA.items():
            if "display_name" not in zone_data:
                errors.append(f"Zone {zone_key} missing display_name")
            
            if "subcategories" not in zone_data:
                errors.append(f"Zone {zone_key} missing subcategories")
                continue
            
            # Check subcategories
            for subcat_key, subcat_data in zone_data["subcategories"].items():
                if "display_name" not in subcat_data:
                    errors.append(f"Subcategory {zone_key}/{subcat_key} missing display_name")
                
                if "items" not in subcat_data:
                    errors.append(f"Subcategory {zone_key}/{subcat_key} missing items")
                elif not isinstance(subcat_data["items"], list):
                    errors.append(f"Subcategory {zone_key}/{subcat_key} items must be a list")
                elif "All Items" not in subcat_data["items"]:
                    errors.append(f"Subcategory {zone_key}/{subcat_key} must include 'All Items'")
        
        if errors:
            logger.error(f"FFXI data validation errors: {errors}")
            return False
        
        logger.info("FFXI data validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating FFXI data: {e}")
        return False

# Initialize validation on import
if __name__ == "__main__":
    validate_ffxi_data_integrity()
