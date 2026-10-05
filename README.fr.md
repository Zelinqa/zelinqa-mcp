# Zelinqa MCP

Adaptateur MCP officiel pour mener une conversation guidée par les objectifs.
Le SDK Python `zelinqa` est une dépendance. Voir [le guide complet](README.md)
et [les prérequis de publication](RELEASING.md).

Le modèle manipule le texte des questions, les réponses, les libellés des choix et
un nom de conversation. `zelinqa_adjust` utilise aussi les identifiants métier
configurés des dimensions et informations. Le SDK gère les identifiants de session,
de question et de décision ainsi que la version de l'état.

| Outil | Fonction |
|---|---|
| `zelinqa_start` | Démarrer ou retrouver une conversation nommée et sa première question ou la question en attente |
| `zelinqa_next_question` | Envoyer la réponse et obtenir la suite ; sans réponse, réafficher la question en attente sans consommer de tour |
| `zelinqa_add_context` | Ajouter un résumé de contexte |
| `zelinqa_adjust` | Appliquer des données confirmées ou des statuts sans consommer de tour |
| `zelinqa_status` | Relire la progression et la question en attente |
| `zelinqa_feedback` | Enregistrer le résultat métier observé |
| `zelinqa_forget` | Libérer la mémoire locale, sans supprimer les données serveur |

La boucle utilise sept outils métier : `zelinqa_start` renvoie directement la
première question. La poser, attendre la réponse, puis appeler
`zelinqa_next_question` avec les mots de la personne ou les libellés exacts des
choix. Répéter jusqu'à l'arrêt ou l'atteinte de l'objectif, puis déclarer le vrai
résultat avec `zelinqa_feedback`. Réutiliser un nom ne crée pas une autre session.

Une question ouverte exige `user_text`, sauf `outcome: refused` ou
`outcome: asked_no_answer`. Les questions fermées et semi-ouvertes acceptent
`choice_labels` ; `free_text` peut compléter un choix semi-ouvert.
Sans champ de réponse, la question est seulement réaffichée. Une réponse invalide
rejetée localement peut être corrigée sans resynchronisation ni appel API.

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
réenvoyer aveuglément. À `max_turns`, la réponse porte `action: "stop"` et
`stop_reason: "max_turns_reached"`, et les appels suivants renvoient le même arrêt.
Une limite de tours atteinte ne signifie pas un objectif atteint.

Le même guide sert d'instructions au serveur et de ressource `zelinqa://guide`.
Un seul prompt, sans argument : `zelinqa_integration_check`. Leur lecture n'appelle pas l'API.
Le [skill Zelinqa](skills/zelinqa/SKILL.md) est fourni pour les agents compatibles.

Le mode `--advanced` conserve les six outils techniques avec identifiants explicites.
La gestion de configuration reste dans le SDK, avec ses permissions séparées.
