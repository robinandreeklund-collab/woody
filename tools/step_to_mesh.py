#!/usr/bin/env python3
"""STEP → lättviktig GLB-mesh för GUI:ts 3D-vy (digital tvilling).

Tesselerar en CAD-STEP (t.ex. step/Rig.step) till en grov ytmesh och exporterar
en kompakt binär glTF (.glb) som Qt Quick 3D laddar via RuntimeLoader. Backdrop-
kvalitet: lågt polygonantal, ej precision.

Beroenden (installeras på dev-dator, EJ Jetson — OpenCASCADE är tungt på arm64):
    pip install gmsh trimesh fast-simplification
    # gmsh kräver libGLU:  sudo apt-get install -y libglu1-mesa

Användning:
    python tools/step_to_mesh.py step/Rig.step app/ui/assets/rig.glb
    python tools/step_to_mesh.py step/Rig.step out.glb --size-max 14 --faces 120000
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile


def tessellate(step_path: str, size_min: float, size_max: float) -> str:
    """STEP → STL (grov ytmesh) via gmsh/OpenCASCADE. Returnerar STL-sökväg."""
    import gmsh
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.OCCImportLabels", 0)
        gmsh.open(step_path)
        bb = gmsh.model.getBoundingBox(-1, -1)
        print(f"bbox mm: X[{bb[0]:.0f},{bb[3]:.0f}] Y[{bb[1]:.0f},{bb[4]:.0f}] "
              f"Z[{bb[2]:.0f},{bb[5]:.0f}]  "
              f"storlek {bb[3]-bb[0]:.0f}×{bb[4]-bb[1]:.0f}×{bb[5]-bb[2]:.0f}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", size_min)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size_max)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.option.setNumber("Mesh.Algorithm", 6)            # Frontal-Delaunay
        gmsh.model.mesh.generate(2)                           # endast ytmesh
        out = os.path.join(tempfile.gettempdir(), "woody_rig_tess.stl")
        gmsh.write(out)
        return out
    finally:
        gmsh.finalize()


def to_glb(stl_path: str, glb_path: str, target_faces: int) -> None:
    """STL → decimerad GLB via trimesh (+ fast-simplification om tillgängligt)."""
    import numpy as np
    import trimesh
    m = trimesh.load(stl_path, process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    print(f"in: {len(m.faces)} faces, {len(m.vertices)} verts  "
          f"extents {np.round(m.extents, 1).tolist()} mm")
    if target_faces and len(m.faces) > target_faces:
        try:
            import fast_simplification
            v, f = fast_simplification.simplify(m.vertices, m.faces,
                                                target_count=target_faces)
            m = trimesh.Trimesh(v, f, process=True)
            print(f"decimerad → {len(m.faces)} faces")
        except Exception as exc:
            print(f"decimering hoppad ({exc}) — exporterar full mesh")
    m.merge_vertices()
    # matt mörk-grå (rigg) — låg metallic → syns under direktljus utan IBL-miljö
    # (metalliska ytor blir svarta utan omgivning att spegla)
    from trimesh.visual.material import PBRMaterial
    mat = PBRMaterial(name="rig_matte", baseColorFactor=[72, 78, 86, 255],
                      metallicFactor=0.08, roughnessFactor=0.55)
    uv = np.zeros((len(m.vertices), 2), np.float32)
    m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
    os.makedirs(os.path.dirname(os.path.abspath(glb_path)), exist_ok=True)
    m.export(glb_path)
    print(f"GLB: {glb_path}  {os.path.getsize(glb_path)/1e6:.1f} MB")


def main(argv):
    ap = argparse.ArgumentParser(description="STEP → GLB för GUI:ts digitala tvilling")
    ap.add_argument("step", help="indata STEP/STP")
    ap.add_argument("glb", help="utdata GLB")
    ap.add_argument("--size-min", type=float, default=2.0, help="min elementstorlek (mm)")
    ap.add_argument("--size-max", type=float, default=14.0, help="max elementstorlek (mm)")
    ap.add_argument("--faces", type=int, default=120000, help="måltrianglar efter decimering (0=ingen)")
    a = ap.parse_args(argv[1:])
    if not os.path.isfile(a.step):
        sys.exit(f"hittar inte {a.step}")
    stl = tessellate(a.step, a.size_min, a.size_max)
    to_glb(stl, a.glb, a.faces)
    print("klart.")


if __name__ == "__main__":
    main(sys.argv)
