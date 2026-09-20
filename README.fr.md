# Zelinqa MCP

Adaptateur MCP officiel pour mener une conversation guidée par les objectifs.
**Version candidate, pas encore publiée.** Le SDK Python `zelinqa` doit être publié
avant `zelinqa-mcp`. Voir [le guide complet](README.md) et [la publication](PUBLISHING.md).

Le modèle manipule le texte des questions, les réponses, les libellés des choix et
un nom de conversation. Le SDK gère les identifiants de session, de question et de
décision ainsi que la version de l'état.

| Outil | Fonction |
|---|---|
| `zelinqa_start` | Démarrer une conversation nommée |
| `zelinqa_next_question` | Obtenir ou retrouver la question en attente |
| `zelinqa_answer` | Envoyer la réponse réelle et obtenir la suite |
| `zelinqa_add_context` | Ajouter un résumé de contexte |
| `zelinqa_status` | Relire la progression et la question en attente |
| `zelinqa_feedback` | Enregistrer le résultat métier observé |
| `zelinqa_forget` | Libérer la mémoire locale, sans supprimer les données serveur |

Installation après publication : `uvx zelinqa-mcp`. En attendant, utiliser le checkout
et `uv run zelinqa-mcp`. Configurer la clé runtime dans `ZELINQA_API_KEY` côté hôte,
jamais dans la conversation. Les exemples de configuration sont dans `examples/`.

Le transport est **stdio uniquement**, isolé par hôte/utilisateur de confiance.
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
