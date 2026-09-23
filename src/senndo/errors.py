"""Les erreurs typées — ce qui sépare un SDK d'un enrobage de ``urlopen``.

LA RÈGLE : ON BRANCHE SUR UNE CLASSE OU SUR UN CODE, JAMAIS SUR UN MESSAGE. Le contrat le dit
explicitement (``error.code`` est stable, ``error.message`` est un libellé humain qui évolue). Un
SDK qui lèverait ``RuntimeError(body)`` forcerait chaque intégrateur à lire une chaîne pour savoir
s'il doit recharger le compte ou corriger son appel — et à la relire le jour où le libellé change.

LA FAMILLE VIENT DU STATUT HTTP, PAS DU CODE. Les statuts sont peu nombreux et stables ; les codes,
eux, s'ajoutent (senndo s'y engage). Une classe par code aurait rendu toute nouvelle valeur amont
invisible du ``except`` d'un client déjà déployé. Le code reste donc lisible sur ``error.code``, et
c'est le statut qui choisit la classe.
"""

from __future__ import annotations

import json
from typing import Any


class SenndoError(Exception):
    """La racine de toute erreur levée par ce SDK.

    ``except SenndoError:`` attrape tout ce que le paquet peut lever, et rien d'autre.
    """


class SenndoRequestError(SenndoError):
    """Une erreur levée AVANT tout appel réseau : le SDK a détecté que la requête serait refusée.

    Elle n'a pas de statut parce qu'aucune requête n'est partie — et c'est l'intérêt : un champ
    obligatoire absent ne coûte ni un aller-retour ni, sur un canal facturé, le risque d'un débit.
    """


class SenndoTimeoutError(SenndoError):
    """L'appel a dépassé le délai imparti. Ce que le serveur en a fait reste INCONNU."""

    def __init__(self, timeout: float, operation_id: str) -> None:
        #: Le délai dépassé, en secondes.
        self.timeout = timeout
        self.operation_id = operation_id
        super().__init__(
            f"senndo : « {operation_id} » a dépassé le délai de {timeout} s. L'état côté serveur "
            "est INDÉTERMINÉ : sur un envoi, relisez list_messages avec votre clé d'idempotence "
            "avant de renvoyer — un délai dépassé ne prouve pas que rien n'est parti."
        )


class SenndoConnectionError(SenndoError):
    """Le transport a échoué : DNS, TLS, coupure. Aucune réponse HTTP n'a été reçue."""

    def __init__(self, operation_id: str, cause: BaseException) -> None:
        self.operation_id = operation_id
        #: L'erreur d'origine remontée par le transport.
        self.cause = cause
        super().__init__(f"senndo : « {operation_id} » n'a pas abouti (échec de transport).")


class SenndoProtocolError(SenndoError):
    """Le serveur a répondu, mais avec une enveloppe que le contrat ne décrit pas."""

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        #: Le corps brut, tronqué — utile au support, jamais à une logique.
        self.body = body
        super().__init__(
            f"senndo : réponse {status} illisible (ni JSON valide, ni enveloppe d'erreur connue)."
        )


class SenndoApiError(SenndoError):
    """Toute réponse d'erreur RENVOYÉE PAR L'API — l'enveloppe ``{"error": {"code", "message"}}``."""

    def __init__(self, status: int, code: str, api_message: str, operation_id: str) -> None:
        #: Le statut HTTP.
        self.status = status
        #: Le code STABLE. Branchez votre logique dessus.
        self.code = code
        #: Le libellé humain renvoyé par l'API. Ne branchez RIEN dessus.
        self.api_message = api_message
        #: L'opération concernée.
        self.operation_id = operation_id
        #: L'attente demandée par un 429, quand le serveur la précise.
        self.retry_after: int | None = None
        super().__init__(f"senndo : {operation_id} → {status} {code} — {api_message}")


class SenndoValidationError(SenndoApiError):
    """400 / 422 — la requête est mal formée, ou irrecevable en l'état. Corrigez l'appel.

    Le corps peut n'avoir jamais été LU : ``EMPTY_BODY`` (corps annoncé en JSON mais vide) et
    ``MALFORMED_JSON`` (corps illisible) sont rendus par le serveur avant d'atteindre la route,
    donc avant toute validation métier. Les autres codes de ce statut concernent un corps bien
    formé mais refusé sur le fond. Dans tous les cas la reprise est inutile tant que l'appel n'a
    pas changé — c'est ce qui sépare ce statut d'un 5xx.
    """


class SenndoAuthError(SenndoApiError):
    """401 — clé absente, malformée, inconnue ou révoquée."""


