"""Les types d'EXÉCUTION du SDK — tout ce que le contrat ne décrit pas.

POURQUOI UN TRANSPORT INJECTABLE. Le paquet n'a aucune dépendance : son transport par défaut est
``urllib.request``, de la bibliothèque standard. Cela ne doit pas enfermer l'appelant. Un projet
déjà bâti sur ``httpx``, ``requests`` ou un client interne (proxy d'entreprise, mTLS, métriques)
passe le sien à la construction du client, et le SDK garde la validation, les erreurs typées et la
politique de retentative — la partie qu'un enrobage de ``urlopen`` ne donne pas.

C'est aussi ce qui rend le gate de retentative honnête : il compte les requêtes RÉELLEMENT parties
en substituant le transport, pas en observant la forme des appels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True)
class HttpRequest:
    """Une requête HTTP, réduite à ce que le SDK produit."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    #: Délai maximal, en secondes, pour CETTE tentative.
    timeout: float


@dataclass(frozen=True)
class HttpResponse:
    """Une réponse HTTP, réduite à ce que le SDK consomme.

    ``status`` porte le code même quand il vaut 4xx ou 5xx : un transport qui lèverait sur un 402
    priverait le SDK de l'enveloppe d'erreur, donc du code stable sur lequel l'appelant branche.
    """

    status: int
    headers: Mapping[str, str]
    body: str


class Transport(Protocol):
    """Toute implémentation capable d'exécuter une requête HTTP.

    Elle DOIT lever ``TimeoutError`` sur dépassement de délai et ``OSError`` sur échec de
    transport ; le SDK les traduit en ``SenndoTimeoutError`` et ``SenndoConnectionError``. Elle ne
    doit JAMAIS lever sur un statut d'erreur HTTP.
    """

    # Le paramètre est POSITIONNEL SEUL (`/`). Sans la barre, un `Protocol` à `__call__` exige que
    # l'implémentation nomme son paramètre `request` : une fonction écrite
    # `def mon_transport(requete: HttpRequest)` était refusée par mypy — un refus qui n'apprend
    # rien, sur du code parfaitement correct. C'est le gate du README qui l'a révélé, en typant
    # l'extrait « brancher votre propre client HTTP ».
    def __call__(self, request: HttpRequest, /) -> HttpResponse: ...


@dataclass(frozen=True)
class MultipartUpload:
    """Un fichier à téléverser sur ``POST /v1/wa-media``.

    LE CORPS MULTIPART EST CONSTRUIT PAR LE SDK. La bibliothèque standard n'offre pas d'encodeur
    ``multipart/form-data`` côté client — ``email.mime`` en produit un, au prix d'un
    ré-encodage complet du fichier en mémoire et d'un jeu de sauts de ligne qui n'est pas celui que
    HTTP attend. Quelques dizaines de lignes d'octets concaténés sont plus courtes et plus sûres.
    """

    #: Le contenu du fichier.
    file: bytes
    #: Le nom transmis au serveur — il détermine l'extension vérifiée contre le type MIME réel.
    file_name: str
    #: Le type MIME. À défaut, ``application/octet-stream``, que le serveur refuse en 415.
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class RequestOptions:
    """Ce qui peut être surchargé POUR UN APPEL, sans reconstruire le client."""

    #: Délai maximal en secondes. À défaut, celui du client.
    timeout: float | None = None
    #: Nombre maximal de retentatives. À défaut, celui du client. ``0`` les désactive.
    max_retries: int | None = None
    #: En-têtes supplémentaires. ``Authorization`` n'est PAS surchargeable.
    headers: Mapping[str, str] = field(default_factory=dict)
