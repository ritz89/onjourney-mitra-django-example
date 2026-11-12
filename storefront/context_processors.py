from integrations.onjourney.adapters.demo import DemoClient


def demo_context(request):
    subject = request.session.get("demo_subject")
    return {
        "tenant": DemoClient().get_tenant(),
        "demo_mode": True,
        "demo_user": (
            {"subject": subject, "name": request.session.get("demo_name", "Wisatawan Demo")}
            if subject
            else None
        ),
    }
