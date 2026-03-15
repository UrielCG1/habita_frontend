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


class EmailAlreadyExistsError(AuthServiceError):
    pass


class UnauthorizedRefreshError(AuthServiceError):
    pass


def login_with_backend(email: str, password: str) -> dict:
    url = f"{settings.BACKEND_API_BASE_URL}/auth/login"

    try:
        response = requests.post(
            url,
            data={
                "username": email,
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


def register_with_backend(payload: dict) -> dict:
    url = f"{settings.BACKEND_API_BASE_URL}/auth/register"

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise BackendUnavailableError(
            "No fue posible conectar con el servidor de registro."
        ) from exc

    if response.status_code == 409:
        raise EmailAlreadyExistsError("Ese correo ya está registrado.")

    if response.status_code >= 500:
        raise BackendUnavailableError(
            "El servidor de registro no está disponible en este momento."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthServiceError("La respuesta del servidor no es válida.") from exc

    data = payload.get("data")
    if not data or "access_token" not in data or "refresh_token" not in data or "user" not in data:
        raise AuthServiceError("La respuesta del servidor está incompleta.")

    return data


def save_auth_session(request, auth_data: dict) -> None:
    request.session["habita_logged_in"] = True
    request.session["habita_auth"] = {
        "access_token": auth_data["access_token"],
        "refresh_token": auth_data.get("refresh_token"),
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


def refresh_access_token(request) -> str:
    auth_data = request.session.get("habita_auth", {})
    refresh_token = auth_data.get("refresh_token")

    if not refresh_token:
        raise UnauthorizedRefreshError("No hay refresh token disponible.")

    url = f"{settings.BACKEND_API_BASE_URL}/auth/refresh"

    try:
        response = requests.post(
            url,
            json={"refresh_token": refresh_token},
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise BackendUnavailableError(
            "No fue posible renovar la sesión."
        ) from exc

    if response.status_code == 401:
        raise UnauthorizedRefreshError("La sesión ya no es válida.")

    if response.status_code >= 500:
        raise BackendUnavailableError(
            "El servidor de autenticación no está disponible en este momento."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthServiceError("La respuesta del servidor no es válida.") from exc

    data = payload.get("data")
    access_token = data.get("access_token") if data else None

    if not access_token:
        raise AuthServiceError("No se recibió un nuevo access token.")

    request.session["habita_auth"]["access_token"] = access_token
    request.session.modified = True

    return access_token


def get_authorization_header(request, auto_refresh: bool = False) -> dict:
    auth_data = request.session.get("habita_auth", {})
    access_token = auth_data.get("access_token")

    if not access_token and auto_refresh:
        access_token = refresh_access_token(request)

    if not access_token:
        raise UnauthorizedRefreshError("No hay access token disponible.")

    return {
        "Authorization": f"Bearer {access_token}",
    }