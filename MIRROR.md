# Dépôt miroir

Ce dépôt est un **miroir en lecture seule** du SDK Python de senndo. Le développement a lieu dans le
monorepo senndo, où vivent le contrat OpenAPI, le générateur qui en dérive les types des trois SDK,
et les suites de tests (conformité au contrat, fraîcheur du code généré, politique de retentative,
compilation des extraits du README).

Ces tests ne sont pas ici parce qu'ils lisent le contrat depuis un paquet privé : les publier
donnerait des fichiers qui échouent chez quiconque les lance.

Installation :

```bash
uv add senndo
```

Les rapports de bug et les demandes d'évolution sont les bienvenus dans les *issues* de ce dépôt.
