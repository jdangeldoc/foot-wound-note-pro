
from dataclasses import dataclass, field
from typing import Dict, List
import math
import os
import pandas as pd
from .constants import DATA_DIR

@dataclass
class MappingResult:
    cpt: List[str] = field(default_factory=list)
    icd10: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)

def _load_crosswalks():
    cpt_path = os.path.join(DATA_DIR, "cpt_mapping.csv")
    icd_path = os.path.join(DATA_DIR, "icd_mapping.csv")
    cpt_df = pd.read_csv(cpt_path, dtype=str, on_bad_lines="skip")
    icd_df = pd.read_csv(icd_path, dtype=str, on_bad_lines="skip")
    return cpt_df, icd_df

def _laterality_modifier(laterality: str, bilateral: bool) -> List[str]:
    if bilateral:
        return ["-50"]
    if laterality == "Right":
        return ["-RT"]
    if laterality == "Left":
        return ["-LT"]
    return []

def _return_modifier(encounter_timing: str) -> List[str]:
    if encounter_timing.lower().startswith("planned"):
        return ["-58"]
    if encounter_timing.lower().startswith("unplanned"):
        return ["-78"]
    return []

def _add_on_units(area_cm2: float, base_threshold: float = 20.0) -> int:
    if area_cm2 <= base_threshold:
        return 0
    remaining = max(0.0, area_cm2 - base_threshold)
    return math.ceil(remaining / 20.0)

