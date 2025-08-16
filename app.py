
import os, json
import pandas as pd
import streamlit as st
import pyperclip

from core.constants import APP_NAME, VERSION, DATA_DIR, DEFAULTS, ZONES, HAND_FOOT_AREAS
from core.mapping_engine import map_to_coding
from core.note_generator import render_note
from core.exporters import export_to_pdf, export_to_docx, export_to_json

st.set_page_config(page_title=APP_NAME, layout="wide")
st.title(f"{APP_NAME} — {VERSION}")
st.caption("Orthopedic coding + operative note generator (offline, local).")

# ---------- Session ----------
for key, default in [
    ("selected_areas", []),
    ("per_area_flags", {}),
    ("per_area_depths", {}),
    ("note_text",""),
    ("mapping_dict",{}),
]:
    if key not in st.session_state: st.session_state[key] = default

def reset_all():
    for k in ["selected_areas","per_area_flags","per_area_depths","note_text","mapping_dict"]:
        st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else {}

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Controls")
    laterality = st.radio("Laterality", options=["Left","Right","Bilateral"], index=1)
    bilateral = laterality == "Bilateral"
    effective_lat = "Right" if laterality=="Right" else ("Left" if laterality=="Left" else "Right")
    encounter_timing = st.selectbox("Procedure timing", ["First encounter","Planned return to OR","Unplanned return to OR"], index=0)
    one_per_session = st.toggle("One-per-session rules (13160 only once; 28003 capped to 1)")

    admin_mode = st.toggle("Admin mode (edit code tables)")
    if st.button("Reset (clear + restore defaults)"):
        reset_all()
        st.experimental_rerun()

# ---------- Data tables (load + admin) ----------
def _prep_for_editor(df):
    import pandas as _pd
    if isinstance(df.index, _pd.MultiIndex) or df.index.name is not None:
        df = df.reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    if isinstance(df.columns, _pd.MultiIndex):
        df.columns = [" ".join([str(x) for x in tup if x is not None]).strip() for tup in df.columns.values]
    return df

cpt_df = pd.read_csv(os.path.join(DATA_DIR,"cpt_mapping.csv"), dtype=str, on_bad_lines="skip")
icd_df = pd.read_csv(os.path.join(DATA_DIR,"icd_mapping.csv"), dtype=str, on_bad_lines="skip")
cpt_df = _prep_for_editor(cpt_df); icd_df = _prep_for_editor(icd_df)

