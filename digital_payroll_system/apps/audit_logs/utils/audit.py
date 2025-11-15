from ..models import AuditLog

def create_audit_log(profile, action, description=""):
    try:
        AuditLog.objects.create(
            profile=profile,
            action=action,
            description=description
        )
    except Exception:
        pass 
