bl_info = {
    "name": "Facial Biometric Landmarks",
    "author": "Custom Addon",
    "version": (5, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Biometry",
    "description": "27 Farkas landmarks, SVG schematic, editable groups, convex hull vertex groups",
    "category": "Mesh",
}

import bpy, bmesh, mathutils, math, os
import gpu, blf
from gpu_extras.batch import batch_for_shader
from mathutils.geometry import convex_hull_2d
from bpy.props import (FloatProperty, StringProperty, BoolProperty,
                       IntProperty, EnumProperty, FloatVectorProperty,
                       CollectionProperty, PointerProperty)
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy_extras import view3d_utils

# ─────────────────────────────────────────────────────────────────────────────
#  27 FARKAS LANDMARKS  (Farkas 1994, corrected ear positions)
# ─────────────────────────────────────────────────────────────────────────────
LANDMARK_DEFS = [
    # (id, full_name, side, group)
    ("g",    "Glabella",              "C", "upper"),
    ("n",    "Nasion",                "C", "upper"),
    ("pn",   "Pronasale",             "C", "nose"),
    ("sn",   "Subnasale",             "C", "nose"),
    ("alr",  "Alare R",               "R", "nose"),
    ("all",  "Alare L",               "L", "nose"),
    ("exr",  "Exocanthion R",         "R", "eye"),
    ("psr",  "Palpebrale Sup. R",     "R", "eye"),
    ("enr",  "Endocanthion R",        "R", "eye"),
    ("pir",  "Palpebrale Inf. R",     "R", "eye"),
    ("enl",  "Endocanthion L",        "L", "eye"),
    ("psl",  "Palpebrale Sup. L",     "L", "eye"),
    ("exl",  "Exocanthion L",         "L", "eye"),
    ("pil",  "Palpebrale Inf. L",     "L", "eye"),
    ("cphr", "Crista Philtri R",      "R", "mouth"),
    ("ls",   "Labiale Superius",      "C", "mouth"),
    ("cphl", "Crista Philtri L",      "L", "mouth"),
    ("chr",  "Cheilion R",            "R", "mouth"),
    ("li",   "Labiale Inferius",      "C", "mouth"),
    ("chl",  "Cheilion L",            "L", "mouth"),
    ("pg",   "Pogonion",              "C", "chin"),
    ("sar",  "Superaurale R",         "R", "ear"),
    ("tr",   "Tragion R",             "R", "ear"),
    ("sbar", "Subaurale R",           "R", "ear"),
    ("sal",  "Superaurale L",         "L", "ear"),
    ("tl",   "Tragion L",             "L", "ear"),
    ("sbal", "Subaurale L",           "L", "ear"),
]

GROUP_COLORS = {
    "upper": (0.9,0.6,0.1,1.0), "nose":  (0.2,0.8,0.4,1.0),
    "eye":   (0.2,0.6,1.0,1.0), "mouth": (1.0,0.6,0.2,1.0),
    "chin":  (0.6,0.9,0.3,1.0), "ear":   (0.9,0.75,0.5,1.0),
}

EMPTY_SIZE      = 0.005
COLLECTION_NAME = "FacialLandmarks"
_WIZARD_TEMP    = "LM__wiz_temp"

# ── SVG-derived schematic positions (Farkas 1994 diagram, normalized 0-1) ──
SCHEMATIC_POS = {
    "g":    (0.500, 0.738), "n":    (0.500, 0.663),
    "pn":   (0.500, 0.478), "sn":   (0.500, 0.398),
    "alr":  (0.398, 0.440), "all":  (0.601, 0.440),
    "exr":  (0.221, 0.615), "psr":  (0.308, 0.658),
    "enr":  (0.396, 0.615), "pir":  (0.308, 0.583),
    "enl":  (0.599, 0.615), "psl":  (0.686, 0.658),
    "exl":  (0.774, 0.615), "pil":  (0.686, 0.583),
    "cphr": (0.455, 0.326), "ls":   (0.500, 0.309),
    "cphl": (0.544, 0.326), "chr":  (0.361, 0.245),
    "li":   (0.500, 0.204), "chl":  (0.639, 0.245),
    "pg":   (0.500, 0.099),
    # Ear – CORRECTED (top=sa, middle=t, bottom=sba)
    "sar":  (0.105, 0.726), "tr":   (0.141, 0.567), "sbar": (0.105, 0.449),
    "sal":  (0.894, 0.726), "tl":   (0.859, 0.567), "sbal": (0.894, 0.449),
    # Wizard internal anchors
    "_eye_r": (0.310, 0.620), "_eye_l": (0.690, 0.620),
}

LANDMARK_DESC = {
    "g":   "Glabella: most forward pt between eyebrows",
    "n":   "Nasion: deepest pt of the nasal bridge",
    "pn":  "Pronasale: very tip of the nose",
    "sn":  "Subnasale: base of nose, above philtrum",
    "alr": "Alare R: outermost pt of right nostril",
    "all": "Alare L: outermost pt of left nostril",
    "exr": "Exocanthion R: outer corner of right eye",
    "psr": "Palpebrale Superius R: top of right eyelid",
    "enr": "Endocanthion R: inner corner of right eye",
    "pir": "Palpebrale Inferius R: bottom of right eyelid",
    "enl": "Endocanthion L: inner corner of left eye",
    "psl": "Palpebrale Superius L: top of left eyelid",
    "exl": "Exocanthion L: outer corner of left eye",
    "pil": "Palpebrale Inferius L: bottom of left eyelid",
    "cphr":"Crista Philtri R: right philtrum ridge",
    "ls":  "Labiale Superius: center of upper lip border",
    "cphl":"Crista Philtri L: left philtrum ridge",
    "chr": "Cheilion R: right corner of the mouth",
    "li":  "Labiale Inferius: center of lower lip border",
    "chl": "Cheilion L: left corner of the mouth",
    "pg":  "Pogonion: most forward pt of chin",
    "sar": "Superaurale R: topmost pt of right ear",
    "tr":  "Tragion R: notch above right ear tragus",
    "sbar":"Subaurale R: lowest pt of right earlobe",
    "sal": "Superaurale L: topmost pt of left ear",
    "tl":  "Tragion L: notch above left ear tragus",
    "sbal":"Subaurale L: lowest pt of left earlobe",
    "_eye_r":"Right Eye Center: click on the iris/pupil",
    "_eye_l":"Left Eye Center: click on the iris/pupil",
}

# ── SVG paths (normalized 0-1, Y already flipped) ──────────────────────────
SVG_PATHS = {
    "face":      [(0.141,0.815),(0.153,0.840),(0.203,0.895),(0.310,0.951),
                  (0.494,0.976),(0.680,0.951),(0.791,0.895),(0.845,0.840),
                  (0.859,0.815),(0.858,0.441),(0.837,0.322),(0.767,0.162),
                  (0.615,0.043),(0.385,0.043),(0.234,0.161),(0.163,0.320),
                  (0.142,0.439),(0.141,0.815)],
    "eye_r":     [(0.221,0.616),(0.225,0.622),(0.239,0.637),(0.265,0.652),
                  (0.307,0.658),(0.349,0.652),(0.377,0.637),(0.391,0.622),
                  (0.396,0.615),(0.390,0.610),(0.372,0.599),(0.345,0.588),
                  (0.308,0.583),(0.272,0.588),(0.245,0.599),(0.227,0.610),
                  (0.221,0.616)],
    "eye_l":     [(0.599,0.616),(0.603,0.622),(0.616,0.637),(0.643,0.652),
                  (0.685,0.658),(0.727,0.652),(0.754,0.637),(0.769,0.622),
                  (0.774,0.615),(0.767,0.610),(0.750,0.599),(0.722,0.588),
                  (0.686,0.583),(0.650,0.588),(0.622,0.599),(0.605,0.610),
                  (0.599,0.616)],
    "nose_r":    [(0.178,0.701),(0.219,0.714),(0.309,0.733),(0.399,0.729),
                  (0.442,0.672),(0.444,0.596),(0.443,0.551),(0.443,0.529),
                  (0.442,0.523),(0.435,0.515),(0.420,0.495),(0.406,0.467),
                  (0.399,0.437),(0.404,0.412),(0.420,0.398),(0.451,0.392),
                  (0.500,0.391)],
    "nose_l":    [(0.822,0.701),(0.781,0.714),(0.691,0.733),(0.601,0.729),
                  (0.558,0.672),(0.556,0.596),(0.557,0.551),(0.558,0.529),
                  (0.558,0.523),(0.565,0.515),(0.580,0.495),(0.594,0.467),
                  (0.601,0.437),(0.597,0.412),(0.580,0.398),(0.549,0.392),
                  (0.500,0.391)],
    "mouth_r":   [(0.500,0.302),(0.494,0.302),(0.480,0.302),(0.466,0.307),
                  (0.460,0.322),(0.445,0.325),(0.411,0.303),(0.377,0.274),
                  (0.361,0.251),(0.364,0.245),(0.379,0.252),(0.420,0.262),
                  (0.500,0.267)],
    "mouth_l":   [(0.500,0.302),(0.506,0.302),(0.520,0.302),(0.534,0.307),
                  (0.540,0.322),(0.555,0.325),(0.589,0.303),(0.623,0.274),
                  (0.639,0.251),(0.636,0.245),(0.621,0.252),(0.580,0.262),
                  (0.500,0.267)],
    "chin":      [(0.383,0.234),(0.390,0.223),(0.413,0.211),(0.460,0.201),
                  (0.500,0.200),(0.540,0.201),(0.581,0.211),(0.613,0.223),
                  (0.617,0.234)],
    "ear_r_out": [(0.859,0.622),(0.860,0.638),(0.863,0.675),(0.873,0.710),
                  (0.891,0.726),(0.910,0.714),(0.922,0.685),(0.928,0.650),
                  (0.930,0.615),(0.928,0.572),(0.921,0.517),(0.910,0.469),
                  (0.894,0.449),(0.879,0.466),(0.868,0.503),(0.861,0.540),
                  (0.859,0.557)],
    "ear_l_out": [(0.141,0.622),(0.140,0.638),(0.137,0.675),(0.127,0.710),
                  (0.109,0.726),(0.089,0.714),(0.078,0.685),(0.072,0.650),
                  (0.070,0.615),(0.072,0.572),(0.079,0.517),(0.090,0.469),
                  (0.105,0.449),(0.121,0.466),(0.132,0.503),(0.139,0.540),
                  (0.141,0.557)],
    "concha_r":  [(0.883,0.567),(0.882,0.558),(0.881,0.550),(0.879,0.543),
                  (0.877,0.538),(0.874,0.535),(0.871,0.533),(0.868,0.535),
                  (0.865,0.538),(0.863,0.543),(0.861,0.550),(0.859,0.558),
                  (0.859,0.567),(0.859,0.575),(0.861,0.583),(0.863,0.590),
                  (0.865,0.595),(0.868,0.599),(0.871,0.600),(0.874,0.599),
                  (0.877,0.595),(0.879,0.590),(0.881,0.583),(0.882,0.575),
                  (0.883,0.567)],
    "concha_l":  [(0.141,0.567),(0.140,0.558),(0.139,0.550),(0.137,0.543),
                  (0.135,0.538),(0.132,0.535),(0.129,0.533),(0.126,0.535),
                  (0.123,0.538),(0.121,0.543),(0.119,0.550),(0.118,0.558),
                  (0.117,0.567),(0.118,0.575),(0.119,0.583),(0.121,0.590),
                  (0.123,0.595),(0.126,0.599),(0.129,0.600),(0.132,0.599),
                  (0.135,0.595),(0.137,0.590),(0.139,0.583),(0.140,0.575),
                  (0.141,0.567)],
}

# Panel geometry
P_X, P_Y = 15, 15
P_W, P_H = 430, 460

WIZARD_STEPS = [
    ("pn",    "Pronasale",        "Click sulla punta del naso"),
    ("_eye_r","Occhio Dx Center", "Click al centro dell'iride DESTRA"),
    ("_eye_l","Occhio Sx Center", "Click al centro dell'iride SINISTRA"),
    ("tr",    "Tragion Dx",       "Click sul notch sopra il tragus destro"),
    ("tl",    "Tragion Sx",       "Click sul notch sopra il tragus sinistro"),
    ("pg",    "Pogonion",         "Click sul punto più prominente del mento"),
]

WIZARD_RATIOS = {
    "g":    (0.00,+0.23,-0.04), "n":    (0.00,+0.10,-0.08),
    "sn":   (0.00,-0.44,+0.08), "alr":  (+0.26,-0.39,+0.06),
    "all":  (-0.26,-0.39,+0.06),"exr":  (+0.70, 0.00,-0.02),
    "psr":  (+0.45,+0.06,-0.01),"enr":  (+0.25, 0.00,+0.02),
    "pir":  (+0.45,-0.06,-0.01),"enl":  (-0.25, 0.00,+0.02),
    "psl":  (-0.45,+0.06,-0.01),"exl":  (-0.70, 0.00,-0.02),
    "pil":  (-0.45,-0.06,-0.01),"cphr": (+0.20,-0.55,+0.14),
    "ls":   (0.00,-0.55,+0.16), "cphl": (-0.20,-0.55,+0.14),
    "chr":  (+0.39,-0.59,+0.12),"li":   (0.00,-0.63,+0.15),
    "chl":  (-0.39,-0.59,+0.12),"pg":   None,  # anchor
    "sar":  (0.00,+0.18, 0.00), "sbar": (0.00,-0.62, 0.00),
    "sal":  (0.00,+0.18, 0.00), "sbal": (0.00,-0.62, 0.00),
}

DEFAULT_GROUPS = [
    ("Occhio Destro",   "exr,psr,enr,pir",         (0.2,0.6,1.0)),
    ("Occhio Sinistro", "exl,psl,enl,pil",          (0.2,0.4,0.9)),
    ("Naso",            "alr,all,pn,sn",             (0.2,0.8,0.4)),
    ("Bocca",           "ls,li,chr,chl,cphr,cphl",   (1.0,0.6,0.2)),
    ("Orecchio Destro", "sar,tr,sbar",               (0.9,0.75,0.5)),
    ("Orecchio Sinistro","sal,tl,sbal",              (0.8,0.65,0.4)),
    ("Viso Completo",   ",".join(d[0] for d in LANDMARK_DEFS), (0.7,0.7,0.7)),
]

DISTANCE_LINES = [
    ("exr","exl"),("enr","enl"),("alr","all"),("chr","chl"),
    ("cphr","cphl"),("cphr","ls"),("cphl","ls"),
    ("n","pn"),("n","sn"),("sn","pg"),("g","pg"),
    ("enr","exr"),("enl","exl"),("psr","pir"),("psl","pil"),
    ("ls","li"),("sar","sbar"),("sal","sbal"),("tr","tl"),
]

MEASUREMENT_PAIRS = [
    ("enr","enl",   "Intercanthal Width (en-en)"),
    ("exr","exl",   "Biocular Width (ex-ex)"),
    ("alr","all",   "Nasal Width (al-al)"),
    ("chr","chl",   "Mouth Width (ch-ch)"),
    ("cphr","cphl", "Philtrum Width (cph-cph)"),
    ("tr", "tl",    "Biauricular Width (t-t)"),
    ("n",  "pn",    "Nasal Length (n-pn)"),
    ("n",  "sn",    "Nasal Height (n-sn)"),
    ("sn", "pg",    "Lower Face Height (sn-pg)"),
    ("g",  "pg",    "Total Face Height (g-pg)"),
    ("ls", "li",    "Lip Height (ls-li)"),
    ("cphr","ls",   "Philtrum Ridge R to Labiale Sup"),
    ("cphl","ls",   "Philtrum Ridge L to Labiale Sup"),
    ("cphr","chr",  "Crista Philtri R to Cheilion R"),
    ("cphl","chl",  "Crista Philtri L to Cheilion L"),
    ("sar","sbar",  "Ear Height R"),
    ("sal","sbal",  "Ear Height L"),
    ("psr","pir",   "Palpebral Fissure Height R"),
    ("psl","pil",   "Palpebral Fissure Height L"),
    ("enr","exr",   "Palpebral Fissure Width R"),
    ("enl","exl",   "Palpebral Fissure Width L"),
]

# ─────────────────────────────────────────────────────────────────────────────
#  MODULE-LEVEL STATE
# ─────────────────────────────────────────────────────────────────────────────
_handle_3d = _handle_2d = None
_dot_positions = {}           # {lid: (sx,sy)} screen coords
_schematic_running = False
_wizard_placed = False
_wizard_temps  = {}

# ─────────────────────────────────────────────────────────────────────────────
#  PROPERTIES
# ─────────────────────────────────────────────────────────────────────────────
class LandmarkGroupItem(PropertyGroup):
    name:      StringProperty(name="Group Name", default="New Group")
    lm_ids:    StringProperty(name="Landmark IDs", default="",
                              description="Comma-separated landmark IDs")
    color:     FloatVectorProperty(name="Color", subtype='COLOR',
                                   size=3, min=0, max=1, default=(0.5,0.5,1.0))
    expanded:  BoolProperty(default=False)
    hull_margin: FloatProperty(name="Hull Margin (m)", default=0.005, min=0.0, max=0.1)

class FacialBiomProps(PropertyGroup):
    target_mesh:    StringProperty(name="Target Mesh")
    select_radius:  FloatProperty(name="Select Radius (m)", default=0.01, min=0.0001, max=1.0)
    active_landmark:StringProperty(default="")
    export_path:    StringProperty(name="Export Path", default="//facial_measurements.txt", subtype='FILE_PATH')
    show_labels:    BoolProperty(name="Show Labels",    default=True)
    show_lines:     BoolProperty(name="Show Lines",     default=True)
    show_distances: BoolProperty(name="Show Distances", default=True)
    label_size:     IntProperty(name="Label Size", default=12, min=6, max=32)
    line_thickness: FloatProperty(name="Line Thickness", default=3.0, min=1.0, max=12.0)
    line_color:  FloatVectorProperty(subtype='COLOR', size=4, default=(1.0,0.85,0.0,0.95), min=0, max=1)
    label_color: FloatVectorProperty(subtype='COLOR', size=4, default=(1.0,1.0,1.0,1.0),   min=0, max=1)
    dist_color:  FloatVectorProperty(subtype='COLOR', size=4, default=(1.0,0.85,0.2,1.0),  min=0, max=1)
    wizard_active:  BoolProperty(default=False)
    wizard_step:    IntProperty(default=0)
    groups:         CollectionProperty(type=LandmarkGroupItem)
    active_group:   IntProperty(default=0)
    filter_group:   EnumProperty(name="Filter",
        items=[("ALL","All",""),("upper","Upper",""),("nose","Nose",""),
               ("eye","Eye",""),("mouth","Mouth",""),("chin","Chin",""),("ear","Ear","")],
        default="ALL")

# ─────────────────────────────────────────────────────────────────────────────
#  GEOMETRY HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_mesh_bm(obj):
    m=obj.data.copy(); m.transform(obj.matrix_world)
    bm=bmesh.new(); bm.from_mesh(m); bpy.data.meshes.remove(m); return bm

def empty_name(lid): return f"LM_{lid}"
def get_lm_pos(lid):
    n=empty_name(lid)
    return tuple(bpy.data.objects[n].location) if n in bpy.data.objects else None
def lm_placed(lid): return empty_name(lid) in bpy.data.objects
def get_active_lid(context):
    o=getattr(context,'active_object',None)
    return o.get("facial_landmark_id") if o else None
def get_or_create_col():
    if COLLECTION_NAME not in bpy.data.collections:
        c=bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(c)
    return bpy.data.collections[COLLECTION_NAME]
def create_lm_empty(lid, pos, group):
    col=get_or_create_col(); name=empty_name(lid)
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    bpy.ops.object.empty_add(type='SPHERE',location=pos)
    e=bpy.context.object; e.name=name; e.empty_display_size=EMPTY_SIZE
    e.color=GROUP_COLORS.get(group,(1,1,1,1))
    for c in e.users_collection: c.objects.unlink(e)
    col.objects.link(e); e["facial_landmark_id"]=lid; return e
def _tag():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type=='VIEW_3D': a.tag_redraw()
def _in_panel(mx,my): return P_X<=mx<=P_X+P_W and P_Y<=my<=P_Y+P_H

# ─────────────────────────────────────────────────────────────────────────────
#  AUTO DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def auto_detect(obj):
    bm=get_mesh_bm(obj); bm.verts.ensure_lookup_table(); av=bm.verts
    xs=[v.co.x for v in av]; ys=[v.co.y for v in av]; zs=[v.co.z for v in av]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    zmin,zmax=min(zs),max(zs)
    cx=(xmin+xmax)/2; cz=(zmin+zmax)/2
    fw=ymax-ymin; ht=zmax-zmin; wd=xmax-xmin
    fvs=[v for v in av if v.co.y>=ymin+fw*0.30]
    def cs(v,f=.15): return abs(v.co.x-cx)<wd*f
    def fwd(vl,ax=1): return max(vl,key=lambda v:v.co[ax])
    def sides(vl,ax=0):
        return (min(vl,key=lambda v:v.co[ax]).co.copy(),
                max(vl,key=lambda v:v.co[ax]).co.copy())
    r={}
    nc=[v for v in fvs if cs(v) and (cz-.05*ht)<v.co.z<(cz+.20*ht)]
    pn=fwd(nc).co.copy() if nc else mathutils.Vector((cx,ymax,cz+.05*ht))
    r["pn"]=tuple(pn)
    nac=[v for v in fvs if cs(v) and (pn.z+.07*ht)<v.co.z<(pn.z+.18*ht)]
    n_pt=min(nac,key=lambda v:v.co.y).co.copy() if nac else mathutils.Vector((cx,pn.y-.03*fw,pn.z+.10*ht))
    r["n"]=tuple(n_pt)
    gc=[v for v in fvs if cs(v) and (n_pt.z+.03*ht)<v.co.z<(n_pt.z+.12*ht)]
    r["g"]=tuple(fwd(gc).co) if gc else (cx,n_pt.y+.01*fw,n_pt.z+.07*ht)
    sc=[v for v in fvs if cs(v) and (pn.z-.07*ht)<v.co.z<(pn.z-.01*ht)]
    sn=min(sc,key=lambda v:v.co.y).co.copy() if sc else mathutils.Vector((cx,pn.y-.02*fw,pn.z-.04*ht))
    r["sn"]=tuple(sn)
    alc=[v for v in fvs if sn.z<v.co.z<(pn.z+.01*ht) and v.co.y>(pn.y-.06*fw)]
    if alc: alr,all_=sides(alc)
    else:
        alr=mathutils.Vector((cx+wd*.06,sn.y,sn.z+.01*ht))
        all_=mathutils.Vector((cx-wd*.06,sn.y,sn.z+.01*ht))
    r["alr"]=tuple(alr); r["all"]=tuple(all_)
    ez_lo=n_pt.z-.01*ht; ez_hi=n_pt.z+.10*ht; ey_lo=n_pt.y-.05*fw
    er=[v for v in fvs if v.co.x>cx+wd*.04 and ez_lo<v.co.z<ez_hi and v.co.y>ey_lo]
    el=[v for v in fvs if v.co.x<cx-wd*.04 and ez_lo<v.co.z<ez_hi and v.co.y>ey_lo]
    def ec(c):
        if not c: return None,None
        return (min(c,key=lambda v:abs(v.co.x-cx)).co.copy(),
                max(c,key=lambda v:abs(v.co.x-cx)).co.copy())
    en_r,ex_r=ec(er); en_l,ex_l=ec(el)
    ez=n_pt.z+.04*ht; ey=n_pt.y+.005*fw
    r["exr"]=tuple(ex_r) if ex_r else (cx+wd*.18,ey-.01*fw,ez)
    r["enr"]=tuple(en_r) if en_r else (cx+wd*.08,ey,ez)
    r["exl"]=tuple(ex_l) if ex_l else (cx-wd*.18,ey-.01*fw,ez)
    r["enl"]=tuple(en_l) if en_l else (cx-wd*.08,ey,ez)
    # Palpebral pts: above/below eye center
    for side,cx_off,base_en,base_ex in [
            ("r",+1,r["enr"],r["exr"]),("l",-1,r["enl"],r["exl"])]:
        em=((base_en[0]+base_ex[0])/2,(base_en[1]+base_ex[1])/2,(base_en[2]+base_ex[2])/2)
        r[f"ps{side}"]=(em[0],em[1]-fw*0.005,em[2]+ht*0.02)
        r[f"pi{side}"]=(em[0],em[1]-fw*0.005,em[2]-ht*0.02)
    mc=[v for v in fvs if (sn.z-.12*ht)<v.co.z<(sn.z-.01*ht)
        and abs(v.co.x-cx)<wd*.20 and v.co.y>sn.y-.04*fw]
    if mc:
        sto=fwd(mc).co.copy()
        lsc=[v for v in mc if v.co.z>sto.z]; lic=[v for v in mc if v.co.z<sto.z]
        ls=fwd(lsc).co.copy() if lsc else mathutils.Vector((sto.x,sto.y,sto.z+.02*ht))
        li=fwd(lic).co.copy() if lic else mathutils.Vector((sto.x,sto.y,sto.z-.02*ht))
        chc=[v for v in fvs if (sto.z-.025*ht)<v.co.z<(sto.z+.025*ht) and v.co.y>sto.y-.03*fw]
        ch_r,ch_l=sides(chc) if chc else (mathutils.Vector((cx+wd*.12,sto.y,sto.z)),mathutils.Vector((cx-wd*.12,sto.y,sto.z)))
    else:
        sto=mathutils.Vector((cx,sn.y-.02*fw,sn.z-.06*ht))
        ls=mathutils.Vector((cx,sto.y,sto.z+.02*ht)); li=mathutils.Vector((cx,sto.y,sto.z-.02*ht))
        ch_r=mathutils.Vector((cx+wd*.12,sto.y,sto.z)); ch_l=mathutils.Vector((cx-wd*.12,sto.y,sto.z))
    r["ls"]=tuple(ls); r["li"]=tuple(li); r["chr"]=tuple(ch_r); r["chl"]=tuple(ch_l)
    r["cphr"]=(r["chr"][0]*.6+r["ls"][0]*.4, r["chr"][1], (r["chr"][2]+r["ls"][2])/2)
    r["cphl"]=(r["chl"][0]*.6+r["ls"][0]*.4, r["chl"][1], (r["chl"][2]+r["ls"][2])/2)
    chinc=[v for v in fvs if abs(v.co.x-cx)<wd*.15 and zmin<v.co.z<(li.z-.01*ht)]
    r["pg"]=tuple(fwd(chinc).co) if chinc else (cx,sn.y-.03*fw,cz-.20*ht)
    evz=[v for v in av if n_pt.z-.05*ht<v.co.z<n_pt.z+.12*ht]
    if evz: tr_r,tr_l=sides(evz)
    else:
        tr_r=mathutils.Vector((cx+wd*.50,(ymin+ymax)/2-.15*fw,n_pt.z))
        tr_l=mathutils.Vector((cx-wd*.50,(ymin+ymax)/2-.15*fw,n_pt.z))
    r["tr"]=tuple(tr_r); r["tl"]=tuple(tr_l)
    def ear_pts(tr_pt, sign):
        sa_v=[v for v in av if v.co.x*sign>cx*sign+wd*.30 and (tr_pt.z+.04*ht)<v.co.z<(tr_pt.z+.18*ht)]
        sba_v=[v for v in av if v.co.x*sign>cx*sign+wd*.30 and (tr_pt.z-.45*ht)<v.co.z<(tr_pt.z-.04*ht)]
        sa=max(sa_v,key=lambda v:v.co.x*sign).co if sa_v else mathutils.Vector((tr_pt.x,tr_pt.y,tr_pt.z+.12*ht))
        sba=max(sba_v,key=lambda v:v.co.x*sign).co if sba_v else mathutils.Vector((tr_pt.x,tr_pt.y,tr_pt.z-.50*ht))
        return sa,sba
    sar,sbar=ear_pts(mathutils.Vector(r["tr"]),+1)
    sal,sbal=ear_pts(mathutils.Vector(r["tl"]),-1)
    r["sar"]=tuple(sar); r["sbar"]=tuple(sbar); r["sal"]=tuple(sal); r["sbal"]=tuple(sbal)
    bm.free(); return r

# ─────────────────────────────────────────────────────────────────────────────
#  WIZARD COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
def compute_from_anchors(pn, eye_r, eye_l, tr, tl, pg, obj):
    eye_mid=(eye_r+eye_l)*.5; IPD=(eye_r-eye_l).length
    if IPD<1e-6: return {}
    rv=(eye_r-eye_l).normalized()
    ce=eye_mid-pg; uv=(ce-ce.dot(rv)*rv).normalized()
    fv=rv.cross(uv).normalized()
    if (pn-eye_mid).dot(fv)<0: fv=-fv
    res={"pn":pn,"pg":pg,"tr":tr,"tl":tl}
    EAR_R={"sar","sbar"}; EAR_L={"sal","sbal"}
    for lid,rat in WIZARD_RATIOS.items():
        if rat is None or lid in res: continue
        base=tr if lid in EAR_R else (tl if lid in EAR_L else eye_mid)
        res[lid]=base+rv*(IPD*rat[0])+uv*(IPD*rat[1])+fv*(IPD*rat[2])
    bm=get_mesh_bm(obj); bvh=mathutils.bvhtree.BVHTree.FromBMesh(bm); bm.free()
    out={}
    for lid,pos in res.items():
        if isinstance(pos,tuple): pos=mathutils.Vector(pos)
        hit,_,_,d=bvh.find_nearest(pos)
        out[lid]=hit if (hit and d<IPD*.7) else pos
    return out

# ─────────────────────────────────────────────────────────────────────────────
#  CONVEX HULL VERTEX SELECTION
# ─────────────────────────────────────────────────────────────────────────────
def select_by_convex_hull(obj, lm_positions, margin=0.005):
    """Select vertices inside convex hull of landmark positions (XZ projection + Y range)."""
    pts=[mathutils.Vector(p) for p in lm_positions]
    if len(pts)<1: return 0
    mat=obj.matrix_world
    # Y depth range from landmarks
    ys=[p.y for p in pts]; y_min=min(ys); y_max=max(ys)
    y_tol=max((y_max-y_min)*.6, margin*8)

    if len(pts)<3:
        # Sphere fallback
        center=sum(pts,mathutils.Vector())/(len(pts))
        r=max((p-center).length for p in pts)+margin
        count=0
        for v in obj.data.vertices:
            w=mat@v.co
            if (w-center).length<=r: v.select=True; count+=1
        return count

    # 2D convex hull in XZ plane
    pts_2d=[(p.x,p.z) for p in pts]
    try:
        hull_idx=convex_hull_2d(pts_2d)
    except Exception:
        hull_idx=list(range(len(pts_2d)))
    hull=[(pts_2d[i][0]+dx, pts_2d[i][1]+dz)
          for i in hull_idx
          for dx,dz in [(0,0)]]  # base pts

    # Expand hull by margin
    cx_h=sum(p[0] for p in hull)/len(hull)
    cz_h=sum(p[1] for p in hull)/len(hull)
    hull_exp=[]
    for px,pz in hull:
        dx,dz=px-cx_h, pz-cz_h
        L=math.sqrt(dx*dx+dz*dz) or 1
        hull_exp.append((px+dx/L*margin, pz+dz/L*margin))

    def inside_hull(px,pz):
        n=len(hull_exp)
        for i in range(n):
            x1,z1=hull_exp[i]; x2,z2=hull_exp[(i+1)%n]
            if (x2-x1)*(pz-z1)-(z2-z1)*(px-x1)<0: return False
        return True

    count=0
    for v in obj.data.vertices:
        w=mat@v.co
        if w.y<y_min-y_tol or w.y>y_max+y_tol: continue
        if inside_hull(w.x,w.z): v.select=True; count+=1
    return count

# ─────────────────────────────────────────────────────────────────────────────
#  DRAW UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def _sh(): return gpu.shader.from_builtin('UNIFORM_COLOR')
def _fill(pts, color):
    s=_sh(); b=batch_for_shader(s,'TRIS',{"pos":pts}); s.bind()
    s.uniform_float("color",color); b.draw(s)
def _stroke(pts, color, width=1.0, closed=False):
    if closed: pts=list(pts)+[pts[0]]
    try:
        s=gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        b=batch_for_shader(s,'LINE_STRIP',{"pos":pts}); s.bind()
        s.uniform_float("color",color); s.uniform_float("lineWidth",width)
        for w in bpy.context.window_manager.windows:
            for a in w.screen.areas:
                if a.type=='VIEW_3D':
                    for rg in a.regions:
                        if rg.type=='WINDOW':
                            s.uniform_float("viewportSize",(rg.width,rg.height))
        b.draw(s)
    except Exception:
        s2=_sh(); b2=batch_for_shader(s2,'LINE_STRIP',{"pos":pts})
        s2.bind(); s2.uniform_float("color",color); b2.draw(s2)
def _circ_tris(cx,cy,r,n=10):
    t=[]
    for i in range(n):
        a1,a2=2*math.pi*i/n,2*math.pi*(i+1)/n
        t+=[(cx,cy),(cx+r*math.cos(a1),cy+r*math.sin(a1)),(cx+r*math.cos(a2),cy+r*math.sin(a2))]
    return t
def _circ_pts(cx,cy,r,n=16):
    return [(cx+r*math.cos(2*math.pi*i/n),cy+r*math.sin(2*math.pi*i/n)) for i in range(n+1)]

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEMATIC PANEL DRAW
# ─────────────────────────────────────────────────────────────────────────────
def _n2s(nx,ny):
    """Normalized SVG coord → screen pixel inside panel."""
    dx=P_X+22; dy=P_Y+22; dw=P_W-44; dh=P_H-44
    return dx+nx*dw, dy+ny*dh

def draw_schematic():
    global _dot_positions
    _dot_positions={}
    context=bpy.context
    if not hasattr(context.scene,'facial_biom'): return
    props=context.scene.facial_biom
    active_lid=get_active_lid(context)
    placing=props.active_landmark
    eff_active=placing if placing else active_lid
    wiz=props.wizard_active; wstep=props.wizard_step
    wiz_lid=WIZARD_STEPS[wstep][0] if (wiz and wstep<len(WIZARD_STEPS)) else None

    gpu.state.blend_set('ALPHA')

    # Background
    _fill([(P_X,P_Y),(P_X+P_W,P_Y),(P_X+P_W,P_Y+P_H),(P_X,P_Y),(P_X+P_W,P_Y+P_H),(P_X,P_Y+P_H)],
          (0.05,0.05,0.05,0.90))
    _stroke([_n2s(0,0),_n2s(1,0),_n2s(1,1),_n2s(0,1),_n2s(0,0)],(0.28,0.28,0.28,1.0),1.5)

    # SVG paths
    path_style = {
        "face":     ((0.55,0.55,0.55,0.90), 1.8),
        "eye_r":    ((0.42,0.42,0.42,0.85), 1.2),
        "eye_l":    ((0.42,0.42,0.42,0.85), 1.2),
        "nose_r":   ((0.38,0.38,0.38,0.80), 1.0),
        "nose_l":   ((0.38,0.38,0.38,0.80), 1.0),
        "mouth_r":  ((0.38,0.38,0.38,0.80), 1.0),
        "mouth_l":  ((0.38,0.38,0.38,0.80), 1.0),
        "chin":     ((0.38,0.38,0.38,0.80), 1.0),
        "ear_r_out":((0.45,0.45,0.45,0.85), 1.5),
        "ear_l_out":((0.45,0.45,0.45,0.85), 1.5),
        "concha_r": ((0.35,0.35,0.35,0.75), 1.0),
        "concha_l": ((0.35,0.35,0.35,0.75), 1.0),
    }
    for pname,(col,w) in path_style.items():
        if pname in SVG_PATHS:
            pts_s=[_n2s(x,y) for x,y in SVG_PATHS[pname]]
            _stroke(pts_s, col, w)

    # Group highlight overlay
    if props.groups:
        gi=props.active_group
        if 0<=gi<len(props.groups):
            grp=props.groups[gi]
            gc=grp.color
            for lid in [x.strip() for x in grp.lm_ids.split(',') if x.strip()]:
                if lid in SCHEMATIC_POS:
                    sx,sy=_n2s(*SCHEMATIC_POS[lid])
                    _fill(_circ_tris(sx,sy,9,12),(gc[0],gc[1],gc[2],0.25))
                    _stroke(_circ_pts(sx,sy,9),(gc[0],gc[1],gc[2],0.70),1.5)

    # Landmark dots
    fid=0
    for d in LANDMARK_DEFS:
        lid=d[0]
        if lid not in SCHEMATIC_POS: continue
        sx,sy=_n2s(*SCHEMATIC_POS[lid])
        _dot_positions[lid]=(sx,sy)
        placed=lm_placed(lid)
        is_act=(lid==eff_active); is_wiz=(lid==wiz_lid)
        col=(1.0,0.55,0.0,1.0) if is_act else \
            ((0.0,0.85,1.0,1.0) if is_wiz else \
             ((0.25,0.95,0.35,0.90) if placed else (0.40,0.40,0.40,0.55)))
        r=6.5 if is_act else (5.5 if is_wiz else 4.0)
        _fill(_circ_tris(sx,sy,r,10),col)
        if is_act:   _stroke(_circ_pts(sx,sy,r+3.5),(1.0,0.55,0.0,0.7),1.5)
        if is_wiz and not _wizard_placed:
            _stroke(_circ_pts(sx,sy,r+5.5),(0.0,0.85,1.0,0.55),1.5)
        if is_wiz and _wizard_placed:
            _stroke(_circ_pts(sx,sy,r+4.0),(0.2,1.0,0.2,0.8),1.5)
        blf.size(fid,8); blf.color(fid,0.88,0.88,0.88,0.85 if placed else 0.4)
        blf.position(fid,sx+5,sy+3,0); blf.draw(fid,lid)

    # Title
    blf.size(fid,11); blf.color(fid,0.72,0.72,0.72,1.0)
    blf.position(fid,P_X+10,P_Y+P_H-16,0)
    title=f"FARKAS 1994  ·  {sum(1 for d in LANDMARK_DEFS if lm_placed(d[0]))}/27"
    blf.draw(fid,title)

    # Wizard info
    if wiz and wstep<len(WIZARD_STEPS):
        _,sname,sinstr=WIZARD_STEPS[wstep]
        blf.size(fid,10); blf.color(fid,1.0,0.78,0.2,1.0)
        blf.position(fid,P_X+10,P_Y+P_H-30,0); blf.draw(fid,f"▶ {sname}")
        blf.size(fid,9); blf.color(fid,0.75,0.75,0.75,1.0)
        blf.position(fid,P_X+10,P_Y+P_H-43,0); blf.draw(fid,sinstr[:38])

    # Description at bottom
    desc_lid=eff_active or (wiz_lid if wiz else None)
    if desc_lid and desc_lid in LANDMARK_DESC:
        desc=LANDMARK_DESC[desc_lid]
        words=desc.split(); cur=""; lines=[]
        for w in words:
            if len(cur)+len(w)+1<=44: cur=(cur+" "+w).strip()
            else: lines.append(cur); cur=w
        if cur: lines.append(cur)
        blf.size(fid,9); blf.color(fid,0.68,0.68,0.68,1.0)
        for i,ln in enumerate(lines[:2]):
            blf.position(fid,P_X+10,P_Y-14-i*13,0); blf.draw(fid,ln)

    gpu.state.blend_set('NONE')

# ─────────────────────────────────────────────────────────────────────────────
#  3D / 2D DRAW CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────
def draw_3d():
    ctx=bpy.context
    if not hasattr(ctx.scene,'facial_biom'): return
    props=ctx.scene.facial_biom
    if not props.show_lines: return
    region=ctx.region
    placed={d[0]:mathutils.Vector(get_lm_pos(d[0])) for d in LANDMARK_DEFS if lm_placed(d[0])}
    if not placed: return
    verts=[]
    for a,b in DISTANCE_LINES:
        if a in placed and b in placed: verts+=[tuple(placed[a]),tuple(placed[b])]
    if not verts: return
    lc=props.line_color
    gpu.state.blend_set('ALPHA')
    try:
        s=gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        bat=batch_for_shader(s,'LINES',{"pos":verts}); s.bind()
        s.uniform_float("color",(lc[0],lc[1],lc[2],lc[3]))
        s.uniform_float("lineWidth",props.line_thickness)
        s.uniform_float("viewportSize",(region.width,region.height)); bat.draw(s)
    except Exception:
        s2=_sh(); bat2=batch_for_shader(s2,'LINES',{"pos":verts})
        s2.bind(); s2.uniform_float("color",(lc[0],lc[1],lc[2],lc[3])); bat2.draw(s2)
    gpu.state.blend_set('NONE')

def draw_2d():
    ctx=bpy.context
    if not hasattr(ctx.scene,'facial_biom'): return
    props=ctx.scene.facial_biom
    region=ctx.region; rv3d=ctx.region_data
    if not region or not rv3d: return
    draw_schematic()
    placed={d[0]:mathutils.Vector(get_lm_pos(d[0])) for d in LANDMARK_DEFS if lm_placed(d[0])}
    fid=0
    if props.show_labels and placed:
        lc=props.label_color; blf.color(fid,lc[0],lc[1],lc[2],lc[3]); blf.size(fid,props.label_size)
        for lid,p3 in placed.items():
            p2=view3d_utils.location_3d_to_region_2d(region,rv3d,p3)
            if p2: blf.position(fid,p2.x+6,p2.y+5,0); blf.draw(fid,lid)
    if props.show_distances and placed:
        dc=props.dist_color; blf.color(fid,dc[0],dc[1],dc[2],dc[3]); blf.size(fid,max(props.label_size-2,8))
        for a,b in DISTANCE_LINES:
            if a not in placed or b not in placed: continue
            m3=(placed[a]+placed[b])*.5; m2=view3d_utils.location_3d_to_region_2d(region,rv3d,m3)
            if m2: blf.position(fid,m2.x+3,m2.y+3,0); blf.draw(fid,f"{(placed[a]-placed[b]).length*1000:.1f}mm")
    if props.wizard_active and props.wizard_step<len(WIZARD_STEPS):
        _,sn,si=WIZARD_STEPS[props.wizard_step]
        title=f"WIZARD  {props.wizard_step+1}/{len(WIZARD_STEPS)}  —  {sn}"
        blf.size(fid,16); blf.color(fid,1.0,0.85,0.15,1.0)
        tw,_=blf.dimensions(fid,title)
        blf.position(fid,(region.width-tw)//2,region.height-52,0); blf.draw(fid,title)
        blf.size(fid,12); blf.color(fid,.9,.9,.9,1.0); iw,_=blf.dimensions(fid,si)
        blf.position(fid,(region.width-iw)//2,region.height-70,0); blf.draw(fid,si)
        hint=("INVIO = conferma  |  clicca di nuovo per riposizionare"
              if _wizard_placed else "Clicca sulla mesh")
        blf.size(fid,11); blf.color(fid,.5,1.0,.5,1.0); hw,_=blf.dimensions(fid,hint)
        blf.position(fid,(region.width-hw)//2,region.height-88,0); blf.draw(fid,hint)

def reg_handlers():
    global _handle_3d,_handle_2d
    if not _handle_3d:
        _handle_3d=bpy.types.SpaceView3D.draw_handler_add(draw_3d,(),'WINDOW','POST_VIEW')
    if not _handle_2d:
        _handle_2d=bpy.types.SpaceView3D.draw_handler_add(draw_2d,(),'WINDOW','POST_PIXEL')
def unreg_handlers():
    global _handle_3d,_handle_2d
    if _handle_3d: bpy.types.SpaceView3D.draw_handler_remove(_handle_3d,'WINDOW'); _handle_3d=None
    if _handle_2d: bpy.types.SpaceView3D.draw_handler_remove(_handle_2d,'WINDOW'); _handle_2d=None
def overlay_on(): return _handle_3d is not None

# ─────────────────────────────────────────────────────────────────────────────
#  OPERATORS
# ─────────────────────────────────────────────────────────────────────────────
class FBIO_OT_ToggleOverlay(Operator):
    bl_idname="fbio.toggle_overlay"; bl_label="Toggle Overlay"
    def execute(self,c):
        if overlay_on(): unreg_handlers(); self.report({'INFO'},"OFF")
        else: reg_handlers(); self.report({'INFO'},"ON")
        _tag(); return {'FINISHED'}

class FBIO_OT_AutoDetect(Operator):
    bl_idname="fbio.auto_detect"; bl_label="Auto-Detect Landmarks"
    def execute(self,c):
        p=c.scene.facial_biom
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"Seleziona una mesh"); return {'CANCELLED'}
        obj=bpy.data.objects[p.target_mesh]
        if obj.type!='MESH': self.report({'ERROR'},"Deve essere una mesh"); return {'CANCELLED'}
        res=auto_detect(obj); count=0
        for d in LANDMARK_DEFS:
            if d[0] in res: create_lm_empty(d[0],res[d[0]],d[3]); count+=1
        self.report({'INFO'},f"{count} landmark piazzati"); _tag(); return {'FINISHED'}

class FBIO_OT_WizardAdvance(Operator):
    bl_idname="fbio.wizard_advance"; bl_label="Avanti →"
    def execute(self,c):
        global _wizard_should_advance; _wizard_should_advance=True; return {'FINISHED'}

_wizard_should_advance=False

class FBIO_OT_Wizard(Operator):
    bl_idname="fbio.wizard"; bl_label="Alignment Wizard"
    bl_description="6 punti → genera tutti i 27 landmark"
    def invoke(self,c,e):
        global _wizard_should_advance,_wizard_placed,_wizard_temps
        p=c.scene.facial_biom
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"Seleziona una mesh"); return {'CANCELLED'}
        _wizard_should_advance=False; _wizard_placed=False; _wizard_temps={}
        if _WIZARD_TEMP in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[_WIZARD_TEMP],do_unlink=True)
        p.wizard_active=True; p.wizard_step=0
        c.window_manager.modal_handler_add(self); _tag(); return {'RUNNING_MODAL'}
    def modal(self,c,e):
        global _wizard_should_advance,_wizard_placed
        _tag()
        if e.type=='ESC': self._cancel(c); return {'CANCELLED'}
        adv=(_wizard_should_advance or (e.type in {'RET','SPACE'} and e.value=='PRESS'))
        if adv:
            _wizard_should_advance=False
            if not _wizard_placed: self.report({'WARNING'},"Piazza prima il punto!"); return {'RUNNING_MODAL'}
            self._commit(c); p=c.scene.facial_biom
            if p.wizard_step>=len(WIZARD_STEPS): self._finish(c); return {'FINISHED'}
            _wizard_placed=False
            if _WIZARD_TEMP in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[_WIZARD_TEMP],do_unlink=True)
            _tag(); return {'RUNNING_MODAL'}
        if (e.type=='LEFTMOUSE' and e.value=='PRESS'
                and c.area and c.area.type=='VIEW_3D'):
            if _in_panel(e.mouse_region_x,e.mouse_region_y): return {'PASS_THROUGH'}
            p=c.scene.facial_biom; obj=bpy.data.objects.get(p.target_mesh)
            if not obj: return {'RUNNING_MODAL'}
            region=c.region; rv3d=c.region_data
            ro=view3d_utils.region_2d_to_origin_3d(region,rv3d,(e.mouse_region_x,e.mouse_region_y))
            rd=view3d_utils.region_2d_to_vector_3d(region,rv3d,(e.mouse_region_x,e.mouse_region_y))
            mi=obj.matrix_world.inverted()
            hit,loc,_,_=obj.ray_cast(mi@ro,mi.to_3x3()@rd)
            if hit:
                wloc=obj.matrix_world@loc
                if _WIZARD_TEMP in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects[_WIZARD_TEMP],do_unlink=True)
                bpy.ops.object.empty_add(type='PLAIN_AXES',location=wloc)
                em=bpy.context.object; em.name=_WIZARD_TEMP; em.empty_display_size=0.012
                em.color=(1.0,0.4,0.0,1.0)
                col=get_or_create_col()
                for cc in em.users_collection: cc.objects.unlink(em)
                col.objects.link(em); _wizard_placed=True; _tag()
            else: self.report({'WARNING'},"Clicca sulla mesh")
            return {'RUNNING_MODAL'}
        if e.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE'} or e.alt: return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}
    def _commit(self,c):
        p=c.scene.facial_biom; lid=WIZARD_STEPS[p.wizard_step][0]
        if _WIZARD_TEMP in bpy.data.objects:
            _wizard_temps[lid]=bpy.data.objects[_WIZARD_TEMP].location.copy()
        p.wizard_step+=1
    def _finish(self,c):
        p=c.scene.facial_biom; p.wizard_active=False; p.wizard_step=0
        if _WIZARD_TEMP in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[_WIZARD_TEMP],do_unlink=True)
        req=('pn','_eye_r','_eye_l','tr','tl','pg')
        if not all(k in _wizard_temps for k in req): self.report({'ERROR'},"Anchor incompleto"); return
        obj=bpy.data.objects.get(p.target_mesh)
        if not obj: return
        res=compute_from_anchors(_wizard_temps['pn'],_wizard_temps['_eye_r'],
                                  _wizard_temps['_eye_l'],_wizard_temps['tr'],
                                  _wizard_temps['tl'],_wizard_temps['pg'],obj)
        count=0
        for d in LANDMARK_DEFS:
            if d[0] in res: create_lm_empty(d[0],tuple(res[d[0]]),d[3]); count+=1
        self.report({'INFO'},f"Wizard: {count} landmark generati"); _tag()
    def _cancel(self,c):
        c.scene.facial_biom.wizard_active=False; c.scene.facial_biom.wizard_step=0
        if _WIZARD_TEMP in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[_WIZARD_TEMP],do_unlink=True)
        _tag(); self.report({'INFO'},"Wizard annullato")

