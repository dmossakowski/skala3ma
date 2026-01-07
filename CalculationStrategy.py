
import json
from datetime import datetime, date, timedelta



class CalculationStrategy:

    # these results represent the categories in the competition
    # there are three categories for women and three for men
    # this should be improved to be more dynamic
    emptyResults = {"M":{ "0":[], "1":[], "2":[]}, "F":{"0":[], "1":[], "2":[] }}


    # Legacy integer codes (kept for backward compatibility)
    calc_type_fsgt0 = 0
    calc_type_fsgt1 = 1

    # Strategy registry: slug -> {"class": cls, "label": str}
    registry = {}
    legacy_map = {0: 'fsgt0', 1: 'fsgt1'}

    @classmethod
    def register(cls, slug, strategy_class, label=None):
        if not isinstance(slug, str) or not slug:
            raise ValueError("Strategy slug must be a non-empty string")
        cls.registry[slug] = {"class": strategy_class, "label": label or slug}

    @classmethod
    def normalize_strategy_key(cls, key):
        """
        Normalize a calculation strategy key to a registered slug.
        - Accepts legacy ints (0/1/2), numeric strings, or existing slugs.
        """
     
        # None -> default base
        if key is None:
            return f"fsgt1"

        # Legacy int -> base 
        if isinstance(key, int):
            base = cls.legacy_map.get(key, None)
            return f"{base}"


        # String handling
        if isinstance(key, str):
            # first check if it's already a known slug
            if key in cls.registry:
                return key
            # Numeric string -> legacy int
            try:
                base = cls.legacy_map.get(int(key), None)
                return f"{base}"
            except ValueError:       
                return None

        # Fallback -> default base + audience
        return None

    @classmethod
    def get_strategy_class(cls, key, audience: str = 'adult'):
        slug = cls.normalize_strategy_key(key)
        entry = cls.registry.get(slug)
        if entry is None:
            raise ValueError(f"Unknown calculation strategy: {slug}")
        return entry["class"], slug

    @classmethod
    def create_strategy(cls, key, audience: str = 'adult'):
        strategy_class, _ = cls.get_strategy_class(key, audience=audience)
        return strategy_class()

    @classmethod
    def list_calc_types(cls):
        # Return list of {slug, label}
        return [{"slug": s, "label": v.get("label", s)} for s, v in cls.registry.items()]

    def recalculate(self, competition):
        raise NotImplementedError("Subclasses should implement this!")
    