# Maps and location

Anuvarthan uses Mappls as the India-focused geospatial layer for mapping, search, geocoding, reverse geocoding, routing and distance. Anuvarthan remains the source of truth for users, donations, organisations, verification, assignments and impact.

## Architecture

Business screens consume normalized location services. They do not call Mappls REST APIs directly.

- Frontend: `services/location` + `MapCanvas`
- Backend: `app/services/location` + `/api/location/*`

Mappls answers “where is this place?”
Anuvarthan answers “is this place authorized and eligible to receive this resource?”

A Mappls POI is never an Anuvarthan destination.

## Configuration

Obtain keys from the official Mappls console: https://auth.mappls.com/console

Server REST (never expose these to Vite):

- `MAPPLS_ACCESS_TOKEN` — current static key, sent as `access_token` query parameter
- or legacy `MAPPLS_CLIENT_ID` + `MAPPLS_CLIENT_SECRET` for OAuth token generation

Browser (domain-whitelisted static key only):

- `VITE_MAPPLS_WEB_KEY`

Optional service-area overview (not a fake user location):

- `SERVICE_AREA_NAME`
- `SERVICE_AREA_CENTER_LAT`
- `SERVICE_AREA_CENTER_LNG`
- `SERVICE_AREA_RADIUS_KM`

## Flows

Search → autosuggest (`/search/places/autosuggest/json`) → optional place details (`/O2O/entity/place-details/{eLoc}`) → map pin → reverse geocode on drag-end → explicit confirm.

Routing uses `route.mappls.com` `route_adv` / `driving|biking|walking`. Coordinates in those URLs are `longitude,latitude`.

Distance matrix is used only after Anuvarthan has already filtered verified, active, category-compatible destinations.

## Privacy

Donor A cannot read Donor B’s donation. Volunteers and drivers see exact pickup coordinates only after assignment. Organisations see a donation only when it is matched to their destination.

## Fallback

If Mappls is not configured or the Web SDK fails, address text and operational status remain. Leaflet remains available only when `VITE_MAP_PROVIDER=leaflet`. The UI does not label a fallback route as a Mappls route.

## Route optimisation

Not enabled. No Mappls route-optimisation entitlement is assumed.

## Limitations

Place-details coordinates are a Mappls entitlement. If a selected place has a Mappls Pin but no coordinates, the user can drop a pin or use device GPS. PIN searches stay approximate.
