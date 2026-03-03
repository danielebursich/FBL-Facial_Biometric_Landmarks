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

Allanson, J. E., Cunniff, C., Hoyme, H. E., McGaughran, J., Muenke, M., & Neri, G. (2009). Elements of morphology: Standard terminology for the head and face. American Journal of Medical Genetics Part A.

Barbera, A. L., Sampson, W. J., & Townsend, G. C. (2009). An evaluation of head position and craniofacial reference line variation. HOMO, 60(1), 1–28. https://doi.org/10.1016/j.jchb.2008.05.003

Bookstein, F. L. (1991). Morphometric tools for landmark data: Geometry and biology. Cambridge University Press.

Bruner, E., & Manzi, G. (2007). Landmark-based shape analysis of the archaic Homo calvarium from Ceprano (Italy). American Journal of Physical Anthropology, 132, 355–366. https://doi.org/10.1002/ajpa.20545

Cevidanes, L. H. S., Franco, A. A., Gerig, G., Proffit, W. R., Slice, D. E., Enlow, D. H., Lederman, H. M., Amorim, L., Scanavini, M. A., & Vigorito, J. W. (2005). Comparison of relative mandibular growth vectors with high-resolution 3-dimensional imaging. American Journal of Orthodontics and Dentofacial Orthopedics, 128(1), 27–34. https://doi.org/10.1016/j.ajodo.2004.03.033

Cuccia, A. M., & Caradonna, C. (2009). The natural head position: Different techniques of head positioning in the study of craniocervical posture. Minerva Stomatologica, 58(11–12).

Farkas, L. G. (1994). Anthropometry of the head and face (2nd ed.). Raven Press.

Farkas, L. G., & Munro, I. R. (1987). Anthropometric facial proportions in medicine. Charles C Thomas.

Grant, S. F. A., et al. (2009). A genome-wide association study identifies a locus for nonsyndromic cleft lip with or without cleft palate on 8q24. The Journal of Pediatrics, 155(6), 909–913. https://doi.org/10.1016/j.jpeds.2009.06.020

Gwilliam, J. R., Cunningham, S. J., & Hutton, T. J. (2006). Reproducibility of soft tissue landmarks on three-dimensional facial scans. European Journal of Orthodontics, 28, 408–415.

Hall, J. G., et al. (2009). Elements of morphology: Standard terminology for the periorbital region. American Journal of Medical Genetics Part A, 149A(1), 29–39.

Hennekam, R. C. M., Cormier-Daire, V., Hall, J. G., Méhes, K., Patton, M., & Stevenson, R. E. (2009). Elements of morphology: Standard terminology for the nose and philtrum. American Journal of Medical Genetics Part A, 149A(1), 61–76. https://doi.org/10.1002/ajmg.a.32600

Kau, C. H., & Richmond, S. (2008). Three-dimensional imaging for orthodontics and craniofacial assessment. Orthodontics & Craniofacial Research.

Kau, C. H., & Richmond, S. (2010). Three-dimensional analysis of facial morphology. Orthodontics & Craniofacial Research.

McIntyre, G. T., & Mossey, P. A. (2003). Size and shape measurement in contemporary cephalometrics. European Journal of Orthodontics, 25, 231–237.

Richmond, S., Toma, A. M., & Zhurov, A. I. (2009). Three-dimensional facial imaging in clinical practice. Orthodontics & Craniofacial Research.

Toma, A. M., Zhurov, A., Playle, R., Ong, E., & Richmond, S. (2009). Reproducibility of facial soft tissue landmarks on 3D laser-scanned facial images. Orthodontics & Craniofacial Research, 12, 33–42.

Zhurov, A. I., Kau, C. H., & Richmond, S. (2005). Computer methods for measuring 3D facial morphology. In J. Middleton, M. G. Shrive, & M. L. Jones (Eds.), Computer Methods in Biomechanics and Biomedical Engineering – 5. FIRST Numerics Ltd.

---

## Project Context

This tool was developed within the framework of the **RESP — The Roman Emperor Seen from the Provinces** research project (ERC Consolidator Grant, G.A.: 101002763), hosted at the University of Verona. The project applies 3D scanning, photogrammetry, and computational morphology to the study of imperial Roman portraiture, with a particular focus on provincial receptions of metropolitan iconographic models.

IRIMeS (Integrated Research Infrastructure for Morphometric Studies) provides the digital infrastructure for systematic biometric comparison across 3D scan datasets of ancient sculptural portraits.

🔗 Project website: [https://irimes.dcuci.univr.it/](https://irimes.dcuci.univr.it/)

---

## License

MIT License — free for academic and research use. If you use this tool in published research, please cite the RESP project.
