"""Exemple exécutable — envoie un SMS, puis relit son verdict.

    export SENNDO_API_KEY=sk_test_…
    python examples/quickstart.py +15550001111

UNE CLÉ `sk_test_` NE DÉPLACE AUCUN ARGENT et ne fait sonner aucun téléphone : c'est celle à
utiliser pour vérifier une intégration. Avec une clé `sk_live_`, ce script envoie un vrai message
et débite le compte — d'où le refus explicite plus bas si `--live` n'est pas passé.

LE VERDICT N'EST PAS DANS LA RÉPONSE DE L'ENVOI. `send_message` rend l'état au moment de
l'acceptation ; savoir si le message est arrivé demande de le relire, ou d'écouter un webhook. Ce
script relit — c'est la version courte, et elle suffit à voir la différence.
"""

from __future__ import annotations

import os
import sys
import time

from senndo import SenndoClient, SenndoError, SenndoInsufficientFundsError, new_idempotency_key


def main(argv: list[str]) -> int:
    destinataire = next((a for a in argv[1:] if not a.startswith("-")), None)
    if destinataire is None:
        print("usage : python examples/quickstart.py <+E164> [--live]", file=sys.stderr)
        return 2

    cle = os.environ.get("SENNDO_API_KEY", "")
    if cle == "":
        print("SENNDO_API_KEY est absente de l'environnement.", file=sys.stderr)
        return 2

    if cle.startswith("sk_live_") and "--live" not in argv:
        print(
            "Cette clé est une clé de PRODUCTION : l'envoi sera réel et facturé.\n"
            "Relancez avec --live si c'est bien ce que vous voulez.",
            file=sys.stderr,
        )
        return 2

    senndo = SenndoClient(api_key=cle)
    print(f"client : {senndo}")

    try:
        solde = senndo.get_balance()
        print(f"solde : {solde['balanceUsd']} USD")

        envoi = senndo.send_message(
            {
                "channel": "sms",
                "to": destinataire,
                "text": "senndo — exemple du SDK Python.",
                # La clé vient d'ici parce qu'un script n'a rien de métier à en dériver. Dans une
                # application, elle vient de VOTRE base : c'est la seule qui survive à un
                # redémarrage entre l'envoi et la réponse.
                "idempotencyKey": new_idempotency_key("exemple-python-"),
            }
        )
        print(f"envoyé : {envoi['id']} — état initial {envoi['status']}")

        time.sleep(3)
        message = senndo.get_message(envoi["id"])
        print(f"verdict : {message['status']} (code d'échec : {message.get('failureCode')})")
        print(f"facturé : {message.get('billedAmountUsd')} USD")
    except SenndoInsufficientFundsError:
        print("solde insuffisant — rechargez le compte.", file=sys.stderr)
        return 1
    except SenndoError as erreur:
        print(f"échec senndo : {erreur}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
