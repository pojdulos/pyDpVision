import numpy as np
from collections import defaultdict

class MeshQualityAnalyzer:

    def __init__(self, mesh, k=20):
        """
        mesh  – Twoja klasa Mesh
        k     – liczba sąsiadów do analizy lokalnej
        """
        self.mesh = mesh
        self.V = mesh.m_vertices
        self.F = mesh.m_faces
        self.k = k

        self.N = len(self.V)
        self.M = len(self.F)

        self._build_adjacency()


    # -----------------------------------------------------------
    # ADJACENCY
    # -----------------------------------------------------------

    def _build_adjacency(self):

        neighbors = defaultdict(set)

        for a, b, c in self.F:
            neighbors[a].update([b, c])
            neighbors[b].update([a, c])
            neighbors[c].update([a, b])

        self.neighbors = {k: list(v) for k, v in neighbors.items()}


    # -----------------------------------------------------------
    # FACE GEOMETRY
    # -----------------------------------------------------------

    def compute_face_metrics(self):

        v0 = self.V[self.F[:,0]]
        v1 = self.V[self.F[:,1]]
        v2 = self.V[self.F[:,2]]

        e01 = v1 - v0
        e02 = v2 - v0
        e12 = v2 - v1

        # area
        cross = np.cross(e01, e02)
        area = 0.5 * np.linalg.norm(cross, axis=1)

        # edge lengths
        l01 = np.linalg.norm(e01, axis=1)
        l02 = np.linalg.norm(e02, axis=1)
        l12 = np.linalg.norm(e12, axis=1)

        max_edge = np.maximum.reduce([l01, l02, l12])
        min_edge = np.minimum.reduce([l01, l02, l12])

        aspect_ratio = max_edge / np.maximum(min_edge, 1e-12)

        return {
            "face_area": area,
            "face_max_edge": max_edge,
            "face_aspect_ratio": aspect_ratio
        }


    # -----------------------------------------------------------
    # VERTEX SPACING
    # -----------------------------------------------------------

    def compute_vertex_spacing(self):

        spacing = np.zeros(self.N)

        for i in range(self.N):

            neigh = self.neighbors.get(i, [])

            if len(neigh) == 0:
                continue

            d = np.linalg.norm(self.V[neigh] - self.V[i], axis=1)

            spacing[i] = d.mean()

        return spacing


    # -----------------------------------------------------------
    # PCA CURVATURE
    # -----------------------------------------------------------

    def compute_vertex_curvature(self):

        curvature = np.zeros(self.N)

        for i in range(self.N):

            neigh = self.neighbors.get(i, [])

            if len(neigh) < 3:
                continue

            pts = self.V[neigh]

            C = np.cov(pts.T)

            eigvals = np.linalg.eigvalsh(C)

            eigvals = np.sort(eigvals)[::-1]

            s = eigvals.sum()

            if s > 0:
                curvature[i] = eigvals[-1] / s

        return curvature


    # -----------------------------------------------------------
    # NORMAL VARIATION
    # -----------------------------------------------------------

    def compute_normal_variation(self):

        if len(self.mesh.m_vnormals) != self.N:
            raise ValueError("Mesh has no vertex normals")

        normals = self.mesh.m_vnormals

        var = np.zeros(self.N)

        for i in range(self.N):

            neigh = self.neighbors.get(i, [])

            if len(neigh) == 0:
                continue

            n0 = normals[i]
            nn = normals[neigh]

            dots = np.clip(nn @ n0, -1, 1)

            angles = np.arccos(dots)

            var[i] = angles.mean()

        return var


    # -----------------------------------------------------------
    # PLANE RESIDUAL
    # -----------------------------------------------------------

    def compute_planarity_residual(self):

        residual = np.zeros(self.N)

        for i in range(self.N):

            neigh = self.neighbors.get(i, [])

            if len(neigh) < 3:
                continue

            pts = self.V[neigh]

            centroid = pts.mean(axis=0)

            X = pts - centroid

            U, S, Vt = np.linalg.svd(X)

            normal = Vt[-1]

            d = np.abs(X @ normal)

            residual[i] = d.mean()

        return residual


    # -----------------------------------------------------------
    # VALENCE
    # -----------------------------------------------------------

    def compute_valence(self):

        valence = np.zeros(self.N)

        for i in range(self.N):
            valence[i] = len(self.neighbors.get(i, []))

        return valence


    # -----------------------------------------------------------
    # BOUNDARY DISTANCE
    # -----------------------------------------------------------

    def compute_boundary_distance(self):

        edge_count = defaultdict(int)

        for a,b,c in self.F:

            edges = [(a,b),(b,c),(c,a)]

            for e in edges:
                edge = tuple(sorted(e))
                edge_count[edge] += 1

        boundary_vertices = set()

        for (a,b), c in edge_count.items():
            if c == 1:
                boundary_vertices.add(a)
                boundary_vertices.add(b)

        dist = np.full(self.N, np.inf)

        frontier = list(boundary_vertices)

        for v in frontier:
            dist[v] = 0

        i = 1

        while frontier:

            new_frontier = []

            for v in frontier:

                for n in self.neighbors.get(v, []):

                    if dist[n] == np.inf:
                        dist[n] = i
                        new_frontier.append(n)

            frontier = new_frontier
            i += 1

        return dist


    # -----------------------------------------------------------
    # GLOBAL ANALYSIS
    # -----------------------------------------------------------

    def analyze(self):

        face = self.compute_face_metrics()

        vertex_spacing = self.compute_vertex_spacing()
        curvature = self.compute_vertex_curvature()
        normal_var = None

        if len(self.mesh.m_vnormals) == self.N:
            normal_var = self.compute_normal_variation()

        residual = self.compute_planarity_residual()
        valence = self.compute_valence()
        boundary = self.compute_boundary_distance()

        return {
            **face,
            "vertex_spacing": vertex_spacing,
            "vertex_curvature": curvature,
            "vertex_planarity_residual": residual,
            "vertex_valence": valence,
            "vertex_boundary_distance": boundary,
            "vertex_normal_variation": normal_var
        }
    

	