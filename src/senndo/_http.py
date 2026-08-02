"""Le transport : URL, en-têtes, délais, retentatives, multipart, décodage décimal.

LA POLITIQUE DE RETENTATIVE EST LA PARTIE DANGEREUSE DE CE FICHIER, et elle tient en une phrase :
**on ne rejoue que ce qui est rejouable**. Rejouer un ``POST /v1/messages`` sans clé d'idempotence,
c'est facturer deux messages ; rejouer un ``POST /v1/webhooks``, c'est créer deux endpoints, donc
DOUBLER toutes les livraisons futures. Un ``Retry`` d'``urllib3`` monté sur un adaptateur
``requests`` fait exactement cela, en silence, et la facture arrive plus tard.

La règle appliquée, sans exception :
  - ``GET`` et ``DELETE`` sont rejouables — la sémantique HTTP le garantit ;
  - un ``POST`` n'est rejouable QUE s'il porte une clé d'idempotence non vide dans son corps.
    C'est le cas de ``send_message``, et d'aucune autre opération de la surface ;
  - un ``POST`` sans clé n'est JAMAIS rejoué, même sur 503, même sur coupure réseau. L'appelant
    reçoit l'échec et décide — avec le contexte que le SDK n'a pas.
Et, quelle que soit la rejouabilité, on ne retente que sur un échec de TRANSPORT, un 429 ou un 5xx.
Un 4xx rejoué à l'identique échoue à l'identique.

LE DÉCODAGE PASSE PAR ``parse_float=Decimal``. C'est la ligne la plus facile à perdre de tout le
paquet : sans elle, ``json.loads`` rend des ``float``, et un montant qui traverse un double
IEEE-754 perd des unités sur les longues traînes. Les montants du contrat sont des chaînes, donc
rien ne casserait visiblement — jusqu'au jour où un champ numérique décimal apparaît.
"""

from __future__ import annotations

import json
import os
import random
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any, Mapping

from .errors import (
    SenndoConnectionError,
    SenndoRateLimitError,
    SenndoTimeoutError,
    error_from_response,
)
from .types import HttpRequest, HttpResponse, MultipartUpload, Transport


def mask_api_key(api_key: str) -> str:
    """Masque une clé API : le préfixe reste lisible (il dit l'environnement), le reste non."""
    if len(api_key) <= 8:
        return "…"
    return f"{api_key[:8]}…{len(api_key) - 8} caractères masqués"


def new_idempotency_key(prefix: str | None = None) -> str:
    """Fabrique une clé d'idempotence aléatoire — À N'UTILISER QUE SI VOUS N'EN AVEZ PAS.

    Le SDK n'en pose JAMAIS à votre place. Une clé inventée au moment de l'appel ne protège de rien
    de plus que ce que le transport fait déjà : elle est perdue si le processus meurt entre l'envoi
    et la réponse, exactement le cas où l'idempotence sert. La bonne clé vient de VOTRE domaine —
    l'identifiant de la commande, de la tentative de connexion, de la ligne de campagne — et c'est
    la seule qui rende un rejeu inoffensif après un redémarrage.
    """
    key = secrets.token_hex(16)
    return key if prefix is None else f"{prefix}{key}"


def decode_json(text: str) -> Any:
    """Décode une réponse. ``parse_float=Decimal`` : voir l'en-tête de ce module."""
    return json.loads(text, parse_float=Decimal)


def build_url(
    base_url: str,
    descriptor: Mapping[str, Any],
    path_values: Mapping[str, str],
    query: Mapping[str, Any] | None,
) -> str:
    """Construit l'URL en substituant les paramètres de chemin et en sérialisant la requête."""
    path: str = descriptor["path"]
    for name in descriptor["pathParams"]:
        value = path_values.get(name)
        if value is None or value == "":
            raise ValueError(f"senndo : paramètre de chemin « {name} » manquant")
        path = path.replace("{" + name + "}", urllib.parse.quote(str(value), safe=""))

    pairs: list[tuple[str, str]] = []
    for name in descriptor["queryParams"]:
        value = None if query is None else query.get(name)
        # ``None`` vaut « non fourni » : un client qui passe le résultat d'un champ de formulaire
        # vide ne doit pas envoyer ``?status=None``.
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            pairs.append((name, "true" if value else "false"))
        else:
            pairs.append((name, str(value)))

    base = base_url[:-1] if base_url.endswith("/") else base_url
    suffix = f"?{urllib.parse.urlencode(pairs)}" if pairs else ""
    return f"{base}{path}{suffix}"


def encode_multipart(upload: MultipartUpload) -> tuple[bytes, str]:
    """Encode un téléversement en corps ``multipart/form-data``, sans dépendance."""
    boundary = f"----senndo{secrets.token_hex(16)}"
    file_name = upload.file_name.replace('"', "")
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: {upload.content_type}\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    return head + upload.file + tail, f"multipart/form-data; boundary={boundary}"


def is_replayable(descriptor: Mapping[str, Any], body: Mapping[str, Any] | None) -> bool:
    """Cet appel peut-il être REJOUÉ sans changer l'état du compte ?

    Exposé parce que c'est la décision la plus coûteuse du SDK : elle mérite d'être testée seule, et
    lue sans dérouler la boucle de retentative.
    """
    if descriptor["method"] in ("GET", "DELETE"):
        return True
    key = None if body is None else body.get("idempotencyKey")
    return isinstance(key, str) and key != ""


