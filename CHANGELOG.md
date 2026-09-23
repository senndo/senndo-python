# Journal des versions — `senndo` (Python)

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le versionnage
sémantique.

## 1.2.0 — 2026-09-23

- `verify_webhook_signature(secret, en_tete, corps)` : authentifie un webhook reçu (`X-Senndo-Signature`), comparaison à durée constante et
  refus d'un rejeu au-delà de 300 secondes (réglable). Le corps doit être le corps BRUT reçu.
- `list_content_templates()` : les modèles hébergés que la plateforme prête au canal `whatsapp_twilio`, à citer dans
  `content.sid` (`GET /v1/channels/whatsapp_twilio/templates`). Ce canal n'envoie que des
  modèles : sans cette lecture, un identifiant ne s'obtenait que depuis la console. Liste vide et
  `reason` égal à `byok` quand le compte émet sous ses propres identifiants d'acheminement.
- `list_sender_ids()` : `verification.dmarcRisk` (`reject`, `quarantine` ou `null`) sur un expéditeur e-mail.
  Un AVERTISSEMENT, jamais un refus : le domaine publie une politique DMARC stricte et aucune
  signature n'est alignée sur lui, donc les envois partent, sont facturés, puis sont écartés par
  le destinataire. Mesuré au rafraîchissement de la vérification.

## 1.1.0 — 2026-09-23

**Le canal `whatsapp_twilio` s'envoie enfin depuis le SDK.** Le serveur le livrait ; le SDK le
refusait avant tout appel réseau, parce que sa validation locale ne connaissait pas `content`
comme contenu d'envoi. Un envoi `{ channel: 'whatsapp_twilio', content: { sid: 'HX…' } }` sans
`text` partait en erreur locale.

### Ajouté

* `whatsapp_twilio` rejoint l'énumération des canaux, et `content` (`sid`, `variables`) le corps
  de `send_message`.
* `verdictPending` et `failureCode` sur les messages lus (`get_message, list_messages`) : `sent` dit « pris en
  charge », `verdictPending` dit si une preuve de remise est encore attendue.
* `get_routing_credentials` : les identifiants WhatsApp Twilio déposés par le compte.
* `get_balance` porte le plancher de découvert et le disponible réellement dépensable.
* Les erreurs 400, 404 et 413 documentent leurs cas particuliers (`EMPTY_BODY`,
  `MALFORMED_JSON`, `ROUTE_NOT_FOUND`).
* `delivering` rejoint l'énumération de `listWebhookDeliveries` → `status`, et une valeur hors
  énumération est désormais REFUSÉE (`400 INVALID_STATUS`) au lieu d'être ignorée en silence.

### Corrigé

* La règle « un envoi doit porter du contenu » accepte `content` au même titre que `text`,
  `media` et `template`.

### Documentation

* Le premier extrait du README importe et construit le client : il s'exécute tel quel.
* E-mail (`subject` obligatoire), WhatsApp Twilio, `template.language` (exigé quand un modèle
  existe en plusieurs langues), lecture des expéditeurs et des modèles du compte, et le sens des
  statuts définitifs.

### À savoir sur la charge utile des webhooks

**`reversedAmountUsd` est désormais TOUJOURS présent** dans `data` d'un `message.sent` /
`message.failed`, à `null` quand il n'y a pas eu de contre-passage. `billedAmountUsd` garde sa
sémantique : le montant BRUT débité, la dépense nette étant `billedAmountUsd − reversedAmountUsd`.

## 1.0.2 — 2026-08-10

**Ce paquet n'a jamais publié l'extrait fautif** — c'est le README TypeScript qui le portait.
L'entrée est conservée ici parce que les trois SDK partagent le contrat, et que les points
suivants les concernent tous. Pour mémoire, l'exemple faux était :

```python
any(p["country"] == "FRA" and p["status"] == "approved" for p in emetteur["countries"])
```

`countries[].country` est en ISO 3166-1 **alpha-2**, pas alpha-3 : ce filtre rendait
systématiquement une liste vide, sans erreur. Le bon code est `'FR'`. L'extrait est corrigé, et un
gate vérifie désormais chaque littéral pays des extraits contre le système de codes du champ
auquel il s'applique — il aurait refusé `'FRA'`.

### Ajouté — deux alias qui NOMMENT le système de codes

`CountryIso3` et `CountryAlpha2` sont déclarés dans le contrat généré et portés par les trois champs `country` du
contrat. Ce sont des `string` : rien ne cesse de compiler. Ils existent parce que le contrat
portait deux systèmes de codes sous un seul type, et que l'autocomplétion ne disait pas lequel.

| Champ | Système |
|---|---|
| `sendMessage` → `country` | `CountryIso3` — « CIV », « FRA » |
| `estimateMessage` → `country` | `CountryIso3` — « CIV », « FRA » |
| `listSenderIds` → `senderIds[].countries[].country` | `CountryAlpha2` — « CI », « FR » |

### Corrigé — le contrat annonçait le mauvais système sur le devis

`estimateMessage` documentait `country` en alpha-2 quand le moteur de routage le matche en
alpha-3. Un devis publié avec « FR » ne matchait aucune règle pays : la cascade retombait en
silence sur la route par défaut et le devis annonçait **un prix qui n'était pas celui du débit**.
La description dit désormais alpha-3.

