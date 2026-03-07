import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from streamlit.components.v1 import html

# ===== Admin helpers =====
def _atomic_write_csv_with_backup(df, target_path: str) -> str:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    backups = Path("backups")
    backups.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = backups / f"{target.stem}_{ts}{target.suffix}"
    df.to_csv(backup, index=False)
    tmp = target.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, target)   # atomic on NTFS
    return str(backup)

def _show_diag(bundle: dict | None):
    import platform
    st.write("### Diagnostics")
    st.write({
        "python": platform.python_version(),
        "streamlit": st.__version__,
        "cwd": str(Path.cwd()),
        "files_present": [p.name for p in Path('.').glob('*')],
        "bundle_example": bundle or {}
    })
# ===== End Admin helpers =====



from core.mapping_engine import compute_coding_bundle, suggest_icd10_from_rows
from core.note_generator import generate_note_text
from core.exporters import export_docx, export_json

st.set_page_config(page_title="OrthoCoder Pro", layout="wide")
st.title("OrthoCoder Pro — Feature Pack 1.3")
st.caption("Multi-site entry • Delete rows • ICD‑10 infection crosswalk w/ overrides • Full op note • DOCX/JSON • Copy & Clear")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Encounter Settings")
    packs = st.multiselect(
        "Comorbidity Packs (encounter‑wide)",
        options=[
            "Diabetes + Neuropathy",
            "PVD + Ulcer",
            "PVD + Gangrene",
            "Smoker",
            "Chronic Kidney Disease",
            "Heart Failure (HFpEF/HFrEF)"
        ],
        default=[]
    )

    st.divider()
    st.subheader("Searchable CPT/ICD Table")
    mapping_file = Path("cpt_mapping.csv")
    if mapping_file.exists():
        df_map = pd.read_csv(mapping_file)
        q = st.text_input("Filter (any field):", key="mapfilter")
        if q:
            q_low = q.lower()
            mask = df_map.apply(lambda c: c.astype(str).str.lower().str.contains(q_low, na=False))
            df_view = df_map[mask.any(axis=1)]
        else:
            df_view = df_map
        st.dataframe(df_view, use_container_width=True, height=260)
    else:
        st.warning("cpt_mapping.csv not found.")

st.divider()

# ---------------- State init ----------------
if "wounds" not in st.session_state:
    st.session_state.wounds = []  # list of dict rows
if "bundle" not in st.session_state:
    st.session_state.bundle = None

# ---------------- Add row form ----------------
st.subheader("1) Add Site / Wound")
with st.form("add_row"):
    c1, c2, c3 = st.columns([1.2,1,1])
    with c1:
        site = st.text_input("Site/Location", value="Right plantar forefoot")
        proc = st.selectbox("Procedure", ["Debridement","Incision & Drainage","Joint Injection","Foreign Body Removal","Wound Closure"])
    with c2:
        depth = st.selectbox("Depth (Debridement)", ["Skin (epi/dermis)","Subcutaneous Tissue","Fascia/Muscle","Bone"])
        area = st.number_input("Area (cm²)", min_value=0.0, step=0.1, value=8.0)
    with c3:
        instruments = st.multiselect("Instruments (multi)", ["scalpel","rongeur","scissors","curette","pulse lavage","forceps","bovie"], default=["scalpel","curette"])
        vasc = st.selectbox("Vascularity", ["Good","Poor"], index=1)
        contam = st.selectbox("Contamination/Infection", ["Clean","Contaminated","Infected"], index=2)
        infection_type = st.selectbox("Infection Dx (ICD‑10 assist)", ["None","Abscess","Cellulitis","Osteomyelitis (acute)","Osteomyelitis (chronic)","Diabetic foot ulcer","Septic arthritis"])
    submitted = st.form_submit_button("➕ Add site/wound", use_container_width=True)
    if submitted:
        row = {
            "site": site.strip(),
            "procedure": proc,
            "depth": depth,
            "area_cm2": float(area or 0.0),
            "instruments": instruments,
            "vascularity": vasc,
            "contamination": contam,
            "infection_type": infection_type
        }
        st.session_state.wounds.append(row)
        st.success("Added.")
        st.experimental_rerun()

# ---------------- Rows table with delete ----------------
st.subheader("2) Current Sites / Wounds")
if not st.session_state.wounds:
    st.info("No rows yet. Add the first site/wound above.")
else:
    for idx, row in enumerate(st.session_state.wounds):
        cols = st.columns([6,2,1])
        with cols[0]:
            st.write(f"**{idx+1}. {row['site']}** — {row['procedure']} • Depth: {row['depth']} • Area: {row['area_cm2']} cm² • "
                     f"Vasc: {row['vascularity']} • Status: {row['contamination']} • Infection Dx: {row.get('infection_type','None')} • "
                     f"Instruments: {', '.join(row['instruments']) if row['instruments'] else '(none)'}")
        with cols[2]:
            if st.button("🗑️", key=f"del_{idx}"):
                st.session_state.wounds.pop(idx)
                st.experimental_rerun()