def is_transient(status: int | None) -> bool:
    """Cet échec vaut-il une retentative, indépendamment de la rejouabilité ?

    ``status is None`` = échec de transport.
    """
    return status is None or status == 429 or status >= 500


def _backoff_seconds(attempt: int, retry_after: int | None) -> float:
    if retry_after is not None:
        return min(float(retry_after), 60.0)
    # Exponentiel plafonné, plein jitter : sans jitter, N clients qui échouent ensemble retentent
    # ensemble et reproduisent la surcharge qu'ils devaient laisser retomber.
    # `2.0` et non `2` : `int ** int` est typé `Any` par typeshed (l'exposant peut être négatif et
    # rendre un `float`), et le délai d'attente entre deux tentatives est le dernier endroit où
    # l'on veut d'un type non vérifié.
    ceiling = min(0.25 * (2.0**attempt), 8.0)
    return random.random() * ceiling


class UrllibTransport:
    """Le transport par défaut : ``urllib.request``, zéro dépendance.

    ``HTTPError`` est traduit en réponse, PAS en exception : un 402 porte l'enveloppe d'erreur, donc
    le code stable sur lequel l'appelant branche. Le laisser remonter comme une panne de transport
    ferait perdre cette information et — pire — rendrait un 402 retentable.
    """

    def __call__(self, request: HttpRequest) -> HttpResponse:
        req = urllib.request.Request(
            request.url, data=request.body, headers=dict(request.headers), method=request.method
        )
        try:
            with urllib.request.urlopen(req, timeout=request.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return HttpResponse(
                    status=response.status,
                    headers={k.lower(): v for k, v in response.headers.items()},
                    body=body,
                )
        except urllib.error.HTTPError as http_error:
            body = http_error.read().decode("utf-8", errors="replace")
            return HttpResponse(
                status=http_error.code,
                headers={k.lower(): v for k, v in http_error.headers.items()},
                body=body,
            )
        except urllib.error.URLError as url_error:
            # ``URLError`` enveloppe la cause réelle. Un dépassement de délai y arrive sous forme de
            # ``TimeoutError`` dans ``reason`` — le laisser passer comme échec de transport ferait
            # retenter un appel que l'appelant croit abandonné.
            if isinstance(url_error.reason, TimeoutError):
                raise TimeoutError(str(url_error.reason)) from url_error
            raise OSError(str(url_error.reason)) from url_error


def perform_request(
    *,
    transport: Transport,
    api_key: str,
    base_url: str,
    user_agent: str,
    timeout: float,
    max_retries: int,
    descriptor: Mapping[str, Any],
    path_values: Mapping[str, str] | None = None,
    query: Mapping[str, Any] | None = None,
    body: Mapping[str, Any] | None = None,
    upload: MultipartUpload | None = None,
    extra_headers: Mapping[str, str] | None = None,
    sleep: Any = time.sleep,
) -> Any:
    """Exécute un appel : en-têtes, délai, retentatives, désérialisation, erreurs typées."""
    operation_id: str = descriptor["operationId"]
    url = build_url(base_url, descriptor, path_values or {}, query)
    replayable = is_replayable(descriptor, body)

    headers: dict[str, str] = dict(extra_headers or {})
    # Après l'étalement des en-têtes de l'appelant : ``Authorization`` n'est PAS surchargeable. Le
    # laisser l'être offrirait un moyen silencieux d'envoyer la requête d'un compte avec la
    # configuration d'un autre.
    headers["Authorization"] = f"Bearer {api_key}"
    headers["Accept"] = "application/json"
    headers["User-Agent"] = user_agent

    payload: bytes | None = None
    if upload is not None:
        payload, content_type = encode_multipart(upload)
        headers["Content-Type"] = content_type
    elif body is not None:
        payload = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        headers["Content-Type"] = "application/json"

    last_error: BaseException | None = None
    for attempt in range(max_retries + 1):
        request = HttpRequest(
            method=descriptor["method"], url=url, headers=headers, body=payload, timeout=timeout
        )
        status: int | None = None
        try:
            response = transport(request)
        except TimeoutError as cause:
            last_error = SenndoTimeoutError(timeout, operation_id)
            last_error.__cause__ = cause
        except OSError as cause:
            last_error = SenndoConnectionError(operation_id, cause)
        else:
            if 200 <= response.status < 300:
                if response.status == 204 or response.body == "":
                    return None
                return decode_json(response.body)
            status = response.status
            last_error = error_from_response(
                response.status,
                response.body,
                operation_id,
                response.headers.get("retry-after"),
            )

        if not replayable or not is_transient(status) or attempt == max_retries:
            raise last_error
        retry_after = (
            last_error.retry_after if isinstance(last_error, SenndoRateLimitError) else None
        )
        sleep(_backoff_seconds(attempt, retry_after))

    raise last_error if last_error is not None else RuntimeError("senndo : état inatteignable")


def env_base_url(default: str) -> str:
    """``SENNDO_BASE_URL`` surcharge la base — pour un bac à sable ou un miroir régional.

    Une valeur VIDE vaut absente : une variable d'environnement définie à la chaîne vide est le cas
    normal d'un ``.env`` rempli à moitié, et ``os.environ.get(x, default)`` rendrait alors ``""``,
    c'est-à-dire une base d'URL invalide au lieu du défaut.
    """
    value = os.environ.get("SENNDO_BASE_URL", "")
    return value if value != "" else default
