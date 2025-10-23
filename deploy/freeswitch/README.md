FreeSWITCH PoC configuration
=============================

This folder contains a minimal FreeSWITCH config used by the repo's Docker Compose
override to run a local FreeSWITCH instance for testing.

What is included
- Dockerfile: extends the official FreeSWITCH image and installs `curl`.
- `autoload_configs/`:
  - `modules.conf.xml` - enables `mod_event_socket` and other modules.
  - `event_socket.conf.xml` - configures the ESL port (8021) and a default password `ClueCon`.
- `dialplan/default.xml` - minimal dialplan that `answer`s and calls the app webhook via `curl`.
- `directory/default/1000.xml` - test SIP user `1000` with password `1234` for softphone testing.

Quick test (Docker Compose)
1. Build and start app + FreeSWITCH:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.freeswitch.yml up --build
   ```

2. Register a softphone to the FreeSWITCH server at UDP/TCP 5060 on the host. Use:
   - username: 1000
   - password: 1234
   - domain/host: (your host IP or `localhost` if running locally)

3. Make a call to any number that hits the default dialplan. The dialplan will POST a JSON payload to `http://app:8000/api/orchestration/emit/call.incoming` inside the Docker network.

Notes and next steps
- The ESL password defaults to `ClueCon`. Change it in `event_socket.conf.xml` for production.
- For programmatic control, the next step is to run an ESL connector (Python) which will connect to port 8021 and drive call flows.
