from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/topology/', views.get_topology, name='get_topology'),
    path('api/topology/stats/', views.topology_stats, name='topology_stats'),
    path('api/router/add/', views.add_router, name='add_router'),
    path('api/router/pos/', views.update_router_pos, name='update_router_pos'),
    path('api/router/<int:router_id>/delete/', views.delete_router, name='delete_router'),
    path('api/link/add/', views.add_link, name='add_link'),
    path('api/link/<int:link_id>/delete/', views.delete_link, name='delete_link'),
    path('api/link/<int:link_id>/toggle/', views.toggle_link, name='toggle_link'),
    path('api/bgp/session/add/', views.add_bgp_session, name='add_bgp_session'),
    path('api/bgp/session/<int:session_id>/delete/', views.delete_bgp_session, name='delete_bgp_session'),
    path('api/run/ospf/', views.run_ospf, name='run_ospf'),
    path('api/run/bgp/', views.run_bgp, name='run_bgp'),
    path('api/logs/', views.get_logs, name='get_logs'),
    path('api/preset/', views.load_preset, name='load_preset'),
    path('api/paths/', views.find_paths, name='find_paths'),
    path('api/export/', views.export_config, name='export_config'),
]