class FBIO_OT_SchematicClick(Operator):
    bl_idname="fbio.schematic_click"; bl_label="Schematic Click"
    bl_options={'INTERNAL'}
    def invoke(self,c,e):
        global _schematic_running; _schematic_running=True
        c.window_manager.modal_handler_add(self); return {'RUNNING_MODAL'}
    def modal(self,c,e):
        global _schematic_running
        if not overlay_on(): _schematic_running=False; return {'CANCELLED'}

        # Always pass through keyboard events — never block Tab, shortcuts, etc.
        if e.type not in {'LEFTMOUSE','RIGHTMOUSE','MIDDLEMOUSE'}:
            return {'PASS_THROUGH'}

        # Only act on LMB press inside schematic panel
        if (e.type=='LEFTMOUSE' and e.value=='PRESS'
                and c.area and c.area.type=='VIEW_3D'):
            mx,my=e.mouse_region_x,e.mouse_region_y
            if _in_panel(mx,my):
                best=None; bd=14**2
                for lid,(sx,sy) in _dot_positions.items():
                    d=(mx-sx)**2+(my-sy)**2
                    if d<bd: bd=d; best=lid
                if best:
                    name=empty_name(best)
                    if name in bpy.data.objects:
                        bpy.ops.object.select_all(action='DESELECT')
                        obj=bpy.data.objects[name]; obj.select_set(True)
                        try: c.view_layer.objects.active=obj
                        except Exception: pass
                        _tag()
                return {'RUNNING_MODAL'}  # consume only clicks inside panel

        return {'PASS_THROUGH'}
    def cancel(self,c): global _schematic_running; _schematic_running=False

