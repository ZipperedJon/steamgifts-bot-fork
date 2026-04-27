# SteamGifts-Bot (Web UI Edition)

> [!NOTE]
> This is a modernized, Dockerized fork of the original [stilManiac/steamgifts-bot](https://github.com/stilManiac/steamgifts-bot). All original bot features remain, but with added backend architecture, multi-node webhook support, and a seamlessly animated graphical User Interface!

### Features
- Modern, dynamic Web UI with animated, glassmorphic aesthetics.
- Real-time logging console via Server-Sent Events.
- Live point tracker and automated giveaway entry configurations.
- Dynamic Web History pane pulling high-resolution game banners straight from the Valve content delivery network.
- Explicit formatting and 1-click test support for Deep Webhooks (Discord Embeds, Direct Telegram bots, or Raw n8n node feeds).
- Intelligent CSS Layouts featuring hash-routing (`#history`, `#settings`), allowing you to effortlessly iframe specific tabs flawlessly into Homarr dashboards!
- Fully Headless REST orchestration for zero-touch background execution.

<br>

🔥 **A massive shoutout to [Komodo](https://github.com/mbecker20/komodo) for making robust graphical Docker management absolutely incredible. Testing and managing this persistent container across iterations was an absolute breeze thanks to Komodo!** 🔥

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

## Star History

<a href="https://www.star-history.com/?repos=ZipperedJon%2Fsteamgifts-bot-fork&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=ZipperedJon/steamgifts-bot-fork&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=ZipperedJon/steamgifts-bot-fork&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=ZipperedJon/steamgifts-bot-fork&type=date&legend=top-left" />
 </picture>
</a>
