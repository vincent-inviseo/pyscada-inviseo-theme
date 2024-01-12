# pyscada-inviseo-theme

Le plugin PyScada `pyscada-inviseo-theme` est le thème pour le système SCADA Open Source `PyScada` développé par la société `Inviseo`.

## Installation

Cloner le dépôt du projet
```
git clone https://github.com/vincent-inviseo/pyscada-inviseo-theme.git
```

Déplacer le projet dans le dossier utilisateur de pyscada
```
cp -r pyscada-inviseo-theme /home/pyscada/
```

Donner les bons droits et le bon groupe au dossier du plugin
```
# Attribution du bon groupe utilisateur
sudo chown -R pyscada:pyscada /home/pyscada/pyscada-inviseo-theme

# Attribution des bons droits
sudo chmod -R 777 /home/pyscada/pyscada-inviseo-theme
```

Activer l'environnment virtuel de `PyScada`
```
source /home/pyscada/.venv/bin/activate
```

Installation du plugin `pyscada-inviseo-theme`
```
sudo -u pyscada -E env PATH=${PATH} pip3 install /home/pyscada/pyscada-inviseo-theme
```

Si vous désirez l'installer en mode `edition`
```
sudo -u pyscada -E env PATH=${PATH} pip3 install -e /home/pyscada/pyscada-inviseo-theme
```

Copie des fichiers statiques (CSS, JS, assets)
```
sudo -u pyscada -E env PATH=${PATH} python3 /var/www/pyscada/PyScadaServer/manage.py collectstatic
```

Modification du fichier `urls.py` pour la prise en compte de la réécriture de certaines routes
```
sudo -u pyscada nano /var/www/pyscada/PyScadaServer/PyScadaServer/urls.py
```

Ajouter le routing avant le `pyscada.core.urls` comme suit
```
urlpatterns = [
    path('', include('pyscada.theme.urls')), # Ajouter ici
    path('', include('pyscada.core.urls')),
]
```

Redémarrer gunicorn
```
sudo systemctl restart `gunicorn`
```

Redémarrer le service `pyscada`
```
sudo systemctl restart pyscada
```