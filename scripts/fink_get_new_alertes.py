import datetime

import requests

# Fix du DeprecationWarning
yesterday = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)).strftime("%Y%m%d")

print(f"Requête pour la date : {yesterday}")

# Nouvelle URL de l'API (depuis janvier 2025)
r = requests.post(
    "https://api.fink-portal.org/api/v1/statistics", json={"date": yesterday, "output-format": "json"}
)

print(f"Status HTTP : {r.status_code}")
print(f"Contenu brut : {r.text[:500]}")  # debug

if r.status_code == 200 and r.text:
    data = r.json()
    print(data)
else:
    print("Réponse vide ou erreur.")