class FBIO_OT_PlaceLandmark(Operator):
    bl_idname="fbio.place_landmark"; bl_label="Place Landmark"
    lid: StringProperty()
    def invoke(self,c,e):
        c.scene.facial_biom.active_landmark=self.lid
        c.window_manager.modal_handler_add(self)
        self.report({'INFO'},f"Clicca mesh → [{self.lid}]  ESC=annulla")
        _tag(); return {'RUNNING_MODAL'}
    def modal(self,c,e):
        _tag()
        if e.type=='ESC': c.scene.facial_biom.active_landmark=""; _tag(); return {'CANCELLED'}
        if (e.type=='LEFTMOUSE' and e.value=='PRESS'
                and c.area and c.area.type=='VIEW_3D'):
            if _in_panel(e.mouse_region_x,e.mouse_region_y): return {'PASS_THROUGH'}
            p=c.scene.facial_biom
            if not p.target_mesh or p.target_mesh not in bpy.data.objects:
                p.active_landmark=""; return {'CANCELLED'}
            obj=bpy.data.objects[p.target_mesh]
            region=c.region; rv3d=c.region_data
            coord=(e.mouse_region_x,e.mouse_region_y)
            ro=view3d_utils.region_2d_to_origin_3d(region,rv3d,coord)
            rd=view3d_utils.region_2d_to_vector_3d(region,rv3d,coord)
            mi=obj.matrix_world.inverted()
            hit,loc,_,_=obj.ray_cast(mi@ro,mi.to_3x3()@rd)
            if hit:
                wloc=obj.matrix_world@loc
                grp=next((d[3] for d in LANDMARK_DEFS if d[0]==self.lid),"upper")
                create_lm_empty(self.lid,wloc,grp); self.report({'INFO'},f"{self.lid} piazzato")
            else: self.report({'WARNING'},"Nessun hit")
            p.active_landmark=""; _tag(); return {'FINISHED'}
        if e.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE','RIGHTMOUSE'} or e.alt:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

