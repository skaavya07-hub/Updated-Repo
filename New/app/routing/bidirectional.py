import heapq


def search(graph, start, goal, edge_cost, heuristic):
    """Directed bidirectional A*; reverse expansion evaluates the corresponding forward edge."""
    if start == goal:
        return [start], 1
    f_heap, b_heap = [(0, start)], [(0, goal)]
    gf, gb = {start: 0.0}, {goal: 0.0}
    pf, pb = {}, {}
    settled_f, settled_b = set(), set()
    best, meet, evaluated = float("inf"), None, 0
    reverse = {i: [] for i in graph.nodes}
    for u, edges in graph.adj.items():
        for v, d in edges:
            reverse[v].append((u, d))
    while f_heap and b_heap:
        forward = f_heap[0][0] <= b_heap[0][0]
        heap, g, other, settled = (f_heap, gf, gb, settled_f) if forward else (b_heap, gb, gf, settled_b)
        _, u = heapq.heappop(heap)
        if u in settled:
            continue
        settled.add(u); evaluated += 1
        if u in other and g[u] + other[u] < best:
            best, meet = g[u] + other[u], u
        if g[u] + heuristic(u, goal if forward else start) >= best:
            continue
        edges = graph.adj[u] if forward else reverse[u]
        for v, distance in edges:
            c = edge_cost(u, v, distance) if forward else edge_cost(v, u, distance)
            if c == float("inf"):
                continue
            ng = g[u] + c
            if ng < g.get(v, float("inf")):
                g[v] = ng
                (pf if forward else pb)[v] = u
                heapq.heappush(heap, (ng + heuristic(v, goal if forward else start), v))
    if meet is None:
        raise ValueError("No safe water-only route could be found for the selected limits")
    left, n = [meet], meet
    while n != start:
        n = pf[n]; left.append(n)
    left.reverse(); right, n = [], meet
    while n != goal:
        n = pb[n]; right.append(n)
    return left + right, evaluated

