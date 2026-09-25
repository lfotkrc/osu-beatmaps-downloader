# osu-beatmaps-downloader
une app en python permettant de telecharger des beatmaps osu sans avoir besoin de se rendre sur le site officiel et donc vous n'avez pas besoin de vous créer de comptes

osu! Beatmap Downloader

Une application de bureau moderne et futuriste permettant de rechercher et télécharger facilement des beatmaps osu!.

L'interface est basée sur ttkbootstrap et propose plusieurs thèmes visuels, des miniatures de beatmaps et une barre de progression pour les téléchargements.

✨ Fonctionnalités
🔎 Recherche de beatmaps via l'API de Nerinyan
🖼️ Affichage des miniatures des covers
🎮 Filtres par mode :
osu!
Taiko
Catch
Mania
📊 Filtres par statut :
Ranked
Loved
Qualified
Pending
Graveyard
WIP
⭐ Filtre selon le nombre minimum d'étoiles
↕️ Plusieurs options de tri :
Pertinence
Popularité
Récent
Titre (A-Z)
🎨 Sélection du thème directement depuis l'application
⬇️ Téléchargement des beatmaps au format .osz
📈 Barre de progression pour chaque téléchargement
📁 Choix du dossier de téléchargement
🖥️ Interface pensée pour Windows
📦 Installation
Prérequis

Vous devez avoir Python 3 installé sur votre ordinateur.

Les dépendances nécessaires sont :

pip install ttkbootstrap requests pillow
Lancer le programme

Placez-vous dans le dossier contenant votre fichier Python, puis exécutez :

python <nom_de_votre_programme>.py

Remplacez <nom_de_votre_programme>.py par le nom réel de votre fichier Python.

Par exemple :

python osu_downloader.py
🪟 Créer un fichier .exe

Pour créer une version exécutable autonome sous Windows, installez d'abord PyInstaller :

pip install pyinstaller

Puis utilisez la commande suivante :

pyinstaller --onefile --windowed --name "osu-downloader" <nom_de_votre_programme>.py
Explication des options
--onefile : crée un seul fichier .exe
--windowed : lance l'application sans afficher de fenêtre console
--name "osu-downloader" : définit le nom du fichier exécutable

Une fois la compilation terminée, le fichier .exe sera disponible dans le dossier :

dist/

Vous pourrez donc retrouver votre programme ici :

dist/osu-downloader.exe
📂 Dossier de téléchargement

Par défaut, les beatmaps téléchargées sont enregistrées dans :

~/Downloads/osu_maps

Le dossier peut également être modifié directement depuis l'application.

🌐 API utilisée

Le programme utilise le miroir Nerinyan pour rechercher et télécharger les beatmaps :

https://api.nerinyan.moe/search
https://api.nerinyan.moe/d/{id}

Une connexion Internet est donc nécessaire pour effectuer les recherches et télécharger les beatmaps.

🛠️ Technologies utilisées
Python 3
Tkinter / ttkbootstrap — interface graphique
Requests — requêtes HTTP
Pillow — gestion des images
PyInstaller — création du .exe
⚠️ Remarque

Le programme utilise des services externes pour rechercher et télécharger les beatmaps. Leur disponibilité peut donc dépendre de ces services.