if admin_mode:
    st.sidebar.subheader("CPT/ICD Tables")
    with st.sidebar.expander("CPT crosswalk (save to persist)"):
        edt = st.data_editor(cpt_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save CPT crosswalk"):
            edt.to_csv(os.path.join(DATA_DIR,"cpt_mapping.csv"), index=False)
            st.success("CPT crosswalk saved.")
    with st.sidebar.expander("ICD-10 crosswalk (save to persist)"):
        ed2 = st.data_editor(icd_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save ICD crosswalk"):
            ed2.to_csv(os.path.join(DATA_DIR,"icd_mapping.csv"), index=False)
            st.success("ICD-10 crosswalk saved.")

# ---------- Area list (no diagrams) ----------
FEET_FIRST = [
    "Plantar foot (L)","Dorsum foot (L)","Heel/Calcaneus (L)","Sinus tarsi (L)",
    "Great toe (L)","Second toe (L)","Third toe (L)","Fourth toe (L)","Fifth toe (L)",
    "Plantar foot (R)","Dorsum foot (R)","Heel/Calcaneus (R)","Sinus tarsi (R)",
    "Great toe (R)","Second toe (R)","Third toe (R)","Fourth toe (R)","Fifth toe (R)"
]
HANDS_ALL = sorted([a for a in HAND_FOOT_AREAS if "hand" in a.lower() or "finger" in a.lower()])
BODY_ALL = sorted(list({label for key in ["body_front","body_back"] for (label,_) in ZONES[key]} - set(FEET_FIRST) - set(HANDS_ALL)))
MASTER_AREAS = FEET_FIRST + HANDS_ALL + BODY_ALL

st.subheader("Areas & Inputs")
st.markdown("Use the list to select areas (feet first). No diagrams.")
pick = st.multiselect("Select one or more areas", MASTER_AREAS, default=[])
colA, colB = st.columns(2)
with colA:
    if st.button("Add selected areas"):
        for area in pick:
            if area not in st.session_state.selected_areas:
                st.session_state.selected_areas.append(area)
                st.session_state.per_area_flags.setdefault(area, {"lesion_type":"Wound","infected":True,"deep_compartment":False,"deep_compartment_count":0})
                st.session_state.per_area_depths.setdefault(area, {
                    "skin":{"instrument":"Scalpel","size":0.0},
                    "subq":{"instrument":"Rongeur","size":0.0},
                    "fascia":{"instrument":"Scalpel","size":0.0},
                    "muscle":{"instrument":"Scalpel","size":0.0},
                    "bone":{"instrument":"Rongeur","size":0.0,"bone_name":""}
                })
        st.success("Areas added below.")
with colB:
    if st.button("Clear selected areas"):
        st.session_state.selected_areas = []


# --- Selected Areas Management ---
st.markdown("#### Selected areas (manage)")
sel_current = st.multiselect("Currently selected", st.session_state.selected_areas, default=st.session_state.selected_areas, key="sel_current_view")
cols_mg = st.columns(3)
with cols_mg[0]:
    if st.button("Remove highlighted areas"):
        to_remove = set(sel_current)
        st.session_state.selected_areas = [a for a in st.session_state.selected_areas if a not in to_remove]
        for a in list(st.session_state.per_area_flags.keys()):
            if a in to_remove: del st.session_state.per_area_flags[a]
        for a in list(st.session_state.per_area_depths.keys()):
            if a in to_remove: del st.session_state.per_area_depths[a]
        st.success("Removed highlighted areas.")
with cols_mg[1]:
    if st.button("Clear ALL areas"):
        st.session_state.selected_areas = []
        st.session_state.per_area_flags.clear()
        st.session_state.per_area_depths.clear()
        st.success("All areas cleared.")
with cols_mg[2]:
    pass


st.divider()
st.markdown("### Indications & Diagnoses")
indications = st.multiselect("Indications",
    ["Induration","Swelling","Erythema","Tenderness","Open wound","Drainage","X-ray findings","MRI findings","Elevated WBC","Elevated ESR/CRP"],
    default=DEFAULTS["indications"])
clinical_dx = st.multiselect("Clinical diagnoses",
    ["Diabetic ulcer","Cellulitis","Acute osteomyelitis (ankle/foot) RIGHT","Acute osteomyelitis (ankle/foot) LEFT",
     "Chronic osteomyelitis (ankle/foot) RIGHT","Chronic osteomyelitis (ankle/foot) LEFT",
     "Abscess","Dry gangrene","Septic gangrene with ascending lymphangitis","Septic foot","Necrosis of skin",
     "Abscess of deep compartment of foot","Necrotizing fasciitis"],
    default=DEFAULTS["clinical_dx"])
comorb = st.multiselect("Comorbidities",
    ["Diabetes with neuropathy","Diabetes with foot ulcer","Peripheral vascular disease","Atherosclerosis of native arteries of extremities",
     "Smoking","Noncompliance","Morbid obesity","COPD","Chronic kidney disease"], default=[])

st.divider()
st.markdown("### Per-area details")
if st.session_state.selected_areas:
    for area in st.session_state.selected_areas:
        with st.expander(area, expanded=True):
            # Per-area remove
            if st.button(f"Remove area — {area}", key=f"rm_{area}"):
                if area in st.session_state.selected_areas:
                    st.session_state.selected_areas.remove(area)
                st.session_state.per_area_flags.pop(area, None)
                st.session_state.per_area_depths.pop(area, None)
                st.experimental_rerun()
            flags = st.session_state.per_area_flags.get(area, {})
            depths = st.session_state.per_area_depths.get(area, {})
            flags["lesion_type"] = st.selectbox(f"{area} — Lesion type", ["Wound","Induration"], index=0, key=f"lt_{area}")
            flags["infected"] = st.checkbox(f"{area} — Infection present", value=flags.get("infected", True), key=f"inf_{area}")
            is_hf = any(s in area.lower() for s in ["hand","foot","toe","heel","calcaneus"])
            if is_hf:
                flags["deep_compartment"] = st.checkbox(f"{area} — Deep compartment involved/drained", value=flags.get("deep_compartment", False), key=f"deep_{area}")
                if flags["deep_compartment"]:
                    flags["deep_compartment_count"] = st.number_input(f"{area} — Number of compartments (1–6)", min_value=1, max_value=6, value=int(flags.get("deep_compartment_count",1) or 1), step=1, key=f"deepcnt_{area}")
                else:
                    flags["deep_compartment_count"] = 0
            st.session_state.per_area_flags[area] = flags

            st.write("**Lines for depth of debridement**")
            cols = st.columns(5)
            options = {
                "skin":["Scalpel"],
                "subq":["Scalpel","Scissors","Rongeur"],
                "fascia":["Scalpel","Scissors","Rongeur"],
                "muscle":["Scalpel","Rongeur","Scissors"],
                "bone":["Rongeur","Saw","Curette"]
            }
            defaults = {"skin":"Scalpel","subq":"Rongeur","fascia":"Scalpel","muscle":"Scalpel","bone":"Rongeur"}
            units = {"skin":"cm²","fascia":"cm²","subq":"cm³","muscle":"cm³","bone":"cm³"}
            levels = ["skin","subq","fascia","muscle","bone"]
            for idx,lvl in enumerate(levels):
                with cols[idx]:
                    inst = st.selectbox(f"{lvl.title()} instrument", options[lvl], index=options[lvl].index(defaults[lvl]), key=f"{area}_{lvl}_inst")
                    size = st.number_input(f"{lvl.title()} size ({units[lvl]})", min_value=0.0, value=float(depths.get(lvl,{}).get("size",0.0)), step=1.0, key=f"{area}_{lvl}_size")
                    if lvl=="bone":
                        bone_name = st.text_input("Bone name", value=depths.get(lvl,{}).get("bone_name",""), key=f"{area}_bone_name")
                        depths[lvl] = {"instrument": inst, "size": size, "bone_name": bone_name}
                    else:
                        depths[lvl] = {"instrument": inst, "size": size}
            st.session_state.per_area_depths[area] = depths
else:
    st.info("Use the list above to add areas.")

# ---- Global Debridement Lines Matrix (All Areas) ----
st.divider()
st.markdown("### Debridement Lines Matrix (All Areas) — edit in one place")
import pandas as _pd

def _areas_to_matrix():
    rows = []
    for area in st.session_state.selected_areas:
        flags = st.session_state.per_area_flags.get(area, {"lesion_type":"Wound","infected":True,"deep_compartment":False,"deep_compartment_count":0})
        d = st.session_state.per_area_depths.get(area, {})
        rows.append({
            "Area": area,
            "Skin inst": d.get("skin",{}).get("instrument","Scalpel"),
            "Skin size (cm²)": float(d.get("skin",{}).get("size",0.0) or 0.0),
            "Subq inst": d.get("subq",{}).get("instrument","Rongeur"),
            "Subq size (cm³)": float(d.get("subq",{}).get("size",0.0) or 0.0),
            "Fascia inst": d.get("fascia",{}).get("instrument","Scalpel"),
            "Fascia size (cm²)": float(d.get("fascia",{}).get("size",0.0) or 0.0),
            "Muscle inst": d.get("muscle",{}).get("instrument","Scalpel"),
            "Muscle size (cm³)": float(d.get("muscle",{}).get("size",0.0) or 0.0),
            "Bone inst": d.get("bone",{}).get("instrument","Rongeur"),
            "Bone size (cm³)": float(d.get("bone",{}).get("size",0.0) or 0.0),
            "Bone name": d.get("bone",{}).get("bone_name",""),
            "Deep compartment (hand/foot)": bool(flags.get("deep_compartment", False)),
            "Deep count (1–6)": int(flags.get("deep_compartment_count",0) or 0)
        })
    return _pd.DataFrame(rows)

if st.session_state.selected_areas:
    if "matrix_df" not in st.session_state:
        st.session_state.matrix_df = _areas_to_matrix()
    else:
        # Keep matrix in sync with any newly added areas
        st.session_state.matrix_df = _areas_to_matrix()
    matrix_edit = st.data_editor(
        st.session_state.matrix_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Area": st.column_config.TextColumn(disabled=True),
            "Skin inst": st.column_config.SelectboxColumn(options=["Scalpel"], default="Scalpel"),
            "Subq inst": st.column_config.SelectboxColumn(options=["Scalpel","Scissors","Rongeur"], default="Rongeur"),
            "Fascia inst": st.column_config.SelectboxColumn(options=["Scalpel","Scissors","Rongeur"], default="Scalpel"),
            "Muscle inst": st.column_config.SelectboxColumn(options=["Scalpel","Rongeur","Scissors"], default="Scalpel"),
            "Bone inst": st.column_config.SelectboxColumn(options=["Rongeur","Saw","Curette"], default="Rongeur"),
        }
    )
    if st.button("Apply Debridement Matrix to Session"):
        for _, row in matrix_edit.iterrows():
            area = str(row.get("Area","")).strip()
            if not area: continue
            st.session_state.per_area_depths[area] = {
                "skin":{"instrument": row.get("Skin inst","Scalpel"), "size": float(row.get("Skin size (cm²)",0.0) or 0.0)},
                "subq":{"instrument": row.get("Subq inst","Rongeur"), "size": float(row.get("Subq size (cm³)",0.0) or 0.0)},
                "fascia":{"instrument": row.get("Fascia inst","Scalpel"), "size": float(row.get("Fascia size (cm²)",0.0) or 0.0)},
                "muscle":{"instrument": row.get("Muscle inst","Scalpel"), "size": float(row.get("Muscle size (cm³)",0.0) or 0.0)},
                "bone":{"instrument": row.get("Bone inst","Rongeur"), "size": float(row.get("Bone size (cm³)",0.0) or 0.0), "bone_name": str(row.get("Bone name",""))}
            }
            flags = st.session_state.per_area_flags.get(area, {"lesion_type":"Wound","infected":True,"deep_compartment":False,"deep_compartment_count":0})
            flags["deep_compartment"] = bool(row.get("Deep compartment (hand/foot)", False))
            flags["deep_compartment_count"] = int(row.get("Deep count (1–6)",0) or 0)
            st.session_state.per_area_flags[area] = flags
        st.success("Matrix applied. Now click **Code & Write Note**.")
else:
    st.caption("Add areas above to activate the matrix.")


# Quick editor remains (optional)
st.divider()
st.markdown("### Cultures / Biopsy / Irrigation / Closure / Dressings")
biopsy = st.multiselect("Biopsy", ["Tissue","Bone"], default=[])
cultures = st.multiselect("Cultures", ["Swab","Soft tissue","Bone"], default=DEFAULTS["cultures"])
irrigation = st.multiselect("Irrigation", ["Saline","Betadine","Antibiotic"], default=DEFAULTS["irrigation"])
closure = st.selectbox("Closure", ["Packing","Partial closure","Negative pressure foam dressing","Artificial/Skin graft","Delayed closure"], index=0)
packing_media = []
partial_suture = {"material": [], "technique": []}
graft = {"type": None, "defect_size": "", "graft_size": ""}
delayed_deep = {"material_tech": "2-0 PDS simple"}
delayed_superficial = {"material_tech": "3-0 nylon simple"}

if closure == "Packing":
    packing_media = st.multiselect("Packing media", ["Saline gauze","1/4% acetic acid gauze","Betadine gauze","Other"], default=["Saline gauze"])
elif closure == "Partial closure":
    partial_suture["material"] = st.multiselect("Suture", ["0 Prolene","2-0 Prolene","3-0 Nylon","4-0 Nylon"], default=["0 Prolene"])
    partial_suture["technique"] = st.multiselect("Technique", ["Simple","Vertical mattress","Horizontal mattress"], default=["Simple"])
elif closure == "Negative pressure foam dressing":
    graft_size_cm2 = 0.0
    negative_p = st.radio("Foam", ["Plain","Silver"], index=1)
    npwt_size_cm2 = st.number_input("NPWT wound size (cm²) — sum across treated wounds", min_value=0.0, value=0.0, step=1.0)
elif closure == "Artificial/Skin graft":
    npwt_size_cm2 = 0.0
    graft["type"] = st.selectbox("Graft type", ["Split thickness skin graft","Full thickness skin graft","Artificial skin (Novasorb)"], index=0)
    graft["defect_size"] = st.text_input("Defect size (e.g., 6x4 cm)", value="")
    graft["graft_size"] = st.text_input("Graft size (e.g., 6x4 cm)", value="")
elif closure == "Delayed closure":
    graft_size_cm2 = 0.0
    npwt_size_cm2 = 0.0
    delayed_deep["material_tech"] = st.selectbox("Deep suture", ["2-0 Monocryl simple","3-0 Monocryl simple","2-0 Vicryl simple","3-0 Vicryl simple","2-0 PDS simple","3-0 PDS simple"], index=4)
    delayed_superficial["material_tech"] = st.selectbox("Superficial suture", ["2-0 Prolene simple","3-0 Prolene simple","3-0 Nylon simple","4-0 Nylon simple"], index=2)

first = st.multiselect("First layer", ["Sofsorb","Adaptic","Xeroform","Telfa","Gauze","Cotton balls w/ mineral oil + betadine","Other","None"], default=["Sofsorb"])
second = st.multiselect("Second layer", ["Kerlix","Kling","Sterile Webril","None"], default=["Kerlix"])
third = st.multiselect("Third layer", ["Ace wrap","Coban","None"], default=["Ace wrap"])
splint = st.selectbox("Splint", ["None","Short leg","Short arm","Hand","Long arm","Long leg"], index=0)

st.divider()
st.markdown("### Anesthesia & Post-op")
anesthesia = st.radio("Anesthesia", ["General","Local","Regional"], index=0)
transport_status = st.radio("Post-op status", ["Stable","Unstable"], index=0)

if st.button("Code & Write Note"):
    npwt_size_cm2 = float(locals().get("npwt_size_cm2", 0.0) or 0.0)
    # Fallback: if no areas explicitly selected, infer from any area that has depth entries
    if not st.session_state.selected_areas and st.session_state.per_area_depths:
        st.session_state.selected_areas = list(st.session_state.per_area_depths.keys())
    inputs = {
        "selected_areas": st.session_state.selected_areas,
        "per_area_flags": st.session_state.per_area_flags,
        "per_area_depths": st.session_state.per_area_depths,
        "indications": indications,
        "clinical_dx": clinical_dx,
        "comorbidities": comorb,
        "laterality": effective_lat,
        "bilateral": bilateral,
        "encounter_timing": encounter_timing,
        "biopsy": biopsy,
        "cultures": cultures,
        "irrigation": irrigation,
        "closure_type": closure,
        "packing_media": packing_media,
        "partial_suture": partial_suture,
        "graft": graft, "graft_size_cm2": float(locals().get("graft_size_cm2", 0.0) or 0.0),
        "delayed_deep": delayed_deep,
        "delayed_superficial": delayed_superficial,
        "bandage": {"first": first, "second": second, "third": third, "splint": splint},
        "vascularity": DEFAULTS["vascularity"],
        "arthrotomy": {"enabled": False, "joint": ""},
        "metatarsal_head_resection": {"enabled": False, "count": 0},
        "anesthesia": anesthesia,
        "transport_status": transport_status,
        "one_per_session": one_per_session
    }
    mapping = map_to_coding("wound", inputs)
    mapping_dict = {"cpt": mapping.cpt, "icd10": mapping.icd10, "modifiers": mapping.modifiers, "rationale": mapping.rationale}
    note = render_note("wound", inputs, mapping_dict)
    st.session_state.mapping_dict = mapping_dict
    st.session_state.note_text = note
    if not mapping.cpt:
        st.warning("No CPT debridement/I&D codes generated. Enter sizes (cm²/cm³) or set deep-compartment count.")

with st.container(border=True):
    st.markdown("#### Operative Note + Codes (copy as one block)")
    if st.session_state.note_text:
        st.text(st.session_state.note_text)
        if st.button("Copy note + codes to clipboard"):
            pyperclip.copy(st.session_state.note_text)
            st.success("Copied to clipboard.")
    else:
        st.info("Click 'Code & Write Note' above to render.")

# ---------- Tables tab ----------
st.divider()
st.subheader("Searchable CPT/ICD Tables")
q = st.text_input("Filter CPT/ICD by keyword")
cpt_show = cpt_df.copy(); icd_show = icd_df.copy()
if q:
    ql = q.lower()
    cpt_show = cpt_show[cpt_show.apply(lambda r: any(ql in str(v).lower() for v in r), axis=1)]
    icd_show = icd_show[icd_show.apply(lambda r: any(ql in str(v).lower() for v in r), axis=1)]
st.write("**CPT Crosswalk**"); st.dataframe(cpt_show, use_container_width=True, height=240)
st.write("**ICD-10 Crosswalk**"); st.dataframe(icd_show, use_container_width=True, height=240)
