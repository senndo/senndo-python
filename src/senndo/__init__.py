"""SDK Python officiel de l'API senndo — messagerie multicanale et vérification.

    from senndo import SenndoClient, new_idempotency_key

    senndo = SenndoClient(api_key="sk_live_…")
    envoi = senndo.send_message(
        {
            "channel": "sms",
            "to": "+33612345678",
            "text": "Votre code est 4821.",
            "idempotencyKey": "connexion-8421",
        }
    )

Le paquet n'a AUCUNE dépendance d'exécution. Voir ``types.Transport`` pour brancher ``httpx``,
``requests`` ou un client interne à la place de ``urllib``.
"""

from ._generated.contract import (
    KNOWN_FAILURE_CODES,
    OPERATION_IDS,
    OPERATIONS,
    SENNDO_API_BASE_URL,
    SENNDO_CONTRACT_VERSION,
    Channel,
    FailureCode,
    MessageStatus,
)
from ._http import mask_api_key, new_idempotency_key
from .client import SDK_VERSION, SenndoClient
from .errors import (
    SenndoApiError,
    SenndoAuthError,
    SenndoConflictError,
    SenndoConnectionError,
    SenndoError,
    SenndoForbiddenError,
    SenndoInsufficientFundsError,
    SenndoNotFoundError,
    SenndoPayloadTooLargeError,
    SenndoProtocolError,
    SenndoRateLimitError,
    SenndoRequestError,
    SenndoServiceUnavailableError,
    SenndoTimeoutError,
    SenndoUnsupportedMediaTypeError,
    SenndoValidationError,
)
from .types import HttpRequest, HttpResponse, MultipartUpload, RequestOptions, Transport

__version__ = SDK_VERSION

__all__ = [
    "KNOWN_FAILURE_CODES",
    "OPERATIONS",
    "OPERATION_IDS",
    "SDK_VERSION",
    "SENNDO_API_BASE_URL",
    "SENNDO_CONTRACT_VERSION",
    "Channel",
    "FailureCode",
    "HttpRequest",
    "HttpResponse",
    "MessageStatus",
    "MultipartUpload",
    "RequestOptions",
    "SenndoApiError",
    "SenndoAuthError",
    "SenndoClient",
    "SenndoConflictError",
    "SenndoConnectionError",
    "SenndoError",
    "SenndoForbiddenError",
    "SenndoInsufficientFundsError",
    "SenndoNotFoundError",
    "SenndoPayloadTooLargeError",
    "SenndoProtocolError",
    "SenndoRateLimitError",
    "SenndoRequestError",
    "SenndoServiceUnavailableError",
    "SenndoTimeoutError",
    "SenndoUnsupportedMediaTypeError",
    "SenndoValidationError",
    "Transport",
    "__version__",
    "mask_api_key",
    "new_idempotency_key",
]
