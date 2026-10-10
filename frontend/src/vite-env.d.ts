/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_MAP_TILE_URL?: string;
  readonly VITE_MAP_ATTRIBUTION?: string;
  readonly VITE_GEOCODER_URL?: string;
  readonly VITE_ROUTING_URL?: string;
  readonly VITE_MAP_PROVIDER?: string;
  readonly VITE_MAPPLS_WEB_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
