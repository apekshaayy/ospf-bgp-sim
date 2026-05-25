"""
OSPF (Dijkstra SPF) and BGP path selection simulation engine.
Links use 'source_id'/'target_id' keys (Django ORM default).
"""
import heapq
from collections import defaultdict


def ospf_dijkstra(routers, links, source_id):
    """Dijkstra SPF. Returns {router_id: {cost, path, reachable}}"""
    graph = defaultdict(list)
    for link in links:
        if link.get('is_active', True):
            s = link.get('source_id', link.get('source'))
            t = link.get('target_id', link.get('target'))
            c = link['cost']
            graph[s].append((t, c))
            graph[t].append((s, c))

    dist = {r['id']: float('inf') for r in routers}
    prev = {r['id']: None for r in routers}
    dist[source_id] = 0
    heap = [(0, source_id)]
    visited = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        for neighbor, link_cost in graph[node]:
            new_cost = cost + link_cost
            if new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))

    results = {}
    for r in routers:
        rid = r['id']
        if dist[rid] == float('inf'):
            results[rid] = {'cost': None, 'path': [], 'reachable': False}
        else:
            path, node = [], rid
            while node is not None:
                path.append(node)
                node = prev[node]
            path.reverse()
            results[rid] = {'cost': dist[rid], 'path': path, 'reachable': True}
    return results


def ospf_lsdb(routers, links):
    """Build full OSPF LSDB and routing table per router."""
    lsdb = {}
    router_map = {r['id']: r for r in routers}

    for r in routers:
        spf = ospf_dijkstra(routers, links, r['id'])
        neighbors = []
        for link in links:
            if not link.get('is_active', True):
                continue
            s = link.get('source_id', link.get('source'))
            t = link.get('target_id', link.get('target'))
            if s == r['id']:
                neighbors.append({'router': t, 'router_name': router_map.get(t, {}).get('name', str(t)), 'cost': link['cost'], 'state': 'FULL'})
            elif t == r['id']:
                neighbors.append({'router': s, 'router_name': router_map.get(s, {}).get('name', str(s)), 'cost': link['cost'], 'state': 'FULL'})

        routing_table = []
        for dest_id, info in spf.items():
            if dest_id == r['id']:
                continue
            dest_router = router_map.get(dest_id, {})
            next_hop_id = info['path'][1] if len(info['path']) > 1 else None
            nh_router = router_map.get(next_hop_id, {}) if next_hop_id else {}
            routing_table.append({
                'destination': dest_router.get('router_id', str(dest_id)),
                'dest_name': dest_router.get('name', str(dest_id)),
                'dest_id': dest_id,
                'cost': info['cost'],
                'next_hop': nh_router.get('router_id', str(next_hop_id)) if next_hop_id else 'Direct',
                'next_hop_name': nh_router.get('name', '') if next_hop_id else '',
                'path': [router_map.get(p, {}).get('name', str(p)) for p in info['path']],
                'path_ids': info['path'],
                'reachable': info['reachable'],
            })

        lsdb[r['id']] = {
            'router_id': r['router_id'],
            'name': r['name'],
            'area': r.get('ospf_area', '0.0.0.0'),
            'protocol': r.get('protocol', 'ospf'),
            'neighbors': neighbors,
            'routing_table': sorted(routing_table, key=lambda x: x['cost'] or 9999),
            'lsa_sequence': 1,
            'spf_runs': 1,
        }
    return lsdb


def bgp_best_path(sessions, routers, route_prefix='0.0.0.0/0'):
    """BGP best-path selection per router."""
    router_map = {r['id']: r for r in routers}
    peer_graph = defaultdict(list)
    for s in sessions:
        if s.get('is_established', True):
            local = s.get('local_router_id', s.get('local'))
            peer  = s.get('peer_router_id',  s.get('peer'))
            peer_graph[local].append({'peer': peer, 'session_type': s['session_type'],
                                       'local_preference': s['local_preference'], 'med': s['med']})
            peer_graph[peer].append({'peer': local, 'session_type': s['session_type'],
                                      'local_preference': s['local_preference'], 'med': s['med']})

    results = {}
    for r in routers:
        rid = r['id']
        peers = peer_graph[rid]
        rib = []
        for pi in peers:
            peer = router_map.get(pi['peer'], {})
            rib.append({
                'prefix': route_prefix,
                'peer': peer.get('name', str(pi['peer'])),
                'peer_id': pi['peer'],
                'peer_as': peer.get('as_number', 'N/A'),
                'local_pref': pi['local_preference'],
                'med': pi['med'],
                'session_type': pi['session_type'],
                'as_path_len': 1,
                'weight': 32768 if pi['session_type'] == 'ibgp' else 0,
                'next_hop': peer.get('router_id', ''),
            })

        best = None
        if rib:
            best = sorted(rib, key=lambda x: (
                -x['weight'], -x['local_pref'],
                x['as_path_len'], x['med'],
                0 if x['session_type'] == 'ebgp' else 1,
            ))[0]

        results[rid] = {
            'router': r['name'],
            'router_id': r['router_id'],
            'as_number': r.get('as_number'),
            'rib': rib,
            'best_path': best,
            'peer_count': len(peers),
            'established': len(peers),
        }
    return results


def find_all_paths(routers, links, src_id, dst_id, max_paths=5):
    """Find up to max_paths between two routers (for animation)."""
    graph = defaultdict(list)
    for link in links:
        if link.get('is_active', True):
            s = link.get('source_id', link.get('source'))
            t = link.get('target_id', link.get('target'))
            graph[s].append((t, link['cost'], link['id']))
            graph[t].append((s, link['cost'], link['id']))

    all_paths = []
    def dfs(node, dst, path, link_path, cost, visited):
        if node == dst:
            all_paths.append({'nodes': list(path), 'links': list(link_path), 'cost': cost})
            return
        if len(all_paths) >= max_paths:
            return
        for neighbor, c, lid in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                link_path.append(lid)
                dfs(neighbor, dst, path, link_path, cost + c, visited)
                path.pop()
                link_path.pop()
                visited.discard(neighbor)

    dfs(src_id, dst_id, [src_id], [], 0, {src_id})
    return sorted(all_paths, key=lambda x: x['cost'])


def generate_ospf_logs(lsdb):
    logs = []
    for rid, data in lsdb.items():
        logs.append(f"[OSPF] {data['name']} ({data['router_id']}) Area {data['area']} - SPF complete, {len(data['neighbors'])} neighbors")
        for n in data['neighbors']:
            logs.append(f"[OSPF] {data['name']}: Adj {n['router_name']} cost={n['cost']} state={n['state']}")
        for rt in data['routing_table'][:3]:
            logs.append(f"[OSPF] {data['name']}: Route {rt['destination']} cost={rt['cost']} via {rt['next_hop']}")
    return logs


def generate_bgp_logs(bgp_results):
    logs = []
    for rid, data in bgp_results.items():
        if data['peer_count'] > 0:
            logs.append(f"[BGP] {data['router']} AS{data['as_number']}: {data['established']} sessions ESTABLISHED")
            if data['best_path']:
                bp = data['best_path']
                logs.append(f"[BGP] {data['router']}: Best path prefix={bp['prefix']} via {bp['peer']} LP={bp['local_pref']} MED={bp['med']} {bp['session_type'].upper()}")
    return logs