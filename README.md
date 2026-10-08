# Roast my CV

Tu envoies ton CV en PDF, « Si Lamine », un recruteur tunisien sans filtre, le roaste en derja.
Puis il redevient sérieux, tamponne une note sur 10 et te laisse un post-it avec ce qu'il faut corriger.

Trois niveaux : **Chwaya**, **Normal**, **Bla r7ma**.

## Stack

- **FastAPI** pour l'API (`POST /api/roast`) et la page web
- **pdfplumber** pour extraire le texte du CV
- **Groq** (LLM) en mode JSON pour générer le roast, les conseils, la note et le verdict
- Une seule page HTML / CSS / JS, sans framework, avec les polices Public Sans et Patrick Hand (licence OFL) incluses dans `static/fonts`

Aucune base de données : le CV est lu en mémoire puis oublié. L'e-mail et le numéro de téléphone
sont masqués avant l'envoi au modèle.

## Lancer le projet

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # puis colle ta clé dans .env
uvicorn main:app --reload
```

Ouvre http://localhost:8000.

Pour voir la page de résultat sans clé API, ouvre http://localhost:8000/?demo (un exemple de roast écrit à la main).

La clé API se crée gratuitement sur https://console.groq.com/keys.
Le modèle se change avec `GROQ_MODEL` dans `.env` (liste à jour : https://console.groq.com/docs/models).

## Le prompt

Tout se joue dans `prompts.py` :

- un persona précis (Si Lamine) et des exemples de ton en derja
- des limites claires : on se moque du contenu du CV, jamais de la personne (nom, genre, origine, physique...)
- le CV est placé entre balises `<cv>` et le modèle doit ignorer toute instruction qui s'y cache (protection contre l'injection de prompt)
- une sortie JSON validée par Pydantic côté serveur

## Idées pour aller plus loin

- Télécharger le résultat en image pour le partager (html2canvas)
- Lire les CV scannés avec un modèle vision
- Comparer le CV à une offre d'emploi collée par l'utilisateur
- Limiter le nombre de requêtes par IP avant de le mettre en ligne
- Déployer gratuitement sur Render ou Railway
