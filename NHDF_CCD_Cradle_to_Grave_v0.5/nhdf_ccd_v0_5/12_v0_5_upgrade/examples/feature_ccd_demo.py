from nhdf_ccd_v05 import LinearPoint, Vec3, vertex_face_ccd, edge_edge_ccd


def lp(p0, p1=None):
    p1 = p0 if p1 is None else p1
    return LinearPoint(Vec3(*p0), Vec3(*p1))

vf = vertex_face_ccd(
    lp((0.2, 0.2, 1.0), (0.2, 0.2, -1.0)),
    lp((0,0,0)), lp((1,0,0)), lp((0,1,0)), pair_id="demo-vf"
)
ee = edge_edge_ccd(
    lp((-1,0,0)), lp((1,0,0)),
    lp((0,-1,1),(0,-1,-1)), lp((0,1,1),(0,1,-1)), pair_id="demo-ee"
)
print(vf.canonical_json())
print(ee.canonical_json())
