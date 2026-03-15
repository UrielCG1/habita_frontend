import requests
from django.conf import settings


class AuthServiceError(Exception):
    pass


class InvalidCredentialsError(AuthServiceError):
    pass


class InactiveUserError(AuthServiceError):
    pass


class BackendUnavailableError(AuthServiceError):
    pass


def login_with_backend(email: str, password: str) -> dict:
    url = f"{settings.BACKEND_API_BASE_URL}/auth/login"

    try:
        response = requests.post(
            url,
            data={
                "username": email,   # FastAPI OAuth2 espera username
                "password": password,
            },
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise BackendUnavailableError(
            "No fue posible conectar con el servidor de autenticación."
        ) from exc

    if response.status_code == 401:
        raise InvalidCredentialsError("Correo o contraseña incorrectos.")

    if response.status_code == 403:
        raise InactiveUserError("Tu cuenta está inactiva.")

    if response.status_code >= 500:
        raise BackendUnavailableError(
            "El servidor de autenticación no está disponible en este momento."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthServiceError("La respuesta del servidor no es válida.") from exc

    data = payload.get("data")
    if not data or "access_token" not in data or "user" not in data:
        raise AuthServiceError("La respuesta del servidor está incompleta.")

    return data


def save_auth_session(request, auth_data: dict) -> None:
    request.session["habita_logged_in"] = True
    request.session["habita_auth"] = {
        "access_token": auth_data["access_token"],
        "token_type": auth_data.get("token_type", "bearer"),
        "user": {
            "id": auth_data["user"]["id"],
            "full_name": auth_data["user"]["full_name"],
            "email": auth_data["user"]["email"],
            "phone": auth_data["user"].get("phone"),
            "role": auth_data["user"]["role"],
            "is_active": auth_data["user"]["is_active"],
        },
    }
    request.session.modified = True
    
    
def clear_auth_session(request) -> None:
    request.session.pop("habita_logged_in", None)
    request.session.pop("habita_auth", None)
    request.session.modified = True