class FBIO_OT_DeleteLandmark(Operator):
    bl_idname="fbio.delete_landmark"; bl_label="Delete"
    lid: StringProperty()
    def execute(self,c):
        n=empty_name(self.lid)
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
        _tag(); return {'FINISHED'}

class FBIO_OT_DeleteAll(Operator):
    bl_idname="fbio.delete_all"; bl_label="Delete All"
    def execute(self,c):
        for d in LANDMARK_DEFS:
            n=empty_name(d[0])
            if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
        _tag(); return {'FINISHED'}

class FBIO_OT_SnapToMesh(Operator):
    bl_idname="fbio.snap_to_mesh"; bl_label="Snap All to Mesh"
    def execute(self,c):
        p=c.scene.facial_biom
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"No mesh"); return {'CANCELLED'}
        bm=get_mesh_bm(bpy.data.objects[p.target_mesh])
        bvh=mathutils.bvhtree.BVHTree.FromBMesh(bm); bm.free(); count=0
        for d in LANDMARK_DEFS:
            n=empty_name(d[0])
            if n in bpy.data.objects:
                e=bpy.data.objects[n]; hit,*_=bvh.find_nearest(mathutils.Vector(e.location))
                if hit: e.location=hit; count+=1
        self.report({'INFO'},f"Snapped {count}"); return {'FINISHED'}

