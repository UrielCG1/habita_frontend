from typing import Optional

def get_habita_auth_session(request) -> dict:
    return request.session.get("habita_auth", {})


def get_habita_user(request) -> Optional[dict]:
    auth_data = get_habita_auth_session(request)
    user = auth_data.get("user")

    if not user or not request.session.get("habita_logged_in"):
        return None

    return user


def is_habita_authenticated(request) -> bool:
    return bool(request.session.get("habita_logged_in") and get_habita_user(request))