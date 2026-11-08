import os
import re
import math
import streamlit as st
from decimal import Decimal

# --- 3D RENDERING ---
try:
    import py3Dmol
    from stmol import showmol
    HAS_3D = True
except ImportError:
    HAS_3D = False

HARTREE_TO_KCAL = Decimal('627.509')

ATOMIC_SYMBOLS = {
    1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 9: 'F', 10: 'Ne',
    11: 'Na', 12: 'Mg', 13: 'Al', 14: 'Si', 15: 'P', 16: 'S', 17: 'Cl', 18: 'Ar',
    19: 'K', 20: 'Ca', 24: 'Cr', 25: 'Mn', 26: 'Fe', 27: 'Co', 28: 'Ni', 29: 'Cu', 30: 'Zn',
    35: 'Br', 53: 'I'
}

def extract_energy(uploaded_file, is_bsse=False):
    if uploaded_file is None: return None
    uploaded_file.seek(0)
    content = uploaded_file.read().decode('utf-8')
    if is_bsse:
        matches = re.findall(r'Counterpoise\s*corrected\s*energy\s*=\s*([-+]?\d*\.\d+)', content, re.IGNORECASE)
        return Decimal(matches[-1]) if matches else None
    else:
        stitched = re.sub(r'[\r\n]+ ', '', content)
        matches = re.findall(r'HF=([-+]?\d*\.\d+|\d+)', stitched)
        return Decimal(matches[-1]) if matches else None

def format_nbo(text):
    text = re.sub(r'^\s*\d+\.\s*', '', text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'([A-Za-z\*]+)\s+(\d+)', r'\1\2', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def extract_led_values(uploaded_file, target_strings):
    extracted = {}
    if uploaded_file is None: return extracted
    uploaded_file.seek(0)
    lines = uploaded_file.read().decode('utf-8').splitlines()
    for line in lines:
        for term in target_strings:
            if term.lower() in line.lower():
                if term.lower().startswith("dispersion") and "non" in line.lower(): continue
                parts = line.strip().split()
                try:
                    if term == "Intra REF. energy":
                        extracted["Intra REF. energy of Fragment 1"] = Decimal(parts[3])
                        extracted["Intra REF. energy of Fragment 2"] = Decimal(parts[4])
                    else: extracted[term] = Decimal(parts[-1])
                except (ValueError, IndexError): continue
    return extracted

def show_3d_molecule(content, filename=""):
    lines = content.splitlines()
    coords = []
    ext = os.path.splitext(filename)[1].lower()

    if ext == '.wfn':
        BOHR_TO_ANG = 0.529177249
        for line in lines:
            match = re.search(r'([A-Za-z]{1,2})\s+(\d+)\s+\(CENTRE\s+\d+\)\s+X=\s*([\-\d\.]+)\s+Y=\s*([\-\d\.]+)\s+Z=\s*([\-\d\.]+)', line, re.IGNORECASE)
            if match:
                coords.append({"idx": match.group(2), "sym": match.group(1).capitalize(), "x": float(match.group(3)) * BOHR_TO_ANG, "y": float(match.group(4)) * BOHR_TO_ANG, "z": float(match.group(5)) * BOHR_TO_ANG})
    elif ext == '.wfx':
        BOHR_TO_ANG = 0.529177249
        names, xyz = [], []
        in_names, in_coords = False, False
        for line in lines:
            if "<AtomicNames>" in line: in_names = True; continue
            if "</AtomicNames>" in line: in_names = False; continue
            if "<NuclearCartesianCoordinates>" in line: in_coords = True; continue
            if "</NuclearCartesianCoordinates>" in line: in_coords = False; continue
            if in_names: names.extend([re.sub(r'[^A-Za-z]', '', n).capitalize() for n in line.split() if re.sub(r'[^A-Za-z]', '', n)])
            if in_coords: xyz.extend([float(v) for v in line.split() if any(c.isdigit() for c in v)])
        if names and len(xyz) == len(names) * 3:
            for i, name in enumerate(names):
                coords.append({"idx": str(i+1), "sym": name, "x": xyz[i*3] * BOHR_TO_ANG, "y": xyz[i*3+1] * BOHR_TO_ANG, "z": xyz[i*3+2] * BOHR_TO_ANG})
    else:
        for i in range(len(lines)-1, -1, -1):
            if "Standard orientation:" in lines[i] or "Input orientation:" in lines[i]:
                start_idx = i + 5
                for j in range(start_idx, len(lines)):
                    if "---------------------------------------------------------------------" in lines[j]: break
                    parts = lines[j].split()
                    if len(parts) == 6:
                        atom_num = int(parts[1])
                        sym = ATOMIC_SYMBOLS.get(atom_num, 'X')
                        coords.append({"idx": parts[0], "sym": sym, "x": parts[3], "y": parts[4], "z": parts[5]})
                break
                
    if not coords: 
        st.warning("Could not extract molecular coordinates for 3D viewer.")
        return

    xyz_str = f"{len(coords)}\n\n"
    for c in coords: xyz_str += f"{c['sym']} {c['x']} {c['y']} {c['z']}\n"
        
    view = py3Dmol.view(width=450, height=400)
    view.addModel(xyz_str, 'xyz')
    view.setStyle({'stick':{'radius': 0.15}, 'sphere':{'scale': 0.3}})
    for c in coords:
        view.addLabel(f"{c['sym']}{c['idx']}", {"position": {"x": float(c['x']), "y": float(c['y']), "z": float(c['z'])}, "fontColor": "black", "backgroundColor": "white", "backgroundOpacity": 0.8, "fontsize": 14})
    view.zoomTo()
    showmol(view, height=400, width=450)

def calculate_distance(coord1, coord2):
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(coord1, coord2)))