# ── Group management ─────────────────────────────────────────────────────────
class FBIO_OT_AddGroup(Operator):
    bl_idname="fbio.add_group"; bl_label="Add Group"
    def execute(self,c):
        g=c.scene.facial_biom.groups.add(); g.name="New Group"; return {'FINISHED'}

class FBIO_OT_RemoveGroup(Operator):
    bl_idname="fbio.remove_group"; bl_label="Remove Group"
    def execute(self,c):
        p=c.scene.facial_biom
        if 0<=p.active_group<len(p.groups):
            p.groups.remove(p.active_group)
            p.active_group=max(0,p.active_group-1)
        return {'FINISHED'}

class FBIO_OT_ToggleLmInGroup(Operator):
    """Toggle a landmark in/out of the active group."""
    bl_idname="fbio.toggle_lm_in_group"; bl_label="Toggle in Group"
    lid: StringProperty()
    def execute(self,c):
        p=c.scene.facial_biom
        if not (0<=p.active_group<len(p.groups)): return {'CANCELLED'}
        grp=p.groups[p.active_group]
        ids=[x.strip() for x in grp.lm_ids.split(',') if x.strip()]
        if self.lid in ids: ids.remove(self.lid)
        else: ids.append(self.lid)
        grp.lm_ids=','.join(ids); _tag(); return {'FINISHED'}

