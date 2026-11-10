"""Historique quotidien des classements, pour les flèches de progression (▲ ▼ « Nouveau ») et le champion de la semaine.

Une photo par jour (heure de Paris) de chaque classement : grains, #infini, vocal, série, DeckFR, et le total des grains.
Elle est gardée 9 jours dans historique.json, sur la branche « data » du dépôt, mais jamais publiée sur le site.
Le dépôt pouvant être public, les membres n'y apparaissent que sous un identifiant haché (HMAC) dont la clé est
tirée d'un secret du dépôt : on ne peut pas relier un total à un membre.
"""
import datetime
import hashlib
import hmac
import json
import os
import pathlib
from zoneinfo import ZoneInfo

GARDER = 9  # jours d'historique


def aujourdhui():
    return datetime.datetime.now(ZoneInfo("Europe/Paris")).date()


class Historique:
    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin) if chemin else None
        self.cle = hashlib.sha256(("cafe-fr/historique|" + os.environ.get("CAFE_DB_URL", "")).encode()).digest()
        self.jours = {}
        if self.chemin and self.chemin.exists():
            try:
                self.jours = json.loads(self.chemin.read_text(encoding="utf-8")).get("jours", {})
            except (ValueError, AttributeError):
                self.jours = {}
        self.date = aujourdhui()

    def hacher(self, identifiant):
        return hmac.new(self.cle, str(identifiant).encode(), hashlib.sha256).hexdigest()[:16]

    def photo(self, metrique, valeurs):
        """Photo du jour d'un classement ({identifiant: valeur}), prise au premier relevé de la journée seulement."""
        jour = self.jours.setdefault(self.date.isoformat(), {})
        if metrique not in jour:
            jour[metrique] = {self.hacher(i): int(v) for i, v in valeurs.items() if v}

    def photo_valeur(self, metrique, valeur):
        jour = self.jours.setdefault(self.date.isoformat(), {})
        jour.setdefault(metrique, int(valeur))

    def reference(self, metrique, jours):
        """La photo d'il y a `jours` jours, sinon la plus ancienne d'avant aujourd'hui : (âge en jours, photo) ou None."""
        cible = (self.date - datetime.timedelta(days=jours)).isoformat()
        anciennes = sorted(d for d, p in self.jours.items() if d < self.date.isoformat() and metrique in p)
        if not anciennes:
            return None
        date = cible if cible in anciennes else (max((d for d in anciennes if d <= cible), default=None) or anciennes[0])
        return (self.date - datetime.date.fromisoformat(date)).days, self.jours[date][metrique]

    def evolutions(self, metrique, top):
        """Pour un top [(identifiant, valeur), …] : places gagnées (+) ou perdues (−) depuis hier, ou « nouveau »."""
        ref = self.reference(metrique, 1)
        if not ref:
            return [None] * len(top)
        photo = ref[1]
        rangs = {h: r for r, (h, _) in enumerate(sorted(photo.items(), key=lambda x: (-x[1], x[0])), 1)}
        return [(rangs[h] - rang if (h := self.hacher(i)) in rangs else "nouveau") for rang, (i, _) in enumerate(top, 1)]

    def plus_forte_hausse(self, metrique, valeurs, jours=7):
        """Le membre dont la valeur a le plus augmenté sur `jours` jours : (identifiant, hausse, âge réel) ou None."""
        ref = self.reference(metrique, jours)
        if not ref:
            return None
        age, photo = ref
        meilleur = max(((i, v - photo.get(self.hacher(i), 0)) for i, v in valeurs.items()), key=lambda x: x[1], default=None)
        return (meilleur[0], meilleur[1], age) if meilleur and meilleur[1] > 0 else None

    def ecart(self, metrique, valeur, jours=7):
        ref = self.reference(metrique, jours)
        return (valeur - ref[1], ref[0]) if ref and isinstance(ref[1], int) else None

    def enregistrer(self):
        if not self.chemin:
            return
        limite = (self.date - datetime.timedelta(days=GARDER)).isoformat()
        self.jours = {d: p for d, p in self.jours.items() if d >= limite}
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(json.dumps({"jours": self.jours}, separators=(",", ":")) + "\n", encoding="utf-8")
