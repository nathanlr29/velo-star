"""Surveille la disponibilité des vélos STAR et envoie une notification ntfy.

Aucune dépendance externe : uniquement la bibliothèque standard de Python.
Variables d'environnement :
  NTFY_TOPIC  nom du topic ntfy (secret GitHub, obligatoire)
  WATCH       ids des tailles à surveiller, séparés par des virgules (défaut : 3,4)
  TEST        "true" pour envoyer une notification de test
"""
import os
import re
import sys
import urllib.parse
import urllib.request

URL = "https://location-velo.star.fr/fr/catvehicletype/list"
PAGE = "https://location-velo.star.fr/fr/pages/location-longue-duree"

NAMES = {
    "3": "VAE taille M",
    "4": "VAE taille S",
    "7": "Cargo",
    "8": "Longtail",
    "9": "Cargotail",
}
WATCH = [v.strip() for v in os.environ.get("WATCH", "3,4").split(",") if v.strip()]
TOPIC = os.environ.get("NTFY_TOPIC", "").strip()


def notify(title, message, priority="high"):
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,        # ASCII uniquement dans les en-têtes
            "Priority": priority,
            "Tags": "bike",
            "Click": PAGE,         # un appui sur la notif ouvre le site
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=15).close()


def fetch():
    req = urllib.request.Request(
        URL,
        data=urllib.parse.urlencode({"data": "2"}).encode(),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://location-velo.star.fr",
            "Referer": PAGE,
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def main():
    if not TOPIC:
        sys.exit("NTFY_TOPIC manquant : ajoutez-le dans les secrets du dépôt")

    if os.environ.get("TEST") == "true":
        notify("Test velo STAR", "Les notifications fonctionnent.", "default")
        print("Notification de test envoyée")

    html = fetch()
    options = re.findall(
        r'<option value="(\d+)"[^>]*data-limit-nbdossier="(-?\d+)"[^>]*data-nbdossier="(\d+)"',
        html,
    )
    if not options:
        sys.exit("Aucune option trouvée : requête bloquée, page modifiée ou paramètre incorrect")

    state = {v: (int(nb) < int(limit), nb, limit) for v, limit, nb in options}

    disponibles = []
    for v in WATCH:
        if v not in state:
            print(f"{NAMES.get(v, v)} : absent de la réponse")
            continue
        ok, nb, limit = state[v]
        print(f"{NAMES.get(v, v)} : {'DISPONIBLE' if ok else 'indisponible'} ({nb}/{limit})")
        if ok:
            disponibles.append(NAMES.get(v, v))

    if disponibles:
        notify("Velo STAR disponible !", "Disponible : " + ", ".join(disponibles))
        print("Notification envoyée")


if __name__ == "__main__":
    main()