class FBIO_OT_SelectGroup(Operator):
    """Select vertices in the convex hull of the active landmark group."""
    bl_idname="fbio.select_group"; bl_label="Select Group (Convex Hull)"
    group_idx: IntProperty(default=-1)
    def execute(self,c):
        p=c.scene.facial_biom
        idx=self.group_idx if self.group_idx>=0 else p.active_group
        if not (0<=idx<len(p.groups)): self.report({'ERROR'},"No group"); return {'CANCELLED'}
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"No mesh"); return {'CANCELLED'}
        grp=p.groups[idx]; obj=bpy.data.objects[p.target_mesh]
        ids=[x.strip() for x in grp.lm_ids.split(',') if x.strip()]
        positions=[get_lm_pos(lid) for lid in ids if get_lm_pos(lid)]
        if not positions: self.report({'WARNING'},"Nessun landmark piazzato nel gruppo"); return {'CANCELLED'}
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        n=select_by_convex_hull(obj,positions,grp.hull_margin)
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'},f"{n} vertici selezionati per '{grp.name}'"); return {'FINISHED'}

class FBIO_OT_CreateVGroup(Operator):
    """Select + assign to Vertex Group."""
    bl_idname="fbio.create_vgroup"; bl_label="Crea Vertex Group"
    group_idx: IntProperty(default=-1)
    def execute(self,c):
        p=c.scene.facial_biom
        idx=self.group_idx if self.group_idx>=0 else p.active_group
        if not (0<=idx<len(p.groups)): self.report({'ERROR'},"No group"); return {'CANCELLED'}
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"No mesh"); return {'CANCELLED'}
        grp=p.groups[idx]; obj=bpy.data.objects[p.target_mesh]
        ids=[x.strip() for x in grp.lm_ids.split(',') if x.strip()]
        positions=[get_lm_pos(lid) for lid in ids if get_lm_pos(lid)]
        if not positions: self.report({'WARNING'},"Nessun landmark piazzato"); return {'CANCELLED'}
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        select_by_convex_hull(obj,positions,grp.hull_margin)
        # Create / overwrite vertex group
        vg_name=f"FBM_{grp.name}"
        if vg_name in obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups[vg_name])
        vg=obj.vertex_groups.new(name=vg_name)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.vertex_group_assign()
        n_verts=sum(1 for v in obj.data.vertices if v.select)
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'},f"Vertex Group '{vg_name}' creato con {n_verts} vertici")
        return {'FINISHED'}

