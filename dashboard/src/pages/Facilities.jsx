import { useEffect, useState } from "react";

import { getFacilities } from "../services/api";
import LocationFilter from "../components/LocationFilter";
const getFacilityCoordinates = (facility) => {
  const lat = Number(facility.latitude);
  const lon = Number(facility.longitude);

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    return null;
  }

  return { lat, lon };
};

const openFacilityMap = (facility) => {
  const coords = getFacilityCoordinates(facility);

  if (!coords) return;

  window.open(
    `https://www.openstreetmap.org/?mlat=${coords.lat}&mlon=${coords.lon}#map=16/${coords.lat}/${coords.lon}`,
    "_blank",
    "noopener,noreferrer"
  );
};

const openThermalLocation = (facility) => {
  const coords = getFacilityCoordinates(facility);

  if (!coords) return;

  // Small bounding box around the facility.
  const delta = 0.08;

  const west = coords.lon - delta;
  const south = coords.lat - delta;
  const east = coords.lon + delta;
  const north = coords.lat + delta;

  const worldviewUrl =
    `https://worldview.earthdata.nasa.gov/?` +
    `v=${west},${south},${east},${north}`;

  window.open(
    worldviewUrl,
    "_blank",
    "noopener,noreferrer"
  );
};

export default function Facilities() {

  const [facilities, setFacilities] = useState([]);

  const [totalFacilities, setTotalFacilities] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [search, setSearch] =
    useState("");

  const [pageSize, setPageSize] = useState(100);
  const [currentPage, setCurrentPage] = useState(1);
  const [location, setLocation] = useState(null);


  // =========================================================
  // LOAD FACILITIES
  // =========================================================

  const loadFacilities = async () => {

    try {

      setLoading(true);
      setError("");

      const data = await getFacilities(null, 0, location, search);

      setFacilities(
        Array.isArray(data?.facilities)
          ? data.facilities
          : []
      );

      setTotalFacilities(
        Number(data?.total_count) || 0
      );

      setCurrentPage(1);

    } catch (err) {

      console.error(
        "[Facilities] Loading error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to load industrial facilities."
      );

    } finally {

      setLoading(false);

    }

  };

  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadFacilities();
  }, [location]);


  // =========================================================
  // SEARCH
  // =========================================================

  const filteredFacilities =
    facilities.filter((facility) => {

      const text = `
        ${facility.name || ""}
        ${facility.facility_type || ""}
        ${facility.industrial_type || ""}
        ${facility.osm_type || ""}
        ${facility.source || ""}
        ${facility.osm_id || ""}
      `.toLowerCase();


      return text.includes(
        search.toLowerCase()
      );

    });

  const totalPages = Math.max(1, Math.ceil(filteredFacilities.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const pageStart = (safePage - 1) * pageSize;
  const visibleFacilities = filteredFacilities.slice(pageStart, pageStart + pageSize);


  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {

    return (

      <div style={styles.page}>

        <div style={styles.loading}>

          <div style={styles.loadingDot}></div>

          <div>
            Loading industrial facilities...
          </div>

        </div>

      </div>

    );

  }


  // =========================================================
  // ERROR
  // =========================================================

  if (error) {

    return (

      <div style={styles.page}>

        <div style={styles.error}>

          <h2>
            Unable to load facilities
          </h2>

          <p>
            {error}
          </p>

          <p>
            Make sure the ThermoIntel FastAPI
            backend is running on port 8000.
          </p>

          <button
            onClick={loadFacilities}
            style={styles.retryButton}
          >
            Retry
          </button>

        </div>

      </div>

    );

  }


  // =========================================================
  // PAGE
  // =========================================================

  return (

    <div style={styles.page}>


      {/* ===================================================
          HEADER
      =================================================== */}

      <div style={styles.header}>

        <div>

          <div style={styles.eyebrow}>
            THERMOINTEL / INFRASTRUCTURE
          </div>

          <h1 style={styles.title}>
            Industrial Facilities
          </h1>

          <p style={styles.subtitle}>
            Industrial infrastructure detected
            from the spatial intelligence dataset.
          </p>

        </div>


        {/* =================================================
            TOTAL COUNT
        ================================================= */}

        <div style={styles.countCard}>

          <span style={styles.countLabel}>
            TOTAL FACILITIES
          </span>

          <strong style={styles.count}>
            {totalFacilities}
          </strong>

        </div>

      </div>


      <div style={{ marginBottom: 14 }}>
        <LocationFilter value={location} onApply={setLocation} compact />
      </div>

      {/* ===================================================
          TOOLBAR
      =================================================== */}

      <div style={styles.toolbar}>

        <input
          type="text"
          placeholder={
            "Search facilities, types or industrial categories..."
          }
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setCurrentPage(1);
          }}
          style={styles.search}
        />


        <div style={styles.toolbarRight}>

          <div style={styles.resultCount}>
            Showing {filteredFacilities.length} of {totalFacilities} loaded
          </div>

          <label style={styles.pageLabel}>
            Rows / page
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              style={styles.pageSelect}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={250}>250</option>
              <option value={500}>500</option>
            </select>
          </label>


          <button
            onClick={loadFacilities}
            style={styles.refreshButton}
          >
            ↻ Refresh
          </button>

        </div>

      </div>


      {/* ===================================================
          TABLE
      =================================================== */}

      <div style={styles.tableContainer}>

        <table style={styles.table}>

          <thead>

            <tr>

              <th style={styles.th}>
                ID
              </th>

              <th style={styles.th}>
                FACILITY
              </th>

              <th style={styles.th}>
                FACILITY TYPE
              </th>

              <th style={styles.th}>
                INDUSTRIAL TYPE
              </th>

              <th style={styles.th}>
                COORDINATES
              </th>

              <th style={styles.th}>
                MAP
              </th>

              <th style={styles.th}>
                THERMAL LOCATION
              </th>

              <th style={styles.th}>
                SOURCE
              </th>

            </tr>

          </thead>


          <tbody>

            {visibleFacilities.map(
              (facility) => (

                <tr
                  key={facility.id}
                  style={styles.row}
                >


                  {/* ======================================
                      ID
                  ====================================== */}

                  <td style={styles.td}>

                    <span
                      style={styles.idBadge}
                    >
                      {facility.id}
                    </span>

                  </td>


                  {/* ======================================
                      FACILITY
                  ====================================== */}

                  <td style={styles.td}>

                    <div
                      style={styles.facilityName}
                    >
                      {displayValue(facility.name, "Unnamed facility")}
                    </div>


                    <div style={styles.osm}>

                      {facility.osm_type ||
                        "OSM"}

                      {" "}

                      {facility.osm_id ||
                        ""}

                    </div>

                  </td>


                  {/* ======================================
                      FACILITY TYPE
                  ====================================== */}

                  <td style={styles.td}>

                    <span style={styles.tag}>

                      {displayValue(facility.facility_type)}

                    </span>

                  </td>


                  {/* ======================================
                      INDUSTRIAL TYPE
                  ====================================== */}

                  <td style={styles.td}>

                    {displayValue(facility.industrial_type)}

                  </td>


                  {/* ======================================
                      COORDINATES
                  ====================================== */}

                  <td style={styles.td}>

                    <div
                      style={styles.coordinates}
                    >

                      {facility.latitude !==
                        null &&
                        facility.latitude !==
                        undefined
                        ? Number(
                          facility.latitude
                        ).toFixed(5)
                        : "—"}

                    </div>


                    <div
                      style={styles.coordinates}
                    >

                      {facility.longitude !==
                        null &&
                        facility.longitude !==
                        undefined
                        ? Number(
                          facility.longitude
                        ).toFixed(5)
                        : "—"}

                    </div>

                  </td>
                  {/* ======================================
    MAP LOCATION
====================================== */}

                  <td style={styles.td}>

                    <button
                      type="button"
                      onClick={() => openFacilityMap(facility)}
                      disabled={!getFacilityCoordinates(facility)}
                      style={styles.mapButton}
                      title="Open facility location on map"
                    >
                      📍 MAP
                    </button>

                  </td>


                  {/* ======================================
    THERMAL LOCATION
====================================== */}

                  <td style={styles.td}>

                    <button
                      type="button"
                      onClick={() => openThermalLocation(facility)}
                      disabled={!getFacilityCoordinates(facility)}
                      style={styles.thermalButton}
                      title="Open facility location in NASA Worldview"
                    >
                      🔥 THERMAL
                    </button>

                  </td>

                  {/* ======================================
                      SOURCE
                  ====================================== */}

                  <td style={styles.td}>

                    <span
                      style={styles.source}
                    >

                      {facility.source ||
                        "Unknown"}

                    </span>

                  </td>


                </tr>

              )
            )}

          </tbody>

        </table>


        {filteredFacilities.length > 0 && (
          <div style={styles.pagination}>
            <button type="button" style={styles.pageButton} disabled={safePage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}>
              ← Previous
            </button>
            <span style={styles.pageInfo}>
              Page {safePage} of {totalPages} · Showing {pageStart + 1}-{Math.min(pageStart + pageSize, filteredFacilities.length)} of {filteredFacilities.length}
            </span>
            <button type="button" style={styles.pageButton} disabled={safePage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}>
              Next →
            </button>
          </div>
        )}

        {/* =================================================
            EMPTY SEARCH
        ================================================= */}

        {filteredFacilities.length === 0 && (

          <div style={styles.empty}>

            No facilities match your search.

          </div>

        )}

      </div>


      {/* ===================================================
          DATABASE STATUS
      =================================================== */}

      <div style={styles.statusBar}>

        <div style={styles.statusIndicator}></div>

        <span>
          LIVE DATABASE CONNECTION
        </span>

        <span style={styles.statusSeparator}>
          •
        </span>

        <span>
          {totalFacilities} facilities currently
          stored
        </span>

      </div>

    </div>

  );

}


