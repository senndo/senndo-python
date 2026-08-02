# senndo — SDK Python officiel

Messagerie multicanale et vérification : SMS, WhatsApp, e-mail, voix, OTP. Une seule API, un seul
solde, un verdict de livraison par message.

```bash
uv add senndo
pip install senndo
poetry add senndo
```

Python ≥ 3.11. **Aucune dépendance d'exécution.**

---

## Premier envoi

```python
senndo = SenndoClient(api_key=cle_api)

envoi = senndo.send_message(
    {
        "channel": "sms",
        "to": "+33612345678",
        "text": "Votre code de connexion est 4821.",
        "idempotencyKey": f"connexion-{utilisateur_id}",
    }
)

print(envoi["id"], envoi["status"])
```

`send_message` rend l'état **au moment de l'acceptation**, pas le verdict final. Un `sent` dit que
l'opérateur a pris le message ; il ne dit pas qu'il est arrivé. Le verdict se lit sur un webhook, ou
en relisant le message.

```python
message = senndo.get_message(identifiant_du_message)

if message["status"] == "failed":
    journaliser("échec", message.get("failureCode"))
```

---

## La clé d'idempotence : le SDK n'en fabrique pas à votre place

`idempotencyKey` est **obligatoire** sur tout envoi, et c'est délibéré. Rejouer la même clé renvoie
le message déjà créé — sans jamais redébiter le compte.

Le SDK **n'en pose jamais une pour vous**. Une clé inventée au moment de l'appel serait perdue si le
processus meurt entre l'envoi et la réponse : exactement le cas où l'idempotence sert. La bonne clé
vient de votre domaine.

```python
# CORRECT : la clé survit à un redémarrage, parce qu'elle vient de votre base.
senndo.send_message(
    {
        "channel": "whatsapp_cloud",
        "to": commande["telephone"],
        "text": "Votre commande est prête.",
        "idempotencyKey": f"commande-{commande['reference']}-prete",
    }
)
```

`new_idempotency_key()` existe pour les cas où il n'y a **vraiment** rien à dériver — un envoi
manuel depuis un script, un test :

```python
senndo.send_message(
    {
        "channel": "sms",
        "to": "+15551234567",
        "text": "Essai.",
        "idempotencyKey": new_idempotency_key("essai-"),
    }
)
```

---

## Les erreurs se branchent sur une classe, jamais sur un message

```python
try:
    senndo.send_message(
        {
            "channel": "sms",
            "to": "+22507000000",
            "text": "Bonjour.",
            "idempotencyKey": f"bienvenue-{utilisateur_id}",
        }
    )
except SenndoInsufficientFundsError:
    recharger_le_compte()
except SenndoValidationError as erreur:
    journaliser("appel à corriger", erreur.code, erreur.api_message)
except SenndoRateLimitError as erreur:
    attendre(erreur.retry_after or 5)
except SenndoError as erreur:
    journaliser("échec senndo", erreur)
```

`erreur.code` est **stable** ; `erreur.api_message` est un libellé humain qui évolue. Ne branchez
jamais sur le second.

Le code d'échec d'un message livré-puis-refusé est en union **ouverte** : senndo ajoute des valeurs,
n'en retire pas.

```python
message = senndo.get_message(identifiant_du_message)
code = message.get("failureCode")

if code is not None and code not in KNOWN_FAILURE_CODES:
    journaliser("code plus récent que ce SDK", code)
```

---

## Les montants sont des chaînes décimales

Un `NUMERIC(18,6)` passé par un flottant perd des unités sur les longues traînes, et un prix
unitaire sub-centime arrondi à deux décimales devient zéro.

```python
solde = senndo.get_balance({"currency": "EUR"})
disponible = Decimal(solde["balanceUsd"])

journal = senndo.list_ledger({"pageSize": 100})
mouvement_net = sum(
    (Decimal(ligne["amountUsd"]) for ligne in journal["rows"]),
    Decimal("0"),
)
```

Le SDK décode les réponses avec `parse_float=Decimal` : aucun nombre à virgule ne traverse un
`float`.

---

## Retentatives : ce qui est rejoué, et ce qui ne l'est jamais

Le SDK retente **uniquement** ce qui peut l'être sans conséquence :

| Appel | Retenté ? |
|---|---|
| `GET`, `DELETE` | oui — sur échec de transport, 429, 5xx |
| `send_message` (porte une clé d'idempotence) | oui |
| `create_webhook`, `estimate_message`, `revoke_webhook` | **jamais** |
| tout `4xx` autre que 429 | jamais |

`create_webhook` crée une ressource à chaque exécution : une retentative aveugle produirait deux
endpoints, donc deux livraisons pour chaque événement.

```python
options = RequestOptions(timeout=10.0, max_retries=0)
senndo.send_message(
    {
        "channel": "sms",
        "to": "+5511998877665",
        "text": "Ping.",
        "idempotencyKey": f"ping-{tentative}",
    },
    options,
)
```

---

## Téléverser un média

```python
fichier = senndo.upload_media(
    MultipartUpload(file=octets, file_name="facture.pdf", content_type="application/pdf")
)

senndo.send_message(
    {
        "channel": "whatsapp_cloud",
        "to": "+33612345678",
        "text": "Votre facture.",
        "media": {"ref": fichier["ref"]},
        "idempotencyKey": f"facture-{commande['reference']}",
    }
)
```

---

## Brancher votre propre client HTTP

Le transport par défaut est `urllib.request` — zéro dépendance. Un projet qui a déjà `httpx`,
`requests`, un proxy d'entreprise ou du mTLS injecte le sien, et garde la validation, les erreurs
typées et la politique de retentative.

```python
def transport_maison(requete: HttpRequest) -> HttpResponse:
    reponse = appeler_mon_client(
        requete.method, requete.url, dict(requete.headers), requete.body, requete.timeout
    )
    return HttpResponse(status=reponse.code, headers=reponse.entetes, body=reponse.texte)


senndo = SenndoClient(api_key=cle_api, transport=transport_maison)
```

Le transport doit lever `TimeoutError` sur dépassement de délai et `OSError` sur échec de transport,
et **ne jamais lever** sur un statut d'erreur HTTP — sinon le code stable de l'enveloppe est perdu.

---

## La clé API ne s'imprime pas

```python
journaliser(repr(senndo))  # SenndoClient(base_url='…', api_key='sk_live_…32 caractères masqués')
```

Il n'existe aucun accesseur qui rende la clé en clair.

---

## Webhooks

```python
endpoint = senndo.create_webhook(
    {
        "name": "Production",
        "url": "https://exemple.test/senndo",
        "events": ["message.sent", "message.failed"],
    }
)

conserver_le_secret(endpoint["secret"])
```

Le secret n'est lisible **qu'à la création**. Il signe chaque livraison : vérifiez la signature
avant de faire quoi que ce soit du corps.

---

## Licence

MIT. Voir [CHANGELOG.md](CHANGELOG.md) pour les changements de version.
