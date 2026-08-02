"""``SenndoClient`` — une méthode par opération du contrat.

POURQUOI UNE SURFACE PLATE, ET PAS ``client.messages.send()``. Le regroupement se lit mieux dans une
brochure ; la surface plate se VÉRIFIE. Le test de conformité affirme, pour chaque opération du
contrat, que ``callable(getattr(client, descripteur["methodName"]))`` — et ``methodName`` est
DÉRIVÉ du contrat par le générateur, pas maintenu à la main. Aucune table de correspondance à
tenir, donc aucune à oublier le jour où une opération est ajoutée.

POURQUOI DES NOMS EN SNAKE_CASE alors que le contrat les nomme en camelCase. Un SDK Python qui
exposerait ``sendMessage`` ferait porter au consommateur le confort de l'outil. La conversion est
mécanique et publiée dans la table générée, donc vérifiable ; l'inconfort, lui, aurait été
permanent.

CE QUE CE FICHIER AJOUTE AU CONTRAT, et qu'aucun générateur ne donne :
  - une validation LOCALE avant l'appel — un champ obligatoire absent coûte zéro aller-retour, et
    sur un canal facturé, zéro risque de débit ;
  - la règle que ``required`` ne sait pas exprimer (D-122) : un envoi porte du contenu par au moins
    un de ``text``, ``media``, ``template`` ;
  - le rejet local des préfixes d'idempotence réservés, que le serveur refuse en 400 ;
  - la clé API MASQUÉE dans toute représentation de l'objet.
"""

from __future__ import annotations

from typing import Any, Mapping, cast

from ._generated.contract import (
    OPERATIONS,
    SENNDO_API_BASE_URL,
    CreateWebhookBody,
    CreateWebhookResponse,
    EstimateMessageBody,
    EstimateMessageResponse,
    GetBalanceQuery,
    GetBalanceResponse,
    GetMessageResponse,
    ListCurrenciesResponse,
    ListInboxMessagesQuery,
    ListInboxMessagesResponse,
    ListInboxThreadsQuery,
    ListInboxThreadsResponse,
    ListLedgerQuery,
    ListLedgerResponse,
    ListMediaQuery,
    ListMediaResponse,
    ListMessagesQuery,
    ListMessagesResponse,
    ListPricesResponse,
    ListSenderIdsResponse,
    ListWaCloudNumbersResponse,
    ListWaTemplatesResponse,
    ListWebhookDeliveriesQuery,
    ListWebhookDeliveriesResponse,
    ListWebhooksResponse,
    RevokeWebhookResponse,
    SendMessageBody,
    SendMessageResponse,
    UploadMediaResponse,
)
from ._http import env_base_url, mask_api_key, perform_request
from .errors import SenndoRequestError
from .types import MultipartUpload, RequestOptions, Transport

#: La version du paquet, vérifiée contre ``pyproject.toml`` par un test.
SDK_VERSION = "0.1.0"

#: Les préfixes d'idempotence que la plateforme se réserve (entrants, campagnes).
RESERVED_IDEMPOTENCY_PREFIXES = ("in:", "cmp:")

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2


