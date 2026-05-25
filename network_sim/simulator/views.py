from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import Router, Link, BGPSession, SimulationLog
from .simulation import ospf_lsdb, bgp_best_path, generate_ospf_logs, generate_bgp_logs


def index(request):
    return render(request, 'simulator/index.html')


def get_topology(request):
    routers = list(Router.objects.values())
    links = list(Link.objects.select_related('source', 'target').values(
        'id', 'source_id', 'target_id', 'cost', 'bandwidth', 'is_active',
        'source__name', 'target__name', 'source__router_id', 'target__router_id'
    ))
    sessions = list(BGPSession.objects.select_related('local_router', 'peer_router').values(
        'id', 'local_router_id', 'peer_router_id', 'session_type', 'is_established',
        'local_preference', 'med', 'local_router__name', 'peer_router__name'
    ))
    return JsonResponse({'routers': routers, 'links': links, 'sessions': sessions})


@csrf_exempt
def add_router(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)

        name = data.get('name')
        router_id = data.get('router_id')

        if not name or not router_id:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        router = Router.objects.create(
            name=name,
            router_id=router_id,
            protocol=data.get('protocol', 'ospf'),
            as_number=data.get('as_number'),
            ospf_area=data.get('ospf_area', '0.0.0.0'),
            x_pos=data.get('x_pos', 300),
            y_pos=data.get('y_pos', 300),
        )

        return JsonResponse({'status': 'ok', 'id': router.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def update_router_pos(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    Router.objects.filter(id=data['id']).update(x_pos=data['x'], y_pos=data['y'])
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def delete_router(request, router_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE required'}, status=405)
    router = get_object_or_404(Router, id=router_id)
    name = router.name
    router.delete()
    SimulationLog.objects.create(log_type='system', message=f"Router {name} removed")
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def add_link(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    source = get_object_or_404(Router, id=data['source_id'])
    target = get_object_or_404(Router, id=data['target_id'])
    link, created = Link.objects.get_or_create(
        source=source, target=target,
        defaults={'cost': data.get('cost', 10), 'bandwidth': data.get('bandwidth', 1000)}
    )
    if not created:
        link.cost = data.get('cost', link.cost)
        link.save()
    SimulationLog.objects.create(log_type='system', message=f"Link {source.name} <-> {target.name} cost={link.cost}")
    return JsonResponse({'status': 'ok', 'id': link.id})


@csrf_exempt
def delete_link(request, link_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE required'}, status=405)
    link = get_object_or_404(Link, id=link_id)
    msg = f"Link {link.source.name} <-> {link.target.name} removed"
    link.delete()
    SimulationLog.objects.create(log_type='system', message=msg)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
def toggle_link(request, link_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    link = get_object_or_404(Link, id=link_id)
    link.is_active = not link.is_active
    link.save()
    state = "UP" if link.is_active else "DOWN"
    SimulationLog.objects.create(log_type='system', message=f"Link {link.source.name} <-> {link.target.name} is {state}")
    return JsonResponse({'status': 'ok', 'is_active': link.is_active})


@csrf_exempt
def add_bgp_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    local = get_object_or_404(Router, id=data['local_router_id'])
    peer = get_object_or_404(Router, id=data['peer_router_id'])
    session_type = 'ibgp' if local.as_number == peer.as_number else 'ebgp'
    sess, _ = BGPSession.objects.get_or_create(
        local_router=local, peer_router=peer,
        defaults={'session_type': session_type,
                  'local_preference': data.get('local_preference', 100),
                  'med': data.get('med', 0)}
    )
    SimulationLog.objects.create(log_type='bgp', message=f"BGP {local.name} <-> {peer.name} ({session_type.upper()}) established")
    return JsonResponse({'status': 'ok', 'id': sess.id, 'session_type': sess.session_type})


@csrf_exempt
def delete_bgp_session(request, session_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE required'}, status=405)
    sess = get_object_or_404(BGPSession, id=session_id)
    msg = f"BGP session {sess.local_router.name} <-> {sess.peer_router.name} removed"
    sess.delete()
    SimulationLog.objects.create(log_type='bgp', message=msg)
    return JsonResponse({'status': 'ok'})


def run_ospf(request):
    routers = list(Router.objects.values())
    links = list(Link.objects.values('id', 'source_id', 'target_id', 'cost', 'bandwidth', 'is_active'))
    if not routers:
        return JsonResponse({'error': 'No routers in topology'}, status=400)
    lsdb = ospf_lsdb(routers, links)
    logs = generate_ospf_logs(lsdb)
    for log in logs:
        SimulationLog.objects.create(log_type='ospf', message=log)
    return JsonResponse({'lsdb': lsdb, 'logs': logs})


def run_bgp(request):
    routers = list(Router.objects.values())
    sessions = list(BGPSession.objects.values(
        'id', 'local_router_id', 'peer_router_id', 'session_type',
        'is_established', 'local_preference', 'med'
    ))
    bgp_sessions = [{'local': s['local_router_id'], 'peer': s['peer_router_id'],
                     'session_type': s['session_type'], 'is_established': s['is_established'],
                     'local_preference': s['local_preference'], 'med': s['med']} for s in sessions]
    bgp_results = bgp_best_path(bgp_sessions, routers)
    logs = generate_bgp_logs(bgp_results)
    for log in logs:
        SimulationLog.objects.create(log_type='bgp', message=log)
    return JsonResponse({'bgp_table': bgp_results, 'logs': logs})


def get_logs(request):
    logs = list(SimulationLog.objects.values('log_type', 'message', 'created_at').order_by('-created_at')[:100])
    return JsonResponse({'logs': logs})


@csrf_exempt
def load_preset(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    preset = data.get('preset', 'ospf_basic')
    BGPSession.objects.all().delete()
    Link.objects.all().delete()
    Router.objects.all().delete()
    SimulationLog.objects.all().delete()
    if preset == 'ospf_basic':
        _load_ospf_basic()
    elif preset == 'bgp_multias':
        _load_bgp_multias()
    elif preset == 'mixed':
        _load_mixed_topology()
    SimulationLog.objects.create(log_type='system', message=f"Preset '{preset}' loaded")
    return JsonResponse({'status': 'ok'})


def _load_ospf_basic():
    routers_data = [
        ('R1', '1.1.1.1', 'ospf', None, '0.0.0.0', 150, 120),
        ('R2', '2.2.2.2', 'ospf', None, '0.0.0.0', 350, 80),
        ('R3', '3.3.3.3', 'ospf', None, '0.0.0.0', 550, 120),
        ('R4', '4.4.4.4', 'ospf', None, '0.0.0.0', 150, 320),
        ('R5', '5.5.5.5', 'ospf', None, '0.0.0.1', 350, 280),
        ('R6', '6.6.6.6', 'ospf', None, '0.0.0.1', 550, 320),
    ]
    routers = {}
    for name, rid, proto, asn, area, x, y in routers_data:
        r = Router.objects.create(name=name, router_id=rid, protocol=proto, as_number=asn, ospf_area=area, x_pos=x, y_pos=y)
        routers[name] = r
    for src, tgt, cost in [('R1','R2',10),('R2','R3',10),('R1','R4',20),('R2','R5',15),('R3','R6',20),('R4','R5',10),('R5','R6',10),('R4','R6',50)]:
        Link.objects.create(source=routers[src], target=routers[tgt], cost=cost)


def _load_bgp_multias():
    routers_data = [
        ('R1','10.0.0.1','bgp',100,'0.0.0.0',120,150),
        ('R2','10.0.0.2','bgp',100,'0.0.0.0',300,100),
        ('R3','10.0.0.3','bgp',200,'0.0.0.0',480,150),
        ('R4','10.0.0.4','bgp',200,'0.0.0.0',480,300),
        ('R5','10.0.0.5','bgp',300,'0.0.0.0',300,350),
        ('R6','10.0.0.6','bgp',100,'0.0.0.0',120,300),
    ]
    routers = {}
    for name, rid, proto, asn, area, x, y in routers_data:
        r = Router.objects.create(name=name, router_id=rid, protocol=proto, as_number=asn, ospf_area=area, x_pos=x, y_pos=y)
        routers[name] = r
    for src, tgt, cost in [('R1','R2',10),('R1','R6',5),('R2','R3',10),('R3','R4',5),('R4','R5',10),('R5','R6',10)]:
        Link.objects.create(source=routers[src], target=routers[tgt], cost=cost)
    BGPSession.objects.create(local_router=routers['R1'], peer_router=routers['R2'], session_type='ibgp', local_preference=100)
    BGPSession.objects.create(local_router=routers['R1'], peer_router=routers['R6'], session_type='ibgp', local_preference=100)
    BGPSession.objects.create(local_router=routers['R2'], peer_router=routers['R3'], session_type='ebgp', local_preference=100, med=50)
    BGPSession.objects.create(local_router=routers['R3'], peer_router=routers['R4'], session_type='ibgp', local_preference=150)
    BGPSession.objects.create(local_router=routers['R4'], peer_router=routers['R5'], session_type='ebgp', local_preference=100)
    BGPSession.objects.create(local_router=routers['R5'], peer_router=routers['R6'], session_type='ebgp', local_preference=80)


def _load_mixed_topology():
    routers_data = [
        ('Core1','10.1.1.1','both',65001,'0.0.0.0',300,150),
        ('Core2','10.1.1.2','both',65001,'0.0.0.0',500,150),
        ('Edge1','10.2.1.1','both',65001,'0.0.0.1',150,280),
        ('Edge2','10.2.1.2','both',65002,'0.0.0.1',650,280),
        ('ISP1', '10.3.1.1','bgp', 65100,'0.0.0.0',150,100),
        ('ISP2', '10.3.1.2','bgp', 65200,'0.0.0.0',650,100),
    ]
    routers = {}
    for name, rid, proto, asn, area, x, y in routers_data:
        r = Router.objects.create(name=name, router_id=rid, protocol=proto, as_number=asn, ospf_area=area, x_pos=x, y_pos=y)
        routers[name] = r
    for src, tgt, cost in [('Core1','Core2',5),('Core1','Edge1',10),('Core2','Edge2',10),('Edge1','Edge2',20),('ISP1','Core1',50),('ISP2','Core2',50)]:
        Link.objects.create(source=routers[src], target=routers[tgt], cost=cost)
    BGPSession.objects.create(local_router=routers['Core1'], peer_router=routers['Core2'], session_type='ibgp', local_preference=100)
    BGPSession.objects.create(local_router=routers['ISP1'], peer_router=routers['Core1'], session_type='ebgp', local_preference=100, med=10)
    BGPSession.objects.create(local_router=routers['ISP2'], peer_router=routers['Core2'], session_type='ebgp', local_preference=90, med=20)


def find_paths(request):
    """Find all paths between two routers for animation."""
    src_id = request.GET.get('src')
    dst_id = request.GET.get('dst')
    if not src_id or not dst_id:
        return JsonResponse({'error': 'src and dst required'}, status=400)
    routers = list(Router.objects.values())
    links = list(Link.objects.values('id', 'source_id', 'target_id', 'cost', 'bandwidth', 'is_active'))
    from .simulation import find_all_paths
    router_map = {r['id']: r for r in routers}
    paths = find_all_paths(routers, links, int(src_id), int(dst_id))
    # Annotate with names
    for p in paths:
        p['node_names'] = [router_map.get(n, {}).get('name', str(n)) for n in p['nodes']]
    return JsonResponse({'paths': paths})


def topology_stats(request):
    """Return topology statistics and health metrics."""
    routers = list(Router.objects.values())
    links = list(Link.objects.values('id', 'source_id', 'target_id', 'cost', 'bandwidth', 'is_active'))
    sessions = list(BGPSession.objects.values())

    active_links = [l for l in links if l['is_active']]
    down_links = [l for l in links if not l['is_active']]

    ospf_routers = [r for r in routers if r['protocol'] in ('ospf', 'both')]
    bgp_routers = [r for r in routers if r['protocol'] in ('bgp', 'both')]

    # Calculate average degree (connectivity)
    from collections import defaultdict
    degree = defaultdict(int)
    for l in active_links:
        degree[l['source_id']] += 1
        degree[l['target_id']] += 1
    avg_degree = sum(degree.values()) / len(routers) if routers else 0

    # Diameter from OSPF if routers exist
    diameter = 0
    if ospf_routers:
        from .simulation import ospf_dijkstra
        for r in ospf_routers[:3]:  # Sample a few for performance
            spf = ospf_dijkstra(routers, links, r['id'])
            max_cost = max((v['cost'] for v in spf.values() if v['reachable']), default=0)
            diameter = max(diameter, max_cost)

    as_numbers = list(set(r['as_number'] for r in routers if r.get('as_number')))

    return JsonResponse({
        'router_count': len(routers),
        'link_count': len(links),
        'active_links': len(active_links),
        'down_links': len(down_links),
        'session_count': len(sessions),
        'ospf_routers': len(ospf_routers),
        'bgp_routers': len(bgp_routers),
        'avg_degree': round(avg_degree, 2),
        'diameter': diameter,
        'as_count': len(as_numbers),
        'as_numbers': sorted(as_numbers),
    })


def export_config(request):
    """Export topology as Cisco-style config snippets."""
    routers = list(Router.objects.select_related().all())
    links = list(Link.objects.select_related('source', 'target').all())
    sessions = list(BGPSession.objects.select_related('local_router', 'peer_router').all())

    configs = {}
    for router in routers:
        lines = [
            f"! Router {router.name} configuration",
            f"hostname {router.name}",
            f"!",
        ]
        if router.protocol in ('ospf', 'both'):
            lines += [
                f"router ospf 1",
                f" router-id {router.router_id}",
                f" area {router.ospf_area} stub",
                f"!",
            ]
            for link in links:
                if link.source_id == router.id or link.target_id == router.id:
                    other = link.target if link.source_id == router.id else link.source
                    ifname = f"GigabitEthernet0/{links.index(link)}"
                    lines += [
                        f"interface {ifname}",
                        f" ip address 10.{router.id}.{other.id}.1 255.255.255.252",
                        f" ip ospf 1 area {router.ospf_area}",
                        f" ip ospf cost {link.cost}",
                        f" {'no ' if not link.is_active else ''}shutdown",
                        f"!",
                    ]
        if router.protocol in ('bgp', 'both') and router.as_number:
            lines += [
                f"router bgp {router.as_number}",
                f" bgp router-id {router.router_id}",
                f" bgp log-neighbor-changes",
            ]
            for sess in sessions:
                if sess.local_router_id == router.id:
                    peer = sess.peer_router
                    lines.append(f" neighbor {peer.router_id} remote-as {peer.as_number}")
                    lines.append(f" neighbor {peer.router_id} description {peer.name}")
                    if sess.session_type == 'ibgp':
                        lines.append(f" neighbor {peer.router_id} next-hop-self")
                    lines.append(f" neighbor {peer.router_id} local-preference {sess.local_preference}")
            lines.append("!")

        configs[router.name] = '\n'.join(lines)

    return JsonResponse({'configs': configs})