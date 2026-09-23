"""FICHIER GÉNÉRÉ — NE PAS ÉDITER À LA MAIN.

Source : `OPENAPI_OPERATIONS` du monorepo senndo, document version 1.0.0.
Régénérer : `node packages/sdk-codegen/bin/generate.mjs python`.

Toute édition manuelle est effacée à la prochaine génération, et le test de fraîcheur la signale
en ROUGE avant même qu'elle atteigne une revue.

LES MONTANTS SONT DES CHAÎNES DÉCIMALES, jamais des flottants. Un `NUMERIC(18,6)` passé par un
double IEEE-754 perd des unités sur les longues traînes, et un prix unitaire sub-centime arrondi à
deux décimales devient zéro. Additionnez-les avec `decimal.Decimal`, jamais avec `float`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, NotRequired, Required, TypeAlias, TypedDict

from ..types import MultipartUpload

__all__ = ["SENNDO_API_BASE_URL", "SENNDO_CONTRACT_VERSION", "OPERATIONS", "OPERATION_IDS"]

#: Base publique de production. Surchargeable à la construction du client.
SENNDO_API_BASE_URL = "https://api.senndo.com"

#: Version du document OpenAPI dont ce fichier est dérivé.
SENNDO_CONTRACT_VERSION = "1.0.0"

Channel = Literal["sms", "whatsapp_cloud", "whatsapp_baileys", "email", "voice", "whatsapp_twilio"]

MessageStatus = Literal["pending", "dispatching", "queued", "sent", "delivered", "read", "failed", "unknown"]

# Raison NORMALISÉE d'un échec, propre à senndo et indépendante de l'opérateur.
#
# LE TYPE EST `str`, ET C'EST DÉLIBÉRÉ. senndo s'engage à AJOUTER des valeurs, jamais à en
# retirer : un `Literal[…]` fermé ferait échouer le typecheck de tout client au prochain ajout,
# et une validation fermée à l'exécution ferait LEVER le SDK sur une réponse parfaitement valide.
# Testez l'appartenance avec `KNOWN_FAILURE_CODES` quand vous devez distinguer « code connu » de
# « code plus récent que votre version du SDK ».
FailureCode = str

#: Les valeurs de `FailureCode` connues de CETTE version du SDK.
KNOWN_FAILURE_CODES: tuple[str, ...] = (
    "RECIPIENT_NOT_REACHABLE",
    "RECIPIENT_OPTED_OUT",
    "WHATSAPP_WINDOW_CLOSED",
    "TEMPLATE_INVALID",
    "SENDER_NOT_AUTHORIZED",
    "MESSAGE_BLOCKED",
    "UNSUPPORTED_CONTENT",
    "MEDIA_ERROR",
    "RATE_LIMITED",
    "NO_ANSWER",
    "BUSY",
    "CALL_CANCELED",
    "BILLING_REFUSED",
    "PROVIDER_REFUSED",
)

# Code pays ISO 3166-1 alpha-3, en majuscules (« CIV », « FRA », « SEN ») — le format du
# moteur de routage. Un code que le catalogue ne connaît pas est REFUSÉ, jamais ignoré : il ne
# pourrait matcher aucune règle, et l’appel retomberait en silence sur la route par défaut, à
# un prix que vous n’avez pas demandé.
CountryIso3: TypeAlias = str

# Code pays ISO 3166-1 alpha-2, en majuscules (« CI », « FR », « SN ») — le format des
# approbations d’émetteur. À ne pas confondre avec l’alpha-3 attendu par les champs de
# routage.
CountryAlpha2: TypeAlias = str

SendMessageBodyMedia = TypedDict(
    "SendMessageBodyMedia",
    {
        # Référence opaque rendue par POST /v1/wa-media.
        "ref": NotRequired[str],
    },
)

SendMessageBodyTemplate = TypedDict(
    "SendMessageBodyTemplate",
    {
        # Nom du modèle approuvé, tel qu’il s’affiche dans la console (par exemple
        # official_otp_code_template). Exclusif avec id. Un nom introuvable, ou ambigu après
        # application de la précédence, est refusé avant tout débit.
        "name": NotRequired[str],
        # Langue du modèle (fr, en, en_US…), à préciser seulement quand le nom existe en
        # plusieurs langues — le refus TEMPLATE_LANGUAGE_REQUIRED énumère alors celles qui
        # existent. Ne se combine qu’avec name.
        "language": NotRequired[str],
        # Identifiant du modèle approuvé (UUID). Exclusif avec name.
        "id": NotRequired[str],
        # Valeurs des variables positionnelles du corps, dans l’ordre. Défaut : [].
        "variables": NotRequired[list[str]],
        # Valeur de la variable d’en-tête texte, si le modèle en déclare une.
        "headerVariable": NotRequired[str],
        # Valeur du bouton URL dynamique ({{1}} dans l’URL approuvée), si le modèle en porte
        # un. Requise dans ce cas, refusée sinon.
        "urlButtonVariable": NotRequired[str],
    },
)

SendMessageBodyContent = TypedDict(
    "SendMessageBodyContent",
    {
        # Identifiant opaque du modèle approuvé auprès du partenaire d’acheminement (préfixe
        # HX, 34 caractères).
        "sid": NotRequired[str],
        # Variables du modèle, par nom ("1", "2", … pour les positionnelles), valeurs en
        # chaînes. Défaut : {}.
        "variables": NotRequired[dict[str, Any]],
    },
)

SendMessageBody = TypedDict(
    "SendMessageBody",
    {
        # Canal d’envoi.
        "channel": Required[Channel],
        # Destinataire — numéro E.164 pour sms, voice et whatsapp ; adresse pour email.
        "to": Required[str],
        # Contenu du message — ou légende lorsqu’une pièce jointe est fournie. Requis, SAUF si
        # media OU template est présent : une image sans légende est un envoi valide, et le
        # corps d’un modèle EST son contenu (le texte d’un envoi de modèle est de toute façon
        # remplacé par les composants approuvés). Dans les deux cas le message est facturé une
        # unité, comme tout porteur de contenu.
        "text": NotRequired[str],
        # Pièce jointe, sur les canaux whatsapp_cloud et whatsapp_baileys uniquement. Sans
        # modèle, elle constitue le message ; avec un modèle à en-tête média, elle remplit cet
        # en-tête. La référence provient de POST /v1/wa-media et doit appartenir au compte
        # appelant, sinon 404.
        "media": NotRequired[SendMessageBodyMedia],
        # Modèle WhatsApp managé, REQUIS sur le canal whatsapp_cloud hors fenêtre de 24 h :
        # WhatsApp n’accepte un texte libre que si le destinataire vous a écrit dans les 24
        # heures. Désignez-le par name (+ language si le nom existe en plusieurs langues) ou
        # par id. L’appartenance du modèle au compte et son statut « approuvé » sont vérifiés
        # avant tout débit. Les variables sont positionnelles ; un modèle à en-tête média
        # prend sa pièce jointe via le champ media.
        "template": NotRequired[SendMessageBodyTemplate],
        # Modèle hébergé, REQUIS sur le canal whatsapp_twilio (et refusé ailleurs) : ce canal
        # n’envoie que des modèles approuvés auprès du partenaire d’acheminement — un texte
        # libre y est refusé AVANT tout débit (CONTENT_REQUIRED). Collez l’identifiant opaque
        # du modèle (préfixe HX) et ses variables nommées. Un identifiant que le partenaire ne
        # connaît pas est refusé avant tout débit (CONTENT_NOT_FOUND).
        "content": NotRequired[SendMessageBodyContent],
        # Clé d’idempotence fournie par le client. Les préfixes in: et cmp: sont réservés à la
        # plateforme et refusés en 400.
        "idempotencyKey": Required[str],
        # Expéditeur affiché. Pour email, doit être un Sender ID e-mail vérifié.
        "senderId": NotRequired[str],
        # Override du pays de routage, en ISO 3166-1 alpha-3 (« BRA », « JPN »). Absent, le
        # pays est DÉRIVÉ du destinataire. Un code inconnu du catalogue est refusé en 400
        # (COUNTRY_INVALID) avant tout débit : il ne pourrait matcher aucune règle de routage,
        # et l’envoi partirait — facturé — sur la route par défaut.
        "country": NotRequired[CountryIso3],
        # Catégorie du message.
        "category": NotRequired[Literal["marketing", "utility", "authentication", "service"]],
        # Type de SMS (canal "sms" uniquement). "premium" route par le réseau international à
        # haute délivrabilité et se facture au tarif premium ; absent = "standard".
        "tier": NotRequired[Literal["standard", "premium"]],
        # Convertit le texte en GSM-7 avant segmentation, envoi et facturation (canal "sms"
        # uniquement). Un SEUL caractère hors de l’alphabet GSM 03.38 fait passer le message
        # entier en UCS-2 et divise la capacité par plus de deux (160 → 70 caractères) :
        # l’apostrophe typographique ’ (U+2019), que la plupart des éditeurs substituent
        # automatiquement, suffit à tripler la facture. Avec ce drapeau, les apostrophes et
        # tirets typographiques sont remplacés par leur équivalent ASCII, les lettres
        # accentuées hors alphabet (ê â î ô û ç œ) perdent leur accent, et les emoji sont
        # RETIRÉS — le destinataire ne verra donc pas exactement ce que vous avez soumis.
        # Absent = le texte est envoyé tel quel. Vérifiez le résultat avec POST
        # /v1/messages/estimate avant d’envoyer.
        "convertGsm7": NotRequired[bool],
        # Résout les champs {{clé}} du texte contre le catalogue de champs du compte (GET
        # /v1/merge-fields) et le contact correspondant à la destination, AVANT toute
        # facturation. Le message envoyé, segmenté et facturé est le texte SUBSTITUÉ — pas le
        # gabarit. Un champ absent du catalogue rend 400 UNKNOWN_MERGE_FIELD ; un champ sans
        # valeur pour ce destinataire rend 422 MISSING_MERGE_FIELD et RIEN n’est facturé
        # (mieux vaut ne pas envoyer qu’envoyer « Bonjour , »). Absent = le texte part tel
        # quel, accolades comprises : un corps qui contient légitimement {{ }} n’est jamais
        # modifié sans ce drapeau. Incompatible avec template (les variables de modèle {{1}},
        # {{2}}… sont un espace de noms distinct). Devisez sous le même drapeau avec POST
        # /v1/messages/estimate.
        "personalize": NotRequired[bool],
        # Objet — requis pour channel: "email".
        "subject": NotRequired[str],
    },
)

SendMessageResponse = TypedDict(
    "SendMessageResponse",
    {
        # Identifiant du message créé.
        "id": Required[str],
        # Statut à l’acceptation. Ce n’est PAS un verdict de livraison : celui-ci arrive par
        # webhook ou par relecture de GET /v1/messages/{id}.
        "status": Required[MessageStatus],
        # Canal retenu.
        "channel": Required[Channel],
        # Destinataire tel qu’accepté.
        "to": Required[str],
        # Expéditeur affiché, résolu.
        "senderId": Required[str | None],
        # Règle de routage retenue. Identifiant opaque, utile au support ; il ne nomme aucun
        # fournisseur.
        "routeRuleId": Required[str | None],
        # Montant débité en USD, chaîne décimale. null avec une clé sk_test_ (aucun mouvement
        # d’argent).
        "billedAmountUsd": Required[str | None],
        # Devise de facturation.
        "billedCurrency": Required[str | None],
        # Crédit RENDU par un contre-passage déclenché pendant cet appel, en USD, chaîne
        # décimale. null si le message n’a pas été contre-passé. billedAmountUsd garde le
        # montant BRUT débité : la dépense NETTE est billedAmountUsd − reversedAmountUsd.
        "reversedAmountUsd": Required[str | None],
        # Raison de l’échec, quand cet appel s’est conclu par status: "failed". null sur tout
        # autre statut — un envoi accepté n’a pas de raison d’échec, et un verdict de
        # livraison ultérieur se lit par webhook ou par GET /v1/messages/{id}. Mêmes valeurs,
        # même sens et mêmes garanties de compatibilité que le champ du journal : c’est le
        # code stable senndo, indépendant de l’opérateur, sur lequel brancher votre logique.
        "failureCode": Required[FailureCode | None],
        # true quand la clé d’idempotence avait DÉJÀ produit ce message : aucun nouveau débit
        # n’a eu lieu, et le corps décrit l’envoi d’origine.
        "replay": Required[bool],
    },
)

GetMessageResponse = TypedDict(
    "GetMessageResponse",
    {
        # Identifiant du message.
        "id": Required[str],
        # Horodatage de création.
        "createdAt": Required[str],
        # Canal utilisé.
        "channel": Required[Channel],
        # Destinataire.
        "toAddr": Required[str | None],
        # Expéditeur affiché.
        "senderId": Required[str | None],
        # Statut courant.
        "status": Required[MessageStatus],
        # Montant facturé en USD, chaîne décimale. null si non facturé (clé de test).
        "billedAmountUsd": Required[str | None],
        # Crédit RENDU par un contre-passage, en USD, chaîne décimale. null si le message n’a
        # pas été contre-passé. billedAmountUsd garde le montant BRUT débité (un fait qui
        # s’est produit, inscrit au grand livre) : la dépense NETTE d’un message est
        # billedAmountUsd − reversedAmountUsd. Sommer billedAmountUsd seul SURESTIME la
        # dépense de tout ce qui a été remboursé.
        "reversedAmountUsd": Required[str | None],
        # Raison de l’échec. Renseignée sur TOUT message status: "failed", et null sur tout
        # autre statut. Code stable propre à senndo, indépendant de l’opérateur : branchez
        # votre logique dessus. PROVIDER_REFUSED est le fourre-tout explicite — le canal a
        # refusé sans raison normalisable.
        "failureCode": Required[FailureCode | None],
        # true quand l’envoi a été FACTURÉ et qu’aucun verdict de livraison n’est jamais
        # arrivé du fournisseur. À ne pas confondre avec status: "sent", qui dit seulement que
        # l’opérateur a pris le message en charge : un message peut rester "sent"
        # indéfiniment, et le statut seul ne distingue pas un envoi de deux secondes d’un
        # envoi de quatre semaines resté sans preuve. false dès qu’un verdict existe — un
        # refus est un verdict — et false sur un envoi non facturé.
        "verdictPending": Required[bool],
        # Devise de facturation.
        "billedCurrency": Required[str | None],
        # Catégorie déclarée à l’envoi.
        "category": Required[str | None],
        # Corps du message tel qu’envoyé (après translittération éventuelle).
        "body": Required[str],
        # Origine de l’envoi : console, appel par clé API, ou test du parcours de démarrage.
        "source": Required[Literal["console", "api", "api_test"]],
    },
)

ListMessagesQuery = TypedDict(
    "ListMessagesQuery",
    {
        # Numéro de page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page, 50 par défaut, 100 au maximum.
        "pageSize": NotRequired[int],
        # Colonne de tri.
        "sort": NotRequired[Literal["date", "channel", "status", "amount"]],
        # Sens du tri.
        "dir": NotRequired[Literal["asc", "desc"]],
        # Filtre par canal.
        "channel": NotRequired[Channel],
        # Filtre par statut.
        "status": NotRequired[MessageStatus],
        # Début de plage, YYYY-MM-DD inclus.
        "from": NotRequired[str],
        # Fin de plage, YYYY-MM-DD inclus (la journée entière).
        "to": NotRequired[str],
        # via=api : ne garder que les envois partis par la surface API (clé sk_… ou tests du
        # parcours de démarrage).
        "via": NotRequired[Literal["api"]],
    },
)

ListMessagesResponseRowsItem = TypedDict(
    "ListMessagesResponseRowsItem",
    {
        # Identifiant du message.
        "id": Required[str],
        # Horodatage de création.
        "createdAt": Required[str],
        # Canal utilisé.
        "channel": Required[Channel],
        # Destinataire.
        "toAddr": Required[str | None],
        # Expéditeur affiché.
        "senderId": Required[str | None],
        # Statut courant.
        "status": Required[MessageStatus],
        # Montant facturé en USD, chaîne décimale. null si non facturé (clé de test).
        "billedAmountUsd": Required[str | None],
        # Crédit RENDU par un contre-passage, en USD, chaîne décimale. null si le message n’a
        # pas été contre-passé. billedAmountUsd garde le montant BRUT débité (un fait qui
        # s’est produit, inscrit au grand livre) : la dépense NETTE d’un message est
        # billedAmountUsd − reversedAmountUsd. Sommer billedAmountUsd seul SURESTIME la
        # dépense de tout ce qui a été remboursé.
        "reversedAmountUsd": Required[str | None],
        # Raison de l’échec. Renseignée sur TOUT message status: "failed", et null sur tout
        # autre statut. Code stable propre à senndo, indépendant de l’opérateur : branchez
        # votre logique dessus. PROVIDER_REFUSED est le fourre-tout explicite — le canal a
        # refusé sans raison normalisable.
        "failureCode": Required[FailureCode | None],
        # true quand l’envoi a été FACTURÉ et qu’aucun verdict de livraison n’est jamais
        # arrivé du fournisseur. À ne pas confondre avec status: "sent", qui dit seulement que
        # l’opérateur a pris le message en charge : un message peut rester "sent"
        # indéfiniment, et le statut seul ne distingue pas un envoi de deux secondes d’un
        # envoi de quatre semaines resté sans preuve. false dès qu’un verdict existe — un
        # refus est un verdict — et false sur un envoi non facturé.
        "verdictPending": Required[bool],
        # Devise de facturation.
        "billedCurrency": Required[str | None],
        # Catégorie déclarée à l’envoi.
        "category": Required[str | None],
        # Corps du message tel qu’envoyé (après translittération éventuelle).
        "body": Required[str],
        # Origine de l’envoi : console, appel par clé API, ou test du parcours de démarrage.
        "source": Required[Literal["console", "api", "api_test"]],
    },
)

ListMessagesResponse = TypedDict(
    "ListMessagesResponse",
    {
        # Page courante.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        # Total de lignes filtrées.
        "total": Required[int],
        # Périmètre RÉELLEMENT lu. Vaut toujours account pour un appelant à clé API — network
        # est réservé aux sessions console d’opérateur.
        "scope": Required[Literal["account", "network"]],
        # Les messages.
        "rows": Required[list[ListMessagesResponseRowsItem]],
    },
)

UploadMediaResponse = TypedDict(
    "UploadMediaResponse",
    {
        # Référence OPAQUE à reposer dans media.ref d’un envoi.
        "ref": Required[str],
        # Nature du fichier, déduite du type MIME.
        "kind": Required[Literal["image", "video", "audio", "document"]],
        # Nom de fichier reçu.
        "fileName": Required[str],
        # Type MIME validé.
        "mime": Required[str],
        # Taille en octets.
        "sizeBytes": Required[int],
    },
)

ListMediaQuery = TypedDict(
    "ListMediaQuery",
    {
        # Page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page, 500 par défaut, 500 au maximum.
        "pageSize": NotRequired[int],
    },
)

ListMediaResponseMediaItem = TypedDict(
    "ListMediaResponseMediaItem",
    {
        # Référence opaque.
        "ref": Required[str],
        # Nature du fichier.
        "kind": Required[Literal["image", "video", "audio", "document"]],
        # Type MIME.
        "mime": Required[str],
        # Nom de fichier.
        "fileName": Required[str],
        # Taille en octets.
        "sizeBytes": Required[int],
        # Téléversé le.
        "createdAt": Required[str],
        # true si un message ou une campagne référence encore ce fichier — sa suppression
        # répond alors 409.
        "inUse": Required[bool],
        # URL d’aperçu signée et TEMPORAIRE, sur les images uniquement. null quand l’aperçu
        # n’a pas pu être signé — une liste ne tombe jamais pour un aperçu.
        "previewUrl": Required[str | None],
    },
)

ListMediaResponseUsage = TypedDict(
    "ListMediaResponseUsage",
    {
        # Octets stockés.
        "usedBytes": Required[int],
        # Quota en octets.
        "quotaBytes": Required[int],
    },
)

ListMediaResponseBillingCycle = TypedDict(
    "ListMediaResponseBillingCycle",
    {
        # Période, AAAA-MM.
        "period": Required[str],
        # État du cycle.
        "status": Required[str],
        # Octets mesurés.
        "measuredBytes": Required[int],
        # Tranches facturées.
        "tranches": Required[int],
        # Montant du cycle en USD, chaîne décimale.
        "amountUsd": Required[str],
        # Dernière mesure.
        "updatedAt": Required[str | None],
    },
)

ListMediaResponseBilling = TypedDict(
    "ListMediaResponseBilling",
    {
        # Prix par Gio en USD, chaîne décimale. null quand aucun barème n’est publié —
        # l’afficher deviné serait un prix inventé.
        "pricePerGibUsd": Required[str | None],
        # Début de la période suivante (UTC).
        "nextPeriodStart": Required[str],
        # Cycle de facturation en cours. null tant qu’aucun cycle n’a été mesuré.
        "cycle": Required[ListMediaResponseBillingCycle | None],
    },
)

ListMediaResponse = TypedDict(
    "ListMediaResponse",
    {
        # Les fichiers du compte.
        "media": Required[list[ListMediaResponseMediaItem]],
        # Page courante.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        # Total de fichiers.
        "total": Required[int],
        # Usage du compte ENTIER, jamais de la page.
        "usage": Required[ListMediaResponseUsage],
        # Facturation du stockage, scopée à la relation parent → compte : jamais un coût
        # plateforme, jamais le prix d’un autre compte.
        "billing": Required[ListMediaResponseBilling],
    },
)

ListPricesResponseCostsItem = TypedDict(
    "ListPricesResponseCostsItem",
    {
        # Canal.
        "channel": Required[str],
        # Groupe de destination.
        "destGroup": Required[str],
        # Prix unitaire en USD, chaîne décimale.
        "priceUsd": Required[str],
    },
)

ListPricesResponsePricesItem = TypedDict(
    "ListPricesResponsePricesItem",
    {
        # Canal.
        "channel": Required[str],
        # Groupe de destination.
        "destGroup": Required[str],
        # Prix unitaire en USD, chaîne décimale.
        "priceUsd": Required[str],
        # Compte enfant visé par une dérogation. null = le tarif par défaut appliqué à tous
        # vos enfants.
        "buyerAccountId": Required[str | None],
        # Régime de la ligne. false = tarif ordinaire, l’acheminement est payé par la
        # plateforme. true = transport apporté, le compte facturé paie son transporteur en
        # direct et ne vous achète que la plateforme. LES DEUX PEUVENT COEXISTER sur le même
        # canal et le même groupe : sans ce champ, deux lignes de votre grille seraient
        # indiscernables, et renvoyer l’une à PUT /v1/prices réécrirait l’autre.
        "byok": Required[bool],
    },
)

ListPricesResponse = TypedDict(
    "ListPricesResponse",
    {
        # Le compte appelant.
        "accountId": Required[str],
        # CE QUE VOUS PAYEZ : le prix que votre compte parent vous facture, par canal et
        # groupe de destination. Ce n’est PAS un coût fournisseur — la surface publique n’en
        # expose aucun.
        "costs": Required[list[ListPricesResponseCostsItem]],
        # CE QUE VOUS FACTUREZ : votre propre price book, celui que vous appliquez à vos
        # comptes enfants. Vide si vous n’en avez aucun.
        "prices": Required[list[ListPricesResponsePricesItem]],
    },
)

GetBalanceQuery = TypedDict(
    "GetBalanceQuery",
    {
        # Devise de restitution (ISO 4217). Défaut USD. Les valeurs acceptées sont celles de
        # GET /v1/currencies.
        "currency": NotRequired[str],
    },
)

GetBalanceResponse = TypedDict(
    "GetBalanceResponse",
    {
        # Compte.
        "accountId": Required[str],
        # Solde canonique en USD, chaîne décimale.
        "balanceUsd": Required[str],
        # Devise de restitution.
        "currency": Required[str],
        # Taux administré : 1 USD = unitsPerUsd unités de currency.
        "unitsPerUsd": Required[str],
        # Solde converti, arrondi à 6 décimales — la précision de la plateforme. Arrondir à 2
        # pour l’affichage vous appartient ; ne le faites JAMAIS sur un coût unitaire, qui est
        # sub-centime.
        "balance": Required[str],
        # true = devise encaissée par une passerelle de recharge. false = affichage uniquement
        # : ne proposez pas de paiement dans cette devise.
        "billable": Required[bool],
        # Profondeur de découvert autorisée, USD, chaîne décimale POSITIVE. Le solde peut
        # descendre jusqu’à -overdraftFloorUsd avant qu’un envoi soit refusé. 0.000000 = aucun
        # découvert.
        "overdraftFloorUsd": Required[str],
        # overdraftFloorUsd converti dans currency, arrondi à 6 décimales.
        "overdraftFloor": Required[str],
        # Crédit réellement envoyable, APRÈS réserve en vol et plancher de découvert, jamais
        # négatif. C’est ce chiffre qui répond à « ai-je encore de quoi envoyer ? », et c’est
        # exactement le montant qu’un envoi accepte : balanceUsd seul sous-estime le crédit du
        # plancher entier, peut être négatif, et ignore les blocs de réservation en cours.
        "spendableUsd": Required[str],
    },
)

ListCurrenciesResponseCurrenciesItem = TypedDict(
    "ListCurrenciesResponseCurrenciesItem",
    {
        # Code ISO 4217.
        "currency": Required[str],
        # Taux administré.
        "unitsPerUsd": Required[str],
        # Devise encaissée par une passerelle de recharge.
        "billable": Required[bool],
    },
)

ListCurrenciesResponse = TypedDict(
    "ListCurrenciesResponse",
    {
        "currencies": Required[list[ListCurrenciesResponseCurrenciesItem]],
    },
)

ListSenderIdsResponseSenderIdsItemVerification = TypedDict(
    "ListSenderIdsResponseSenderIdsItemVerification",
    {
        # État de la vérification de l’adresse.
        "status": Required[Literal["pending", "verified", "failed"]],
        # Horodatage ISO 8601 du passage à verified, sinon null.
        "confirmedAt": Required[str | None],
    },
)

ListSenderIdsResponseSenderIdsItemCountriesItem = TypedDict(
    "ListSenderIdsResponseSenderIdsItemCountriesItem",
    {
        # Pays, en ISO 3166-1 alpha-2 (« CI », « FR »). Ce champ N’EST PAS dans le même
        # système que le `country` des envois et des devis, qui est en alpha-3.
        "country": Required[CountryAlpha2],
        # Statut dans ce pays.
        "status": Required[Literal["approved", "pending", "rejected"]],
    },
)

ListSenderIdsResponseSenderIdsItem = TypedDict(
    "ListSenderIdsResponseSenderIdsItem",
    {
        # Identifiant.
        "id": Required[str],
        # Compte propriétaire, ou null pour un expéditeur partagé de la plateforme. Une clé
        # API ne voit jamais que ses propres dédiés et les partagés : cette valeur ne désigne
        # donc jamais un tiers.
        "ownerAccountId": Required[str | None],
        # Nom du compte propriétaire ; null pour un partagé.
        "ownerName": Required[str | None],
        # L’expéditeur tel qu’il s’envoie (à passer en senderId sur POST /v1/messages).
        "value": Required[str],
        # Canal concerné.
        "channel": Required[str],
        # true = expéditeur partagé de la plateforme, utilisable sans dossier.
        "shared": Required[bool],
        # Cycle de vie. Seul active permet d’envoyer.
        "lifecycleStatus": Required[Literal["active", "suspended", "archived"]],
        # Motif de la suspension en cours ; null hors suspension. À afficher à vos
        # utilisateurs : sans lui, leurs envois échouent sans explication.
        "suspensionReason": Required[str | None],
        # Horodatage ISO 8601 de la suspension en cours, sinon null.
        "suspendedAt": Required[str | None],
        # Horodatage ISO 8601 de l’archivage, sinon null.
        "archivedAt": Required[str | None],
        # Horodatage ISO 8601 de création.
        "createdAt": Required[str],
        # Vérification de l’adresse, canal e-mail UNIQUEMENT ; null sur tout autre canal. Un
        # expéditeur e-mail dont le statut n’est pas verified ne délivre pas.
        "verification": Required[ListSenderIdsResponseSenderIdsItemVerification | None],
        # Approbation par pays. Une destination absente de cette liste n’est pas approuvée.
        "countries": Required[list[ListSenderIdsResponseSenderIdsItemCountriesItem]],
    },
)

ListSenderIdsResponse = TypedDict(
    "ListSenderIdsResponse",
    {
        # Réservé à la console : true pour une session d’opérateur plateforme, qui voit alors
        # la file de revue. TOUJOURS false pour une clé API — le périmètre élargi est attaché
        # à la SESSION, jamais au compte.
        "canReview": Required[bool],
        "senderIds": Required[list[ListSenderIdsResponseSenderIdsItem]],
    },
)

EstimateMessageBody = TypedDict(
    "EstimateMessageBody",
    {
        # Canal.
        "channel": Required[Channel],
        # Contenu à estimer.
        "text": Required[str],
        # Nombre de destinataires.
        "recipients": Required[int],
        # Expéditeur envisagé — il participe à la résolution de la route.
        "senderId": NotRequired[str | None],
        # Destination en ISO 3166-1 alpha-3 (« MEX », « IDN ») — le MÊME système que le
        # `country` de l’envoi, parce que c’est la même cascade de routage qui résout les
        # deux. Le devis résout au niveau PAYS. Un code inconnu du catalogue est refusé en 400
        # (COUNTRY_INVALID) : il ne pourrait matcher aucune règle, et le devis annoncerait le
        # prix de la route par défaut — pas celui qui sera débité.
        "country": NotRequired[CountryIso3 | None],
        # Le message portera une pièce jointe (même règle d’unité qu’au débit).
        "hasAttachment": NotRequired[bool],
        # Type de SMS (canal "sms" uniquement) — DOIT valoir celui de l’envoi réel, sinon le
        # devis annonce un prix que le débit ne respectera pas. Absent = "standard".
        "tier": NotRequired[Literal["standard", "premium"]],
        # Conversion GSM-7 (canal "sms" uniquement) — DOIT valoir celle de l’envoi réel, sinon
        # le devis annonce un nombre de segments que le débit ne respectera pas. Le champ
        # transliterated de la réponse dit si le texte A ÉTÉ modifié.
        "convertGsm7": NotRequired[bool],
        # Devise les corps SUBSTITUÉS plutôt que le gabarit — DOIT valoir celui de l’envoi
        # réel. Exige destinations : sans destinataires concrets il n’y a aucune valeur à
        # substituer, donc aucun devis exact possible (400). La substitution fait varier la
        # longueur, donc les segments, donc le prix : deviser le gabarit SOUS-facture dès
        # qu’une valeur est plus longue que sa clé.
        "personalize": NotRequired[bool],
        # Les destinataires concrets (numéros E.164, ou adresses sur le canal "email"), 1 000
        # au plus. Requis quand personalize vaut true. Un destinataire à qui il manque une
        # valeur est EXCLU du devis — c’est celui que l’envoi refusera, donc celui qui ne sera
        # pas facturé : comparez personalized.recipients au nombre soumis pour savoir combien
        # seront écartés.
        "destinations": NotRequired[list[str]],
    },
)

EstimateMessageResponsePersonalized = TypedDict(
    "EstimateMessageResponsePersonalized",
    {
        # Destinataires dont TOUS les champs se sont résolus — les seuls comptés dans
        # totalUsd. L’écart avec le nombre de destinations soumises est le nombre d’envois que
        # MISSING_MERGE_FIELD refusera.
        "recipients": Required[int],
        # Unités du destinataire le MOINS cher.
        "minUnits": Required[int],
        # Unités du destinataire le PLUS cher.
        "maxUnits": Required[int],
    },
)

EstimateMessageResponse = TypedDict(
    "EstimateMessageResponse",
    {
        # Canal estimé.
        "channel": Required[str],
        # Groupe tarifaire résolu.
        "destGroup": Required[str],
        # Encodage retenu. unicode divise la taille du segment SMS.
        "encoding": Required[Literal["gsm7", "unicode"]],
        # Caractères comptés.
        "chars": Required[int],
        # Segments SMS (0 si texte vide).
        "segments": Required[int],
        # Unités facturables d’UN message (segments en SMS, 1 sinon).
        "units": Required[int],
        # Destinataires.
        "recipients": Required[int],
        # La translittération GSM-7 est active pour cette route — indépendant du texte soumis.
        "transliterateGsm7": Required[bool],
        # Le texte A ÉTÉ modifié avant segmentation : le destinataire ne verra pas exactement
        # ce que vous avez soumis. Signalez-le à vos utilisateurs.
        "transliterated": Required[bool],
        # Prix unitaire du compte, chaîne décimale USD — SUB-CENTIME : l’arrondir à deux
        # décimales le rend nul.
        "unitPriceUsd": Required[str],
        # Total exact. Sans personalize : units × recipients × unitPriceUsd. Avec personalize
        # : la SOMME des unités de chaque corps substitué × unitPriceUsd — jamais une moyenne.
        "totalUsd": Required[str],
        # Présent UNIQUEMENT quand personalize vaut true. Les scalaires de tête (encoding,
        # chars, segments, units) décrivent alors le PIRE destinataire, jamais la moyenne :
        # ils bornent par le haut ce qu’un destinataire coûtera.
        "personalized": NotRequired[EstimateMessageResponsePersonalized],
    },
)

ListLedgerQuery = TypedDict(
    "ListLedgerQuery",
    {
        # Page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page — plafonnée à 100.
        "pageSize": NotRequired[int],
        # Filtre par type d’écriture (topup, debit_send, reversal…).
        "kind": NotRequired[Literal["topup", "topup_bonus", "debit_send", "debit_storage", "debit_ai", "margin", "provider_cost", "withdrawal", "adjustment", "reversal", "transfer"]],
        # Date de début (YYYY-MM-DD), incluse.
        "from": NotRequired[str],
        # Date de fin (YYYY-MM-DD), incluse.
        "to": NotRequired[str],
        # Colonne de tri.
        "sort": NotRequired[Literal["date", "amount", "kind", "channel", "balance"]],
        # Sens du tri.
        "dir": NotRequired[Literal["asc", "desc"]],
        # Filtre par canal du message rattaché.
        "channel": NotRequired[Channel],
        # Recherche libre : clé d’idempotence ou destination (correspondance partielle), ou
        # référence exacte si le terme est un UUID.
        "q": NotRequired[str],
    },
)

ListLedgerResponseRowsItem = TypedDict(
    "ListLedgerResponseRowsItem",
    {
        # Écriture.
        "id": Required[str],
        # Horodatage.
        "createdAt": Required[str],
        # Type d’écriture.
        "kind": Required[str],
        # Montant SIGNÉ en USD (négatif = débit).
        "amountUsd": Required[str],
        # Solde après écriture.
        "balanceAfter": Required[str | None],
        # Canal du message lié, null sans message.
        "channel": Required[str | None],
        # Destinataire du message lié.
        "toAddr": Required[str | None],
        # Statut du message lié.
        "status": Required[str | None],
        # Référence de paiement (SENNDO-AAMMJJ-N) quand l’écriture EST une recharge — c’est la
        # clé du reçu. Null partout ailleurs, y compris sur la ligne de bonus, qui partage la
        # référence du crédit principal.
        "receiptRef": NotRequired[str | None],
    },
)

ListLedgerResponseAggregates = TypedDict(
    "ListLedgerResponseAggregates",
    {
        # Somme des débits, en valeur absolue.
        "debitUsd": Required[str],
        # Somme des crédits — les contre-passations en font partie.
        "creditUsd": Required[str],
        # Solde à l’écriture la plus récente de la vue.
        "closingBalanceUsd": Required[str | None],
    },
)

ListLedgerResponse = TypedDict(
    "ListLedgerResponse",
    {
        # Page servie.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        # Total de la vue filtrée.
        "total": Required[int],
        "rows": Required[list[ListLedgerResponseRowsItem]],
        # Totaux de la vue FILTRÉE, calculés par le serveur.
        "aggregates": Required[ListLedgerResponseAggregates],
    },
)

ListInboxThreadsQuery = TypedDict(
    "ListInboxThreadsQuery",
    {
        # Page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page — plafonnée à 100.
        "pageSize": NotRequired[int],
    },
)

ListInboxThreadsResponseThreadsItem = TypedDict(
    "ListInboxThreadsResponseThreadsItem",
    {
        # Canal du fil.
        "channel": Required[str],
        # Correspondant.
        "contact": Required[str],
        # Dernier message REÇU.
        "lastBody": Required[str],
        # Horodatage de ce message.
        "lastAt": Required[str],
    },
)

ListInboxThreadsResponse = TypedDict(
    "ListInboxThreadsResponse",
    {
        # Page servie.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        "threads": Required[list[ListInboxThreadsResponseThreadsItem]],
    },
)

ListInboxMessagesQuery = TypedDict(
    "ListInboxMessagesQuery",
    {
        # Canal du fil (whatsapp_cloud | whatsapp_baileys | sms).
        "channel": Required[Literal["whatsapp_baileys", "whatsapp_cloud", "sms"]],
        # Correspondant du fil.
        "contact": Required[str],
        # Page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page — plafonnée à 500.
        "pageSize": NotRequired[int],
    },
)

ListInboxMessagesResponseMessagesItem = TypedDict(
    "ListInboxMessagesResponseMessagesItem",
    {
        # Identifiant du message.
        "id": Required[str],
        # Canal.
        "channel": Required[str],
        # Sens du message.
        "direction": Required[Literal["in", "out"]],
        # Émetteur.
        "fromAddr": Required[str | None],
        # Destinataire.
        "toAddr": Required[str],
        # Contenu.
        "body": Required[str],
        # Horodatage.
        "createdAt": Required[str],
    },
)

ListInboxMessagesResponse = TypedDict(
    "ListInboxMessagesResponse",
    {
        # Page servie.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        "messages": Required[list[ListInboxMessagesResponseMessagesItem]],
    },
)

ListWaTemplatesResponseTemplatesItemHeader = TypedDict(
    "ListWaTemplatesResponseTemplatesItemHeader",
    {
        # Nature de l’en-tête.
        "type": Required[Literal["none", "text", "image", "video", "document"]],
        # Texte figé de l’en-tête (type text uniquement), au plus une variable.
        "text": NotRequired[str],
        # Valeur d’exemple de la variable d’en-tête, quand il y en a une.
        "example": NotRequired[str],
        # Handle d’échantillon Meta exigé à la soumission d’un en-tête média. Sans usage à
        # l’envoi.
        "exampleHandle": NotRequired[str],
    },
)

ListWaTemplatesResponseTemplatesItemButtonsItem = TypedDict(
    "ListWaTemplatesResponseTemplatesItemButtonsItem",
    {
        # Nature du bouton.
        "type": Required[Literal["quick_reply", "url", "phone_number", "copy_code", "otp"]],
        # Libellé affiché ; absent d’un bouton copy_code.
        "text": NotRequired[str],
        # Destination d’un bouton url. Une variable {{n}} y impose un paramètre à l’envoi.
        "url": NotRequired[str],
        # Numéro appelé par un bouton phone_number.
        "phoneNumber": NotRequired[str],
        # Valeur d’exemple d’un bouton copy_code.
        "example": NotRequired[str],
        # Forme d’OTP exigée par Meta (bouton otp uniquement).
        "otpType": NotRequired[Literal["copy_code", "one_tap", "zero_tap"]],
        # Position 1-based de la variable de CORPS qui porte le code. Meta exige que le code
        # figure dans le corps ET dans le bouton : la valeur du bouton est la recopie de cette
        # variable, jamais une saisie de plus. Absent = 1.
        "codeVariable": NotRequired[int],
    },
)

ListWaTemplatesResponseTemplatesItem = TypedDict(
    "ListWaTemplatesResponseTemplatesItem",
    {
        # Modèle.
        "id": Required[str],
        # Nom à passer en template.name à l’envoi.
        "name": Required[str],
        # Langue du modèle (fr, en, en_US…).
        "language": Required[str],
        # Catégorie à utiliser : l’effective si Meta l’a tranchée, sinon la demandée. C’est
        # celle-ci qu’il faut lire — les deux autres n’existent que pour comprendre un
        # reclassement.
        "category": Required[Literal["MARKETING", "UTILITY", "AUTHENTICATION"]],
        # Catégorie DEMANDÉE à la soumission.
        "requestedCategory": Required[Literal["MARKETING", "UTILITY", "AUTHENTICATION"]],
        # Catégorie RETENUE par Meta ; null tant qu’il n’a pas tranché. Meta reclasse — un
        # modèle demandé en UTILITY et retenu en MARKETING ne coûte pas le même prix.
        "effectiveCategory": Required[Literal["MARKETING", "UTILITY", "AUTHENTICATION"] | None],
        # Seul approved est envoyable.
        "status": Required[Literal["draft", "pending", "approved", "rejected", "paused"]],
        # Modèle partagé de la plateforme : envoyable, non éditable.
        "platformShared": Required[bool],
        # Corps approuvé, variables positionnelles comprises.
        "body": Required[str],
        # Pied de page.
        "footer": Required[str],
        # Valeurs d’exemple des variables du corps, dans l’ordre — celles soumises à la revue
        # Meta. Elles ne sont PAS envoyées : à l’envoi, vous fournissez les vôtres.
        "bodyExamples": Required[list[str]],
        # Motif du refus Meta ; chaîne vide quand le modèle n’a pas été refusé.
        "rejectionReason": Required[str],
        # Note de qualité Meta, INDÉPENDANTE du statut ; null tant que le modèle n’a jamais
        # été noté. Un modèle approuvé passé en RED est en voie d’être mis en pause par Meta.
        "quality": Required[Literal["GREEN", "YELLOW", "RED", "UNKNOWN"] | None],
        # Provenance du modèle. Métadonnée d’exploitation, sans effet sur l’envoi.
        "source": Required[Literal["builder", "library", "synced", "manual"]],
        # Horodatage ISO 8601 de création.
        "createdAt": Required[str],
        # Horodatage ISO 8601 de la dernière modification.
        "updatedAt": Required[str],
        # En-tête du modèle. type vaut none (aucun en-tête), text (texte figé), ou image /
        # video / document — un en-tête MÉDIA ne fige que le FORMAT : le média réel se fournit
        # à CHAQUE envoi, dans le paramètre header. Les champs présents dépendent du type ;
        # seul type est garanti.
        "header": Required[ListWaTemplatesResponseTemplatesItemHeader],
        # Boutons du modèle, DANS L’ORDRE — leur index est ce que Meta attend à l’envoi. Un
        # bouton copy_code ou otp signale un modèle qui attend un CODE ; un bouton url dont
        # l’URL porte une variable en attend un paramètre à chaque envoi. En omettre un fait
        # échouer l’envoi APRÈS le débit.
        "buttons": Required[list[ListWaTemplatesResponseTemplatesItemButtonsItem]],
    },
)

ListWaTemplatesResponse = TypedDict(
    "ListWaTemplatesResponse",
    {
        "templates": Required[list[ListWaTemplatesResponseTemplatesItem]],
    },
)

ListWaCloudNumbersResponseNumbersItem = TypedDict(
    "ListWaCloudNumbersResponseNumbersItem",
    {
        # Numéro.
        "id": Required[str],
        # Identifiant Meta du numéro.
        "phoneNumberId": Required[str],
        # Numéro affiché.
        "displayNumber": Required[str],
        # Un token est enregistré (sa valeur ne sort jamais).
        "hasToken": Required[bool],
        # Enregistrement.
        "createdAt": Required[str],
    },
)

ListWaCloudNumbersResponseSharedSendersItem = TypedDict(
    "ListWaCloudNumbersResponseSharedSendersItem",
    {
        # Nature de l’émetteur partagé. C’est elle qui dit COMMENT il s’identifie : le Cloud
        # par son nom vérifié, l’appairé par son numéro.
        "kind": Required[Literal["whatsapp_cloud", "whatsapp_baileys"]],
        # Canal servi.
        "channel": Required[str],
        # Nom vérifié affiché au destinataire (WhatsApp Cloud). TOUJOURS null pour un émetteur
        # appairé : le nom vérifié est un concept Cloud, et un message appairé arrive avec le
        # NUMÉRO.
        "verifiedName": Required[str | None],
        # Numéro appairé, tel que le destinataire le verra. TOUJOURS null côté Cloud — le
        # numéro plateforme reste un secret. Côté appairé, null seulement dans la fenêtre où
        # la session est connectée mais où le numéro n’a pas encore été remonté.
        "pairedNumber": Required[str | None],
        # Toujours true : un émetteur partagé sert les envois À SENS UNIQUE (codes, alertes,
        # notifications). Les réponses des destinataires ne vous reviennent pas.
        "oneWay": Required[bool],
        # Poignée de désignation de l’émetteur appairé partagé, absente de l’entrée Cloud. Ce
        # n’est pas un credential : le partagé est ouvert à tout compte.
        "sessionId": NotRequired[str],
    },
)

ListWaCloudNumbersResponse = TypedDict(
    "ListWaCloudNumbersResponse",
    {
        # Numéros enregistrés par le compte lui-même.
        "numbers": Required[list[ListWaCloudNumbersResponseNumbersItem]],
        # La plateforme peut émettre pour vous si vous n’avez pas de numéro à vous.
        "platformFallbackAvailable": Required[bool],
        # Émetteurs partagés explicites — identité vue par le destinataire seulement.
        "sharedSenders": Required[list[ListWaCloudNumbersResponseSharedSendersItem]],
    },
)

GetRoutingCredentialsResponseCredentials = TypedDict(
    "GetRoutingCredentialsResponseCredentials",
    {
        # Jeu d’identifiants.
        "id": Required[str],
        # Les QUATRE derniers caractères de l’identifiant de compte, et rien de plus : assez
        # pour reconnaître lequel de vos comptes est branché, trop peu pour en déduire le
        # reste.
        "accountSidLast4": Required[str],
        # Le numéro que verront vos destinataires.
        "waFromNumber": Required[str],
        # La marque affichée au-dessus de votre numéro. null = numéro nu.
        "label": Required[str | None],
        # Quand le couple a été prouvé par un appel réel au partenaire d’acheminement. Un
        # identifiant bien formé ne prouve rien : cette date atteste d’un appel réseau, pas
        # d’une validation de forme.
        "verifiedAt": Required[str],
    },
)

GetRoutingCredentialsResponse = TypedDict(
    "GetRoutingCredentialsResponse",
    {
        # null = aucun identifiant apporté : vos envois partent de l’émetteur partagé.
        "credentials": Required[GetRoutingCredentialsResponseCredentials | None],
        # L’émetteur partagé de la plateforme peut émettre pour vous si vous n’apportez pas
        # d’identifiants.
        "platformFallbackAvailable": Required[bool],
    },
)

ListWebhooksResponseEndpointsItem = TypedDict(
    "ListWebhooksResponseEndpointsItem",
    {
        # Identifiant de l’endpoint.
        "id": Required[str],
        # Libellé.
        "name": Required[str],
        # URL appelée.
        "url": Required[str],
        # Événements souscrits.
        "events": Required[list[str]],
        # Révocation — null tant que l’endpoint est actif.
        "revokedAt": Required[str | None],
        # Création.
        "createdAt": Required[str],
    },
)

ListWebhooksResponse = TypedDict(
    "ListWebhooksResponse",
    {
        "endpoints": Required[list[ListWebhooksResponseEndpointsItem]],
    },
)

CreateWebhookBody = TypedDict(
    "CreateWebhookBody",
    {
        # Libellé libre.
        "name": Required[str],
        # URL http(s) que nous appellerons.
        "url": Required[str],
        # Événements souscrits. message.failed porte failureCode, la même énumération que GET
        # /v1/messages.
        "events": Required[list[Literal["message.sent", "message.failed", "message.inbound"]]],
    },
)

CreateWebhookResponse = TypedDict(
    "CreateWebhookResponse",
    {
        # Identifiant de l’endpoint.
        "id": Required[str],
        # Libellé.
        "name": Required[str],
        # URL appelée.
        "url": Required[str],
        # Événements souscrits.
        "events": Required[list[str]],
        # Toujours null ici : l’endpoint vient d’être créé. Le champ est présent pour que la
        # réponse de création ait la MÊME forme qu’une ligne de GET /v1/webhooks, et qu’un
        # client puisse la ranger dans sa liste sans cas particulier.
        "revokedAt": Required[str | None],
        # Création.
        "createdAt": Required[str],
        # Secret de signature — rendu une seule fois, jamais relisible.
        "secret": Required[str],
    },
)

RevokeWebhookResponse = TypedDict(
    "RevokeWebhookResponse",
    {
        # Identifiant de l’endpoint.
        "id": Required[str],
        # Toujours true.
        "revoked": Required[bool],
    },
)

ListWebhookDeliveriesQuery = TypedDict(
    "ListWebhookDeliveriesQuery",
    {
        # Page, à partir de 1.
        "page": NotRequired[int],
        # Taille de page — plafonnée à 200.
        "pageSize": NotRequired[int],
        # Filtre d’issue : pending | delivering | failed_retrying | succeeded |
        # failed_permanent. Une valeur hors de cette liste est REFUSÉE (400) — jamais ignorée
        # : un filtre ignoré rendrait un sur-ensemble en se faisant passer pour la tranche
        # demandée.
        "status": NotRequired[Literal["pending", "delivering", "failed_retrying", "succeeded", "failed_permanent"]],
    },
)

ListWebhookDeliveriesResponseAggregates = TypedDict(
    "ListWebhookDeliveriesResponseAggregates",
    {
        # Livrées.
        "succeeded": Required[int],
        # Abandonnées.
        "failedPermanent": Required[int],
        # Pas encore tranchées : pending, delivering et failed_retrying réunis. Avec succeeded
        # et failedPermanent, les trois seaux recomposent exactement total.
        "inFlight": Required[int],
    },
)

ListWebhookDeliveriesResponseDeliveriesItem = TypedDict(
    "ListWebhookDeliveriesResponseDeliveriesItem",
    {
        # Livraison.
        "id": Required[str],
        # Endpoint visé.
        "endpointId": Required[str],
        # Événement livré.
        "eventType": Required[str],
        # Issue.
        "status": Required[str],
        # Numéro de tentative.
        "attempt": Required[int],
        # Statut HTTP renvoyé par VOTRE serveur.
        "httpStatus": Required[int | None],
        # Erreur de transport.
        "error": Required[str | None],
        # Durée de l’appel, en millisecondes ; null si la tentative n’a jamais abouti à une
        # réponse. C’est ce qui distingue « votre serveur a refusé » de « votre serveur n’a
        # pas répondu à temps ».
        "durationMs": Required[int | None],
        # La livraison porte un événement émis par une clé de test. Un endpoint reçoit les
        # DEUX : ce drapeau est ce qui permet de les distinguer côté client.
        "testMode": Required[bool],
        # Tentative.
        "createdAt": Required[str],
        # Horodatage de l’issue TERMINALE (succès ou échec définitif) ; null tant que la
        # livraison est en attente ou en retentative.
        "deliveredAt": Required[str | None],
    },
)

ListWebhookDeliveriesResponse = TypedDict(
    "ListWebhookDeliveriesResponse",
    {
        # Page servie.
        "page": Required[int],
        # Taille de page.
        "pageSize": Required[int],
        # Total de la vue filtrée.
        "total": Required[int],
        "aggregates": Required[ListWebhookDeliveriesResponseAggregates],
        "deliveries": Required[list[ListWebhookDeliveriesResponseDeliveriesItem]],
    },
)

# ── sendMessage — POST /v1/messages
# ── getMessage — GET /v1/messages/{id}
# ── listMessages — GET /v1/messages
# ── uploadMedia — POST /v1/wa-media
UploadMediaBody = MultipartUpload
# ── listMedia — GET /v1/wa-media
# ── deleteMedia — DELETE /v1/wa-media/{id}
DeleteMediaResponse = None
# ── listPrices — GET /v1/prices
# ── getBalance — GET /v1/balance
# ── listCurrencies — GET /v1/currencies
# ── listSenderIds — GET /v1/sender-ids
# ── estimateMessage — POST /v1/messages/estimate
# ── listLedger — GET /v1/ledger
# ── listInboxThreads — GET /v1/inbox/threads
# ── listInboxMessages — GET /v1/inbox/messages
# ── listWaTemplates — GET /v1/wa-templates
# ── listWaCloudNumbers — GET /v1/wa-cloud/numbers
# ── getRoutingCredentials — GET /v1/channels/whatsapp_twilio/credentials
# ── listWebhooks — GET /v1/webhooks
# ── createWebhook — POST /v1/webhooks
# ── revokeWebhook — POST /v1/webhooks/{id}/revoke
# ── listWebhookDeliveries — GET /v1/webhooks/deliveries

OperationDescriptor = TypedDict(
    "OperationDescriptor",
    {
        "operationId": str,
        # Le nom de la méthode Python correspondante — `sendMessage` → `send_message`. Il est
        # DÉRIVÉ ici plutôt que maintenu à la main : c'est la table oubliée qui crée la
        # divergence, et le test de conformité relit celle-ci au lieu d'en tenir une seconde.
        "methodName": str,
        "method": str,
        "path": str,
        "pathParams": tuple[str, ...],
        "queryParams": tuple[str, ...],
        "requiredQueryParams": tuple[str, ...],
        "requiredBodyFields": tuple[str, ...],
        "contentType": str | None,
        "successStatus": str,
        # True = l'appel produit un effet RÉEL et FACTURÉ avec une clé `sk_live_`. Le transport
        # s'en sert pour refuser tout retry qui ne serait pas protégé par une clé d'idempotence.
        "billableSideEffect": bool,
    },
)

#: LA surface publique, dérivée du contrat. Une opération absente d'ici n'existe pas.
OPERATIONS: dict[str, OperationDescriptor] = {
    "sendMessage": {
        "operationId": "sendMessage",
        "methodName": "send_message",
        "method": "POST",
        "path": "/v1/messages",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": ("channel", "to", "idempotencyKey", ),
        "contentType": "application/json",
        "successStatus": "200",
        "billableSideEffect": True,
    },
    "getMessage": {
        "operationId": "getMessage",
        "methodName": "get_message",
        "method": "GET",
        "path": "/v1/messages/{id}",
        "pathParams": ("id", ),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listMessages": {
        "operationId": "listMessages",
        "methodName": "list_messages",
        "method": "GET",
        "path": "/v1/messages",
        "pathParams": (),
        "queryParams": ("page", "pageSize", "sort", "dir", "channel", "status", "from", "to", "via", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "uploadMedia": {
        "operationId": "uploadMedia",
        "methodName": "upload_media",
        "method": "POST",
        "path": "/v1/wa-media",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": ("file", ),
        "contentType": "multipart/form-data",
        "successStatus": "201",
        "billableSideEffect": False,
    },
    "listMedia": {
        "operationId": "listMedia",
        "methodName": "list_media",
        "method": "GET",
        "path": "/v1/wa-media",
        "pathParams": (),
        "queryParams": ("page", "pageSize", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "deleteMedia": {
        "operationId": "deleteMedia",
        "methodName": "delete_media",
        "method": "DELETE",
        "path": "/v1/wa-media/{id}",
        "pathParams": ("id", ),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "204",
        "billableSideEffect": False,
    },
    "listPrices": {
        "operationId": "listPrices",
        "methodName": "list_prices",
        "method": "GET",
        "path": "/v1/prices",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "getBalance": {
        "operationId": "getBalance",
        "methodName": "get_balance",
        "method": "GET",
        "path": "/v1/balance",
        "pathParams": (),
        "queryParams": ("currency", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listCurrencies": {
        "operationId": "listCurrencies",
        "methodName": "list_currencies",
        "method": "GET",
        "path": "/v1/currencies",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listSenderIds": {
        "operationId": "listSenderIds",
        "methodName": "list_sender_ids",
        "method": "GET",
        "path": "/v1/sender-ids",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "estimateMessage": {
        "operationId": "estimateMessage",
        "methodName": "estimate_message",
        "method": "POST",
        "path": "/v1/messages/estimate",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": ("channel", "text", "recipients", ),
        "contentType": "application/json",
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listLedger": {
        "operationId": "listLedger",
        "methodName": "list_ledger",
        "method": "GET",
        "path": "/v1/ledger",
        "pathParams": (),
        "queryParams": ("page", "pageSize", "kind", "from", "to", "sort", "dir", "channel", "q", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listInboxThreads": {
        "operationId": "listInboxThreads",
        "methodName": "list_inbox_threads",
        "method": "GET",
        "path": "/v1/inbox/threads",
        "pathParams": (),
        "queryParams": ("page", "pageSize", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listInboxMessages": {
        "operationId": "listInboxMessages",
        "methodName": "list_inbox_messages",
        "method": "GET",
        "path": "/v1/inbox/messages",
        "pathParams": (),
        "queryParams": ("channel", "contact", "page", "pageSize", ),
        "requiredQueryParams": ("channel", "contact", ),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listWaTemplates": {
        "operationId": "listWaTemplates",
        "methodName": "list_wa_templates",
        "method": "GET",
        "path": "/v1/wa-templates",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listWaCloudNumbers": {
        "operationId": "listWaCloudNumbers",
        "methodName": "list_wa_cloud_numbers",
        "method": "GET",
        "path": "/v1/wa-cloud/numbers",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "getRoutingCredentials": {
        "operationId": "getRoutingCredentials",
        "methodName": "get_routing_credentials",
        "method": "GET",
        "path": "/v1/channels/whatsapp_twilio/credentials",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listWebhooks": {
        "operationId": "listWebhooks",
        "methodName": "list_webhooks",
        "method": "GET",
        "path": "/v1/webhooks",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "createWebhook": {
        "operationId": "createWebhook",
        "methodName": "create_webhook",
        "method": "POST",
        "path": "/v1/webhooks",
        "pathParams": (),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": ("name", "url", "events", ),
        "contentType": "application/json",
        "successStatus": "201",
        "billableSideEffect": False,
    },
    "revokeWebhook": {
        "operationId": "revokeWebhook",
        "methodName": "revoke_webhook",
        "method": "POST",
        "path": "/v1/webhooks/{id}/revoke",
        "pathParams": ("id", ),
        "queryParams": (),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
    "listWebhookDeliveries": {
        "operationId": "listWebhookDeliveries",
        "methodName": "list_webhook_deliveries",
        "method": "GET",
        "path": "/v1/webhooks/deliveries",
        "pathParams": (),
        "queryParams": ("page", "pageSize", "status", ),
        "requiredQueryParams": (),
        "requiredBodyFields": (),
        "contentType": None,
        "successStatus": "200",
        "billableSideEffect": False,
    },
}

#: Les identifiants, à l'exécution — c'est sur eux que porte le test de conformité.
OPERATION_IDS: tuple[str, ...] = (
    "sendMessage",
    "getMessage",
    "listMessages",
    "uploadMedia",
    "listMedia",
    "deleteMedia",
    "listPrices",
    "getBalance",
    "listCurrencies",
    "listSenderIds",
    "estimateMessage",
    "listLedger",
    "listInboxThreads",
    "listInboxMessages",
    "listWaTemplates",
    "listWaCloudNumbers",
    "getRoutingCredentials",
    "listWebhooks",
    "createWebhook",
    "revokeWebhook",
    "listWebhookDeliveries",
)
