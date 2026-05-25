from django.db import models

class Router(models.Model):
    PROTOCOL_CHOICES = [('ospf', 'OSPF'), ('bgp', 'BGP'), ('both', 'Both')]
    name = models.CharField(max_length=50, unique=True)
    router_id = models.CharField(max_length=20, unique=True)
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICES, default='ospf')
    as_number = models.IntegerField(null=True, blank=True)
    ospf_area = models.CharField(max_length=20, null=True, blank=True)
    x_pos = models.IntegerField(default=200)
    y_pos = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.router_id})"
    
class Link(models.Model):
    source = models.ForeignKey(Router, on_delete=models.CASCADE, related_name='links_form')
    target = models.ForeignKey(Router, on_delete=models.CASCADE, related_name='links_to')
    cost = models.IntegerField(default = 10)
    bandwidth = models.IntegerField(default = 10000)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('source', 'target')

    def __str__(self):
        return f"{self.source.name} --> {self.target.name} | (cost={self.cost})"
    
class BGPSession(models.Model):
    SESSION_TYPES = [('ebgp', 'eBGP'), ('ibgp', 'iBGP')] 
    local_router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name='bgp_sessions_local')
    peer_router = models.ForeignKey(Router, on_delete=models.CASCADE, related_name='bgp_sessions_peer')
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES)
    is_established = models.BooleanField(default=True)
    local_preference = models.IntegerField(default=100)
    med = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.local_router.name} <--> {self.peer_router.name} | ({self.session_type})"
    
class SimulationLog(models.Model):
    LOG_TYPES = [('ospf', 'OSPF'), ('bgp', 'BGP'), ('system', 'System')]
    log_type = models.CharField(max_length=10, choices=LOG_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]