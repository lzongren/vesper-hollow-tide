"""Refine the fitted portrait while preserving the indices of eyelid landmarks."""

from collections import defaultdict


def refine(points, faces):
    def mean(rows):
        return tuple(sum(axis) / len(rows) for axis in zip(*rows))

    centres = [mean([points[i] for i in face]) for face in faces]
    edge_faces = defaultdict(list)
    vertex_faces = defaultdict(list)
    vertex_edges = defaultdict(list)
    for f, face in enumerate(faces):
        for i, j in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((i, j)))
            if not edge_faces[edge]:
                vertex_edges[i].append(j)
                vertex_edges[j].append(i)
            edge_faces[edge].append(f)
            vertex_faces[i].append(f)

    result = list(points)
    for i, adjacent in vertex_faces.items():
        neighbours = vertex_edges[i]
        boundary = [
            j for j in neighbours if len(edge_faces[tuple(sorted((i, j)))]) == 1
        ]
        if len(boundary) == 2:
            result[i] = tuple(
                (6 * a + b + c) / 8
                for a, b, c in zip(points[i], *(points[j] for j in boundary))
            )
        elif not boundary and len(neighbours) == len(adjacent):
            n = len(adjacent)
            # Catmull-Clark vertex rule with the edge midpoints expanded.
            face_mean = mean([centres[f] for f in adjacent])
            near_mean = mean([points[j] for j in neighbours])
            result[i] = tuple(
                (f + r + (n - 2) * v) / n
                for f, r, v in zip(face_mean, near_mean, points[i])
            )

    edges = {}
    for (i, j), adjacent in edge_faces.items():
        edges[i, j] = len(result)
        rows = [points[i], points[j]]
        if len(adjacent) == 2:
            rows.extend(centres[f] for f in adjacent)
        result.append(mean(rows))
    first = len(result)
    result.extend(centres)
    quads = []
    for f, face in enumerate(faces):
        for k, i in enumerate(face):
            prev, nxt = face[k - 1], face[(k + 1) % len(face)]
            quads.append(
                [
                    i,
                    edges[tuple(sorted((i, nxt)))],
                    first + f,
                    edges[tuple(sorted((i, prev)))],
                ]
            )
    return result, quads
