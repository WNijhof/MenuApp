# Installation guide — Ubuntu server

This guide sets up Weekmenu on an Ubuntu server (tested on Ubuntu
22.04/24.04) with Docker. You'll need SSH access to the server.

## 1. Install Docker on the server

Log in to the server and install Docker Engine + the Compose plugin via
Docker's own apt repository (recommended over the older `docker.io`
package from the Ubuntu repos, which lags behind in version):

```bash
# Remove old versions (if present)
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
  sudo apt-get remove -y $pkg
done

# Add Docker's repository
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add yourself to the docker group (avoids needing sudo everywhere)
sudo usermod -aG docker $USER
```

Then log out and back in (or run `newgrp docker`) so the group change
takes effect. Verify:

```bash
docker --version
docker compose version
```

## 2. Getting the code onto the server

Log in to the server via SSH and clone the repository:

```bash
mkdir -p ~/menuapp
cd ~/menuapp
git clone https://github.com/WNijhof/MenuApp.git .
```

No git available, or prefer to copy manually? An `rsync`/`scp` of the
project folder works just as well, run **from your own computer** (not on
the server):

```bash
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' \
  "/path/to/Menuapp/" user@server-ip:~/menuapp/
```

Replace `user@server-ip` with your own SSH username and your server's IP
address (or hostname).

## 3. Starting

From the project folder on the server:

```bash
cd ~/menuapp
docker compose up -d
```

Every push to the `main` branch automatically builds the backend and
frontend images and publishes them to the GitHub Container Registry —
so `docker compose up -d` **pulls** those ready-made images instead of
building them locally, which makes the first start a lot faster. Check
that both containers are running:

```bash
docker compose ps
```

The app is now reachable at `http://<server-ip>:8080` from any device on
the same network.

(Prefer to build from source yourself, e.g. after a local change? Add
`--build`: `docker compose up -d --build`.)

Is a firewall enabled (`sudo ufw status`)? Then open port 8080:

```bash
sudo ufw allow 8080/tcp
```

## 4. First use

Recipes aren't fetched automatically on first start. Go to the
**Sources** tab and click **Sync all sources** — this can take a few
minutes (the app fetches politely, with a small delay per page, hundreds
of recipe pages per source). After that, a fresh sync runs automatically
every night at 03:00.

Then configure to taste:
- **Exclusions** — allergies/things you don't want to eat
- **Pantry staples** — what you always have on hand (salt, oil, ...)
- **Settings** — default number of mains/starters/desserts per week

## 5. Updating

```bash
cd ~/menuapp
git pull                # or: rsync again if you're not using git
docker compose pull     # fetch the latest published images
docker compose up -d
```

Existing data (recipes, weekly menus, settings) is preserved — it lives
in a separate Docker volume (`menuapp-data`), not in the containers
themselves.

## 6. Backups

All data lives in one SQLite file inside the `menuapp-data` volume.
Making a backup:

```bash
docker run --rm \
  -v menuapp_menuapp-data:/data \
  -v "$(pwd)":/backup \
  alpine cp /data/menuapp.db /backup/menuapp-backup-$(date +%F).db
```

(The volume name gets the project-folder prefix, e.g.
`menuapp_menuapp-data` — check the exact name with `docker volume ls` if
this command errors.) Restoring works the same way, just with `cp`
reversed.

## Troubleshooting

Viewing logs (e.g. if the app is unreachable or a sync gets stuck):

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Restarting a container without rebuilding:

```bash
docker compose restart backend
```

Container not running? `docker compose ps` shows the status; a container
that keeps restarting usually points to an error visible in the logs.

## 7. Optional: making it reachable outside your own network

This app has no login screen — it's meant for use within your own
network. Want to use it away from home too? Put a reverse proxy with
HTTPS *and* some form of access control in front of it (e.g.
[Tailscale](https://tailscale.com/) to get your devices onto the same
virtual network without exposing the app itself publicly, or otherwise
Caddy/nginx with Let's Encrypt + Basic Auth in front). That's outside the
scope of this guide — feel free to ask if you'd like help setting it up.
