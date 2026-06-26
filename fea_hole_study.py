"""
Homework #1 - Parameter Study: Effect of Hole Size (r) on Stress Concentration
================================================================================
Plane-stress 2D linear-elastic FEA of a plate with a circular hole.
Loading: top edge pulled up by a prescribed displacement (Delta), bottom clamped.

This script reuses the baseline FEA functions and adds:
  - reaction-force extraction (to get the far-field / nominal stress)
  - a loop over several hole radii r
  - computation of the Stress Concentration Factor (SCF)
  - SCF vs (2r/W) plot compared to the classic Kirsch value of 3
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless: save figures to files
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve

# ============================================================
# Fixed input parameters (baseline)
# ============================================================
W = 2.0          # plate width  (x: -W/2 ~ +W/2)
H = 1.0          # plate height (y: -H/2 ~ +H/2)
t = 0.01         # thickness (m)

E = 210e9        # Young's modulus (Pa)
nu = 0.30        # Poisson ratio

cx, cy = 0.1, 0.0   # hole center

h = 0.04         # interior point spacing
n_circle = 80    # points on hole boundary

Delta = 1e-4     # prescribed top-edge upward displacement (m)

# Hole radii to study (baseline r=0.15 included)
r_list = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]


# ============================================================
# Constitutive matrix (plane stress) and CST B-matrix
# ============================================================
def D_plane_stress(E, nu):
    coef = E / (1 - nu**2)
    return coef * np.array([
        [1.0, nu,  0.0],
        [nu,  1.0, 0.0],
        [0.0, 0.0, (1 - nu) / 2]
    ])


def cst_B_and_area(x1, y1, x2, y2, x3, y3):
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    A = 0.5 * det
    if A == 0:
        return None, 0.0
    if A < 0:
        A = -A
        x2, y2, x3, y3 = x3, y3, x2, y2
    b1, b2, b3 = y2 - y3, y3 - y1, y1 - y2
    c1, c2, c3 = x3 - x2, x1 - x3, x2 - x1
    B = (1 / (2 * A)) * np.array([
        [b1, 0,  b2, 0,  b3, 0],
        [0,  c1, 0,  c2, 0,  c3],
        [c1, b1, c2, b2, c3, b3]
    ])
    return B, A


# ============================================================
# Mesh generation
# ============================================================
def graded_hole_rings(cx, cy, r, n_circle, h):
    """Concentric rings around the hole, fine at the edge and gradually
    coarsening toward the interior spacing h.  Returns (ring_pts, r_outer)."""
    rings = []
    spacing = 2 * np.pi * r / n_circle      # boundary element size
    rr = r
    # innermost ring = hole boundary itself
    th = np.linspace(0, 2 * np.pi, n_circle, endpoint=False)
    rings.append(np.column_stack([cx + r * np.cos(th), cy + r * np.sin(th)]))
    while spacing < h and (rr - r) < 0.5:
        rr += spacing
        ntheta = max(int(2 * np.pi * rr / spacing), 12)
        th = np.linspace(0, 2 * np.pi, ntheta, endpoint=False)
        rings.append(np.column_stack([cx + rr * np.cos(th), cy + rr * np.sin(th)]))
        spacing *= 1.25                     # geometric grading
    return np.vstack(rings), rr


def generate_points_with_hole(W, H, h, cx, cy, r, n_circle):
    xmin, xmax = -W / 2, W / 2
    ymin, ymax = -H / 2, H / 2
    xs = np.arange(xmin, xmax + 0.5 * h, h)
    ys = np.arange(ymin, ymax + 0.5 * h, h)
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    pts = np.column_stack([X.ravel(), Y.ravel()])

    # graded refinement rings around the hole
    rings, r_outer = graded_hole_rings(cx, cy, r, n_circle, h)

    # drop interior grid points inside the refined annulus (avoid slivers)
    dist2 = (pts[:, 0] - cx)**2 + (pts[:, 1] - cy)**2
    pts = pts[dist2 >= (r_outer * 1.01)**2]

    xb = xs
    bottom = np.column_stack([xb, np.full_like(xb, ymin)])
    top = np.column_stack([xb, np.full_like(xb, ymax)])
    yl = ys
    left = np.column_stack([np.full_like(yl, xmin), yl])
    right = np.column_stack([np.full_like(yl, xmax), yl])

    all_pts = np.vstack([pts, bottom, top, left, right, rings])
    key = np.round(all_pts / (h * 0.05)).astype(int)   # finer dedup for rings
    _, idx = np.unique(key, axis=0, return_index=True)
    all_pts = all_pts[np.sort(idx)]
    return all_pts


def build_tri_mesh_with_hole(W, H, pts, cx, cy, r):
    tri = Delaunay(pts)
    elems = tri.simplices.copy()
    p = pts
    cent = (p[elems[:, 0]] + p[elems[:, 1]] + p[elems[:, 2]]) / 3.0
    xmin, xmax = -W / 2, W / 2
    ymin, ymax = -H / 2, H / 2
    inside_rect = (cent[:, 0] >= xmin) & (cent[:, 0] <= xmax) & \
                  (cent[:, 1] >= ymin) & (cent[:, 1] <= ymax)
    outside_hole = ((cent[:, 0] - cx)**2 + (cent[:, 1] - cy)**2) >= r**2
    elems = elems[inside_rect & outside_hole]
    return pts, elems


def find_boundary_nodes(nodes, W, H, tol=1e-9):
    xmin, xmax = -W / 2, W / 2
    ymin, ymax = -H / 2, H / 2
    bottom = np.where(np.abs(nodes[:, 1] - ymin) < tol)[0]
    top = np.where(np.abs(nodes[:, 1] - ymax) < tol)[0]
    left = np.where(np.abs(nodes[:, 0] - xmin) < tol)[0]
    right = np.where(np.abs(nodes[:, 0] - xmax) < tol)[0]
    return bottom, top, left, right


# ============================================================
# FEM solve  (now also returns reactions R = K U)
# ============================================================
def solve_plate_with_hole(nodes, elems, E, nu, t, W, H, Delta):
    Nn = nodes.shape[0]
    Ndof = 2 * Nn
    D = D_plane_stress(E, nu)
    K = lil_matrix((Ndof, Ndof), dtype=float)
    F = np.zeros(Ndof)

    for e in range(elems.shape[0]):
        n1, n2, n3 = elems[e]
        x1, y1 = nodes[n1]; x2, y2 = nodes[n2]; x3, y3 = nodes[n3]
        B, A = cst_B_and_area(x1, y1, x2, y2, x3, y3)
        if B is None or A <= 0:
            continue
        Ke = t * A * (B.T @ D @ B)
        dofs = np.array([2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*n3, 2*n3+1], dtype=int)
        for i in range(6):
            for j in range(6):
                K[dofs[i], dofs[j]] += Ke[i, j]

    bottom, top, _, _ = find_boundary_nodes(nodes, W, H, tol=1e-8)

    fixed_dofs, fixed_vals = [], []
    for n in bottom:
        fixed_dofs += [2*n, 2*n+1]
        fixed_vals += [0.0, 0.0]
    top_v_dofs = []
    for n in top:
        fixed_dofs += [2*n+1]
        fixed_vals += [Delta]
        top_v_dofs.append(2*n+1)

    fixed_dofs = np.array(fixed_dofs, dtype=int)
    fixed_vals = np.array(fixed_vals, dtype=float)
    top_v_dofs = np.array(top_v_dofs, dtype=int)

    U_prescribed = np.zeros(Ndof)
    U_prescribed[fixed_dofs] = fixed_vals
    all_dofs = np.arange(Ndof)
    free_dofs = np.setdiff1d(all_dofs, fixed_dofs)

    K_csr = csr_matrix(K)
    Kff = K_csr[free_dofs][:, free_dofs]
    Kfc = K_csr[free_dofs][:, fixed_dofs]
    rhs = F[free_dofs] - Kfc @ U_prescribed[fixed_dofs]
    Uf = spsolve(Kff, rhs)

    U = U_prescribed.copy()
    U[free_dofs] = Uf

    # Reaction forces (external applied loads are zero -> R = K U)
    R = K_csr @ U
    Fy_top = np.sum(R[top_v_dofs])   # total vertical force imposed at the top edge
    return U, Fy_top


# ============================================================
# Post-processing
# ============================================================
def compute_strain_stress(nodes, elems, U, E, nu):
    D = D_plane_stress(E, nu)
    Ne = elems.shape[0]
    strain = np.zeros((Ne, 3))
    stress = np.zeros((Ne, 3))
    vonm = np.zeros(Ne)
    cent = np.zeros((Ne, 2))
    for e in range(Ne):
        n1, n2, n3 = elems[e]
        x1, y1 = nodes[n1]; x2, y2 = nodes[n2]; x3, y3 = nodes[n3]
        B, A = cst_B_and_area(x1, y1, x2, y2, x3, y3)
        if B is None or A <= 0:
            continue
        dofs = np.array([2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*n3, 2*n3+1], dtype=int)
        eps = B @ U[dofs]
        sig = D @ eps
        strain[e] = eps
        stress[e] = sig
        sxx, syy, txy = sig
        vonm[e] = np.sqrt(sxx**2 - sxx*syy + syy**2 + 3*txy**2)
        cent[e] = [(x1+x2+x3)/3.0, (y1+y2+y3)/3.0]
    return strain, stress, vonm, cent


# ============================================================
# Run one case and compute SCF
# ============================================================
def run_case(r):
    pts = generate_points_with_hole(W, H, h, cx, cy, r, n_circle)
    nodes, elems = build_tri_mesh_with_hole(W, H, pts, cx, cy, r)
    U, Fy_top = solve_plate_with_hole(nodes, elems, E, nu, t, W, H, Delta)
    strain, stress, vonm, cent = compute_strain_stress(nodes, elems, U, E, nu)

    # Nominal stresses from the imposed (reaction) force
    sigma_gross = abs(Fy_top) / (t * W)              # over full width
    sigma_net = abs(Fy_top) / (t * (W - 2 * r))      # over net section through hole

    # Peak sigma_yy in the ring of elements around the hole edge
    dist = np.sqrt((cent[:, 0] - cx)**2 + (cent[:, 1] - cy)**2)
    ring = (dist >= r) & (dist <= r + 3 * h)
    syy_peak = np.max(stress[ring, 1])               # tensile peak along loading dir
    vonm_peak = np.max(vonm[ring])

    SCF_gross = syy_peak / sigma_gross
    SCF_net = syy_peak / sigma_net

    return {
        "r": r, "nodes": nodes, "elems": elems, "U": U,
        "stress": stress, "vonm": vonm,
        "sigma_gross": sigma_gross, "sigma_net": sigma_net,
        "syy_peak": syy_peak, "vonm_peak": vonm_peak,
        "SCF_gross": SCF_gross, "SCF_net": SCF_net,
        "n_nodes": nodes.shape[0], "n_elems": elems.shape[0],
    }


def plot_vonmises(res, fname):
    nodes, elems, vonm = res["nodes"], res["elems"], res["vonm"]
    plt.figure(figsize=(9, 4.2))
    tpc = plt.tripcolor(nodes[:, 0], nodes[:, 1], elems,
                        facecolors=vonm / 1e6, shading="flat", cmap="viridis")
    plt.gca().set_aspect("equal", "box")
    plt.title(f"von Mises stress (MPa), r = {res['r']:.2f}")
    plt.xlabel("x"); plt.ylabel("y")
    plt.colorbar(tpc, label="MPa")
    plt.tight_layout()
    plt.savefig(fname, dpi=130)
    plt.close()


# ============================================================
# Main: loop over r values
# ============================================================
if __name__ == "__main__":
    results = []
    print(f"{'r':>6} {'2r/W':>7} {'nodes':>7} {'elems':>7} "
          f"{'sig_gross[MPa]':>14} {'syy_peak[MPa]':>14} "
          f"{'SCF_gross':>10} {'SCF_net':>9}")
    print("-" * 92)
    for r in r_list:
        res = run_case(r)
        results.append(res)
        print(f"{res['r']:>6.2f} {2*res['r']/W:>7.3f} "
              f"{res['n_nodes']:>7d} {res['n_elems']:>7d} "
              f"{res['sigma_gross']/1e6:>14.3f} {res['syy_peak']/1e6:>14.3f} "
              f"{res['SCF_gross']:>10.3f} {res['SCF_net']:>9.3f}")

    # contour plots for smallest and largest holes
    plot_vonmises(results[0], "vonmises_r_min.png")
    plot_vonmises(results[-1], "vonmises_r_max.png")

    # SCF vs 2r/W
    d_over_W = np.array([2 * res["r"] / W for res in results])
    scf_g = np.array([res["SCF_gross"] for res in results])
    scf_n = np.array([res["SCF_net"] for res in results])

    plt.figure(figsize=(7.5, 5))
    plt.plot(d_over_W, scf_g, "o-", label="SCF (gross stress)")
    plt.plot(d_over_W, scf_n, "s--", label="SCF (net-section stress)")
    plt.axhline(3.0, color="r", ls=":", lw=2,
                label="Kirsch theory (infinite plate) = 3")
    for x, y in zip(d_over_W, scf_g):
        plt.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=8)
    plt.xlabel("hole diameter / plate width,  2r / W")
    plt.ylabel("Stress Concentration Factor,  SCF = $\\sigma_{yy,max}/\\sigma_{nom}$")
    plt.title("Effect of hole size on stress concentration")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("SCF_vs_holesize.png", dpi=140)
    plt.close()

    print("\nSaved figures: SCF_vs_holesize.png, vonmises_r_min.png, vonmises_r_max.png")
