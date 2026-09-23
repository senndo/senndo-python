"""Vérification de la signature d'un webhook senndo.

Chaque livraison porte ``X-Senndo-Signature: t=<unix>,v1=<hex>``, où ``v1`` est le HMAC-SHA256 de
``f"{t}.{corps}"`` sous le secret ``whsec_…`` rendu à la création de l'endpoint. La signature est
recalculée à chaque tentative : une tolérance de quelques minutes sur ``t`` ne rejette jamais une
retentative légitime, et refuse un rejeu ancien.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from typing import Callable

_SIGNATURE_RE = re.compile(r"^t=(\d+),v1=([0-9a-f]{64})$")


def verify_webhook_signature(
    secret: str,
    header: str | None,
    raw_body: str | bytes,
    *,
    tolerance_seconds: int = 300,
    now: Callable[[], float] | None = None,
) -> bool:
    """``True`` si l'en-tête authentifie ``raw_body`` sous ``secret``, dans la tolérance.

    ``raw_body`` doit être le corps BRUT reçu, octet pour octet : un JSON re-sérialisé ne vérifie
    pas.
    """
    if not isinstance(header, str) or secret == "":
        return False
    match = _SIGNATURE_RE.match(header.strip())
    if match is None:
        return False
    timestamp = int(match.group(1))
    current = int((now or time.time)())
    if abs(current - timestamp) > tolerance_seconds:
        return False
    body = raw_body if isinstance(raw_body, bytes) else raw_body.encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"), str(timestamp).encode("ascii") + b"." + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, match.group(2))
