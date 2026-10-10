import L from "leaflet";
import type { MapMarkerKind } from "../../services/location/types";

function pictureIcon(url: string, size = 52) {
  return L.icon({
    iconUrl: url,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    className: "map-picture-icon",
  });
}

export const houseIcon = pictureIcon("/images/markers/donor-house.png?v=3");
export const volunteerIcon = pictureIcon("/images/markers/volunteer-scooter.png?v=3");
export const orgIcon = pictureIcon("/images/markers/organisation-building.png?v=3");
export const driverIcon = volunteerIcon;
export const gpsDotIcon = L.divIcon({
  className: "map-gps-dot",
  html: '<div class="map-gps-core"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});
export const defaultPin = L.divIcon({
  className: "map-pin",
  html: "<span></span>",
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

export function iconForKind(kind?: MapMarkerKind | null) {
  switch (kind) {
    case "pickup":
    case "donation":
      return houseIcon;
    case "organisation":
    case "destination":
      return orgIcon;
    case "volunteer":
      return volunteerIcon;
    case "driver":
      return driverIcon;
    case "recovery":
      return driverIcon;
    default:
      return defaultPin;
  }
}