def map_to_coding(domain: str, inputs: Dict) -> MappingResult:
    cpt_df, icd_df = _load_crosswalks()
    res = MappingResult()

    clinical_dx = inputs.get("clinical_dx", [])
    comorb = inputs.get("comorbidities", [])
    laterality = inputs.get("laterality", "Right")
    # ICD mapping
    def pick_icd(label: str) -> List[str]:
        df = icd_df[icd_df["label"] == label]
        codes = []
        if not df.empty:
            lat_df = df[df["laterality"].str.lower() == laterality.lower()] if laterality in ("Left","Right") else pd.DataFrame()
            if not lat_df.empty:
                codes.extend(lat_df["icd10"].tolist())
            if not codes:
                codes.extend(df["icd10"].tolist())
        return codes
    for dx in clinical_dx:
        res.icd10 += pick_icd(dx)
        if pick_icd(dx):
            res.rationale.append(f"ICD for '{dx}': {', '.join(pick_icd(dx))}")
    for c in comorb:
        res.icd10 += pick_icd(c)
        if pick_icd(c):
            res.rationale.append(f"ICD for comorbidity '{c}': {', '.join(pick_icd(c))}")
    # unique
    res.icd10 = list(dict.fromkeys(res.icd10))

    # Debridement depth aggregation
    depths = inputs.get("per_area_depths", {})
    total_area_by_level = {"skin":0.0,"subq":0.0,"fascia":0.0,"muscle":0.0,"bone":0.0}
    for area, levels in depths.items():
        for lvl, spec in levels.items():
            try:
                total_area_by_level[lvl] += float(spec.get("size", 0.0))
            except Exception:
                pass

    if any(v > 0 for v in total_area_by_level.values()):
        level_priority = ["bone","muscle","fascia","subq","skin"]
        for lvl in level_priority:
            area_cm2 = total_area_by_level.get(lvl, 0.0)
            if area_cm2 > 0:
                if lvl == "bone":
                    base, addon = "11044","11047"
                elif lvl in ("muscle","fascia"):
                    base, addon = "11043","11046"
                elif lvl == "subq":
                    base, addon = "11042","11045"
                else:
                    base, addon = "11042","11045"
                res.cpt.append(base)
                units = _add_on_units(area_cm2, 20.0)
                res.cpt.extend([addon]*units)
                res.rationale.append(f"Debridement {lvl}: {area_cm2:.1f} cm² → base {base} + {units}× add-on")
                break

    # Deep / superficial I&D for foot; deep for hand with compartment count
    per_area_flags = inputs.get("per_area_flags", {})
    for area, flags in per_area_flags.items():
        area_l = area.lower()
        deep = bool(flags.get("deep_compartment"))
        deep_count = int(flags.get("deep_compartment_count", 0) or 0)
        infected = bool(flags.get("infected"))
        if "hand" in area_l:
            if deep and deep_count > 0:
                res.cpt.extend(["26025"] * deep_count)
                res.rationale.append(f"Deep space hand I&D for {area} ×{deep_count} → CPT 26025 per compartment")
        elif "foot" in area_l or "toe" in area_l or "calcaneus" in area_l or "heel" in area_l:
            if deep and deep_count > 0:
                res.cpt.extend(["28003"] * deep_count)
                res.rationale.append(f"Deep compartment foot I&D for {area} ×{deep_count} → CPT 28003 per compartment")
            elif infected and not deep:
                res.cpt.append("28002")
                res.rationale.append(f"Superficial foot I&D for {area} → CPT 28002")


    # NPWT (Negative Pressure Wound Therapy) size-based coding
    if inputs.get("closure_type") == "Negative pressure foam dressing":
        try:
            size_npwt = float(inputs.get("npwt_size_cm2", 0) or 0)
        except Exception:
            size_npwt = 0.0
        if size_npwt > 0:
            if size_npwt <= 50.0:
                res.cpt.append("97605")
                res.rationale.append(f"NPWT ≤50 cm² → CPT 97605 (size {size_npwt:.1f} cm²)")
            else:
                res.cpt.append("97606")
                res.rationale.append(f"NPWT >50 cm² → CPT 97606 (size {size_npwt:.1f} cm²)")
    

    # Skin graft CPT mapping
    if inputs.get("closure_type") == "Artificial/Skin graft":
        gtype = (inputs.get("graft",{}).get("type") or "").lower()
        try:
            size = float(inputs.get("graft",{}).get("defect_size",0) or 0)
        except Exception:
            size = 0.0
        if size > 0:
            if "split" in gtype:
                # STSG 15100/15101
                res.cpt.append("15100")
                res.rationale.append(f"STSG {size:.1f} cm² → CPT 15100")
                if size > 100:
                    addons = int(((size-100)+99)//100)
                    res.cpt.extend(["15101"]*addons)
                    res.rationale.append(f"STSG add-ons ×{addons} → CPT 15101")
            elif "full" in gtype:
                # FTSG 15200/15201
                res.cpt.append("15200")
                res.rationale.append(f"FTSG {size:.1f} cm² → CPT 15200")
                if size > 20:
                    addons = int(((size-20)+19)//20)
                    res.cpt.extend(["15201"]*addons)
                    res.rationale.append(f"FTSG add-ons ×{addons} → CPT 15201")
            elif "artificial" in gtype or "novosorb" in gtype:
                # Artificial/Biologic 15271/15272
                res.cpt.append("15271")
                res.rationale.append(f"Artificial graft {size:.1f} cm² → CPT 15271")
                if size > 25:
                    addons = int(((size-25)+24)//25)
                    res.cpt.extend(["15272"]*addons)
                    res.rationale.append(f"Artificial graft add-ons ×{addons} → CPT 15272")
    # Skin Graft Mapping (STSG/FTSG/Artificial) - defensive
    if inputs.get("closure_type") == "Artificial/Skin graft":
        size_cm2 = 0.0
        # 1) Prefer explicit numeric
        try:
            size_cm2 = float(inputs.get("graft_size_cm2", 0) or 0)
        except Exception:
            size_cm2 = 0.0
        # 2) Fallback: parse from text
        if size_cm2 <= 0:
            try:
                import re as _re
                ds = str(inputs.get("graft",{}).get("defect_size",""))
                m = _re.search(r'([\d\.]+)', ds)
                if m: size_cm2 = float(m.group(1))
            except Exception:
                pass
        gtype = (inputs.get("graft",{}).get("type","") or "").lower()
        if gtype:
            if "split thickness" in gtype:  # STSG: 15100 + 15101 per 100 cm²
                if size_cm2 > 0:
                    res.cpt.append("15100")
                    if size_cm2 > 100.0:
                        add_units = math.ceil((size_cm2 - 100.0)/100.0)
                        res.cpt.extend(["15101"]*add_units)
                        res.rationale.append(f"STSG {size_cm2:.1f} cm² → 15100 + {add_units}×15101")
                    else:
                        res.rationale.append(f"STSG {size_cm2:.1f} cm² → 15100")
                else:
                    res.cpt.append("15100")
                    res.rationale.append("STSG size not entered → defaulted to base 15100")
            elif "full thickness" in gtype:  # FTSG: 15200 + 15201 per 20 cm²
                if size_cm2 > 0:
                    res.cpt.append("15200")
                    if size_cm2 > 20.0:
                        add_units = math.ceil((size_cm2 - 20.0)/20.0)
                        res.cpt.extend(["15201"]*add_units)
                        res.rationale.append(f"FTSG {size_cm2:.1f} cm² → 15200 + {add_units}×15201")
                    else:
                        res.rationale.append(f"FTSG {size_cm2:.1f} cm² → 15200")
                else:
                    res.cpt.append("15200")
                    res.rationale.append("FTSG size not entered → defaulted to base 15200")
            elif "artificial" in gtype or "novasorb" in gtype or "novosorb" in gtype:
                if size_cm2 > 0:
                    res.cpt.append("15271")
                    if size_cm2 > 25.0:
                        add_units = math.ceil((size_cm2 - 25.0)/25.0)
                        res.cpt.extend(["15272"]*add_units)
                        res.rationale.append(f"Artificial skin substitute {size_cm2:.1f} cm² → 15271 + {add_units}×15272")
                    else:
                        res.rationale.append(f"Artificial skin substitute {size_cm2:.1f} cm² → 15271")
                else:
                    res.cpt.append("15271")
                    res.rationale.append("Artificial skin substitute size not entered → defaulted to base 15271")

    # Delayed wound closure mapping
    if inputs.get("closure_type") == "Delayed closure":
        res.cpt.append("13160")
        res.rationale.append("Delayed wound closure → CPT 13160")

    # Modifiers

    res.modifiers += _laterality_modifier(laterality, inputs.get("bilateral", False))
    res.modifiers += _return_modifier(inputs.get("encounter_timing",""))


    # One-per-session post-processing rules
    if inputs.get("one_per_session"):
        # 13160 only once
        if res.cpt.count("13160") > 1:
            # keep first, remove extras
            first_kept = False
            new_cpt = []
            for code in res.cpt:
                if code == "13160":
                    if not first_kept:
                        new_cpt.append(code); first_kept = True
                    else:
                        continue
                else:
                    new_cpt.append(code)
            res.cpt = new_cpt
            res.rationale.append("One-per-session: 13160 deduplicated to a single unit")
        # 28003 capped to 1
        if res.cpt.count("28003") > 1:
            seen = False
            capped = []
            for code in res.cpt:
                if code == "28003":
                    if not seen:
                        capped.append(code); seen = True
                    else:
                        continue
                else:
                    capped.append(code)
            res.cpt = capped
            res.rationale.append("One-per-session: 28003 capped at one unit")

    return res
