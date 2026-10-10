# Mappls implementation audit — Anuvarthan (root app)

**Date:** 2026-10-09  
**Workspace:** `frontend/` + `backend/` (hackathon folder removed)  
**Docs verified:** [Mappls Web Maps JS](https://developer.mappls.com/documentation/sdk/Web/Web%20JS/) (SDK `v=3.0`, `access_token` query param; Aug 2025 auth line)

## Credential boundary (current)

| Credential | Where | Status in this workspace |
| --- | --- | --- |
| Browser static key `VITE_MAPPLS_WEB_KEY` | Frontend only | Empty in `.env` → Leaflet/OSM fallback |
| Server `MAPPLS_ACCESS_TOKEN` or OAuth client id/secret | Backend only | Empty → location REST returns provider-unavailable errors honestly |
| Domain whitelist | Mappls Console | Required when browser key is issued |

No fake keys were generated.

## Audit table

| Area | Existing implementation | Missing or broken behavior | Planned change | Verification |
| --- | --- | --- | --- | --- |
| Map rendering | `MapCanvas` → Mappls SDK 3.0 or Leaflet | Silent Leaflet fallback; India centroid as **viewport** default only | Label active provider; keep centroid as map camera only | Visual + unit |
| Current location | `BrowserLocationProvider` `enableHighAccuracy`, `maximumAge:0`, refine watch | Status never shows `refining`; accuracy thresholds not UX-labeled | Accuracy bands, freshness stamp, retry | Manual + mocked geolocation tests |
| Location search | Backend `/api/location/search` → Mappls autosuggest | Fails closed when Mappls unconfigured (correct) | Keep; clearer empty/error copy | API tests |
| Reverse geocoding | `/api/location/reverse-geocode` | OK; pin adjust must clear GPS accuracy ownership | Clear accuracy when pin moved | Frontend logic |
| Location persistence | Donation: lat/lng, accuracy, source, mappls_pin, captured/confirmed, landmark | Migration `d5e9a13c4f36` | Applied via Alembic | pytest + alembic |
| Accuracy metadata | Circle when `accuracy` present; detail page labels device-reported bands | — | Pass through only for DEVICE_GEOLOCATION | UI + pytest |
| Route display | `RoutePreview` + `/api/location/route` | Needs real Mappls routing credentials | Wire volunteer/driver/detail; honest empty without endpoints | API + UI |
| Privacy | Auth on location proxy; volunteer gated | Org coords public to authenticated users (existing product rule) | Keep; no public unauth dump | Existing tests |

## Implementation status (post-work)

| Requirement | Status |
| --- | --- |
| Mappls Web SDK v3.0 script loader with `access_token` | Implemented; inactive without browser key |
| Leaflet fallback labeled as OpenStreetMap | Implemented |
| Browser geolocation + accuracy UX | Implemented |
| LocationPicker confirm / landmark / pin adjust | Implemented |
| Donation + org workflows | Integrated |
| Backend validation (Null Island, accuracy strip) | Implemented |
| Route preview UI | Wired; live road geometry needs Mappls routing credentials |
| Real-device GPS | Documented in `MAPPLS_SETUP_AND_TESTING.md` — not executed in this session |

## Baseline / regression commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest tests/test_location.py -q
cd ..\frontend
npm run build
```

**Classification target:** READY WITH DOCUMENTED LIMITATIONS until Mappls console keys are enabled and a real-device geolocation pass is recorded.
