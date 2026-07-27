# Installatiehandleiding — Ubuntu server

Deze handleiding zet Weekmenu op een Ubuntu-server (getest voor
Ubuntu 22.04/24.04) met Docker. Je hebt SSH-toegang tot de server nodig.

## 1. Docker installeren op de server

Log in op de server en installeer Docker Engine + de Compose-plugin via
Docker's eigen apt-repository (aanbevolen boven de oudere `docker.io`-
package uit de Ubuntu-repo's, die achterloopt in versie):

```bash
# Oude versies opruimen (indien aanwezig)
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
  sudo apt-get remove -y $pkg
done

# Docker's repository toevoegen
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker installeren
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Jezelf toevoegen aan de docker-groep (voorkomt dat je overal sudo nodig hebt)
sudo usermod -aG docker $USER
```

Log daarna even uit en weer in (of `newgrp docker`) zodat de groepswijziging
actief wordt. Controleer:

```bash
docker --version
docker compose version
```

## 2. De code naar de server krijgen

Het project staat nog niet in een git-repository, dus de simpelste manier is
de projectmap direct kopiëren vanaf je eigen machine met `rsync` (of `scp`).
Draai dit **op je eigen computer**, niet op de server:

```bash
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
  "/pad/naar/Menuapp/" gebruiker@server-ip:~/menuapp/
```

Vervang `gebruiker@server-ip` door je eigen SSH-gebruikersnaam en het
IP-adres (of hostnaam) van je server. `node_modules`/`.venv` hoeven niet mee
— Docker installeert die opnieuw tijdens het bouwen van de images.

*Alternatief*: als je liever met git werkt voor toekomstige updates, maak dan
eerst een (eventueel privé) repository aan op GitHub/GitLab, initialiseer
git lokaal (`git init`, commit, push), en doe op de server een `git clone`.
Dat maakt latere updates een kwestie van `git pull` in plaats van opnieuw
rsync'en — geen vereiste, maar wel prettiger op de lange termijn.

## 3. Starten

Log in op de server, ga naar de projectmap en start de containers:

```bash
cd ~/menuapp
docker compose up -d --build
```

De eerste keer bouwen duurt een paar minuten (installeert Python- en
npm-dependencies). Controleer dat beide containers draaien:

```bash
docker compose ps
```

De app is nu bereikbaar op `http://<server-ip>:8080` vanaf elk apparaat in
hetzelfde netwerk.

Staat er een firewall aan (`sudo ufw status`)? Zet dan poort 8080 open:

```bash
sudo ufw allow 8080/tcp
```

## 4. Eerste gebruik

Recepten worden niet automatisch bij de eerste start opgehaald. Ga naar het
tabblad **Bronnen** en klik op **Synchroniseer alle bronnen** — dit kan
enkele minuten duren (de app haalt beleefd, met een kleine vertraging per
pagina, honderden receptpagina's per bron op). Daarna draait er automatisch
elke nacht om 03:00 een verse synchronisatie.

Stel daarna naar wens in:
- **Uitsluitingen** — allergieën/dingen die je niet wilt eten
- **Basisproducten** — wat je altijd in huis hebt (zout, olie, ...)
- **Instellingen** — standaard aantal hoofd-/voor-/nagerechten per week

## 5. Updaten

Wijzigingen doorgevoerd (lokaal aangepast en opnieuw ge-rsync't, of
`git pull` als je voor de git-route koos)? Herbouw en herstart:

```bash
cd ~/menuapp
docker compose up -d --build
```

Bestaande data (recepten, weekmenu's, instellingen) blijft behouden — die
staat in een aparte Docker-volume (`menuapp-data`), niet in de
containers zelf.

## 6. Back-ups

Alle data zit in één SQLite-bestand binnen de `menuapp-data`-volume. Een
back-up maken:

```bash
docker run --rm \
  -v menuapp_menuapp-data:/data \
  -v "$(pwd)":/backup \
  alpine cp /data/menuapp.db /backup/menuapp-backup-$(date +%F).db
```

(De volume-naam krijgt het projectmap-voorvoegsel, bv. `menuapp_menuapp-data`
— check de exacte naam met `docker volume ls` als dit commando een fout
geeft.) Terugzetten gaat met dezelfde aanpak, maar dan `cp` andersom.

## Problemen oplossen

Logs bekijken (bv. als de app niet bereikbaar is of een sync vastloopt):

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Container herstarten zonder opnieuw te bouwen:

```bash
docker compose restart backend
```

Container draait niet? `docker compose ps` toont de status; een container
die steeds herstart wijst meestal op een fout die in de logs staat.

## 7. Optioneel: buiten je eigen netwerk bereikbaar maken

Deze app heeft geen inlogscherm — bedoeld voor gebruik binnen je eigen
netwerk. Wil je 'm ook buitenshuis kunnen gebruiken, zet er dan een
reverse proxy met HTTPS *en* een vorm van toegangscontrole voor (bv.
[Tailscale](https://tailscale.com/) om je apparaten in hetzelfde
virtuele netwerk te krijgen zonder de app zelf publiek open te zetten, of
anders Caddy/nginx met Let's Encrypt + Basic Auth ervoor). Dat valt buiten
deze handleiding — vraag het gerust als je dat wil opzetten.
