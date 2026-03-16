from .utils import get_habita_user, is_habita_authenticated
import logging

logger = logging.getLogger(__name__)


def habita_auth(request):
    habita_user = get_habita_user(request)
    logger.warning(f"habita_auth context processor called. User: {habita_user}, Authenticated: {is_habita_authenticated(request)}")
    return {
        "habita_logged_in": is_habita_authenticated(request),
        "habita_user": habita_user,
    }