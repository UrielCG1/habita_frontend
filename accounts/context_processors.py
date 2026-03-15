from .utils import get_habita_user, is_habita_authenticated


def habita_auth(request):
    return {
        "habita_logged_in": is_habita_authenticated(request),
        "habita_user": get_habita_user(request),
    }