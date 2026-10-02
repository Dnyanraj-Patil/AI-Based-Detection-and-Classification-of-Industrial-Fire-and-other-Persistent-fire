import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import { getRiskScores } from "../services/api";
import LocationFilter from "../components/LocationFilter";
const EVENT_LIMIT = 100000;

function RiskAnalysis() {
  const [events, setEvents] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [location, setLocation] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // ============================================================
  // LOAD LIVE THERMAL EVENTS
  // ============================================================

  const loadRiskData = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getRiskScores(EVENT_LIMIT, location);

      const riskList = Array.isArray(data?.risk_scores)
        ? data.risk_scores
        : [];

      const normalized = riskList.map((event) => ({
        ...event,
        id: event.event_id,
        frp: event.max_frp,
        acquisition_datetime: event.last_detected_at,
        confidence: event.confidence_score,
      }));

      setEvents(normalized);
    } catch (err) {
      console.error("[RiskAnalysis]", err);

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to load risk intelligence from the ThermoIntel backend."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load immediately when the page opens
    loadRiskData();

    // Refresh risk intelligence every 60 seconds
    const interval = setInterval(() => {
      loadRiskData();
    }, 60 * 1000);

    // Cleanup when leaving the page
    return () => {
      clearInterval(interval);
    };
  }, [location]);

  // ============================================================
  // RISK CALCULATION
  // ============================================================

  const getSeverity = (event) =>
    String(
      event?.severity ||
      event?.risk_band ||
      "LOW"
    ).toUpperCase();

  const riskEvents = useMemo(() => {
    const severityRank = {
      CRITICAL: 4,
      HIGH: 3,
      MODERATE: 2,
      LOW: 1,
    };

    const query = searchQuery.trim().toLowerCase();

    const filtered = query
      ? events.filter((event) => {
        const searchable = [
          event?.event_id,
          event?.id,
          event?.latitude,
          event?.longitude,
          event?.facility_name,
          event?.facility_id,
          event?.facility_type,
          event?.industrial_type,
          event?.classification,
          event?.severity,
          event?.risk_band,
          event?.industrial_context,
          event?.intelligence_reason,
          event?.google_maps_url,
          event?.openstreetmap_url,
        ]
          .filter((value) => value !== null && value !== undefined)
          .join(" ")
          .toLowerCase();

        return searchable.includes(query);
      })
      : [...events];

    return filtered.sort((a, b) => {
      const aSeverity = severityRank[getSeverity(a)] || 0;

      const bSeverity = severityRank[getSeverity(b)] || 0;

      if (bSeverity !== aSeverity) {
        return bSeverity - aSeverity;
      }

      return (
        Number(b?.risk_score || 0) -
        Number(a?.risk_score || 0)
      );
    });
  }, [events, searchQuery]);

  // ============================================================
  // RISK SUMMARY
  // ============================================================

  const totalRiskEvents =
    riskEvents.length;

  const criticalEvents =
    riskEvents.filter(
      (event) => getSeverity(event) === "CRITICAL"
    ).length;

  const highEvents =
    riskEvents.filter(
      (event) => getSeverity(event) === "HIGH"
    ).length;

  const moderateEvents =
    riskEvents.filter(
      (event) => getSeverity(event) === "MODERATE"
    ).length;

  const lowEvents =
    riskEvents.filter(
      (event) => getSeverity(event) === "LOW"
    ).length;

  const averageRisk =
    totalRiskEvents > 0
      ? riskEvents.reduce(
        (sum, event) =>
          sum +
          Number(
            event.risk_score || 0
          ),
        0
      ) / totalRiskEvents
      : 0;

  const maximumRisk =
    totalRiskEvents > 0
      ? Math.max(
        ...riskEvents.map(
          (event) =>
            Number(
              event.risk_score || 0
            )
        )
      )
      : 0;

  // ============================================================
  // THERMAL SUMMARY
  // ============================================================

  const thermalEvents =
    events.length;

  const averageFRP =
    events.length > 0
      ? events.reduce(
        (sum, event) =>
          sum +
          (Number(event?.frp) || 0),
        0
      ) / events.length
      : 0;

  const maximumFRP =
    events.length > 0
      ? Math.max(
        ...events.map(
          (event) =>
            Number(event?.frp) || 0
        )
      )
      : 0;

  const sortedEvents = [
    ...events,
  ].sort(
    (a, b) =>
      new Date(
        a?.acquisition_datetime || 0
      ) -
      new Date(
        b?.acquisition_datetime || 0
      )
  );

  const earliestEvent =
    sortedEvents[0]
      ?.acquisition_datetime ||
    null;

  const latestEvent =
    sortedEvents[
      sortedEvents.length - 1
    ]?.acquisition_datetime ||
    null;

  const averageRiskPercentage =
    Math.min(
      Math.max(
        averageRisk * 100,
        0
      ),
      100
    );

  // ============================================================
  // FORMATTERS
  // ============================================================

  const formatScore = (value) => {
    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "0.0000";
    }

    return number.toFixed(4);
  };

  const formatFRP = (value) => {
    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "0.00";
    }

    return number.toFixed(2);
  };

  const formatDate = (value) => {
    if (!value) {
      return "—";
    }

    const date = new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return "—";
    }

    return date.toLocaleString();
  };

  const getRiskClass = (risk) => {
    const value =
      String(
        risk || ""
      ).toUpperCase();

    if (value === "CRITICAL") {
      return "risk-critical";
    }

    if (value === "HIGH") {
      return "risk-high";
    }

    if (value === "MODERATE") {
      return "risk-moderate";
    }

    return "risk-low";
  };

  // ============================================================
  // LOADING
  // ============================================================

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <div className="eyebrow">
              THERMOINTEL / ANALYTICS
            </div>

            <h1>
              Risk Analysis
            </h1>

            <p>
              Loading fused thermal
              event intelligence...
            </p>
          </div>
        </div>

        <div className="loading-panel">
          <div className="loading-spinner" />

          <div>
            <strong>
              Loading risk intelligence
            </strong>

            <span>
              Reading live thermal
              detections from ThermoIntel.
            </span>
          </div>
        </div>
      </div>
    );
  }

  // ============================================================
  // ERROR
  // ============================================================

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <div className="eyebrow">
              THERMOINTEL / ANALYTICS
            </div>

            <h1>
              Risk Analysis
            </h1>

            <p>
              Evidence-fused thermal
              event risk assessment.
            </p>
          </div>
        </div>

        <div className="error-panel">
          <div className="error-icon">
            !
          </div>

          <h2>
            Risk intelligence unavailable
          </h2>

          <p>
            {error}
          </p>

          <button
            onClick={loadRiskData}
          >
            Retry connection
          </button>
        </div>
      </div>
    );
  }

  // ============================================================
  // PAGE
  // ============================================================

  return (
    <div className="page-container">

      {/* HEADER */}

      <div className="page-header risk-header">
        <div>
          <div className="eyebrow">
            THERMOINTEL / ANALYTICS
          </div>

          <h1>
            Risk Analysis
          </h1>

          <p>
            Evidence-fused thermal event
            risk assessment across the
            monitored region.
          </p>
        </div>

        <div className="engine-status">
          <span className="status-dot" />

          <div>
            <strong>
              INTELLIGENCE ENGINE ACTIVE
            </strong>

            <span>
              Risk pipeline operational
            </span>
          </div>
        </div>
      </div>

      <section className="analytics-card" style={{ marginBottom: "18px" }}>
        <LocationFilter value={location} onApply={setLocation} />
      </section>

      {/* KPI CARDS */}

      <section className="risk-kpi-grid">

        <div className="risk-kpi-card">
          <div className="kpi-label">
            RISK EVENTS
          </div>

          <div className="kpi-value">
            {totalRiskEvents}
          </div>

          <div className="kpi-description">
            Events with calculated risk
          </div>
        </div>

        <div className="risk-kpi-card">
          <div className="kpi-label">
            AVERAGE RISK
          </div>

          <div className="kpi-value">
            {formatScore(
              averageRisk
            )}
          </div>

          <div className="kpi-description">
            Mean fused risk score
          </div>
        </div>

        <div className="risk-kpi-card">
          <div className="kpi-label">
            MAXIMUM RISK
          </div>

          <div className="kpi-value">
            {formatScore(
              maximumRisk
            )}
          </div>

          <div className="kpi-description">
            Highest observed risk
          </div>
        </div>

        <div className="risk-kpi-card critical-card">
          <div className="kpi-label">
            CRITICAL EVENTS
          </div>

          <div className="kpi-value critical-number">
            {criticalEvents}
          </div>

          <div className="kpi-description">
            Risk score ≥ 0.70
          </div>
        </div>

      </section>

      {/* MAIN ANALYTICS */}

      <section className="risk-main-grid">

        {/* DISTRIBUTION */}

        <div className="analytics-card">

          <div className="card-header">
            <div>
              <h2>
                Risk Distribution
              </h2>

              <p>
                Current event classification
              </p>
            </div>

            <div className="total-risk-badge">
              {totalRiskEvents} EVENTS
            </div>
          </div>

          <div className="distribution-list">

            <RiskBar
              label="CRITICAL"
              value={criticalEvents}
              total={totalRiskEvents}
              className="critical"
            />

            <RiskBar
              label="HIGH"
              value={highEvents}
              total={totalRiskEvents}
              className="high"
            />

            <RiskBar
              label="MODERATE"
              value={moderateEvents}
              total={totalRiskEvents}
              className="moderate"
            />

            <RiskBar
              label="LOW"
              value={lowEvents}
              total={totalRiskEvents}
              className="low"
            />

          </div>

          <div className="risk-meter">

            <div className="meter-header">
              <span>
                Average risk intensity
              </span>

              <strong>
                {formatScore(
                  averageRisk
                )}
              </strong>
            </div>

            <div className="meter-track">
              <div
                className="meter-fill"
                style={{
                  width:
                    `${averageRiskPercentage}%`,
                }}
              />
            </div>

            <div className="meter-scale">
              <span>0.00</span>
              <span>0.35</span>
              <span>0.70</span>
              <span>1.00</span>
            </div>

          </div>

        </div>

        {/* RISK INTELLIGENCE */}

        <div className="analytics-card">

          <div className="card-header">

            <div>
              <h2>
                Risk Intelligence
              </h2>

              <p>
                Current risk classification
              </p>
            </div>

            <div className="context-status">
              ENGINE ACTIVE
            </div>

          </div>

          <div className="context-grid">

            <ContextMetric
              label="Critical"
              value={criticalEvents}
            />

            <ContextMetric
              label="High"
              value={highEvents}
            />

            <ContextMetric
              label="Moderate"
              value={moderateEvents}
            />

            <ContextMetric
              label="Low"
              value={lowEvents}
            />

          </div>

          <div className="context-summary">

            <div className="summary-icon">
              ◎
            </div>

            <div>
              <strong>
                Risk classification active
              </strong>

              <span>
                {totalRiskEvents} events have
                calculated risk scores.
              </span>
            </div>

          </div>

        </div>

      </section>

      {/* THERMAL STATISTICS */}

      <section className="analytics-card thermal-summary-card">

        <div className="card-header">

          <div>
            <div className="eyebrow">
              THERMAL SIGNAL
            </div>

            <h2>
              Detection Statistics
            </h2>

            <p>
              Underlying thermal observations
              used by the risk engine.
            </p>
          </div>

        </div>

        <div className="thermal-stat-grid">

          <StatItem
            label="THERMAL EVENTS"
            value={thermalEvents}
          />

          <StatItem
            label="AVERAGE FRP"
            value={`${formatFRP(
              averageFRP
            )} MW`}
          />

          <StatItem
            label="MAXIMUM FRP"
            value={`${formatFRP(
              maximumFRP
            )} MW`}
            highlight
          />

          <StatItem
            label="RISK EVENTS"
            value={totalRiskEvents}
          />

        </div>

        <div className="time-range">

          <div>
            <span>
              EARLIEST DETECTION
            </span>

            <strong>
              {formatDate(
                earliestEvent
              )}
            </strong>
          </div>

          <div className="range-arrow">
            →
          </div>

          <div>
            <span>
              LATEST DETECTION
            </span>

            <strong>
              {formatDate(
                latestEvent
              )}
            </strong>
          </div>

        </div>

      </section>

      {/* TOP RISK EVENTS */}

      <section className="analytics-card top-events-card">

        <div className="card-header">

          <div>
            <div className="eyebrow">
              PRIORITY QUEUE
            </div>

            <h2>
              Highest Risk Events
            </h2>

            <p>
              Events ranked by the ThermoIntel
              fused risk score.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search event, location, facility, class..."
              aria-label="Search risk events"
              style={{
                minWidth: "280px",
                padding: "9px 12px",
                borderRadius: "8px",
                border: "1px solid rgba(128, 128, 128, .35)",
                background: "rgba(0, 0, 0, .12)",
                color: "inherit",
                outline: "none",
              }}
            />

            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{
                  padding: "9px 12px",
                  borderRadius: "8px",
                  border: "1px solid rgba(128, 128, 128, .35)",
                  background: "transparent",
                  color: "inherit",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Clear
              </button>
            )}

            <div className="priority-count">
              {riskEvents.length} {searchQuery ? "MATCHED" : "RANKED"} EVENTS
            </div>
          </div>

        </div>

        <div className="risk-table-wrapper">

          <table className="risk-table">

            <thead>
              <tr>
                <th>EVENT</th>
                <th>LOCATION</th>
                <th>RISK</th>
                          <th>XGBOOST</th>
                <th>SEVERITY</th>
                <th>THERMAL SCORE</th>
                <th>PERSISTENCE</th>
                <th>INDUSTRIAL</th>
                <th>CONFIDENCE</th>
                <th>CONTEXT</th>
              </tr>
            </thead>

            <tbody>

              {riskEvents.map(
                (event, index) => {

                  const eventId =
                    event?.event_id ??
                    event?.id ??
                    index + 1;

                  const facilityName =
                    event?.facility_name ||
                    "Unnamed industrial facility";

                  const cleanFacilityName =
                    String(
                      facilityName
                    ).toLowerCase() === "nan"
                      ? "Unnamed industrial facility"
                      : facilityName;

                  const hasCoordinates =
                    Number.isFinite(
                      Number(
                        event?.latitude
                      )
                    ) &&
                    Number.isFinite(
                      Number(
                        event?.longitude
                      )
                    );

                  return (
                    <tr
                      key={`${eventId}-${index}`}
                    >

                      {/* EVENT */}

                      <td>

                        <div className="event-id">
                          #{eventId}
                        </div>

                        <span className="event-time">
                          {formatDate(
                            event?.acquisition_datetime
                          )}
                        </span>

                      </td>

                      {/* LOCATION */}

                      <td>

                        <div className="risk-location">

                          <strong>
                            {cleanFacilityName}
                          </strong>

                          {event?.facility_id && (
                            <span>
                              Facility #
                              {event.facility_id}
                            </span>
                          )}

                          {event?.facility_type &&
                            String(
                              event.facility_type
                            ).toLowerCase() !==
                            "nan" && (
                              <span>
                                {event.facility_type}
                              </span>
                            )}

                          {event?.industrial_type &&
                            String(
                              event.industrial_type
                            ).toLowerCase() !==
                            "nan" && (
                              <span>
                                {event.industrial_type}
                              </span>
                            )}

                          {hasCoordinates && (
                            <span className="coordinates">
                              {Number(
                                event.latitude
                              ).toFixed(5)}
                              ,{" "}
                              {Number(
                                event.longitude
                              ).toFixed(5)}
                            </span>
                          )}

                          <div className="map-links">

                            {event?.google_maps_url && (
                              <a
                                href={
                                  event.google_maps_url
                                }
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                Google Maps
                              </a>
                            )}

                            {event?.openstreetmap_url && (
                              <a
                                href={
                                  event.openstreetmap_url
                                }
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                OpenStreetMap
                              </a>
                            )}

                          </div>

                        </div>

                      </td>

                      {/* RISK */}

                      <td>

                        <span
                          className={`risk-pill ${getRiskClass(
                            event?.risk_band
                          )}`}
                        >
                          {formatScore(
                            event?.risk_score
                          )}
                        </span>

                      </td>

                      {/* XGBOOST */}

                      <td className="confidence-cell">
                        <div style={{ fontWeight: 700 }}>
                          {event?.ml_predicted_class || "—"}
                        </div>
                        <div style={{ opacity: 0.7, marginTop: 3 }}>
                          {event?.xgboost_score != null
                            ? `${(Number(event.xgboost_score) * 100).toFixed(1)}% confidence`
                            : "Model not scored"}
                        </div>
                      </td>

                      {/* SEVERITY */}

                      <td>

                        <span
                          className={`severity-label ${getRiskClass(
                            getSeverity(event)
                          )}`}
                        >
                          {getSeverity(event)}
                        </span>

                      </td>

                      {/* THERMAL */}

                      <td className="confidence-cell">
                        {formatScore(
                          event?.thermal_score
                        )}
                      </td>

                      {/* PERSISTENCE */}

                      <td className="confidence-cell">
                        {formatScore(
                          event?.persistence_score
                        )}
                      </td>

                      {/* INDUSTRIAL */}

                      <td className="confidence-cell">
                        {formatScore(
                          event?.industrial_score
                        )}
                      </td>

                      {/* CONFIDENCE */}

                      <td className="confidence-cell">
                        {formatScore(
                          event?.confidence_score
                        )}
                      </td>

                      {/* CONTEXT */}

                      <td>

                        <span
                          className={`context-pill ${String(
                            event?.industrial_context ||
                            "NONE"
                          ).toLowerCase()}`}
                        >
                          {event?.industrial_context ||
                            "NONE"}
                        </span>

                      </td>

                    </tr>
                  );
                }
              )}

              {riskEvents.length === 0 && (
                <tr>
                  <td
                    colSpan="9"
                    className="empty-table"
                  >
                    {searchQuery
                      ? "No events match your search."
                      : "No thermal events available."}
                  </td>
                </tr>
              )}

            </tbody>

          </table>

        </div>

      </section>

      {/* METHODOLOGY */}

      <section className="methodology-card">

        <div className="methodology-icon">
          ✦
        </div>

        <div>

          <div className="eyebrow">
            RISK INTELLIGENCE ENGINE
          </div>

          <h3>
            Evidence-fused assessment
          </h3>

          <p>
            ThermoIntel combines thermal
            signal characteristics,
            detection persistence,
            confidence and industrial
            context to prioritize
            events for operational review.
          </p>

        </div>

        <div className="methodology-status">
          <span className="status-dot" />
          PIPELINE ACTIVE
        </div>

      </section>

    </div>
  );
}

