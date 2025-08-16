
from typing import Dict, List
from .constants import DEFAULTS

def render_codes_block(mapping: Dict) -> str:
    cpt_lines = mapping.get("cpt", [])
    icd = mapping.get("icd10", [])
    mods = mapping.get("modifiers", [])
    out = []
    if cpt_lines:
        out.append("Codes:")
        out.append("  CPT: " + ", ".join(cpt_lines + (["Modifiers: " + " ".join(mods)] if mods else [])))
    if icd:
        out.append("  ICD-10: " + ", ".join(icd))
    return "\n".join(out)

def render_note(domain: str, inputs: Dict, mapping: Dict) -> str:
    anesthesia = inputs.get("anesthesia", DEFAULTS["anesthesia"])
    indications = inputs.get("indications", DEFAULTS["indications"])
    selected_areas = inputs.get("selected_areas", [])
    irrigation = inputs.get("irrigation", DEFAULTS["irrigation"])
    cultures = inputs.get("cultures", DEFAULTS["cultures"])
    biopsy = inputs.get("biopsy", DEFAULTS["biopsy"])
    closure_type = inputs.get("closure_type", DEFAULTS["closure_type"])
    packing_media = inputs.get("packing_media", DEFAULTS["packing_media"])
    negative_pressure = inputs.get("negative_pressure", DEFAULTS["negative_pressure"])
    transport_status = inputs.get("transport_status", DEFAULTS["transport_status"])
    vascularity = inputs.get("vascularity", DEFAULTS.get("vascularity","Good"))
    per_area_flags = inputs.get("per_area_flags", {})
    depths = inputs.get("per_area_depths", {})

    lines = []
    lines.append("Indications: " + ", ".join(indications) + ". Informed consent for the procedure was confirmed.")
    area_hint = selected_areas[0] if selected_areas else "operative site"
    lines.append(f"{anesthesia} anesthesia was obtained  and then the {area_hint.lower()} was prepped and draped in sterile manner.")
    if selected_areas:
        lines.append("Operative fields: " + ", ".join(selected_areas) + ".")

    culture_clause = ""
    if cultures:
        if any(c.lower().startswith("swab") for c in cultures):
            culture_clause = " Purulence encountered was drained and swab sent for culture."
        else:
            culture_clause = " Purulence encountered was drained and cultures obtained."
    biopsy_clause = ""
    if biopsy:
        if "Bone" in biopsy:
            biopsy_clause = " Biopsy of bone was sent to pathology."
        elif "Tissue" in biopsy:
            biopsy_clause = " Biopsy of tissue was sent to pathology."
    irrig_clause = ""
    if irrigation:
        irrig_clause = " Irrigation performed with copious " + " and ".join(irrigation) + "."
    lines.append("An incision was made through the indurated area or wound and dissection carried down to the bone and deep compartment." + culture_clause + biopsy_clause + irrig_clause)

    detail_bits = []
    order = ["skin","subq","fascia","muscle","bone"]
    for area in selected_areas:
        lvl_strs = []
        for lvl in order:
            spec = depths.get(area, {}).get(lvl, {})
            size = spec.get("size")
            inst = spec.get("instrument")
            if size and float(size) > 0:
                unit = "cm²" if lvl in ("skin","fascia") else "cm³"
                extra = ""
                if lvl == "bone":
                    bone_name = spec.get("bone_name","")
                    if bone_name:
                        extra = f" ({bone_name})"
                lvl_strs.append(f"{lvl} {float(size):.1f}{unit} using {inst}{extra}")
        if lvl_strs:
            detail_bits.append(f"{area}: " + "; ".join(lvl_strs))
    if detail_bits:
        lines.append("Excision of infected/necrotic tissue was performed including: " + " ".join([s if s.endswith('.') else s + '.' for s in detail_bits]) + f" Vascularity was noted to be {'normal' if vascularity=='Good' else vascularity.lower()}.")

    wm = []
    if closure_type == "Packing":
        wm.append("Packing placed using: " + ", ".join(packing_media) + ".")
    elif closure_type == "Partial closure":
        partial = inputs.get("partial_suture", {"material": [], "technique": []})
        wm.append("Partial layered closure was performed with: " + "; ".join(partial.get("material", [])) + " using techniques: " + ", ".join(partial.get("technique", [])) + ".")
    elif closure_type == "Negative pressure foam dressing":
        size_npwt = inputs.get("npwt_size_cm2", 0)
        size_text = f" for a wound measuring {float(size_npwt):.1f} cm²" if size_npwt else ""
        wm.append(f"Negative pressure wound therapy applied ({negative_pressure}) at 125 mmHg{size_text}.")
    elif closure_type == "Artificial/Skin graft":
        graft = inputs.get("graft", {"type": None, "defect_size": "", "graft_size": ""})
        wm.append(f"Graft type: {graft.get('type')}; defect size {graft.get('defect_size')}; graft size {graft.get('graft_size')}.")
    elif closure_type == "Delayed closure":
        deep = inputs.get("delayed_deep", {"material_tech": "2-0 PDS simple"}).get("material_tech", "2-0 PDS simple")
        sup = inputs.get("delayed_superficial", {"material_tech": "3-0 nylon simple"}).get("material_tech", "3-0 nylon simple")
        wm.append(f"Delayed layered closure documented. Deep sutures: {deep}. Superficial sutures: {sup}.")
    band = inputs.get("bandage", {"first": ["Sofsorb"], "second": ["Kerlix"], "third": ["Ace wrap"], "splint": "None"})
    wm.append("Dressings applied: First layer " + (", ".join(band.get("first", [])) if band.get("first") else "") +
              "; Second layer " + (", ".join(band.get("second", [])) if band.get("second") else "") +
              "; Third layer " + (", ".join(band.get("third", [])) if band.get("third") else "") + f". Splint: {band.get('splint','None')}.")
    lines.append("The wounds were then managed as follows: " + " ".join(wm))

    lines.append("The patient was transported to recovery in " + transport_status + " condition.")

    flag_lines = []
    for area in selected_areas:
        flags = per_area_flags.get(area, {})
        lt = flags.get("lesion_type", "Wound")
        inf = "infected" if flags.get("infected") else "not overtly infected"
        if flags.get("deep_compartment"):
            cnt = int(flags.get("deep_compartment_count", 1) or 1)
            suffix = f"deep compartment drained ×{cnt}"
            flag_lines.append(f"{area}: {lt}, {inf}, {suffix}")
        else:
            flag_lines.append(f"{area}: {lt}, {inf}")
    if flag_lines:
        lines.append("Area status summary: " + " | ".join(flag_lines) + ".")

    codes_block = render_codes_block(mapping)
    if codes_block:
        lines.append("")
        lines.append(codes_block)

    return "\n".join(lines)
