# SteamGifts-Bot (Web UI Edition)

![](https://i.imgur.com/oCob3wQ.gif)

> [!NOTE]
> This is a modernized, Dockerized fork of the original [stilManiac/steamgifts-bot](https://github.com/stilManiac/steamgifts-bot). All original bot features remain, but with added backend architecture and a full graphical User Interface!

### Features
- Modern, dynamic Web UI with glassmorphic aesthetics.
- Real-time logging through Server-Sent Events.
- Automated entry into giveaways.
- Configurable settings via UI (Sleep times, min points, pinned giveaways).
- Undetectable (Emulates Chrome User-Agent and handles cookies properly).
- Headless Docker integration for 24/7 unassisted operation.

### Recommended Installation (Docker)

The absolute easiest way to run the bot is through Docker Compose.

1. Ensure you have Docker installed on your host.
2. Clone this repository, and open a terminal inside the project folder.
3. Run: `docker-compose up -d`.
   > *The enclosed `docker-compose.yml` makes it a single-command deployment!*
4. Head to `http://localhost:1738` via your web browser to initialize the bot using your `PHPSESSID`.

#### Example Standard `docker-compose.yml`:
If you choose to run out-of-context without cloning, copy this setup into an empty folder where your bot source lives:
```yaml
services:
  steamgifts-bot:
    image: ghcr.io/zipperedjon/steamgifts-bot-fork:latest
    container_name: steamgifts-bot
    ports:
      - "1738:1738"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Getting Your PHPSESSID Cookie
1. Sign in on [SteamGifts.com](https://www.steamgifts.com/) via Steam.
2. Open your browser Developer Tools (F12) -> Application -> Cookies.
3. Copy the value string corresponding to `PHPSESSID`.

### Help
Please leave your feedback and bugs in the `Issues` page!
