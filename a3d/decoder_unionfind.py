# FILE: a3d/decoder_unionfind.py
from __future__ import annotations

from collections import defaultdict, deque
from typing import List, Set

from .accel import maybe_jit
from .decoder_greedy import DecodeResult
from .graph import DecodingGraph, Edge
from .stats import effective_cost_from_edge


class _DSU:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.sz = [1]*n
        self.parity = [0]*n   # defects mod 2 in the component
        self.has_boundary = [False]*n

    def find(self, x:int)->int:
        while self.p[x]!=x:
            self.p[x]=self.p[self.p[x]]
            x=self.p[x]
        return x

    def unite(self,a:int,b:int):
        ra, rb = self.find(a), self.find(b)
        if ra==rb:
            return ra
        if self.sz[ra]<self.sz[rb]:
            ra,rb = rb,ra
        self.p[rb]=ra
        self.sz[ra]+=self.sz[rb]
        self.parity[ra]=(self.parity[ra]+self.parity[rb])%2
        self.has_boundary[ra]= self.has_boundary[ra] or self.has_boundary[rb]
        return ra


@maybe_jit
def _useful_pair(parity_ru: int, parity_rv: int, has_bnd_ru: int, has_bnd_rv: int) -> int:
    # returns 1 if edge is useful to connect components (pair odd or attach odd to boundary)
    if parity_ru==1 and parity_rv==1:
        return 1
    if (has_bnd_ru==1 or has_bnd_rv==1) and ((parity_ru==1) or (parity_rv==1)):
        return 1
    return 0
class UnionFindErasuresDecoder:
    """Union-Find style decoder with erasure-aware pre-peeling and edge ordering.

    Algorithm:
      1. **Peel erasures:** group nodes connected by time-like edges with high erasure probability
         and greedily connect odd defects along those chains.
      2. **Union-Find growth:** add remaining edges in ascending effective cost until all
         defects are neutralized (paired or absorbed by a boundary).
    """

    def _is_boundary(self, graph: DecodingGraph, nid:int)->bool:
        role = graph.node_meta.get(nid, ('',None,0,''))[3]
        return role.startswith('boundary')

    def _peel_erasures(self, graph: DecodingGraph, defects: Set[int], perase_threshold: float = 0.5) -> List[Edge]:
        """Connect defects along time-like erased edges first (p_erase >= threshold)."""
        adj = defaultdict(list)
        elig: List[Edge] = []
        for e in graph.edges:
            if e.etype == "time" and float(e.p_erase) >= perase_threshold:
                adj[e.u].append(e.v)
                adj[e.v].append(e.u)
                elig.append(e)
        visited: Set[int] = set()
        chosen: List[Edge] = []
        for d in list(defects):
            if d in visited or d not in adj:
                visited.add(d)
                continue
            # BFS component of erased-time connectivity
            comp: List[int] = []
            dq = deque([d]); visited.add(d)
            while dq:
                u = dq.popleft()
                comp.append(u)
                for v in adj[u]:
                    if v not in visited:
                        visited.add(v); dq.append(v)
            # connect odd nodes in this component along eligible edges (simple chain)
            comp_defs = [u for u in comp if u in defects]
            for i in range(1, len(comp_defs)):
                u, v = comp_defs[i-1], comp_defs[i]
                # pick any eligible edge between u and v if it exists
                ok = None
                for e in elig:
                    if (e.u==u and e.v==v) or (e.u==v and e.v==u):
                        ok = e; break
                if ok:
                    chosen.append(ok)
                    if u in defects: defects.remove(u)
                    if v in defects: defects.remove(v)
        return chosen

    def decode(self, graph: DecodingGraph, syndromes: List[int]) -> DecodeResult:
        n = len(graph.nodes)
        syn = syndromes + [0]*(n-len(syndromes)) if len(syndromes)<n else syndromes[:]
        defects: Set[int] = {i for i,s in enumerate(syn) if (s%2)==1}

        # Peel erasures first
        chosen: List[Edge] = self._peel_erasures(graph, defects, perase_threshold=0.5)
        total_cost = 0.0
        matched_to_boundary: List[int] = []

        # Prepare DSU
        dsu = _DSU(n)
        for i in range(n):
            if i in defects: dsu.parity[i]=1
            if self._is_boundary(graph, i): dsu.has_boundary[i]=True

        edges = list(graph.edges)
        edges.sort(key=effective_cost_from_edge)

        odd_components = sum(dsu.parity)  # number of odd nodes

        for e in edges:
            u, v = e.u, e.v
            ru, rv = dsu.find(u), dsu.find(v)
            if ru == rv:
                continue
            # useful if connects two odd components or attaches odd comp to a boundary
            before = (dsu.parity[ru] + dsu.parity[rv])
            will_have_boundary = dsu.has_boundary[ru] or dsu.has_boundary[rv]
            useful = bool(_useful_pair(int(dsu.parity[ru]), int(dsu.parity[rv]), int(dsu.has_boundary[ru]), int(dsu.has_boundary[rv])))
            if not useful:
                continue
            dsu.unite(ru, rv)
            chosen.append(e)
            c = effective_cost_from_edge(e)
            total_cost += c
            if self._is_boundary(graph, u) and (v in defects):
                matched_to_boundary.append(v)
            elif self._is_boundary(graph, v) and (u in defects):
                matched_to_boundary.append(u)

            # update odd component count conservatively
            if before==2:
                odd_components -= 2
            elif will_have_boundary and before==1:
                odd_components -= 1
            if odd_components <= 0:
                break

        pair_count = max(1, len(chosen))
        avg_cost = total_cost / pair_count
        return DecodeResult(chosen, total_cost, matched_to_boundary, avg_cost)