class FBIO_OT_CreateAllVGroups(Operator):
    """Create vertex groups for all groups at once."""
    bl_idname="fbio.create_all_vgroups"; bl_label="Crea Tutti i Vertex Groups"
    def execute(self,c):
        p=c.scene.facial_biom
        if not p.target_mesh or p.target_mesh not in bpy.data.objects:
            self.report({'ERROR'},"No mesh"); return {'CANCELLED'}
        obj=bpy.data.objects[p.target_mesh]
        bpy.context.view_layer.objects.active=obj
        created=0
        for i,grp in enumerate(p.groups):
            ids=[x.strip() for x in grp.lm_ids.split(',') if x.strip()]
            positions=[get_lm_pos(lid) for lid in ids if get_lm_pos(lid)]
            if not positions: continue
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            select_by_convex_hull(obj,positions,grp.hull_margin)
            vg_name=f"FBM_{grp.name}"
            if vg_name in obj.vertex_groups:
                obj.vertex_groups.remove(obj.vertex_groups[vg_name])
            obj.vertex_groups.new(name=vg_name)
            bpy.context.view_layer.objects.active=obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.vertex_group_assign()
            created+=1
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'},f"{created} vertex groups creati"); return {'FINISHED'}

class FBIO_OT_Export(Operator):
    bl_idname="fbio.export_measurements"; bl_label="Export TXT"
    def execute(self,c):
        p=c.scene.facial_biom; path=bpy.path.abspath(p.export_path)
        placed={d[0]:get_lm_pos(d[0]) for d in LANDMARK_DEFS if lm_placed(d[0])}
        if not placed: self.report({'ERROR'},"No landmarks"); return {'CANCELLED'}
        lines=["="*66,"  FARKAS FACIAL MEASUREMENTS (1994 standard)",
               f"  File: {bpy.data.filepath or 'unsaved'}",
               f"  Mesh: {p.target_mesh}","="*66,"",
               "LANDMARK COORDINATES","-"*66]
        for d in LANDMARK_DEFS:
            if d[0] in placed:
                pp=placed[d[0]]
                lines.append(f"  {d[0]:<8} {d[1]:<28}  X={pp[0]:+.4f}  Y={pp[1]:+.4f}  Z={pp[2]:+.4f}")
        lines+=["","MEASUREMENTS","-"*66]
        for a,b,lbl in MEASUREMENT_PAIRS:
            if a in placed and b in placed:
                d=(mathutils.Vector(placed[a])-mathutils.Vector(placed[b])).length
                lines.append(f"  {lbl:<44}  {d*1000:>8.2f} mm")
        lines+=["","DISTANCE MATRIX (mm)","-"*66]
        keys=list(placed.keys())
        lines.append(" "*10+"".join(f"{k:>10}" for k in keys))
        for ka in keys:
            row=f"{ka:<10}"
            for kb in keys:
                row+=f"{'---':>10}" if ka==kb else \
                     f"{(mathutils.Vector(placed[ka])-mathutils.Vector(placed[kb])).length*1000:>10.2f}"
            lines.append(row)
        lines+=["","="*66]
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
            open(path,'w',encoding='utf-8').write("\n".join(lines))
            self.report({'INFO'},f"Salvato → {path}")
        except Exception as e:
            self.report({'ERROR'},str(e)); return {'CANCELLED'}
        return {'FINISHED'}

