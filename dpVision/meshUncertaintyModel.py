import numpy as np
from collections import defaultdict, deque
from .colormaps import make_colormap


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
        """
        Parameters
        ----------
        mesh                      : obiekt z atrybutami m_vertices (N,3), m_faces (F,3)
                                    i opcjonalnie m_vnormals (N,3).
        min_neighbors             : minimalna liczba sąsiadów do wyznaczenia PCA (default 6).
        use_existing_normals      : czy orientować normalne PCA wg m_vnormals (default True).
        tangent_scale             : mnożnik σ_t kowariancji stycznej (default 0.35).
        normal_scale              : mnożnik σ_n kowariancji normalnej (default 1.0).
        boundary_penalty_strength : siła kary przy krawędziach brzegowych (default 0.35).
        eps                       : wartość zabezpieczająca przed dzieleniem przez zero.
        """
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

    def compute_confidence(self):
        """
        Skrót: zwraca jedynie tablicę confidence (N,) [0..1].
        Wartość 1.0 = doskonała jakość geometryczna, 0.0 = duża niepewność.
        Uruchamia pełny potok (łącznie z budową topologii).
        """
        return self.analyze()["confidence"]

    def compute_face_quality(self):
        """
        Zwraca metryki jakości ścian bez budowania macierzy kowariancji.
        Buduje topologię jeśli nie była jeszcze zbudowana.

        Returns
        -------
        dict z kluczami:
            face_area          : (M,) – pole powierzchni trójkąta
            face_max_edge      : (M,) – długość najdłuższej krawędzi
            face_min_edge      : (M,) – długość najkrótszej krawędzi
            face_aspect_ratio  : (M,) – max_edge / min_edge (1.0 = równoboczny)
            face_min_dihedral  : (M,) – minimalny kąt dwuścienny z sąsiadami [rad]
            face_mean_dihedral : (M,) – średni kąt dwuścienny z sąsiadami [rad]
        """
        if self.neighbors is None:
            self._build_topology()
        fm = self._compute_face_metrics()
        min_dih, mean_dih = self._compute_face_dihedral_stats()
        return {**fm, "face_min_dihedral": min_dih, "face_mean_dihedral": mean_dih}

    def compute_vertex_quality(self):
        """
        Zwraca metryki jakości wierzchołków bez budowania macierzy kowariancji.
        Buduje topologię jeśli nie była jeszcze zbudowana.

        Returns
        -------
        dict z kluczami:
            vertex_spacing            : (N,) – średnia odległość do sąsiadów
            vertex_planarity_residual : (N,) – odchylenie od płaszczyzny PCA
            vertex_curvature          : (N,) – krzywizna PCA (λ_min / Σλ)
            vertex_normal_variation   : (N,) – średni kąt [rad] między normalnymi sąsiadów
            vertex_valence            : (N,) – liczba sąsiednich wierzchołków
            vertex_boundary_distance  : (N,) – topologiczna odległość od krawędzi brzegowej
        """
        if self.neighbors is None:
            self._build_topology()
        normals, _, pca_eigvals = self._compute_vertex_normals_and_pca()
        return {
            "vertex_spacing":            self._compute_vertex_spacing(),
            "vertex_planarity_residual": self._compute_planarity_residual(normals),
            "vertex_curvature":          self._compute_vertex_curvature_from_pca(pca_eigvals),
            "vertex_normal_variation":   self._compute_vertex_normal_variation(normals),
            "vertex_valence":            self._compute_vertex_valence(),
            "vertex_boundary_distance":  self._compute_boundary_distance(),
        }

    def analyze(self):
        """
        Uruchamia pełną analizę: buduje topologię, oblicza metryki wierzchołków
        i ścian, macierze kowariancji oraz confidence.

        Returns
        -------
        dict z kluczami:
            centers     : (N,3) – współrzędne wierzchołków
            normals     : (N,3) – normalne wierzchołków (z PCA, wyrównane do m_vnormals)
            covariances : (N,3,3) – macierze kowariancji niepewności geometrycznej
            confidence  : (N,) – jakość geometryczna [0..1], 1.0 = najlepsza
            metrics     : dict ze wszystkimi polami face_* i vertex_*
        """
        self._build_topology()

        face_metrics = self._compute_face_metrics()
        face_min_dihedral, face_mean_dihedral = self._compute_face_dihedral_stats()

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
                "face_min_edge": face_metrics["face_min_edge"],
                "face_aspect_ratio": face_metrics["face_aspect_ratio"],
                "face_min_dihedral": face_min_dihedral,
                "face_mean_dihedral": face_mean_dihedral,
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
            "face_min_edge": face_min_edge,
            "face_aspect_ratio": face_aspect_ratio,
        }

    def _compute_face_dihedral_stats(self):
        """
        Per-face: minimalny i średni kąt dwuścienny z sąsiadującymi trójkątami [rad].

        Kąt 0 = ściany płaskie (równoległe normalne), π = ściany odwrócone.
        Krawędzie brzegowe (tylko jedna ściana) nie wchodzą do agregacji.

        Returns
        -------
        face_min_dihedral  : (M,) – min kąt na każdej ścianie
        face_mean_dihedral : (M,) – mean kąt na każdej ścianie
        """
        # normalne ścian (M, 3)
        v0 = self.V[self.F[:, 0]]
        v1 = self.V[self.F[:, 1]]
        v2 = self.V[self.F[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(cross, axis=1, keepdims=True)
        face_normals = cross / np.maximum(norms, self.eps)

        # krawędzie jako (3M, 3): [min_v, max_v, face_idx]
        fi = np.arange(self.M, dtype=np.int64)
        e0 = np.stack([np.minimum(self.F[:, 0], self.F[:, 1]),
                       np.maximum(self.F[:, 0], self.F[:, 1]), fi], axis=1)
        e1 = np.stack([np.minimum(self.F[:, 1], self.F[:, 2]),
                       np.maximum(self.F[:, 1], self.F[:, 2]), fi], axis=1)
        e2 = np.stack([np.minimum(self.F[:, 2], self.F[:, 0]),
                       np.maximum(self.F[:, 2], self.F[:, 0]), fi], axis=1)
        all_edges = np.concatenate([e0, e1, e2], axis=0)  # (3M, 3)

        # stable sort po krawędzi → sąsiadujące wiersze = ta sama krawędź
        order = np.lexsort((all_edges[:, 1], all_edges[:, 0]))
        all_edges = all_edges[order]

        same = np.all(all_edges[:-1, :2] == all_edges[1:, :2], axis=1)
        pair_idx = np.where(same)[0]

        fi_a = all_edges[pair_idx,     2]
        fi_b = all_edges[pair_idx + 1, 2]

        dots   = np.clip(np.sum(face_normals[fi_a] * face_normals[fi_b], axis=1), -1.0, 1.0)
        angles = np.arccos(dots)

        face_min_dihedral  = np.full(self.M, np.pi, dtype=np.float64)
        face_mean_dihedral = np.zeros(self.M, dtype=np.float64)
        counts = np.zeros(self.M, dtype=np.int64)

        np.minimum.at(face_min_dihedral, fi_a, angles)
        np.minimum.at(face_min_dihedral, fi_b, angles)
        np.add.at(face_mean_dihedral, fi_a, angles)
        np.add.at(face_mean_dihedral, fi_b, angles)
        np.add.at(counts, fi_a, 1)
        np.add.at(counts, fi_b, 1)

        mask = counts > 0
        face_mean_dihedral[mask] /= counts[mask]
        face_min_dihedral[~mask]  = 0.0  # ściana bez żadnego sąsiada

        return face_min_dihedral, face_mean_dihedral

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
        # Wszystkie skierowane krawędzie z trójkątów (3M, 2)
        edges = np.concatenate([
            self.F[:, [0, 1]],
            self.F[:, [1, 2]],
            self.F[:, [2, 0]],
        ], axis=0)
        a, b = edges[:, 0], edges[:, 1]
        lengths = np.linalg.norm(self.V[a] - self.V[b], axis=1)

        spacing = np.zeros(self.N, dtype=np.float64)
        counts  = np.zeros(self.N, dtype=np.int64)
        np.add.at(spacing, a, lengths)
        np.add.at(counts,  a, 1)
        mask = counts > 0
        spacing[mask] /= counts[mask]
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
        # Wszystkie skierowane krawędzie z trójkątów (3M, 2)
        edges = np.concatenate([
            self.F[:, [0, 1]],
            self.F[:, [1, 2]],
            self.F[:, [2, 0]],
        ], axis=0)
        a, b = edges[:, 0], edges[:, 1]
        dots   = np.clip(np.sum(normals[a] * normals[b], axis=1), -1.0, 1.0)
        angles = np.arccos(dots)

        var    = np.zeros(self.N, dtype=np.float64)
        counts = np.zeros(self.N, dtype=np.int64)
        np.add.at(var,    a, angles)
        np.add.at(counts, a, 1)
        mask = counts > 0
        var[mask] /= counts[mask]
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

        # --- znormalizowane normalne -----------------------------------------
        n = normals.copy()
        n_norms = np.linalg.norm(n, axis=1)
        bad_n = n_norms <= self.eps
        n /= np.maximum(n_norms, self.eps)[:, np.newaxis]
        n[bad_n] = [0.0, 0.0, 1.0]

        # --- baza styczna z pca_basis ----------------------------------------
        e1 = pca_basis[:, :, 0].copy()
        e2 = pca_basis[:, :, 1].copy()

        e1_norms = np.linalg.norm(e1, axis=1)
        need_fallback = e1_norms <= self.eps

        e1 /= np.maximum(e1_norms, self.eps)[:, np.newaxis]
        # Gram-Schmidt
        e2 -= np.sum(e2 * e1, axis=1, keepdims=True) * e1
        e2 /= np.maximum(np.linalg.norm(e2, axis=1), self.eps)[:, np.newaxis]

        # fallback dla zdegenerowanych wierzchołków
        if np.any(need_fallback):
            for i in np.where(need_fallback)[0]:
                e1[i], e2[i] = self._orthonormal_basis_from_normal(n[i])

        # --- kowariancje przez einsum (bez pętli Pythona) ---------------------
        st2 = sigma_t ** 2
        sn2 = sigma_n ** 2
        covariances = (
            np.einsum('i,ij,ik->ijk', st2, e1, e1)
            + np.einsum('i,ij,ik->ijk', st2, e2, e2)
            + np.einsum('i,ij,ik->ijk', sn2, n,  n)
        )

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
    


def confidence_to_rgba(confidence, cmap="skala"):
    """
    Zamienia confidence (0..1) na kolory RGBA (uint8).
    Korzysta z make_colormap; domyślna paleta: 'skala'.
    Dostępne: 'skala', 'jet', 'rainbow', 'hot', 'cool', 'gray', 'terrain'.
    """
    c = np.clip(confidence, 0.0, 1.0)
    lut = make_colormap(cmap, n=256)                          # (256, 3) float32
    idx = np.clip(np.round(c * 255).astype(np.int32), 0, 255)
    rgb = lut[idx]                                            # (N, 3) float32
    alpha = np.ones((len(c), 1), dtype=np.float32)
    rgba = np.concatenate([rgb, alpha], axis=1)
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
	