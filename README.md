# Weekmenu

Zelf te hosten webapp voor het samenstellen van je weekmenu. Haalt recepten op
van de sites die je zelf configureert (standaard gevuld met de Nederlandse
receptensites van [kadaza.nl/recepten](https://www.kadaza.nl/recepten)),
verdeelt willekeurig 7 dagen met variatie in gerecht-type, en houdt rekening
met ingrediënten die je wilt uitsluiten (bv. "vis" sluit ook kabeljauw, zalm,
... uit).

## Screenshots

| Weekmenu | Boodschappenlijst |
|---|---|
| ![Weekmenu-overzicht met per dag een recept](docs/screenshots/weekmenu.jpg) | ![Automatisch samengestelde boodschappenlijst](docs/screenshots/boodschappenlijst.jpg) |

| Recepten | Bronnen |
|---|---|
| ![Doorzoekbare receptenlijst met waardering](docs/screenshots/recepten.jpg) | ![Beheer van receptensites en hun synchronisatiestatus](docs/screenshots/bronnen.jpg) |

## Hoe het werkt

- **Bronnen**: elke bron is een receptensite. De app zoekt zelf de sitemap
  van de site, vindt receptpagina's daarin, en leest per pagina de
  gestructureerde receptgegevens (schema.org/Recipe) uit die vrijwel alle
  moderne receptensites al standaard in hun paginacode hebben staan. Er is
  dus geen site-specifieke scraper-code nodig — voeg een nieuwe site toe via
  het tabblad **Bronnen** en synchroniseer.
- **Uitsluitingen**: via het tabblad **Uitsluitingen** kun je een categorie
  (vis, noten, varken, zuivel, ...) of een los ingrediënt opgeven. Categorieën
  worden uitgebreid met synoniemen via `backend/app/data/taxonomy.json` —
  pas dit bestand aan om zelf categorieën/synoniemen toe te voegen.
- **Weekmenu**: de 7 dagen worden willekeurig gevuld, verdeeld over
  verschillende gerecht-types (soep, pasta, vis, vlees, vegetarisch, ...) zodat
  de week niet steeds hetzelfde soort gerecht bevat. Met de ↻-knop op een dag
  wissel je dat ene recept voor een ander.

## Starten (Docker)

Elke push naar `main` bouwt de backend- en frontend-image automatisch en
publiceert ze naar GitHub Container Registry
(`ghcr.io/wnijhof/menuapp-backend` / `menuapp-frontend`, zie
`.github/workflows/docker-publish.yml`). Dat betekent: **geen lokale build
nodig om te installeren** — `docker compose` haalt de kant-en-klare images
op.

### Optie 1: docker compose (aanbevolen)

**1. Maak een map en haal de code op**, op de machine waar de app moet
draaien (bv. je Ubuntu-server, via SSH) — enkel `docker-compose.yml` is
eigenlijk nodig, maar de hele repo clonen is simpeler:

```bash
mkdir -p ~/weekmenu
cd ~/weekmenu
git clone https://github.com/WNijhof/MenuApp.git .
```

Geen git beschikbaar, of liever handmatig kopiëren? Dan volstaat ook een
`rsync`/`scp` van de projectmap vanaf je eigen computer naar `~/weekmenu` op
de server — sla dan de `git clone`-stap hierboven over.

**2. Start de containers**, vanuit diezelfde map:

```bash
cd ~/weekmenu
docker compose up -d
```

Dit **pullt** de vooraf gebouwde images (geen lokale build, dus snel) en
start beide containers inclusief het gedeelde netwerk en het opslagvolume
voor de database. Controleer dat beide draaien:

```bash
docker compose ps
```

De app is dan bereikbaar op `http://<server-ip>:8080`.

**3. Beheren:**

```bash
docker compose logs -f backend   # logs bekijken
docker compose restart backend   # container herstarten
docker compose down              # stoppen (database blijft bewaard in het menuapp-data-volume)
```

**4. Bijwerken** naar een nieuwere versie:

```bash
cd ~/weekmenu
docker compose pull   # haalt de nieuwste gepubliceerde images op
docker compose up -d
```

**Liever zelf bouwen vanaf de broncode** (bv. om lokale wijzigingen te
testen) in plaats van de gepubliceerde images te gebruiken? Voeg `--build`
toe — dat overschrijft de gepullde image met een lokaal gebouwde:

```bash
docker compose up -d --build
```

### Optie 2: losse docker run-commando's

Zonder Compose start je zelf twee containers, met de vooraf gebouwde images
(`docker pull` in plaats van `docker build`). Ze moeten op hetzelfde
Docker-netwerk zitten **en** de backend-container moet exact `backend` heten
— de frontend-container (nginx) stuurt `/api`-verzoeken door naar
`http://backend:8000`, wat alleen werkt via Docker's eigen naam-resolutie
binnen een gedeeld netwerk:

```bash
# Eigen netwerk en volume voor persistente data
docker network create weekmenu-net
docker volume create weekmenu-data

# Vooraf gebouwde images ophalen (geen lokale build nodig)
docker pull ghcr.io/wnijhof/menuapp-backend:latest
docker pull ghcr.io/wnijhof/menuapp-frontend:latest

# Backend starten (naam "backend" is verplicht, zie hierboven)
docker run -d \
  --name backend \
  --network weekmenu-net \
  --restart unless-stopped \
  -v weekmenu-data:/data \
  ghcr.io/wnijhof/menuapp-backend:latest

# Frontend starten, poort 8080 op de host
docker run -d \
  --name frontend \
  --network weekmenu-net \
  --restart unless-stopped \
  -p 8080:80 \
  ghcr.io/wnijhof/menuapp-frontend:latest
```

De app is nu ook bereikbaar op `http://<server-ip>:8080`. Bijwerken: nieuwe
images pullen, containers vervangen (`docker rm -f backend frontend` en
opnieuw `docker run`) — het `weekmenu-data`-volume blijft ongemoeid bestaan.

Liever zelf bouwen vanaf de broncode? Vervang de `docker pull`-regels door
`docker build -t weekmenu-backend ./backend` (en `weekmenu-frontend` voor de
frontend), en gebruik die naam in plaats van de `ghcr.io/...`-image in de
`docker run`-commando's.

### Eerste gebruik (beide opties)

Recepten worden niet automatisch bij de eerste start opgehaald — ga naar
**Bronnen** en klik op **Synchroniseer alle bronnen** (kan een paar minuten
duren). Daarna draait er ook een automatische dagelijkse synchronisatie
('s nachts om 03:00).

## Zelf bronnen toevoegen

Vul in het tabblad **Bronnen** een naam en de URL van de site in (de
homepage of een receptenoverzicht-pagina volstaat, bv.
`https://www.voorbeeld.nl/recepten`). De app zoekt zelf naar
`sitemap.xml`/`robots.txt` om receptpagina's te vinden. Werkt de site niet
met een sitemap, of staat er geen schema.org-data op de paginas, dan worden
er simpelweg geen recepten gevonden voor die bron — dat is een beperking van
de site zelf, niet iets om te configureren.

Losse recepten (één specifieke pagina) kun je direct toevoegen via het
tabblad **Recepten** → voeg toe via URL.

## Lokale ontwikkeling (zonder Docker)

Backend:

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate  # of source .venv/bin/activate op Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

De Vite dev-server proxyt `/api` naar `http://localhost:8000`.