class SenndoClient:
    """Le client HTTP de l'API senndo."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: Transport | None = None,
        user_agent: str | None = None,
    ) -> None:
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise SenndoRequestError(
                "senndo : api_key est requise. Créez une clé dans la console (« API » → "
                "« Clés »). Une clé sk_test_ simule la livraison sans déplacer d'argent."
            )
        if transport is None:
            from ._http import UrllibTransport

            transport = UrllibTransport()

        self._api_key = api_key
        self._base_url = base_url if base_url is not None else env_base_url(SENNDO_API_BASE_URL)
        self._timeout = timeout
        self._max_retries = max_retries
        self._transport = transport
        self._user_agent = (
            f"senndo-python/{SDK_VERSION}"
            if user_agent is None
            else f"senndo-python/{SDK_VERSION} {user_agent}"
        )

    @property
    def api_key_masked(self) -> str:
        """La clé API, MASQUÉE.

        Il n'existe aucun accesseur qui la rende en clair : un SDK qui expose sa clé la voit finir
        dans un log d'erreur, puis dans un agrégateur, puis hors du périmètre.
        """
        return mask_api_key(self._api_key)

    @property
    def base_url(self) -> str:
        """La base réellement utilisée par ce client."""
        return self._base_url

    def __repr__(self) -> str:
        """``repr()`` est le chemin par lequel un secret fuit vraiment.

        Un client posé dans un contexte d'exception, une trace Sentry, un ``print`` de débogage :
        chacun appelle ``repr``. La clé n'y apparaît jamais en clair.
        """
        return f"SenndoClient(base_url={self._base_url!r}, api_key={self.api_key_masked!r})"

    __str__ = __repr__

    # ── Envoi ────────────────────────────────────────────────────────────────────────────────

    def send_message(
        self, body: SendMessageBody, options: RequestOptions | None = None
    ) -> SendMessageResponse:
        """Envoie un message unitaire.

        ``idempotencyKey`` EST OBLIGATOIRE, et le SDK n'en fabrique pas à votre place — voir
        ``new_idempotency_key()``. Rejouer la même clé renvoie le message déjà créé avec
        ``replay: True``, sans jamais redébiter.
        """
        raw = cast(Mapping[str, Any], body)
        self._assert_required_body("sendMessage", raw)

        # La règle que ``required`` ne peut pas porter (D-122) : le serveur exempte ``text`` quand
        # le contenu vit dans ``media`` ou ``template``, mais un envoi sans AUCUN des trois n'a pas
        # de contenu et part en 400. L'attraper ici épargne l'aller-retour.
        if all(raw.get(field) is None for field in ("text", "media", "template")):
            raise SenndoRequestError(
                "senndo : un envoi doit porter du contenu — renseignez « text », ou « media », ou "
                "« template ». Le texte n'est facultatif que lorsque l'un des deux autres le "
                "remplace."
            )
        key = raw["idempotencyKey"]
        for prefix in RESERVED_IDEMPOTENCY_PREFIXES:
            if isinstance(key, str) and key.startswith(prefix):
                raise SenndoRequestError(
                    f"senndo : le préfixe « {prefix} » est réservé à la plateforme (entrants, "
                    "campagnes). Choisissez une clé d'idempotence dérivée de VOTRE domaine."
                )
        return cast(SendMessageResponse, self._call("sendMessage", options, body=raw))

    def estimate_message(
        self, body: EstimateMessageBody, options: RequestOptions | None = None
    ) -> EstimateMessageResponse:
        """Estime le coût et le découpage d'un envoi, sans rien envoyer ni débiter."""
        raw = cast(Mapping[str, Any], body)
        self._assert_required_body("estimateMessage", raw)
        return cast(EstimateMessageResponse, self._call("estimateMessage", options, body=raw))

    def get_message(
        self, message_id: str, options: RequestOptions | None = None
    ) -> GetMessageResponse:
        """Relit un message par son identifiant — c'est ici que se lit le VERDICT de livraison."""
        return cast(
            GetMessageResponse, self._call("getMessage", options, path_values={"id": message_id})
        )

    def list_messages(
        self, query: ListMessagesQuery | None = None, options: RequestOptions | None = None
    ) -> ListMessagesResponse:
        """Parcourt le journal des messages du compte."""
        return cast(ListMessagesResponse, self._call("listMessages", options, query=query))

    # ── Média ────────────────────────────────────────────────────────────────────────────────

    def upload_media(
        self, upload: MultipartUpload, options: RequestOptions | None = None
    ) -> UploadMediaResponse:
        """Téléverse une pièce jointe et renvoie la référence à reposer dans ``media.ref``."""
        if upload.file_name == "":
            raise SenndoRequestError(
                "senndo : file_name est requis — le serveur vérifie que le contenu correspond à "
                "l'extension."
            )
        return cast(UploadMediaResponse, self._call("uploadMedia", options, upload=upload))

    def list_media(
        self, query: ListMediaQuery | None = None, options: RequestOptions | None = None
    ) -> ListMediaResponse:
        """Liste les fichiers du compte, l'espace occupé et la facturation du stockage."""
        return cast(ListMediaResponse, self._call("listMedia", options, query=query))

    def delete_media(self, media_id: str, options: RequestOptions | None = None) -> None:
        """Supprime un fichier. Répond 409 tant qu'un message ou une campagne le référence."""
        self._call("deleteMedia", options, path_values={"id": media_id})

    # ── Compte : solde, tarifs, devises, émetteurs ───────────────────────────────────────────

    def get_balance(
        self, query: GetBalanceQuery | None = None, options: RequestOptions | None = None
    ) -> GetBalanceResponse:
        """Le solde du compte, converti dans une devise ARMÉE.

        Aucun repli sur l'USD n'est effectué par le SDK quand la conversion échoue : la route refuse
        précisément de commettre cette faute, et un SDK qui rattraperait le refus en rendant des
        dollars afficherait un montant faux dans une devise que l'utilisateur croit être la sienne.
        """
        return cast(GetBalanceResponse, self._call("getBalance", options, query=query))

    def list_currencies(self, options: RequestOptions | None = None) -> ListCurrenciesResponse:
        """Le catalogue des devises. ``billable`` distingue « convertible » de « encaissable »."""
        return cast(ListCurrenciesResponse, self._call("listCurrencies", options))

    def list_prices(self, options: RequestOptions | None = None) -> ListPricesResponse:
        """Les tarifs du compte.

        ``costs`` = ce que VOUS payez à votre fournisseur direct, ``prices`` = ce que VOUS facturez
        à vos comptes enfants. Aucun coût plateforme, aucun tarif d'un compte voisin n'entre dans
        cette réponse.
        """
        return cast(ListPricesResponse, self._call("listPrices", options))

    def list_sender_ids(self, options: RequestOptions | None = None) -> ListSenderIdsResponse:
        """Les Sender IDs du compte, avec leur statut de cycle de vie ET leur approbation PAR PAYS.

        Proposer un émetteur sans lire ``countries`` conduit à un envoi refusé sur une destination
        où il n'est pas approuvé.
        """
        return cast(ListSenderIdsResponse, self._call("listSenderIds", options))

    def list_ledger(
        self, query: ListLedgerQuery | None = None, options: RequestOptions | None = None
    ) -> ListLedgerResponse:
        """Le grand livre du compte.

        La dépense NETTE d'un message est ``billedAmountUsd − reversedAmountUsd`` : sommer le brut
        SURESTIME de tout ce qui a été contre-passé. Les montants sont des chaînes décimales —
        additionnez-les avec ``decimal.Decimal``, jamais avec ``float``.
        """
        return cast(ListLedgerResponse, self._call("listLedger", options, query=query))

    # ── Réception ────────────────────────────────────────────────────────────────────────────

    def list_inbox_threads(
        self, query: ListInboxThreadsQuery | None = None, options: RequestOptions | None = None
    ) -> ListInboxThreadsResponse:
        """Les conversations entrantes, la plus récente d'abord."""
        return cast(ListInboxThreadsResponse, self._call("listInboxThreads", options, query=query))

    def list_inbox_messages(
        self, query: ListInboxMessagesQuery, options: RequestOptions | None = None
    ) -> ListInboxMessagesResponse:
        """Les messages d'une conversation. ``channel`` et ``contact`` sont obligatoires."""
        raw = cast(Mapping[str, Any], query)
        self._assert_required_query("listInboxMessages", raw)
        return cast(
            ListInboxMessagesResponse, self._call("listInboxMessages", options, query=raw)
        )

    # ── WhatsApp ─────────────────────────────────────────────────────────────────────────────

    def list_wa_templates(self, options: RequestOptions | None = None) -> ListWaTemplatesResponse:
        """Les modèles WhatsApp du compte, dont ceux partagés par la plateforme."""
        return cast(ListWaTemplatesResponse, self._call("listWaTemplates", options))

    def list_wa_cloud_numbers(
        self, options: RequestOptions | None = None
    ) -> ListWaCloudNumbersResponse:
        """Les numéros WhatsApp Cloud rattachés au compte, et les émetteurs partagés disponibles."""
        return cast(ListWaCloudNumbersResponse, self._call("listWaCloudNumbers", options))

    # ── Webhooks ─────────────────────────────────────────────────────────────────────────────

    def list_webhooks(self, options: RequestOptions | None = None) -> ListWebhooksResponse:
        """Les endpoints de webhook du compte, révoqués compris."""
        return cast(ListWebhooksResponse, self._call("listWebhooks", options))

    def create_webhook(
        self, body: CreateWebhookBody, options: RequestOptions | None = None
    ) -> CreateWebhookResponse:
        """Crée un endpoint de webhook et renvoie son SECRET — la seule fois où il est lisible.

        CET APPEL N'EST JAMAIS RETENTÉ AUTOMATIQUEMENT. Il crée une ressource à chaque exécution :
        une retentative aveugle produirait deux endpoints, donc DEUX livraisons pour chaque
        événement. En cas d'échec de transport, listez avant de recréer.
        """
        raw = cast(Mapping[str, Any], body)
        self._assert_required_body("createWebhook", raw)
        return cast(CreateWebhookResponse, self._call("createWebhook", options, body=raw))

    def revoke_webhook(
        self, webhook_id: str, options: RequestOptions | None = None
    ) -> RevokeWebhookResponse:
        """Révoque un endpoint. Les livraisons cessent ; l'historique reste lisible."""
        return cast(
            RevokeWebhookResponse,
            self._call("revokeWebhook", options, path_values={"id": webhook_id}),
        )

    def list_webhook_deliveries(
        self,
        query: ListWebhookDeliveriesQuery | None = None,
        options: RequestOptions | None = None,
    ) -> ListWebhookDeliveriesResponse:
        """L'historique des livraisons de webhook, avec les compteurs d'état."""
        return cast(
            ListWebhookDeliveriesResponse,
            self._call("listWebhookDeliveries", options, query=query),
        )

    # ── Interne ──────────────────────────────────────────────────────────────────────────────

    def _call(
        self,
        operation_id: str,
        options: RequestOptions | None,
        *,
        path_values: Mapping[str, str] | None = None,
        query: Any = None,
        body: Mapping[str, Any] | None = None,
        upload: MultipartUpload | None = None,
    ) -> Any:
        opts = options if options is not None else RequestOptions()
        return perform_request(
            transport=self._transport,
            api_key=self._api_key,
            base_url=self._base_url,
            user_agent=self._user_agent,
            timeout=opts.timeout if opts.timeout is not None else self._timeout,
            max_retries=(
                opts.max_retries if opts.max_retries is not None else self._max_retries
            ),
            descriptor=OPERATIONS[operation_id],
            path_values=path_values,
            query=cast("Mapping[str, Any] | None", query),
            body=body,
            upload=upload,
            extra_headers=opts.headers,
        )

    def _assert_required_body(self, operation_id: str, body: Mapping[str, Any]) -> None:
        """Vérifie les champs obligatoires DEPUIS LE DESCRIPTEUR, jamais depuis une liste recopiée.

        Un champ ajouté au contrat devient obligatoire ici à la régénération, sans édition.
        """
        for field in OPERATIONS[operation_id]["requiredBodyFields"]:
            value = body.get(field)
            if value is None or value == "":
                raise SenndoRequestError(
                    f"senndo : {operation_id} — le champ obligatoire « {field} » est absent."
                )

    def _assert_required_query(self, operation_id: str, query: Mapping[str, Any]) -> None:
        for name in OPERATIONS[operation_id]["requiredQueryParams"]:
            value = query.get(name)
            if value is None or value == "":
                raise SenndoRequestError(
                    f"senndo : {operation_id} — le paramètre obligatoire « {name} » est absent."
                )
