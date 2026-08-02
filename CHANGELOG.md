# Journal des versions — `senndo` (Python)

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le versionnage
sémantique.

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