class SenndoInsufficientFundsError(SenndoApiError):
    """402 — solde insuffisant. Rechargez le compte : rejouer à l'identique échouera pareil."""


class SenndoForbiddenError(SenndoApiError):
    """403 — la clé était valide, l'appel est refusé (allowlist, suspension, contenu bloqué)."""


class SenndoNotFoundError(SenndoApiError):
    """404 — la ressource n'existe pas, ou n'appartient pas au compte appelant.

    ``ROUTE_NOT_FOUND`` est le cas à part : aucune route ne sert ce couple méthode + chemin.
    C'est une URL fautive, pas une ressource absente.
    """


class SenndoConflictError(SenndoApiError):
    """409 — conflit d'état : média encore référencé, quota dépassé, mode d'idempotence divergent."""


class SenndoPayloadTooLargeError(SenndoApiError):
    """413 — le corps de la requête dépasse le plafond accepté.

    Deux causes distinctes : un FICHIER trop volumineux sur un envoi multipart
    (``FILE_TOO_LARGE``), ou un CORPS JSON au-delà du plafond de la route
    (``BODY_TOO_LARGE``, 1 Mio par défaut). Le code du corps d'erreur les sépare —
    la taille du fichier et celle de la requête ne se corrigent pas de la même façon.
    """


class SenndoUnsupportedMediaTypeError(SenndoApiError):
    """415 — le type de contenu n'est pas pris en charge.

    Deux causes distinctes, séparées par le code : le ``Content-Type`` de la REQUÊTE n'est
    servi par aucun parseur — y compris quand il est absent (``UNSUPPORTED_MEDIA_TYPE``) — ou
    le type du FICHIER envoyé en multipart est refusé, ou son contenu ne correspond pas à son
    extension (``UNSUPPORTED_TYPE``). Ce ne sont pas les mêmes corrections : la première tient
    à l'en-tête, la seconde au fichier.
    """


class SenndoRateLimitError(SenndoApiError):
    """429 — cadence dépassée. ``retry_after`` porte l'attente demandée quand elle est connue.

    Deux codes, deux remèdes, et c'est sur ``error.code`` qu'on les sépare — jamais sur le
    statut :

    * ``VELOCITY_EXCEEDED`` — trop d'envois pour ce compte sur 60 secondes. Étalez la campagne ;
      le message refusé n'a jamais été débité.
    * ``RATE_LIMITED`` — trop d'appels (ou trop d'octets) pour cette clé sur 60 secondes,
      lectures comprises. Espacez les requêtes, ou parallélisez moins.
    """


class SenndoServiceUnavailableError(SenndoApiError):
    """503 — le canal ou le service ne peut pas livrer MAINTENANT.

    Ce refus arrive AVANT tout débit (un canal qui ne peut pas livrer refuse avant de facturer).
    Rien n'a été prélevé.
    """


_CLASS_BY_STATUS: dict[int, type[SenndoApiError]] = {
    400: SenndoValidationError,
    401: SenndoAuthError,
    402: SenndoInsufficientFundsError,
    403: SenndoForbiddenError,
    404: SenndoNotFoundError,
    409: SenndoConflictError,
    413: SenndoPayloadTooLargeError,
    415: SenndoUnsupportedMediaTypeError,
    422: SenndoValidationError,
    429: SenndoRateLimitError,
    503: SenndoServiceUnavailableError,
}


def _is_envelope(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    error: Any = value.get("error")
    if not isinstance(error, dict):
        return False
    return isinstance(error.get("code"), str) and isinstance(error.get("message"), str)


def error_from_response(
    status: int, raw_body: str, operation_id: str, retry_after_header: str | None
) -> SenndoError:
    """Construit l'erreur typée d'une réponse d'échec.

    UN STATUT INCONNU NE FAIT PAS LEVER LE SDK sur autre chose que l'erreur du serveur : il retombe
    sur ``SenndoApiError``. Une table exhaustive qui lèverait « statut non répertorié »
    transformerait l'ajout d'un statut amont en panne chez tous les clients déjà déployés.
    """
    try:
        parsed = json.loads(raw_body)
    except ValueError:
        return SenndoProtocolError(status, raw_body[:500])
    if not _is_envelope(parsed):
        return SenndoProtocolError(status, raw_body[:500])

    envelope: Any = parsed["error"]
    cls = _CLASS_BY_STATUS.get(status, SenndoApiError)
    error = cls(status, envelope["code"], envelope["message"], operation_id)

    if isinstance(error, SenndoRateLimitError) and retry_after_header is not None:
        try:
            seconds = int(retry_after_header)
        except ValueError:
            seconds = -1
        error.retry_after = seconds if seconds >= 0 else None
    return error
