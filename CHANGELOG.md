# Journal des versions — `senndo` (Python)

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le versionnage
sémantique.

## 0.1.2 — 2026-08-02

Quatre champs de plus, trouvés non par une sonde mais par un **gate statique** : la campagne live
de `0.1.1` n'observait que ce que l'état courant du serveur produisait, et l'observé n'est qu'une
borne inférieure de l'écart. Le gate, lui, compare les types de TOUTES les réponses aux schémas du
contrat, sans réseau et sans compte.

### Corrigé

- `createWebhook.revokedAt` — toujours `null` à la création, mais présent : la réponse de création
  a donc la MÊME forme qu'une ligne de `listWebhooks`, et se range dans une liste sans cas
  particulier. L'exemple du contrat le portait déjà ; le schéma, non.
- `listWebhookDeliveries.deliveries[]` — `durationMs` (ce qui distingue « votre serveur a refusé »
  de « votre serveur n'a pas répondu à temps »), `testMode` (un endpoint reçoit les événements de
  test ET de production : c'est ce drapeau qui les sépare) et `deliveredAt` (horodatage de l'issue
  terminale).

### Note

`0.1.1` n'a atteint que npm et PyPI ; Packagist ne l'a jamais vue. `0.1.2` atterrit sur les trois
registres ensemble — un paquet PHP qui passe de `0.1.0` à `0.1.2` ne saute donc rien.

## 0.1.1 — 2026-08-02

Première confrontation des trois SDK à l'API **réelle** (`scripts/sdk-live/`). Les gates
prouvaient la fidélité de l'émetteur au contrat et le comportement du transport face à un serveur
simulé ; aucun ne prouvait que le SERVEUR répond ce que le contrat annonce. Il ne le faisait pas
partout.

### Corrigé

- **21 champs que l'API renvoie et que le contrat ne décrivait pas** sont désormais présents dans
  les `TypedDict` — donc vus par `mypy` au lieu d'être invisibles au client. `list_sender_ids`
  (`canReview`, `ownerAccountId`, `ownerName`, `verification`, `createdAt`, `suspensionReason`,
  `suspendedAt`, `archivedAt`), `list_wa_templates` (`requestedCategory`, `effectiveCategory`,
  `rejectionReason`, `quality`, `source`, `header`, `bodyExamples`, `buttons`, `createdAt`,
  `updatedAt`), `list_wa_cloud_numbers` → `sharedSenders` (`kind`, `oneWay`, `sessionId`),
  `list_ledger` → `rows` (`receiptRef`).

  Deux d'entre eux valaient à eux seuls la version : `buttons` est ce qui dit qu'un modèle attend
  un CODE à l'envoi — l'omettre fait échouer l'envoi APRÈS le débit ; `effectiveCategory` est la
  catégorie que Meta a réellement retenue, et un modèle demandé en UTILITY puis reclassé en
  MARKETING ne coûte pas le même prix.

### Note

Aucun écart n'était propre à un SDK : les trois recevaient exactement les mêmes champs non
documentés. La génération faisait son travail ; c'est la source qui était incomplète.

## 0.1.0 — 2026-08-02

Première publication. La version reste `0.x` tant que la surface n'a pas été exercée par des
intégrations réelles : un `1.0.0` promet une stabilité que rien n'a encore éprouvée.

### Ajouté

- `SenndoClient` — les 20 opérations de l'API publique, une méthode par opération, nommées en
  snake_case depuis les identifiants du contrat.
- Types générés depuis le contrat OpenAPI de senndo : corps, paramètres de requête et réponses en
  `TypedDict`, énumérations en `Literal`.
- Erreurs typées par famille (`SenndoInsufficientFundsError`, `SenndoRateLimitError`,
  `SenndoValidationError`…) — on branche sur une classe ou sur `error.code`, jamais sur un message.
- Idempotence de première classe : `idempotencyKey` obligatoire sur l'envoi, préfixes réservés
  refusés localement, `new_idempotency_key()` pour les cas sans clé métier.
- Retentatives limitées à ce qui est rejouable : `GET`/`DELETE` et les `POST` porteurs d'une clé
  d'idempotence, sur échec de transport, 429 et 5xx uniquement.
- Délais explicites (30 s par défaut), surchargeables par appel via `RequestOptions`.
- Transport injectable (`types.Transport`) — `urllib.request` par défaut, aucune dépendance.
- Décodage `parse_float=Decimal` : aucun nombre à virgule ne traverse un flottant.
- Clé API masquée dans `repr()` et `str()`.