# ---------------- ICD‑10 selection/overrides ----------------
st.subheader("3) ICD‑10 Selection & Overrides")
suggested_icds = suggest_icd10_from_rows(st.session_state.wounds, packs)
icd_choices = st.multiselect("Suggested ICD‑10 (you can change):", options=sorted(suggested_icds), default=sorted(suggested_icds), key="icd_multi")
manual_icd = st.text_input("Add custom ICD‑10 code(s), comma‑separated", key="icd_custom")
final_icd10 = list(dict.fromkeys(icd_choices + [c.strip() for c in manual_icd.split(',') if c.strip()]))

# ---------------- Compute & Output ----------------
st.subheader("4) Compute Codes & Generate Note")
if st.button("Compute Coding Bundle", type="primary"):
    df = pd.DataFrame(st.session_state.wounds)
    bundle = compute_coding_bundle(df, packs, override_icd10=final_icd10)
    st.session_state.bundle = bundle

if st.session_state.bundle:
    bundle = st.session_state.bundle
    op_text = generate_note_text(pd.DataFrame(st.session_state.wounds), packs, bundle)
    st.text_area("Operative Note (editable)", value=op_text, height=260, key="note_text")

    # Copy to clipboard button
    copy_payload = op_text
    
    # Replace Streamlit button copy with an HTML button so the clipboard API sees a real user click
    html(f"""
        <button id='copybtn' style='padding:8px 12px;border-radius:8px;'>Copy Operative Note + Codes to Clipboard</button>
        <script>
          const txt = {copy_payload!r};
          const btn = document.getElementById('copybtn');
          btn.addEventListener('click', async () => {{
            try {{
              await navigator.clipboard.writeText(txt);
              btn.innerText = 'Copied!';
            }} catch (e) {{
              // Fallback path for older browsers
              const ta = document.createElement('textarea');
              ta.value = txt;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand('copy');
              document.body.removeChild(ta);
              btn.innerText = 'Copied (fallback)';
            }}
          }});
        </script>
    """, height=60)


    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("Export DOCX"):
            docx_bytes = export_docx("", "", op_text, bundle)  # no patient/date in narrative
            st.download_button("Download Note (DOCX)", data=docx_bytes, file_name="OrthoCoderPro_OperativeNote.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with c2:
        if st.button("Export JSON"):
            json_bytes = export_json("", "", op_text, bundle)
            st.download_button("Download Bundle (JSON)", data=json_bytes, file_name="OrthoCoderPro_Bundle.json", mime="application/json")
    with c3:
        if st.button("Clear for New Case"):
            st.session_state.clear()
            st.experimental_rerun()
else:
    st.info("Add rows and click **Compute Coding Bundle** to generate the operative note and codes.")


# --- Administrator Panel (bottom of page) ---
st.markdown("---")
with st.expander("🔒 Administrator", expanded=False):
    ADMIN_PIN = os.environ.get("ORTHOCODER_ADMIN_PIN", "")
    pin = st.text_input("Enter Admin PIN", type="password", key="admin_pin")
    unlock = st.button("Unlock Admin")

    if unlock:
        if ADMIN_PIN and pin == ADMIN_PIN:
            st.session_state.admin_ok = True
        else:
            st.session_state.admin_ok = False
            st.error("Invalid PIN or ORTHOCODER_ADMIN_PIN not set.")

    if st.session_state.get("admin_ok"):
        tabs = st.tabs(["Mappings", "Backups/Restore", "Diagnostics"])

        # --- Mappings editor ---
        with tabs[0]:
            st.caption("Edit `cpt_mapping.csv` (a timestamped backup is created on Save).")
            try:
                df_map = pd.read_csv("cpt_mapping.csv")
            except Exception as e:
                st.error(f"Failed to load cpt_mapping.csv: {e}")
                df_map = pd.DataFrame()

            edited = st.data_editor(df_map, num_rows="dynamic", use_container_width=True)
            if st.button("Save Mappings"):
                required_cols = {"procedure_category","procedure_subtype","depth","area_cm2_bucket",
                                 "instrument","vascularity","contamination","cpt_code","icd10_code","notes"}
                missing = [c for c in required_cols if c not in edited.columns]
                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    backup_path = _atomic_write_csv_with_backup(edited, "cpt_mapping.csv")
                    st.success(f"Saved. Backup created: {backup_path}")

        # --- Backups/Restore ---
        with tabs[1]:
            backups = sorted(Path("backups").glob("cpt_mapping_*.csv"), reverse=True)
            if not backups:
                st.info("No backups yet.")
            else:
                restore_choice = st.selectbox("Select a backup to restore", backups, format_func=str)
                if st.button("Restore Selected Backup"):
                    src = Path(restore_choice)
                    tmp = Path("cpt_mapping.csv").with_suffix(".restore.tmp")
                    pd.read_csv(src).to_csv(tmp, index=False)
                    os.replace(tmp, "cpt_mapping.csv")
                    st.success(f"Restored from {src.name}")

        # --- Diagnostics ---
        with tabs[2]:
            _show_diag(st.session_state.get("bundle"))
    else:
        st.info("Admin locked. Set env var ORTHOCODER_ADMIN_PIN and enter the PIN.")

