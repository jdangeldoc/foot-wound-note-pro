
from core.mapping_engine import map_to_coding
from core.constants import DEFAULTS

def test_vascularity_default_good():
    assert DEFAULTS["vascularity"] == "Good"

def test_debridement_addons_bone():
    inputs = {
        "selected_areas": ["Dorsum foot (R)"],
        "per_area_flags": {"Dorsum foot (R)": {"lesion_type":"Wound","infected":True,"deep_compartment":False,"deep_compartment_count":0}},
        "per_area_depths": {"Dorsum foot (R)": {
            "skin":{"instrument":"Scalpel","size":0.0},
            "subq":{"instrument":"Rongeur","size":0.0},
            "fascia":{"instrument":"Scalpel","size":0.0},
            "muscle":{"instrument":"Scalpel","size":0.0},
            "bone":{"instrument":"Rongeur","size":55.0,"bone_name":"Metatarsal"}
        }},
        "indications": [], "clinical_dx": ["Abscess"], "comorbidities": [],
        "laterality":"Right", "bilateral": False, "encounter_timing": "First encounter",
        "biopsy":[], "cultures":[], "irrigation":[], "closure_type":"Packing",
        "packing_media":[], "partial_suture":{"material":[],"technique":[]},
        "graft":{"type":None,"defect_size":"","graft_size":""},
        "delayed_deep":{"material_tech":"2-0 PDS simple"},
        "delayed_superficial":{"material_tech":"3-0 nylon simple"},
        "bandage":{"first":[],"second":[],"third":[],"splint":"None"},
        "vascularity":"Good",
        "arthrotomy":{"enabled":False,"joint":""},
        "metatarsal_head_resection":{"enabled":False,"count":0},
        "anesthesia":"General","transport_status":"Stable"
    }
    res = map_to_coding("wound", inputs)
    assert res.cpt[0] == "11044"
    assert res.cpt.count("11047") == 2

def test_foot_deep_compartment_counts():
    inputs = {
        "selected_areas": ["Plantar foot (R)"],
        "per_area_flags": {"Plantar foot (R)": {"lesion_type":"Wound","infected":True,"deep_compartment":True,"deep_compartment_count":3}},
        "per_area_depths": {},
        "indications": [], "clinical_dx": ["Abscess"], "comorbidities": [],
        "laterality":"Right", "bilateral": False, "encounter_timing": "First encounter",
        "biopsy":[], "cultures":[], "irrigation":[], "closure_type":"Packing",
        "packing_media":[], "partial_suture":{"material":[],"technique":[]},
        "graft":{"type":None,"defect_size":"","graft_size":""},
        "delayed_deep":{"material_tech":"2-0 PDS simple"},
        "delayed_superficial":{"material_tech":"3-0 nylon simple"},
        "bandage":{"first":[],"second":[],"third":[],"splint":"None"},
        "vascularity":"Good",
        "arthrotomy":{"enabled":False,"joint":""},
        "metatarsal_head_resection":{"enabled":False,"count":0},
        "anesthesia":"General","transport_status":"Stable"
    }
    res = map_to_coding("wound", inputs)
    assert res.cpt.count("28003") == 3
