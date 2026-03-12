import numpy as np
from collections import defaultdict, deque


class MeshUncertaintyModel:
    """
    Buduje lokalny model niepewności geometrycznej dla mesha.

    Wejście:
        mesh.m_vertices : (N,3)
        mesh.m_faces    : (F,3)
        mesh.m_vnormals : (N,3) [opcjonalne]

    Wynik:
        centers      : (N,3)
        normals      : (N,3)
        covariances  : (N,3,3)
        confidence   : (N,)
        metrics      : dict z dodatkowymi polami
    """

    def __init__(
        self,
        mesh,
        min_neighbors=6,
        use_existing_normals=True,
        tangent_scale=0.35,
        normal_scale=1.0,
        boundary_penalty_strength=0.35,
        eps=1e-12,
    ):
        self.mesh = mesh
        self.V = np.asarray(mesh.m_vertices, dtype=np.float64)
        self.F = np.asarray(mesh.m_faces, dtype=np.int64)

        self.N = self.V.shape[0]
        self.M = self.F.shape[0]

        self.min_neighbors = min_neighbors
        self.use_existing_normals = use_existing_normals
        self.tangent_scale = tangent_scale
        self.normal_scale = normal_scale
        self.boundary_penalty_strength = boundary_penalty_strength
        self.eps = eps

        if self.V.ndim != 2 or self.V.shape[1] != 3:
            raise ValueError("mesh.m_vertices musi mieć kształt (N,3)")
        if self.F.ndim != 2 or self.F.shape[1] != 3:
            raise ValueError("mesh.m_faces musi mieć kształt (F,3)")

        self.neighbors = None
        self.vertex_faces = None
        self.boundary_vertices = None

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze(self):
        self._build_topology()

        face_metrics = self._compute_face_metrics()

        normals, pca_basis, pca_eigvals = self._compute_vertex_normals_and_pca()
        spacing = self._compute_vertex_spacing()
        planarity_residual = self._compute_planarity_residual(normals)
        curvature = self._compute_vertex_curvature_from_pca(pca_eigvals)
        normal_variation = self._compute_vertex_normal_variation(normals)
        valence = self._compute_vertex_valence()
        boundary_distance = self._compute_boundary_distance()

        covariances, sigma_t, sigma_n = self._build_covariances(
            normals=normals,
            pca_basis=pca_basis,
            spacing=spacing,
            planarity_residual=planarity_residual,
            curvature=curvature,
            normal_variation=normal_variation,
            boundary_distance=boundary_distance,
        )

        confidence = self._build_confidence(
            spacing=spacing,
            planarity_residual=planarity_residual,
            curvature=curvature,
            normal_variation=normal_variation,
            boundary_distance=boundary_distance,
        )

        return {
            "centers": self.V.copy(),
            "normals": normals,
            "covariances": covariances,
            "confidence": confidence,
            "metrics": {
                "vertex_spacing": spacing,
                "vertex_planarity_residual": planarity_residual,
                "vertex_curvature": curvature,
                "vertex_normal_variation": normal_variation,
                "vertex_valence": valence,
                "vertex_boundary_distance": boundary_distance,
                "vertex_sigma_t": sigma_t,
                "vertex_sigma_n": sigma_n,
                "vertex_pca_eigenvalues": pca_eigvals,
                "face_area": face_metrics["face_area"],
                "face_max_edge": face_metrics["face_max_edge"],
                "face_aspect_ratio": face_metrics["face_aspect_ratio"],
                "boundary_vertices_mask": self.boundary_vertices.copy(),
            },
        }

    # ============================================================
    # TOPOLOGY
    # ============================================================

    def _build_topology(self):
        neighbors = defaultdict(set)
        vertex_faces = defaultdict(list)
        edge_count = defaultdict(int)

        for fi, (a, b, c) in enumerate(self.F):
            neighbors[a].update((b, c))
            neighbors[b].update((a, c))
            neighbors[c].update((a, b))

            vertex_faces[a].append(fi)
            vertex_faces[b].append(fi)
            vertex_faces[c].append(fi)

            for e in ((a, b), (b, c), (c, a)):
                edge = tuple(sorted(e))
                edge_count[edge] += 1

        self.neighbors = {i: np.array(sorted(v), dtype=np.int64) for i, v in neighbors.items()}
        self.vertex_faces = {i: np.array(v, dtype=np.int64) for i, v in vertex_faces.items()}

        boundary_vertices = np.zeros(self.N, dtype=bool)
        for (a, b), cnt in edge_count.items():
            if cnt == 1:
                boundary_vertices[a] = True
                boundary_vertices[b] = True

        self.boundary_vertices = boundary_vertices

    # ============================================================
    # FACE METRICS
    # ============================================================

    def _compute_face_metrics(self):
        v0 = self.V[self.F[:, 0]]
        v1 = self.V[self.F[:, 1]]
        v2 = self.V[self.F[:, 2]]

        e01 = v1 - v0
        e02 = v2 - v0
        e12 = v2 - v1

        cross = np.cross(e01, e02)
        face_area = 0.5 * np.linalg.norm(cross, axis=1)

        l01 = np.linalg.norm(e01, axis=1)
        l02 = np.linalg.norm(e02, axis=1)
        l12 = np.linalg.norm(e12, axis=1)

        face_max_edge = np.maximum.reduce([l01, l02, l12])
        face_min_edge = np.minimum.reduce([l01, l02, l12])
        face_aspect_ratio = face_max_edge / np.maximum(face_min_edge, self.eps)

        return {
            "face_area": face_area,
            "face_max_edge": face_max_edge,
            "face_aspect_ratio": face_aspect_ratio,
        }

    # ============================================================
    # NORMALS + PCA
    # ============================================================

    def _compute_vertex_normals_and_pca(self):
        normals = np.zeros((self.N, 3), dtype=np.float64)
        pca_basis = np.zeros((self.N, 3, 3), dtype=np.float64)
        pca_eigvals = np.zeros((self.N, 3), dtype=np.float64)

        use_existing = (
            self.use_existing_normals
            and hasattr(self.mesh, "m_vnormals")
            and len(self.mesh.m_vnormals) == self.N
        )

        existing_normals = None
        if use_existing:
            existing_normals = np.asarray(self.mesh.m_vnormals, dtype=np.float64)

        for i in range(self.N):
            neigh = self.neighbors.get(i, np.empty((0,), dtype=np.int64))

            if len(neigh) < 3:
                # fallback
                n = np.array([0.0, 0.0, 1.0], dtype=np.float64)
                pca_basis[i] = np.eye(3, dtype=np.float64)
                pca_eigvals[i] = 0.0
                normals[i] = n
                continue

            pts = self.V[neigh]
            centroid = pts.mean(axis=0)
            X = pts - centroid

            C = (X.T @ X) / max(len(pts), 1)
            eigvals, eigvecs = np.linalg.eigh(C)  # rosnąco
            order = np.argsort(eigvals)[::-1]     # malejąco
            eigvals = eigvals[order]
            eigvecs = eigvecs[:, order]

            # eigvecs[:,2] = kierunek najmniejszej wariancji = normalna
            n = eigvecs[:, 2]
            n_norm = np.linalg.norm(n)
            if n_norm > self.eps:
                n = n / n_norm
            else:
                n = np.array([0.0, 0.0, 1.0], dtype=np.float64)

            if use_existing:
                ref = existing_normals[i]
                ref_norm = np.linalg.norm(ref)
                if ref_norm > self.eps:
                    ref = ref / ref_norm
                    if np.dot(n, ref) < 0.0:
                        n = -n
                        eigvecs[:, 2] = -eigvecs[:, 2]

            pca_basis[i] = eigvecs
            pca_eigvals[i] = eigvals
            normals[i] = n

        return normals, pca_basis, pca_eigvals

    # ============================================================
    # VERTEX METRICS
    # ============================================================

    def _compute_vertex_spacing(self):
        spacing = np.zeros(self.N, dtype=np.float64)

        for i in range(self.N):
            neigh = self.neighbors.get(i, np.empty((0,), dtype=np.int64))
            if len(neigh) == 0:
                continue
            d = np.linalg.norm(self.V[neigh] - self.V[i], axis=1)
            spacing[i] = d.mean()

        return spacing

    def _compute_planarity_residual(self, normals):
        residual = np.zeros(self.N, dtype=np.float64)

        for i in range(self.N):
            neigh = self.neighbors.get(i, np.empty((0,), dtype=np.int64))
            if len(neigh) < 3:
                continue

            pts = self.V[neigh]
            centroid = pts.mean(axis=0)
            X = pts - centroid
            n = normals[i]

            d = np.abs(X @ n)
            residual[i] = d.mean()

        return residual

    def _compute_vertex_curvature_from_pca(self, pca_eigvals):
        curvature = np.zeros(self.N, dtype=np.float64)
        s = pca_eigvals.sum(axis=1)
        mask = s > self.eps
        # pca_eigvals[:,2] po reorder to najmniejsza wartość własna
        curvature[mask] = pca_eigvals[mask, 2] / s[mask]
        return curvature

    def _compute_vertex_normal_variation(self, normals):
        var = np.zeros(self.N, dtype=np.float64)

        for i in range(self.N):
            neigh = self.neighbors.get(i, np.empty((0,), dtype=np.int64))
            if len(neigh) == 0:
                continue

            n0 = normals[i]
            nn = normals[neigh]
            dots = np.clip(nn @ n0, -1.0, 1.0)
            angles = np.arccos(dots)
            var[i] = angles.mean()

        return var

    def _compute_vertex_valence(self):
        valence = np.zeros(self.N, dtype=np.int32)
        for i in range(self.N):
            valence[i] = len(self.neighbors.get(i, ()))
        return valence

    def _compute_boundary_distance(self):
        dist = np.full(self.N, np.inf, dtype=np.float64)

        q = deque()
        for i in np.where(self.boundary_vertices)[0]:
            dist[i] = 0.0
            q.append(i)

        while q:
            v = q.popleft()
            for n in self.neighbors.get(v, np.empty((0,), dtype=np.int64)):
                if np.isinf(dist[n]):
                    dist[n] = dist[v] + 1.0
                    q.append(n)

        # dla zamkniętej siatki bez boundary
        if np.all(np.isinf(dist)):
            dist[:] = np.max([len(self.neighbors.get(i, ())) for i in range(self.N)] + [1])

        return dist

    # ============================================================
    # COVARIANCES
    # ============================================================

    def _build_covariances(
        self,
        normals,
        pca_basis,
        spacing,
        planarity_residual,
        curvature,
        normal_variation,
        boundary_distance,
    ):
        covariances = np.zeros((self.N, 3, 3), dtype=np.float64)

        # normalizacja kilku metryk do skali względnej
        spacing_n = self._robust_normalize(spacing)
        residual_n = self._robust_normalize(planarity_residual)
        curvature_n = self._robust_normalize(curvature)
        nvar_n = self._robust_normalize(normal_variation)

        # boundary penalty: przy boundary trochę zwiększamy niepewność normalną
        bd = boundary_distance.copy()
        bd_finite = bd[np.isfinite(bd)]
        if len(bd_finite) > 0:
            bd_scale = np.percentile(bd_finite, 90)
            bd_scale = max(bd_scale, 1.0)
            boundary_factor = 1.0 + self.boundary_penalty_strength * np.exp(-bd / bd_scale)
        else:
            boundary_factor = np.ones_like(bd)

        sigma_t = self.tangent_scale * np.maximum(spacing, self.eps)

        sigma_n = self.normal_scale * (
            0.55 * np.maximum(planarity_residual, self.eps)
            + 0.25 * spacing * curvature_n
            + 0.20 * spacing * nvar_n
        )

        sigma_n = np.maximum(sigma_n, 0.15 * sigma_t)
        sigma_n = sigma_n * boundary_factor

        for i in range(self.N):
            n = normals[i]
            n_norm = np.linalg.norm(n)
            if n_norm <= self.eps:
                n = np.array([0.0, 0.0, 1.0], dtype=np.float64)
            else:
                n = n / n_norm

            # baza styczna
            e1 = pca_basis[i, :, 0]
            e2 = pca_basis[i, :, 1]

            if np.linalg.norm(e1) <= self.eps or np.linalg.norm(e2) <= self.eps:
                e1, e2 = self._orthonormal_basis_from_normal(n)
            else:
                e1 = e1 / max(np.linalg.norm(e1), self.eps)
                e2 = e2 - np.dot(e2, e1) * e1
                e2 = e2 / max(np.linalg.norm(e2), self.eps)

            st2 = sigma_t[i] ** 2
            sn2 = sigma_n[i] ** 2

            cov = st2 * (np.outer(e1, e1) + np.outer(e2, e2)) + sn2 * np.outer(n, n)
            covariances[i] = cov

        return covariances, sigma_t, sigma_n

    # ============================================================
    # CONFIDENCE
    # ============================================================

    def _build_confidence(
        self,
        spacing,
        planarity_residual,
        curvature,
        normal_variation,
        boundary_distance,
    ):
        spacing_n = self._robust_normalize(spacing)
        residual_n = self._robust_normalize(planarity_residual)
        curvature_n = self._robust_normalize(curvature)
        nvar_n = self._robust_normalize(normal_variation)

        bd = boundary_distance.copy()
        bd_finite = bd[np.isfinite(bd)]
        if len(bd_finite) > 0:
            bd_scale = np.percentile(bd_finite, 90)
            bd_scale = max(bd_scale, 1.0)
            boundary_risk = np.exp(-bd / bd_scale)
        else:
            boundary_risk = np.zeros_like(bd)

        risk = (
            0.30 * residual_n
            + 0.25 * nvar_n
            + 0.20 * spacing_n
            + 0.10 * curvature_n
            + 0.15 * boundary_risk
        )

        confidence = 1.0 / (1.0 + risk)
        confidence = np.clip(confidence, 0.0, 1.0)
        return confidence

    # ============================================================
    # HELPERS
    # ============================================================

    def _robust_normalize(self, x):
        x = np.asarray(x, dtype=np.float64)
        if len(x) == 0:
            return x.copy()

        q50 = np.percentile(x, 50)
        q95 = np.percentile(x, 95)

        scale = max(q95 - q50, self.eps)
        y = (x - q50) / scale
        y = np.clip(y, 0.0, None)
        return y

    def _orthonormal_basis_from_normal(self, n):
        n = n / max(np.linalg.norm(n), self.eps)

        if abs(n[2]) < 0.9:
            t = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            t = np.array([1.0, 0.0, 0.0], dtype=np.float64)

        e1 = np.cross(n, t)
        e1 = e1 / max(np.linalg.norm(e1), self.eps)
        e2 = np.cross(n, e1)
        e2 = e2 / max(np.linalg.norm(e2), self.eps)
        return e1, e2
    


