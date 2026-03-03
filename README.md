# IRIMeS — Facial Biometric Landmarks
### Blender Addon for Anthropometric Analysis of 3D Facial Scans

![Blender](https://img.shields.io/badge/Blender-3.0%2B-orange?logo=blender&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Farkas](https://img.shields.io/badge/Standard-Farkas%201994-lightgrey)

---

> **Created by Daniele Bursich (Ph.D.)**  
> University of Verona  
>
> IRIMeS is conceived as a fundamental complement to the research activities of the **RESP project** — *The Roman Emperor Seen from the Provinces* (ERC Cog – G.A.: 101002763). The project adopts a methodological approach based on the use of 3D scanning and modeling techniques focused on imperial metropolitan portraiture.  
>
> 🔗 [https://irimes.dcuci.univr.it/](https://irimes.dcuci.univr.it/)

---

## Overview

IRIMeS is a Blender addon that implements the **Farkas (1994) anthropometric landmark standard** for the analysis of realistic 3D facial scans (photogrammetry, structured light, etc.). It provides a complete workflow from landmark placement to measurement export and mesh segmentation via vertex groups.

The addon supports **27 Farkas standard landmarks**, covering the full face including orbital region, nasal structures, oral commissures, philtrum ridges, and auricular points.

---

## Features

### 🎯 Landmark Placement
- **Auto-Detection** — heuristic bounding-box detection for quick initialization on front-facing scans
- **Alignment Wizard** — guided 6-point placement (nose tip, eye centers, tragions, chin); the addon computes all 27 remaining landmarks via proportional interpolation and snaps them to the mesh surface
- **Manual placement** — click-on-mesh with ESC to cancel; each landmark can be individually repositioned or deleted
- **Snap to Mesh** — re-projects all placed landmarks onto the nearest mesh surface via BVH tree

### 📐 Farkas 1994 Landmarks (27 points)

| Group | Landmarks |
|-------|-----------|
| Upper | g (Glabella), n (Nasion) |
| Nose | pn (Pronasale), sn (Subnasale), alr, all (Alare) |
| Eye | exr, exl (Exocanthion), enr, enl (Endocanthion), psr, psl (Palpebrale Sup.), pir, pil (Palpebrale Inf.) |
| Mouth | ls (Labiale Sup.), li (Labiale Inf.), chr, chl (Cheilion), cphr, cphl (Crista Philtri) |
| Chin | pg (Pogonion) |
| Ear R | sar (Superaurale), tr (Tragion), sbar (Subaurale) |
| Ear L | sal (Superaurale), tl (Tragion), sbal (Subaurale) |

### 📏 Measurements (21 standard pairs)
| Measurement | Points |
|-------------|--------|
| Intercanthal Width | en-en |
| Biocular Width | ex-ex |
| Nasal Width | al-al |
| Mouth Width | ch-ch |
| Philtrum Width | cph-cph |
| Biauricular Width | t-t |
| Nasal Length | n-pn |
| Nasal Height | n-sn |
| Lower Face Height | sn-pg |
| Total Face Height | g-pg |
| Lip Height | ls-li |
| Palpebral Fissure Height | ps-pi (bilateral) |
| Palpebral Fissure Width | en-ex (bilateral) |
| Ear Height | sa-sba (bilateral) |
| Philtrum Ridge to Labiale Sup. | cph-ls (bilateral) |
| Crista Philtri to Cheilion | cph-ch (bilateral) |

### 🖼 3D Viewport Overlay
- Landmark ID labels in world space
- Distance lines between measurement pairs (configurable thickness, color)
- Distance values in mm displayed at line midpoints
- Toggle on/off from the main panel

### 🗺 Schematic Panel (always visible)
- Permanent schematic diagram derived from the Farkas 1994 landmark layout, rendered directly in the viewport corner
- Landmark dots update in real time: grey = not placed, green = placed, orange = selected
- **Bidirectional selection**: click a dot on the schematic → selects the corresponding empty in the viewport; select an empty in the viewport → highlights the dot
- Wizard guidance: current step highlighted in cyan with description

### 🧩 Anatomical Groups & Vertex Groups
- 7 default anatomical groups: Right Eye, Left Eye, Nose, Mouth, Chin, Right Ear, Left Ear, Full Face
- Fully editable from the UI: rename groups, add/remove landmarks via toggle grid, adjust hull margin
- **Convex Hull Selection** — selects all mesh vertices inside the 3D convex hull of the group's landmarks (XZ projection + Y depth tolerance)
- **Vertex Group Export** — one click to create or overwrite a named `FBM_GroupName` vertex group on the target mesh
- **Batch** — create all vertex groups at once

### 📄 Export
- Plain text report (`.txt`) with:
  - World-space landmark coordinates
  - All standard Farkas measurements in mm
  - Full N×N distance matrix

---

## Installation

1. Download `facial_landmarks_v5b.py`
2. In Blender: **Edit → Preferences → Add-ons → Install**
3. Browse to the `.py` file and install
4. Enable **"Facial Biometric Landmarks"** in the add-on list
5. Open the **N-panel** in the 3D Viewport → tab **"Biometry"**

**Requirements:** Blender 3.0 or later (tested on 3.x and 4.x)

---

## Usage

### Quick Start (Auto-Detect)
1. Select your mesh in the **Target Mesh** field
2. Click **Auto-Detect** — landmarks are placed using geometric heuristics
3. Review and adjust individual landmarks as needed using the **Landmark Placement** panel
4. Enable **3D Overlay** to see lines and measurements in the viewport

### Alignment Wizard (Recommended)
1. Select your mesh and click **▶ Wizard (6 punti)**
2. Follow the on-screen prompts to click 6 anchor points on the mesh:
   - Nose tip → Right iris → Left iris → Right tragion → Left tragion → Chin
3. After each click, confirm with **Avanti →** or **Enter** (or click again to reposition)
4. The addon computes all 27 landmarks and snaps them to the mesh surface

### Vertex Group Workflow
1. Open the **Gruppi & Vertex Groups** panel
2. Select a group from the list or edit its landmark composition
3. Click **Seleziona** to preview the convex hull selection
4. Click **→ Vertex Group** to create the vertex group on the mesh
5. Use **Crea Tutti i Vertex Groups** to batch-generate all groups at once

---

## Scientific Reference

> Farkas, L.G. (1994). *Anthropometry of the Head and Face*, 2nd ed. Raven Press, New York.

> Farkas, L.G. & Munro, I.R. (1987). *Anthropometric Facial Proportions in Medicine*. Charles C Thomas, Springfield.

---

## Project Context

This tool was developed within the framework of the **RESP — The Roman Emperor Seen from the Provinces** research project (ERC Consolidator Grant, G.A.: 101002763), hosted at the University of Verona. The project applies 3D scanning, photogrammetry, and computational morphology to the study of imperial Roman portraiture, with a particular focus on provincial receptions of metropolitan iconographic models.

IRIMeS (Integrated Research Infrastructure for Morphometric Studies) provides the digital infrastructure for systematic biometric comparison across 3D scan datasets of ancient sculptural portraits.

🔗 Project website: [https://irimes.dcuci.univr.it/](https://irimes.dcuci.univr.it/)

---

## License

MIT License — free for academic and research use. If you use this tool in published research, please cite the RESP project.