# ─────────────────────────────────────────────────────────────────────────────
#  UI PANELS
# ─────────────────────────────────────────────────────────────────────────────
class FBIO_UL_Groups(UIList):
    def draw_item(self,c,layout,data,item,icon,active_data,active_prop,index,flt_flag):
        row=layout.row(align=True)
        row.prop(item,"color",text="",emboss=True)
        row.prop(item,"name",text="",emboss=False)
        ids=[x.strip() for x in item.lm_ids.split(',') if x.strip()]
        row.label(text=f"({len(ids)})")

class FBIO_PT_Main(Panel):
    bl_label="Facial Biometry"; bl_idname="FBIO_PT_Main"
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category="Biometry"
    def draw(self,c):
        L=self.layout; p=c.scene.facial_biom; on=overlay_on()
        b=L.box(); b.label(text="Target Mesh",icon='MESH_DATA')
        b.prop_search(p,"target_mesh",bpy.data,"objects",text="")
        L.separator()
        if p.wizard_active and p.wizard_step<len(WIZARD_STEPS):
            b=L.box(); step=p.wizard_step; _,sn,si=WIZARD_STEPS[step]
            b.label(text=f"WIZARD {step+1}/{len(WIZARD_STEPS)}: {sn}",icon='ORIENTATION_CURSOR')
            b.label(text=si,icon='INFO')
            row=b.row(align=True); sub=row.row(); sub.enabled=_wizard_placed
            sub.operator("fbio.wizard_advance",icon='FRAME_NEXT')
            row.operator("fbio.wizard",text="Annulla",icon='X')
        else:
            b=L.box(); b.label(text="Detection",icon='SHADERFX')
            col=b.column(align=True)
            col.operator("fbio.auto_detect",  icon='OUTLINER_OB_EMPTY',text="Auto-Detect")
            col.operator("fbio.wizard",       icon='ORIENTATION_CURSOR',text="▶ Wizard (6 punti)")
            col.operator("fbio.snap_to_mesh", icon='SNAP_ON')
            col.operator("fbio.delete_all",   icon='TRASH')
        L.separator()
        b=L.box(); row=b.row()
        row.label(text="3D Overlay",icon='HIDE_OFF' if on else 'HIDE_ON')
        row.operator("fbio.toggle_overlay",text="ON" if on else "OFF",depress=on)
        if on:
            col=b.column(align=True)
            col.prop(p,"show_labels"); col.prop(p,"show_lines"); col.prop(p,"show_distances")
            col.prop(p,"label_size"); col.prop(p,"line_thickness")
            col.prop(p,"line_color"); col.prop(p,"label_color"); col.prop(p,"dist_color")
        L.separator()
        b=L.box(); b.label(text="Export",icon='TEXT')
        b.prop(p,"export_path",text=""); b.operator("fbio.export_measurements",icon='EXPORT')

class FBIO_PT_Landmarks(Panel):
    bl_label="Landmark Placement"; bl_idname="FBIO_PT_Landmarks"
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category="Biometry"
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):
        L=self.layout; p=c.scene.facial_biom; alid=get_active_lid(c)
        row=L.row(align=True); row.label(text="Filtro:"); row.prop(p,"filter_group",text="")
        n=sum(1 for d in LANDMARK_DEFS if lm_placed(d[0]))
        L.label(text=f"{n}/27",icon='INFO'); L.separator()
        cur=None; box=None
        for d in LANDMARK_DEFS:
            lid,lbl,side,grp=d
            if p.filter_group!="ALL" and grp!=p.filter_group: continue
            if grp!=cur:
                cur=grp; box=L.box(); box.label(text=grp.upper(),icon='BONE_DATA')
            placed=lm_placed(lid); row=box.row(align=True)
            if lid==alid: row.alert=True
            row.label(text="",icon='CHECKMARK' if placed else 'RADIOBUT_OFF')
            row.label(text=f"{lid}  {lbl}")
            if p.active_landmark==lid: row.label(text="← clicca",icon='CURSOR')
            else:
                op=row.operator("fbio.place_landmark",text="",icon='CURSOR'); op.lid=lid
            if placed:
                op2=row.operator("fbio.delete_landmark",text="",icon='X'); op2.lid=lid

class FBIO_PT_Groups(Panel):
    bl_label="Gruppi & Vertex Groups"; bl_idname="FBIO_PT_Groups"
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category="Biometry"
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):
        L=self.layout; p=c.scene.facial_biom
        # Group list
        row=L.row()
        row.template_list("FBIO_UL_Groups","",p,"groups",p,"active_group",rows=5)
        col=row.column(align=True)
        col.operator("fbio.add_group",icon='ADD',text="")
        col.operator("fbio.remove_group",icon='REMOVE',text="")
        # Active group editor
        if 0<=p.active_group<len(p.groups):
            grp=p.groups[p.active_group]; b=L.box()
            b.prop(grp,"name"); b.prop(grp,"hull_margin")
            b.label(text="Landmark nel gruppo:",icon='BONE_DATA')
            ids=[x.strip() for x in grp.lm_ids.split(',') if x.strip()]
            # Grid of toggles
            flow=b.column_flow(columns=3,align=True)
            for d in LANDMARK_DEFS:
                lid=d[0]; is_in=(lid in ids)
                op=flow.operator("fbio.toggle_lm_in_group",
                                 text=lid,
                                 depress=is_in,
                                 emboss=True)
                op.lid=lid
            b.separator()
            row2=b.row(align=True)
            op1=row2.operator("fbio.select_group",text="Seleziona",icon='RESTRICT_SELECT_OFF')
            op1.group_idx=p.active_group
            op2=row2.operator("fbio.create_vgroup",text="→ Vertex Group",icon='GROUP_VERTEX')
            op2.group_idx=p.active_group
        L.separator()
        L.operator("fbio.create_all_vgroups",icon='GROUP_VERTEX')

class FBIO_PT_Measurements(Panel):
    bl_label="Measurements"; bl_idname="FBIO_PT_Measurements"
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category="Biometry"
    bl_options={'DEFAULT_CLOSED'}
    def draw(self,c):
        L=self.layout
        placed={d[0]:get_lm_pos(d[0]) for d in LANDMARK_DEFS if lm_placed(d[0])}
        if not placed: L.label(text="Nessun landmark",icon='INFO'); return
        L.label(text=f"{len(placed)}/27")
        for a,b,lbl in MEASUREMENT_PAIRS:
            if a in placed and b in placed:
                d=(mathutils.Vector(placed[a])-mathutils.Vector(placed[b])).length*1000
                row=L.row(); row.label(text=lbl); row.label(text=f"{d:.1f}mm")

# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────
classes=[
    LandmarkGroupItem, FacialBiomProps,
    FBIO_OT_ToggleOverlay, FBIO_OT_AutoDetect,
    FBIO_OT_Wizard, FBIO_OT_WizardAdvance, FBIO_OT_SchematicClick,
    FBIO_OT_PlaceLandmark, FBIO_OT_DeleteLandmark, FBIO_OT_DeleteAll,
    FBIO_OT_SnapToMesh,
    FBIO_OT_AddGroup, FBIO_OT_RemoveGroup, FBIO_OT_ToggleLmInGroup,
    FBIO_OT_SelectGroup, FBIO_OT_CreateVGroup, FBIO_OT_CreateAllVGroups,
    FBIO_OT_Export,
    FBIO_UL_Groups,
    FBIO_PT_Main, FBIO_PT_Landmarks, FBIO_PT_Groups, FBIO_PT_Measurements,
]

def _init_defaults():
    """Called once after register to populate default groups."""
    if not hasattr(bpy.context,'scene'): return None
    scene=bpy.context.scene
    if not hasattr(scene,'facial_biom'): return None
    p=scene.facial_biom
    if len(p.groups)==0:
        for name,ids,col in DEFAULT_GROUPS:
            g=p.groups.add(); g.name=name; g.lm_ids=ids
            g.color=(col[0],col[1],col[2])
    global _schematic_running
    if not _schematic_running and overlay_on():
        try: bpy.ops.fbio.schematic_click('INVOKE_DEFAULT')
        except Exception: pass
    return None

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.facial_biom=PointerProperty(type=FacialBiomProps)
    reg_handlers()
    bpy.app.timers.register(_init_defaults,first_interval=0.8)

def unregister():
    unreg_handlers()
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    if hasattr(bpy.types.Scene,'facial_biom'): del bpy.types.Scene.facial_biom

if __name__=="__main__": register()