// ============================================================
// DISTANCE
// ============================================================

function distanceKm(
  lat1,
  lon1,
  lat2,
  lon2
) {
  const earthRadius = 6371;

  const dLat =
    toRadians(lat2 - lat1);

  const dLon =
    toRadians(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
    Math.cos(toRadians(lat2)) *
    Math.sin(dLon / 2) ** 2;

  return (
    earthRadius *
    2 *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    )
  );
}

function toRadians(value) {
  return (
    (value * Math.PI) / 180
  );
}

// ============================================================
// RISK BAR
// ============================================================

function RiskBar({
  label,
  value = 0,
  total = 0,
  className,
}) {
  const numericValue =
    Number(value) || 0;

  const numericTotal =
    Number(total) || 0;

  const percentage =
    numericTotal > 0
      ? Math.min(
        (numericValue /
          numericTotal) *
        100,
        100
      )
      : 0;

  return (
    <div className="distribution-item">

      <div className="distribution-header">

        <span>
          {label}
        </span>

        <strong>
          {numericValue}
        </strong>

      </div>

      <div className="distribution-track">

        <div
          className={`distribution-fill ${className}`}
          style={{
            width:
              `${percentage}%`,
          }}
        />

      </div>

      <span className="distribution-percentage">
        {percentage.toFixed(1)}%
      </span>

    </div>
  );
}

// ============================================================
// CONTEXT METRIC
// ============================================================

function ContextMetric({
  label,
  value,
}) {
  return (
    <div className="context-metric">

      <span>
        {label}
      </span>

      <strong>
        {value ?? 0}
      </strong>

      <small>
        events
      </small>

    </div>
  );
}

// ============================================================
// STAT ITEM
// ============================================================

function StatItem({
  label,
  value,
  highlight,
}) {
  return (
    <div
      className={`thermal-stat ${highlight
        ? "highlight"
        : ""
        }`}
    >

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}

export default RiskAnalysis;