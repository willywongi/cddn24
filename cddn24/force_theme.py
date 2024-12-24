def add_theme(request):
    force_theme = request.session.get("force_theme")
    if force_theme in {"dark", "light"}:
        return {"force_theme": force_theme}
    else:
        return {}
