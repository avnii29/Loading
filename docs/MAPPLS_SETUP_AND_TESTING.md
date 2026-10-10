# Mappls setup and location testing — Anuvarthan

## Credentials (do not invent values)

Obtain keys from [Mappls Console](https://auth.mappls.com/console). Enable products for:

- Web Maps SDK (browser static key, domain-whitelisted)
- Autosuggest / search
- Reverse geocode
- Routing / distance matrix (server)

### Backend `.env`

```env
MAP_PROVIDER=mappls
MAPPLS_ACCESS_TOKEN=           # server static token OR leave empty and use OAuth pair
MAPPLS_CLIENT_ID=
MAPPLS_CLIENT_SECRET=
```

Never put `MAPPLS_CLIENT_SECRET` in Vite/`VITE_*` variables.

### Frontend `.env`

```env
VITE_MAP_PROVIDER=mappls
VITE_MAPPLS_WEB_KEY=           # browser static key only; whitelist localhost:5173
```

If `VITE_MAPPLS_WEB_KEY` is empty, the UI uses **Leaflet/OpenStreetMap** and labels that provider honestly. It does not claim Mappls data is shown.

Official Web SDK load (documented):

`https://sdk.mappls.com/map/sdk/web?v=3.0&access_token=<Static Key>`

## Current-location behaviour

1. User taps **Use my location**.
2. Browser Geolocation runs with `enableHighAccuracy: true`, `maximumAge: 0`, timeout ~12s.
3. Device-reported accuracy radius and acquisition time are shown as **estimates**.
4. User must **Confirm this pickup point** before continuing.
5. Moving the pin clears GPS accuracy ownership (manual pin).
6. Permission denial / timeout → manual search or pin; no city default as “current location”.

## Real-device verification procedure

1. Open Anuvarthan on HTTPS or `http://localhost:5173`.
2. Enable device location services; grant browser permission.
3. Open **Donate** → location step → **Use my location**.
4. Record lat, lng, accuracy metres, acquisition time from the UI.
5. Visually check the marker; compare against an independent map app (both have uncertainty).
6. Move the pin; confirm accuracy label no longer claims GPS for the new pin.
7. Confirm and submit; reload donation detail — coordinates and accuracy (if GPS) persist.
8. Deny permission and verify search/pin still work.
9. Repeat indoors to observe larger reported accuracy radii.

Automated tests mock geolocation; they do **not** prove hardware GPS accuracy.

## Run

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

cd ..\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