// ===========================================================
// STYLES
// ===========================================================


function displayValue(value, fallback = "Not specified") {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  if (!text || /^(nan|null|undefined)$/i.test(text)) return fallback;
  return text;
}

const styles = {
  mapButton: {
    padding: "7px 10px",
    borderRadius: "7px",
    border: "1px solid #334155",
    background: "#ffffff",
    color: "#2563eb",
    cursor: "pointer",
    fontSize: "11px",
    fontWeight: 700,
    whiteSpace: "nowrap",
  },

  thermalButton: {
    padding: "7px 10px",
    borderRadius: "7px",
    border: "1px solid #7f1d1d",
    background: "#fee2e2",
    color: "#b91c1c",
    cursor: "pointer",
    fontSize: "11px",
    fontWeight: 700,
    whiteSpace: "nowrap",
  },

  page: {
    minHeight: "100%",
    padding: "32px",
    color: "#0f172a",
  },


  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "24px",
    marginBottom: "28px",
  },


  eyebrow: {
    fontSize: "11px",
    fontWeight: 700,
    letterSpacing: "2px",
    color: "#64748b",
    marginBottom: "8px",
  },


  title: {
    margin: 0,
    fontSize: "32px",
    fontWeight: 700,
    letterSpacing: "-0.8px",
  },


  subtitle: {
    margin: "8px 0 0",
    color: "#64748b",
    fontSize: "14px",
  },


  countCard: {
    minWidth: "150px",
    padding: "18px 20px",
    borderRadius: "14px",
    background: "#ffffff",
    border: "1px solid #e2e8f0",
  },


  countLabel: {
    display: "block",
    fontSize: "10px",
    fontWeight: 700,
    letterSpacing: "1.5px",
    color: "#64748b",
    marginBottom: "7px",
  },


  count: {
    fontSize: "28px",
    color: "#0f172a",
  },


  toolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    marginBottom: "18px",
  },


  toolbarRight: {
    display: "flex",
    alignItems: "center",
    gap: "15px",
  },


  search: {
    width: "420px",
    maxWidth: "100%",
    padding: "12px 15px",
    borderRadius: "10px",
    border: "1px solid #cbd5e1",
    background: "#ffffff",
    color: "#0f172a",
    outline: "none",
    fontSize: "13px",
  },


  resultCount: {
    color: "#64748b",
    fontSize: "13px",
    whiteSpace: "nowrap",
  },


  refreshButton: {
    padding: "10px 15px",
    borderRadius: "9px",
    border: "1px solid #cbd5e1",
    background: "#ffffff",
    color: "#2563eb",
    cursor: "pointer",
    fontSize: "12px",
    fontWeight: 600,
  },


  tableContainer: {
    overflow: "auto",
    borderRadius: "14px",
    border: "1px solid #e2e8f0",
    background: "#f8fafc",
  },


  table: {
    width: "100%",
    borderCollapse: "collapse",
    minWidth: "900px",
  },


  th: {
    padding: "14px 16px",
    textAlign: "left",
    fontSize: "10px",
    fontWeight: 700,
    letterSpacing: "1.2px",
    color: "#64748b",
    background: "#ffffff",
    borderBottom: "1px solid #e2e8f0",
  },


  td: {
    padding: "15px 16px",
    borderBottom: "1px solid #f1f5f9",
    fontSize: "13px",
    color: "#475569",
  },


  row: {
    transition: "background 0.15s ease",
  },


  idBadge: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: "30px",
    height: "26px",
    padding: "0 7px",
    borderRadius: "7px",
    background: "#f1f5f9",
    color: "#64748b",
    fontSize: "11px",
    fontWeight: 700,
  },


  facilityName: {
    color: "#0f172a",
    fontWeight: 600,
    marginBottom: "4px",
  },


  osm: {
    color: "#475569",
    fontSize: "11px",
  },


  tag: {
    display: "inline-block",
    padding: "5px 9px",
    borderRadius: "6px",
    background: "#f1f5f9",
    color: "#2563eb",
    fontSize: "11px",
  },


  coordinates: {
    fontFamily: "monospace",
    fontSize: "11px",
    color: "#64748b",
    lineHeight: "18px",
  },


  source: {
    color: "#64748b",
    fontSize: "12px",
  },


  loading: {
    padding: "80px",
    textAlign: "center",
    color: "#64748b",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "10px",
  },


  loadingDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: "#2563eb",
  },


  error: {
    maxWidth: "600px",
    margin: "80px auto",
    padding: "25px",
    borderRadius: "14px",
    border: "1px solid #7f1d1d",
    background: "#fee2e2",
    color: "#b91c1c",
  },


  retryButton: {
    marginTop: "10px",
    padding: "10px 16px",
    borderRadius: "8px",
    border: "1px solid #7f1d1d",
    background: "#fee2e2",
    color: "#b91c1c",
    cursor: "pointer",
  },


  empty: {
    padding: "50px",
    textAlign: "center",
    color: "#64748b",
  },


  statusBar: {
    marginTop: "14px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    color: "#64748b",
    fontSize: "11px",
    letterSpacing: "0.5px",
  },


  statusIndicator: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: "#15803d",
    boxShadow:
      "0 0 8px rgba(52, 211, 153, 0.6)",
  },


  statusSeparator: {
    color: "#334155",
  },


  pageLabel: { display: "flex", alignItems: "center", gap: "8px", color: "#64748b", fontSize: "13px" },
  pageSelect: { background: "#ffffff", color: "#0f172a", border: "1px solid #cbd5e1", borderRadius: "8px", padding: "8px 10px" },
  pagination: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", padding: "18px 0 4px" },
  pageButton: { border: "1px solid #bfdbfe", background: "#eff6ff", color: "#0f172a", borderRadius: "8px", padding: "9px 14px", cursor: "pointer" },
  pageInfo: { color: "#64748b", fontSize: "13px" },
};