
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
    calc_type_fsgt2 = 2

    # Strategy registry: slug -> {"class": cls, "label": str}
    registry = {}
    legacy_map = {0: 'fsgt0', 1: 'fsgt1', 2: 'fsgt2'}

    @classmethod
    def register(cls, slug, strategy_class, label=None):
        if not isinstance(slug, str) or not slug:
            raise ValueError("Strategy slug must be a non-empty string")
        cls.registry[slug] = {"class": strategy_class, "label": label or slug}

    @classmethod
    def normalize_strategy_key(cls, key):
        # Accept int legacy codes, string slugs, or None
        if key is None:
            return 'fsgt1'  # default
        if isinstance(key, int):
            return cls.legacy_map.get(key, 'fsgt1')
        if isinstance(key, str):
            # If a numeric string, treat as legacy int
            try:
                n = int(key)
                return cls.legacy_map.get(n, 'fsgt1')
            except ValueError:
                return key
        # Fallback
        return 'fsgt1'

    @classmethod
    def get_strategy_class(cls, key):
        slug = cls.normalize_strategy_key(key)
        entry = cls.registry.get(slug)
        if entry is None:
            raise ValueError(f"Unknown calculation strategy: {slug}")
        return entry["class"], slug

    @classmethod
    def create_strategy(cls, key):
        strategy_class, _ = cls.get_strategy_class(key)
        return strategy_class()

    @classmethod
    def list_available_strategies(cls):
        # Return list of {slug, label}
        return [{"slug": s, "label": v.get("label", s)} for s, v in cls.registry.items()]

    def recalculate(self, competition):
        raise NotImplementedError("Subclasses should implement this!")


    
    def get_category_from_dob(dob):
        if dob is None:
            return -1
        dob = datetime.strptime(dob, "%Y-%m-%d")
        # Calculate the age
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Determine the category based on age
        if 18 <= age <= 49:
            return 0
        elif 50 <= age <= 64:
            return 1
        elif age >= 65:
            return 2
        elif 12 <= age <= 13:
            return 0
        elif 14 <= age <= 15:
            return 1
        elif 16 <= age <= 17:
            return 2
        else:
            return -1  # Return -1 if age does not fit any category

    @classmethod
    def get_category_from_dob_for(cls, dob, key):
        # If the resolved strategy defines an override, use it; else fall back to base
        strategy_class, _ = cls.get_strategy_class(key)
        # Prefer a static/class method on the strategy
        override = getattr(strategy_class, 'get_category_from_dob', None)
        if callable(override) and override is not CalculationStrategy.get_category_from_dob:
            return override(dob)
        return CalculationStrategy.get_category_from_dob(dob)