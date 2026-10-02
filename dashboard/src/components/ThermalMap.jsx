import React, { useState } from "react";
import {
  MapContainer,
  TileLayer,
  WMSTileLayer,
  CircleMarker,
  Circle,
  Popup,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const NASA_GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi";

function MapViewport({ location }) {
  const map = useMap();
  React.useEffect(() => {
    if (location?.latitude != null && location?.longitude != null) {
      const zoom = location.radius_km <= 10 ? 10 : location.radius_km <= 25 ? 9 : location.radius_km <= 50 ? 8 : location.radius_km <= 100 ? 7 : 6;
      map.setView([Number(location.latitude), Number(location.longitude)], zoom, { animate: true });
    }
  }, [location, map]);
  return null;
}

export default function ThermalMap({ events = [], location = null }) {
  const [thermalMode, setThermalMode] = useState(true);
  const [satelliteMode, setSatelliteMode] = useState(false);

  const valid = events.filter(
    (e) =>
      Number.isFinite(Number(e.latitude)) &&
      Number.isFinite(Number(e.longitude))
  );

  const center = valid.length
    ? [Number(valid[0].latitude), Number(valid[0].longitude)]
    : [22.5, 79.0];

  return (
    <div className="thermal-map-shell">
      <div className="thermal-map-toolbar">
        <div>
          <span className="thermal-map-kicker">SATELLITE THERMAL IMAGING</span>
          <strong>{thermalMode ? "NASA VIIRS Thermal Anomalies" : "Standard Map"}</strong>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            className={`thermal-mode-toggle ${thermalMode ? "active" : ""}`}
            onClick={() => {
              setThermalMode((value) => !value);
              setSatelliteMode(false);
            }}
            title="Toggle NASA VIIRS thermal anomaly imagery"
          >
            {thermalMode ? "Thermal ON" : "Thermal OFF"}
          </button>
          <button
            type="button"
            className={`thermal-mode-toggle ${satelliteMode ? "active" : ""}`}
            onClick={() => {
              setSatelliteMode((value) => !value);
              setThermalMode(false);
            }}
            title="Show NASA VIIRS corrected-reflectance satellite imagery"
          >
            {satelliteMode ? "Satellite ON" : "Satellite OFF"}
          </button>
        </div>
      </div>

      <div className="thermal-map-canvas">
        <MapContainer
          center={center}
          zoom={valid.length === 1 ? 8 : 5}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <MapViewport location={location} />
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            opacity={thermalMode ? 0.45 : 1}
          />

          {location?.latitude != null && location?.longitude != null && (
            <Circle
              center={[Number(location.latitude), Number(location.longitude)]}
              radius={Number(location.radius_km || 25) * 1000}
              pathOptions={{ weight: 2, fillOpacity: 0.05 }}
            />
          )}

          {thermalMode && (
            <WMSTileLayer
              url={NASA_GIBS_WMS}
              layers="VIIRS_NOAA21_Thermal_Anomalies_375m_All,VIIRS_NOAA20_Thermal_Anomalies_375m_All,VIIRS_SNPP_Thermal_Anomalies_375m_All"
              format="image/png"
              transparent
              version="1.1.1"
              styles=""
              opacity={0.92}
              attribution="NASA GIBS"
            />
          )}

          {satelliteMode && (
            <WMSTileLayer
              url={NASA_GIBS_WMS}
              layers="VIIRS_NOAA21_CorrectedReflectance_TrueColor,VIIRS_NOAA20_CorrectedReflectance_TrueColor,VIIRS_SNPP_CorrectedReflectance_TrueColor"
              format="image/png"
              transparent
              version="1.1.1"
              styles=""
              opacity={0.90}
              attribution="NASA GIBS VIIRS corrected reflectance"
            />
          )}

          {valid.map((event, i) => {
            const frp = Number(event.frp) || 0;
            const radius = Math.max(5, Math.min(18, 5 + frp / 15));

            return (
              <CircleMarker
                key={`${event.id}-${i}`}
                center={[Number(event.latitude), Number(event.longitude)]}
                radius={radius}
                pathOptions={{
                  weight: 2,
                  fillOpacity: 0.78,
                }}
              >
                <Popup>
                  <strong>Thermal Event #{event.id}</strong>
                  <br />
                  Classification: {event.thermal_classification || "OTHER THERMAL SOURCE"}
                  <br />
                  FRP: {frp.toFixed(2)} MW
                  <br />
                  Brightness TI4: {event.bright_ti4 != null ? `${Number(event.bright_ti4).toFixed(2)} K` : "N/A"}
                  <br />
                  FIRMS Detection Confidence: {event.detection_confidence || "Unknown"}<br />Class Confidence: {event.classification_confidence != null ? `${(Number(event.classification_confidence) * 100).toFixed(1)}%` : "N/A"}
                  <br />
                  Satellite: {event.satellite || "N/A"}
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <div className="thermal-map-footer">
        <span>{satelliteMode ? "NASA VIIRS true-color satellite imagery" : thermalMode ? "NASA VIIRS thermal-anomaly overlay" : "OpenStreetMap base layer"}</span>
        <span>•</span>
        <span>Thermal detections remain sourced from FIRMS</span>
      </div>
    </div>
  );
}
