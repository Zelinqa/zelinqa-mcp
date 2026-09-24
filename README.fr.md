# Zelinqa MCP

Adaptateur MCP officiel pour mener une conversation guidée par les objectifs.
Le SDK Python `zelinqa` est une dépendance. Voir [le guide complet](README.md)
et [les prérequis de publication](PUBLISHING.md).

Le modèle manipule le texte des questions, les réponses, les libellés des choix et
un nom de conversation. `zelinqa_adjust` utilise aussi les identifiants métier
configurés des dimensions et informations. Le SDK gère les identifiants de session,
de question et de décision ainsi que la version de l'état.

| Outil | Fonction |
|---|---|
| `zelinqa_start` | Démarrer une conversation nommée |
| `zelinqa_next_question` | Obtenir ou retrouver la question en attente |
| `zelinqa_answer` | Envoyer la réponse réelle et obtenir la suite |
| `zelinqa_add_context` | Ajouter un résumé de contexte |
| `zelinqa_adjust` | Appliquer des données confirmées ou des statuts sans consommer de tour |
| `zelinqa_status` | Relire la progression et la question en attente |
| `zelinqa_feedback` | Enregistrer le résultat métier observé |
| `zelinqa_forget` | Libérer la mémoire locale, sans supprimer les données serveur |

Une fois disponible sur PyPI : `uvx zelinqa-mcp`. Depuis les sources :
`uv run zelinqa-mcp`. Configurer la clé runtime dans `ZELINQA_API_KEY` côté hôte,
jamais dans la conversation. Les exemples de configuration sont dans `examples/`.

Le transport est **stdio uniquement**, isolé par hôte/utilisateur de confiance.
Si le système connaît déjà une réponse, `zelinqa_adjust` accepte une donnée
(`id` et `value`, ou `operation: unset | not_applicable`), une dimension
(`id`, `status: achieved | not_achieved | excluded`) ou l'objectif
(`achieved | not_achieved`). Utiliser les identifiants métier configurés, jamais
des valeurs inventées. Une erreur de conflit exige `zelinqa_status` avant de réessayer.
Une question déjà proposée n'est pas recalculée par `zelinqa_adjust` : vérifier
la vue renvoyée, et appliquer de préférence les ajustements avant de demander la suite.
Le serveur conserve au maximum 128 conversations locales. Après redémarrage, l'hôte
doit fournir `ZELINQA_SESSION_ID` et `ZELINQA_CONVERSATION` pour reprendre une session.
Il ne faut pas envoyer deux réponses simultanément pour la même conversation.
Après erreur ou interruption : `zelinqa_status`, puis vérifier où reprendre, sans
réenvoyer aveuglément. Une limite de tours atteinte ne signifie pas un objectif atteint.

Ressource : `zelinqa://guide`. Prompts sélectionnés par l'utilisateur :
`zelinqa_conversation` et `zelinqa_integration_check`. Leur lecture n'appelle pas l'API.
Le [skill Zelinqa](skills/zelinqa/SKILL.md) est fourni pour les agents compatibles.

Le mode `--advanced` conserve les six outils techniques avec identifiants explicites.
La gestion de configuration reste dans le SDK, avec ses permissions séparées.