def confidence_to_rgba(confidence, cmap="turbo"):
    """
    Zamienia confidence (0..1) na kolory RGBA (uint8).
    """

    c = np.clip(confidence, 0.0, 1.0)

    if cmap == "turbo":
        # szybka implementacja colormap turbo (przybliżona)
        r = np.clip(1.5 - np.abs(4*c - 3), 0, 1)
        g = np.clip(1.5 - np.abs(4*c - 2), 0, 1)
        b = np.clip(1.5 - np.abs(4*c - 1), 0, 1)

    elif cmap == "heat":
        r = c
        g = c**0.5
        b = 0.3*(1-c)

    elif cmap == "gray":
        r = g = b = c

    else:
        raise ValueError("Unknown colormap")

    rgba = np.stack([r, g, b, np.ones_like(r)], axis=1)
    return (rgba * 255).astype(np.uint8)	


def colorize_mesh_by_confidence(mesh, confidence, cmap="turbo"):
    """
    Ustawia kolory vertexów mesha na podstawie confidence.
    """

    colors = confidence_to_rgba(confidence, cmap)

    mesh.m_vcolors = colors
    


def uncertainty_colormap(u):
    """
    u – wartości 0..1 (0 = najlepsza jakość, 1 = największa niepewność)

    zwraca RGBA uint8
    """

    u = np.clip(u, 0.0, 1.0)

    # punkty kontrolne (R,G,B)
    cmap = np.array([
        [0,   0, 130],   # dark blue
        [0, 150, 255],   # cyan
        [0, 200,   0],   # green
        [255, 255,  0],  # yellow
        [255, 140,  0],  # orange
        [255,   0,  0],  # red
    ], dtype=float)

    x = np.linspace(0,1,len(cmap))

    r = np.interp(u, x, cmap[:,0])
    g = np.interp(u, x, cmap[:,1])
    b = np.interp(u, x, cmap[:,2])

    rgba = np.stack([r,g,b,np.full_like(r,255)],axis=1)

    return rgba.astype(np.uint8)
	