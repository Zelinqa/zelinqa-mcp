# Serveur MCP NBQ

Serveur [Model Context Protocol](https://modelcontextprotocol.io) officiel de l'API
**NBQ** (Next Best Question) de Zelinqa. Il donne à un hôte LLM six outils pour mener une
conversation de qualification : votre agent pose les questions, NBQ décide laquelle vaut la
peine d'être posée ensuite.

```text
outil MCP  ->  SDK Python `nbq`  ->  API REST publique https://api.zelinqa.ai
```

Le serveur est un adaptateur de protocole, rien de plus. Il ne parle jamais HTTP lui-même,
n'importe jamais le moteur NBQ, n'ouvre aucune base de données et n'expose aucun score de
sélection.

> **État : pas encore publié.** `nbq-mcp` n'est pas sur PyPI, parce que le SDK `nbq` 1.0.0
> dont il dépend ne l'est pas non plus. Utilisez-le depuis un clone pour l'instant, comme
> décrit ci-dessous. Voir [`PUBLISHING.md`](PUBLISHING.md).

## Installation

Une fois publié, aucune installation n'est nécessaire : `uvx` le récupère et l'exécute.

```bash
uvx nbq-mcp            # pas encore disponible
```

Depuis un clone, aujourd'hui :

```bash
git clone https://github.com/Zelinqa/nbq-mcp.git
cd nbq-mcp
uv sync --group dev
uv run nbq-mcp --version
```

Python 3.11 ou plus récent.

## Configuration

Tout vient de l'environnement du processus serveur.

| Variable | Obligatoire | Défaut | Rôle |
|---|---|---|---|
| `NBQ_API_KEY` | **oui** | — | Clé d'API NBQ portant le scope `runtime`. Sans elle, le serveur refuse de démarrer (code de sortie `2`). |
| `NBQ_BASE_URL` | non | `https://api.zelinqa.ai` | URL de base alternative. |
| `NBQ_TIMEOUT_SECONDS` | non | défaut du SDK (30) | Délai HTTP par tentative. |
| `NBQ_MAX_RETRIES` | non | défaut du SDK (2) | Reprises sur erreur réseau, 429 et 5xx. |

Ligne de commande :

```text
nbq-mcp [--transport stdio|streamable-http] [--host HOST] [--port PORT]
        [--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL] [--version]
```

`stdio` est le transport par défaut, celui qu'utilisent tous les hôtes de bureau. Les logs
vont toujours sur stderr, jamais sur stdout qui porte le protocole MCP lui-même.

## Configuration des hôtes

Des fichiers prêts à copier sont dans [`examples/`](examples).

### Claude Code

```bash
claude mcp add nbq --env NBQ_API_KEY=$NBQ_API_KEY -- uvx nbq-mcp
```

Ou versionnez un [`.mcp.json`](examples/claude-code.mcp.json) au niveau du projet :

```json
{
  "mcpServers": {
    "nbq": {
      "command": "uvx",
      "args": ["nbq-mcp"],
      "env": { "NBQ_API_KEY": "${NBQ_API_KEY}" }
    }
  }
}
```

`${NBQ_API_KEY}` est résolu par Claude Code depuis votre environnement shell : le fichier
ne contient donc aucun secret et peut être commité.

### Claude Desktop

Ajoutez le contenu de [`examples/claude-desktop.json`](examples/claude-desktop.json) à
`claude_desktop_config.json` en remplaçant l'emplacement réservé par votre clé : Claude
Desktop ne résout pas les variables d'environnement. Redémarrez ensuite l'application.

### Codex CLI

Ajoutez le bloc de [`examples/codex-config.toml`](examples/codex-config.toml) à
`~/.codex/config.toml` :

```toml
[mcp_servers.nbq]
command = "uvx"
args = ["nbq-mcp"]
# Codex demande confirmation avant chaque appel d'outil MCP sauf si le serveur
# approuve ses outils ; en `codex exec` (non interactif) un appel non approuvé
# est rejeté avec « user cancelled MCP tool call ». Les six outils NBQ n'agissent
# que sur votre propre NBQ.
default_tools_approval_mode = "approve"
env = { NBQ_API_KEY = "PASTE_YOUR_RUNTIME_KEY_HERE" }
```

### Cursor

Ajoutez [`examples/cursor.mcp.json`](examples/cursor.mcp.json) comme `.cursor/mcp.json`
dans le projet, ou comme `~/.cursor/mcp.json` globalement.

### Exécution depuis un clone

Avant la publication sur PyPI, pointez l'hôte vers votre clone avec
[`examples/local-dev.mcp.json`](examples/local-dev.mcp.json) (ou
[`examples/local-dev-codex-config.toml`](examples/local-dev-codex-config.toml)) :

```json
{
  "mcpServers": {
    "nbq": {
      "command": "uv",
      "args": ["run", "--directory", "/chemin/absolu/vers/nbq-mcp", "nbq-mcp"],
      "env": { "NBQ_API_KEY": "${NBQ_API_KEY}" }
    }
  }
}
```

## Les six outils

| Outil | Route API | Rôle |
|---|---|---|
| `nbq_create_session` | `POST /v1/sessions` | Crée une session pour une conversation. Renvoie l'état initial ; pas encore de question. |
| `nbq_resume_session` | `GET /v1/sessions/{id}` | Reprend une session existante et réapprend son `state_version` et ses candidats en attente. |
| `nbq_next` | `POST /v1/sessions/{id}/next` | Comprend le tour précédent, puis renvoie les questions suivantes classées. |
| `nbq_apply_events` | `POST /v1/sessions/{id}/events` | Applique du contexte ou une donnée connue sans sélectionner de question et sans consommer de tour. |
| `nbq_get_session` | `GET /v1/sessions/{id}` | Lit l'état public de la session. |
| `nbq_submit_feedback` | `POST /v1/sessions/{id}/feedback` | Déclare ce que la conversation a réellement produit. |

Les routes de configuration sont volontairement absentes : ce serveur ne porte que la
surface runtime, un hôte n'a donc besoin de rien d'autre qu'une clé `runtime`.

### Le protocole de tour

1. `nbq_create_session` une fois par conversation.
2. `nbq_next` **sans `previous_turn`** pour le premier tour. Posez le candidat de rang 1,
   reformulé si vous le souhaitez.
3. `nbq_next` à nouveau, en passant ce qui s'est réellement produit :

   ```json
   {
     "session_id": "ses_01J8Z",
     "previous_turn": {
       "assistant_text": "Et côté budget, vous vous situez dans quelle fourchette ?",
       "user_text": "Autour de 2 000 euros, je ne veux pas dépasser 2 500."
     }
   }
   ```

   `decision_id`, `question_id` et `outcome` sont des aides optionnelles, pas des
   identifiants à fabriquer : NBQ résout la candidate utilisée depuis la décision en
   attente et votre texte. Pour une question à choix, envoyez
   `structured_answer: {"choice_ids": ["choice_1m"]}` avec des identifiants copiés depuis
   les `choices` du candidat — ce chemin est déterministe et ne coûte aucun appel LLM.
   Omettre `user_text` est autorisé quand une réponse structurée ou `client_updates`
   portent déjà l'information : le tour est alors compris en mode réduit, signalé dans
   `degraded_reasons`.
4. Répétez. **C'est vous qui décidez d'arrêter.** NBQ continue de proposer la meilleure
   question disponible et signale la situation dans `warnings` : `max_turns_reached`
   (limite souple atteinte), `objective_achieved` (conditions de réussite satisfaites),
   `eligibility_exhausted_fallback`, `constraints_relaxed`. Un `action: "stop"` avec
   `stop_reason: "no_question_available"` est le seul arrêt dur : il n'existe réellement
   plus aucune question.
5. `nbq_submit_feedback` une fois le résultat réel connu.

Chaque résultat est un JSON structuré portant les champs du contrat — `candidates` avec
`rank` / `question_id` / `text` / `type` / `choices` / `target_ids`, `progress`,
`turn_count`, `turns_remaining`, `warnings`, `degraded`, `degraded_reasons`, `request_id`.
Rien n'est filtré.

### `state_version`, sans conflit caché

Chaque mutation est protégée par un contrôle optimiste. Le serveur retient le dernier
`state_version` vu pour chaque session : vous pouvez donc omettre `state_version`, il
envoie celui qu'il a suivi ; s'il n'a jamais vu la session, il la lit d'abord. Un
`state_version` explicite est toujours prioritaire.

Un conflit n'est jamais résolu silencieusement. Quand l'API refuse la version, vous
recevez une erreur lisible nommant `supplied_state_version`, `current_state_version` et
l'instruction *call nbq_get_session then retry*, et la valeur périmée est oubliée plutôt
que rejouée.

Chaque appel d'outil mutant est une mutation logique : le SDK génère sa clé
`Idempotency-Key` et la réutilise sur ses propres reprises, si bien qu'un échec réseau
transitoire ne double jamais un tour. Appeler deux fois le même outil volontairement
correspond à deux mutations, pas à un rejeu.

## Sémantique des erreurs

Les échecs remontent comme des erreurs d'outil MCP dont le texte est fait pour être
actionnable :

```text
state_version_conflict: La session a été modifiée depuis votre dernière lecture. (request_id=req_9003)
  — call nbq_get_session then retry
  — {"current_state_version":8,"supplied_state_version":7}
```

- Les erreurs métier gardent leur enveloppe de contrat :
  `<code>: <message> (request_id=<id>)`, suivi des `details` pertinents en JSON compact —
  `required_scopes` / `granted_scopes`, `supplied_state_version` /
  `current_state_version`, `invalid_choice_ids`, `candidate_question_ids`, etc.
- Un refus d'authentification ou d'autorisation par la passerelle devient :

  ```text
  unauthorized (HTTP 403): the NBQ API key is missing, invalid, revoked, expired,
  or does not carry the `runtime` scope (check NBQ_API_KEY)
  ```

  La passerelle déployée répond un `403` sans enveloppe pour une clé invalide, révoquée ou
  au mauvais scope : ces cas sont réellement indiscernables de l'extérieur, le message
  nomme donc toutes les possibilités au lieu d'en deviner une. Un en-tête `Authorization`
  absent donne le même message avec `HTTP 401`.
- Un échec réseau après les reprises du SDK devient un `connection_error` lisible.
- Des arguments qui ne peuvent pas satisfaire le contrat sont refusés avant tout appel
  réseau, en nommant le champ fautif.

## Sécurité

- La clé d'API est lue depuis `NBQ_API_KEY` dans le processus serveur uniquement. Elle
  n'apparaît jamais dans une ligne de log, un résultat d'outil, un message d'erreur ni une
  trace ; toute clé configurée trouvée dans une chaîne sortante est remplacée par
  `[redacted]`.
- Utilisez une clé qui ne porte que le scope `runtime`.
- Sur stdio, stdout est le canal du protocole : tous les logs vont sur stderr, et aucun
  corps de requête ni contenu de conversation n'est journalisé.
- Voir [`SECURITY.md`](SECURITY.md) pour signaler une vulnérabilité.

## Développement

```bash
uv sync --group dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest            # la suite live est exclue par défaut
```

La suite unitaire exécute le vrai serveur en mémoire via le transport MCP in-process,
contre un faux client SDK asynchrone renvoyant les charges utiles des exemples du contrat
V1. Aucun appel réseau.

### Tests live

La suite live lance le vrai processus `nbq-mcp` en stdio et parle à la vraie API. Elle est
opt-in et ignorée sauf si `NBQ_LIVE=1` :

```bash
NBQ_LIVE=1 \
NBQ_LIVE_RUNTIME_KEY=<clé runtime> \
NBQ_LIVE_BASE_URL=https://api.zelinqa.ai \
uv run pytest -m live tests/live -s
```

Des clés optionnelles activent les cas négatifs : `NBQ_LIVE_REVOKED_KEY` et
`NBQ_LIVE_CONFIG_READ_KEY` (une clé sans le scope `runtime`). Les tests dont la clé n'est
pas fournie sont ignorés. La suite n'affiche que des `request_id` et des codes d'erreur,
jamais une clé ni un verbatim, et espace ses appels `/next` d'une seconde pour respecter le
quota Bedrock de staging.

## Licence

Apache-2.0 — voir [`LICENSE`](LICENSE).