### Changé — un `country` inconnu est REFUSÉ, plus ignoré

`sendMessage` et `estimateMessage` répondent `400 COUNTRY_INVALID` quand `country` ne désigne
aucun pays du catalogue ISO 3166-1 — y compris un code de la bonne longueur mais inexistant. Sur
l'envoi, le refus arrive **avant tout débit**. Auparavant, une valeur de ce genre était acceptée
et l'envoi partait, facturé, sur une route que vous n'aviez pas demandée.

Ce n'est pas cassant pour un appel correct : `country` absent, vide, ou en alpha-3 valide (casse
et espaces indifférents) se comporte exactement comme avant.

## 1.0.1 — 2026-08-05

Version d'alignement : `@senndo/sdk` (npm) a dû repartir en `1.0.1` — son tarball `1.0.0`
embarquait un build périmé. Les trois SDK avancent ensemble pour qu'une même version désigne
toujours le même contrat. **Aucun changement de code** dans ce paquet, qui était correct en
`1.0.0`.

## 1.0.0 — 2026-08-05

Première version **stable**. senndo passe en v1 et le SDK suit : les 20 opérations de la surface
publique sont figées et gardées par les gates de conformité.

### Corrigé — sécurité et argent (audit batch)

- **Les redirections HTTP ne sont plus suivies.** `fetch` et `urllib` les suivaient par défaut et
  **dégradent un POST en GET** sur 301/302. Or `POST /v1/messages` (envoyer) et
  `GET /v1/messages` (lire le journal) partagent le chemin : un 301 sur l'hôte d'API — une
  redirection http→https de bord suffit — transformait un **envoi facturé en lecture, rendue comme
  un succès**. Le SDK échoue désormais bruyamment : une base d'URL se corrige dans la
  configuration, jamais en silence à l'exécution.
- **(Python) La clé d'API ne fuit plus vers l'hôte de redirection.** `urllib` rejouait les en-têtes
  d'origine, `Authorization` compris : une clé `sk_live_` partait chez un tiers. Si vous avez
  utilisé une version 0.1.x derrière une URL susceptible de rediriger, **faites tourner vos clés**.
- **`estimateMessage` accepte `tier`.** Le serveur le lisait déjà ; le contrat ne le déclarait pas,
  donc aucun SDK ne pouvait le transmettre — un devis annonçait le tarif *standard* pour un envoi
  qui partirait en *premium*. Le devis et le débit s'accordent enfin.
- **`listLedger(kind)` et `listWebhookDeliveries(status)` sont des énumérations.** Elles étaient
  typées `string` ; une valeur hors liste ne provoquait aucune erreur — le filtre tombait
  silencieusement et la requête rendait **tout**. Une réconciliation comptable pouvait surcompter
  sans le moindre signal.

## 0.1.3 — 2026-08-03

Le gate serveur↔contrat descend désormais jusqu'à la **feuille** et compare trois axes : le type
de base, l'obligation, la nullité. Il a trouvé **43 écarts, tous dans le même sens** — le contrat
annonçait facultatif ce que la route rend toujours. Aucun n'était dangereux (aucun champ promis
n'était absent de la réponse) et tous coûtaient la même chose : une branche morte à écrire, pour
un cas qui ne se produit jamais.

### Corrigé

- `MessageStatus` gagne **`unknown`**. Le serveur le rend depuis toujours — c'est le statut d'un
  envoi dont l'issue est indéterminée : réconciliation d'un opérateur qui n'a jamais accusé, ou
  verdict qui n'est pas arrivé. Le `Literal` publié n'en décrivait que sept.
- **42 champs perdent leur `NotRequired`** dans les réponses. Les plus visibles : `senderId`,
  `routeRuleId`, `billedAmountUsd`, `billedCurrency`, `reversedAmountUsd`, `failureCode`,
  `category`, `body`, `source`, `toAddr`, `fromAddr`, `status` du journal, `previewUrl`,
  `balanceAfter`, `closingBalanceUsd`, `revokedAt`, `httpStatus`, `durationMs`, `deliveredAt`,
  `testMode`, `transliterateGsm7`, `transliterated`. Ils sont **présents dans chaque réponse** ;
  `None` reste possible là où il l'était déjà, mais la clé, elle, ne manque jamais.
- `listWaCloudNumbers[].displayNumber` cesse d'être **nullable** : la colonne est `NOT NULL
  DEFAULT ''`, donc le champ est une chaîne — éventuellement vide, jamais `None`.

### Note — ce qui peut ne plus passer mypy chez vous

Ces deux corrections ne retirent rien à la réponse, mais elles **resserrent des types**, et un
type plus étroit peut faire échouer une vérification qui passait :

- un `match` exhaustif sur `MessageStatus` avec `assert_never` doit maintenant traiter `unknown` ;
- un `row.get("senderId")` suivi d'un test « absent » décrit une branche morte : la clé était
  déjà toujours là. `row["senderId"]` est désormais le bon accès.

`0.1.2` restera disponible sur PyPI ; nous ne dépublions rien.

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
