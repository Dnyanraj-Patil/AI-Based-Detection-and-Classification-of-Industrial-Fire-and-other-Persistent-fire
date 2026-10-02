import React from "react";
import { Link, useParams } from "react-router-dom";
import { getEventContext } from "../services/api";
import ThermalMap from "../components/ThermalMap";

function EventDetailsPage() {
    const { eventId } = useParams();

    const [event, setEvent] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        async function loadEvent() {
            try {
                setLoading(true);
                setError(null);

                const data = await getEventContext(eventId);
                setEvent(data);
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        if (eventId) {
            loadEvent();
        }
    }, [eventId]);

    if (loading) {
        return (
            <div style={styles.page}>
                <div style={styles.loading}>
                    Loading event intelligence...
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={styles.page}>
                <div style={styles.header}>
                    <Link to="/" style={styles.backButton}>
                        ← Back to Dashboard
                    </Link>
                </div>

                <div style={styles.errorCard}>
                    <h2>Unable to load event</h2>
                    <p>{error}</p>
                    <p>
                        Make sure the ThermoIntel FastAPI backend is
                        running on port 8000.
                    </p>
                </div>
            </div>
        );
    }

    if (!event || !event.thermal_event) {
        return (
            <div style={styles.page}>
                <div style={styles.header}>
                    <Link to="/" style={styles.backButton}>
                        ← Back to Dashboard
                    </Link>
                </div>

                <div style={styles.errorCard}>
                    <h2>Event not found</h2>
                    <p>
                        No thermal event information was returned for
                        event {eventId}.
                    </p>
                </div>
            </div>
        );
    }

    const thermal = event.thermal_event;
    const facility = event.nearest_facility;
    const nearbyFacilities = Array.isArray(event.nearby_facilities)
        ? event.nearby_facilities
        : [];
    const facilitySummary = event.facility_summary || {};

    return (
        <div style={styles.page}>
            {/* HEADER */}
            <header style={styles.header}>
                <div>
                    <div style={styles.eyebrow}>
                        THERMOINTEL / EVENT INTELLIGENCE
                    </div>

                    <h1 style={styles.title}>
                        Thermal Event #{thermal.id}
                    </h1>

                    <p style={styles.subtitle}>
                        Detailed thermal detection and industrial
                        context analysis
                    </p>
                </div>

                <Link to="/" style={styles.backButton}>
                    ← Dashboard
                </Link>
            </header>

            {/* EVENT OVERVIEW */}
            <section style={styles.grid}>
                <MetricCard
                    title="FRP"
                    value={
                        thermal.frp !== null &&
                        thermal.frp !== undefined
                            ? `${Number(thermal.frp).toFixed(2)} MW`
                            : "N/A"
                    }
                    subtitle="Fire Radiative Power"
                />

                <MetricCard
                    title="Class Confidence"
                    value={
                        thermal.classification_confidence != null
                            ? `${(Number(thermal.classification_confidence) * 100).toFixed(1)}%`
                            : "N/A"
                    }
                    subtitle="ThermoIntel source-class confidence"
                />

                <MetricCard
                    title="XGBoost Confidence"
                    value={
                        thermal.ml_anomaly?.classification_confidence != null
                            ? `${(Number(thermal.ml_anomaly.classification_confidence) * 100).toFixed(1)}%`
                            : "N/A"
                    }
                    subtitle={thermal.ml_anomaly?.predicted_class || thermal.ml_anomaly?.classification || "ML classification unavailable"}
                />

                <MetricCard
                    title="Brightness TI4"
                    value={
                        thermal.bright_ti4 !== null &&
                        thermal.bright_ti4 !== undefined
                            ? `${Number(
                                  thermal.bright_ti4
                              ).toFixed(2)} K`
                            : "N/A"
                    }
                    subtitle="Thermal brightness"
                />

                <MetricCard
                    title="Day / Night"
                    value={thermal.daynight || "N/A"}
                    subtitle="Observation period"
                />
            </section>

            {/* XGBOOST ML SIGNAL */}
            {thermal.ml_anomaly && (
                <div style={styles.card}>
                    <div style={styles.cardEyebrow}>XGBOOST SOURCE CLASSIFIER</div>
                    <h3 style={styles.cardTitle}>
                        {thermal.ml_anomaly.predicted_class || thermal.ml_anomaly.classification || "Classification unavailable"}
                    </h3>
                    <p style={styles.explanation}>
                        XGBoost uses thermal, temporal, industrial-context and land-cover
                        features. The current bootstrap model is trained from reviewed
                        labels when available and otherwise from explainable evidence
                        labels. Confidence is model confidence, not a ground-truth
                        probability of physical fire cause.
                    </p>
                    <div style={{ marginTop: 10, fontWeight: 700 }}>
                        Model confidence: {
                            thermal.ml_anomaly.classification_confidence != null
                                ? `${(Number(thermal.ml_anomaly.classification_confidence) * 100).toFixed(1)}%`
                                : "N/A"
                        }
                    </div>
                </div>
            )}

            {/* CLASSIFICATION */}
            <section style={styles.card}>
                <div style={styles.cardHeader}>
                    <div>
                        <div style={styles.cardEyebrow}>CLASSIFICATION</div>
                        <h2 style={styles.cardTitle}>Thermal source assessment</h2>
                    </div>
                    <span style={styles.badge}>EVIDENCE-BASED SCREENING</span>
                </div>
                <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: "0.02em" }}>
                    {thermal.thermal_classification || "OTHER THERMAL SOURCE"}
                </div>
                <div style={{ marginTop: 10, fontWeight: 700 }}>
                    Classification confidence: {
                        thermal.classification_confidence != null
                            ? `${(Number(thermal.classification_confidence) <= 1
                                ? Number(thermal.classification_confidence) * 100
                                : Number(thermal.classification_confidence)
                              ).toFixed(1)}%`
                            : "N/A"
                    }
                </div>
                <p style={{ marginTop: 10, opacity: 0.72, lineHeight: 1.6 }}>
                    Candidate classification derived from FIRMS thermal intensity, persistence and industrial spatial context. It is not a ground-truth fire-cause determination.
                </p>
                <div style={{ marginTop: 14, padding: 14, borderRadius: 12, background: "rgba(128,128,128,.10)" }}>
                    <strong>Probable cause / evidence assessment</strong>
                    <p style={{ margin: "8px 0 0", lineHeight: 1.55, opacity: .82 }}>
                        {thermal.probable_cause_reason || (thermal.thermal_classification
                            ? `Probable source: ${thermal.thermal_classification}. Evidence scores are shown below.`
                            : "No contextual intelligence is available for this event yet.")}
                    </p>
                    <div style={{ display: "flex", gap: 18, flexWrap: "wrap", marginTop: 10, fontSize: 13, opacity: .8 }}>
                        <span>Thermal: {thermal.thermal_score != null ? Number(thermal.thermal_score).toFixed(2) : "—"}</span>
                        <span>Persistence: {thermal.persistence_score != null ? Number(thermal.persistence_score).toFixed(2) : "—"}</span>
                        <span>Industrial: {thermal.industrial_score != null ? Number(thermal.industrial_score).toFixed(2) : "—"}</span>
                    </div>
                </div>
            </section>

            {/* THERMAL EVENT */}
            <section style={styles.card}>
                <div style={styles.cardHeader}>
                    <div>
                        <div style={styles.cardEyebrow}>
                            DETECTION
                        </div>

                        <h2 style={styles.cardTitle}>
                            Thermal Event Information
                        </h2>
                    </div>

                    <span style={styles.badge}>
                        {thermal.satellite || "Unknown satellite"}
                    </span>
                </div>

                <div style={styles.detailGrid}>
                    <Detail
                        label="Event ID"
                        value={thermal.id}
                    />

                    <Detail
                        label="Latitude"
                        value={formatNumber(thermal.latitude, 6)}
                    />

                    <Detail
                        label="Longitude"
                        value={formatNumber(thermal.longitude, 6)}
                    />

                    <Detail
                        label="Satellite"
                        value={thermal.satellite}
                    />

                    <Detail
                        label="Instrument"
                        value={thermal.instrument}
                    />

                    <Detail
                        label="Acquisition"
                        value={formatDate(
                            thermal.acquisition_datetime
                        )}
                    />

                    <Detail
                        label="Brightness TI4"
                        value={formatNumber(
                            thermal.bright_ti4,
                            2
                        )}
                    />

                    <Detail
                        label="Brightness TI5"
                        value={formatNumber(
                            thermal.bright_ti5,
                            2
                        )}
                    />

                    <Detail
                        label="FRP"
                        value={
                            thermal.frp !== null
                                ? `${formatNumber(
                                      thermal.frp,
                                      2
                                  )} MW`
                                : "N/A"
                        }
                    />

                    <Detail
                        label="FIRMS Detection Confidence"
                        value={thermal.detection_confidence || "Unknown"}
                    />

                    <Detail
                        label="Day / Night"
                        value={thermal.daynight}
                    />
                </div>
            </section>

            {/* LOCATION */}
            <section style={styles.card}>
                <div style={styles.cardHeader}>
                    <div>
                        <div style={styles.cardEyebrow}>
                            GEOSPATIAL CONTEXT
                        </div>

                        <h2 style={styles.cardTitle}>
                            Event Location
                        </h2>
                    </div>
                </div>

                <div style={styles.locationBox}>
                    <div>
                        <span style={styles.locationLabel}>
                            Latitude
                        </span>

                        <strong style={styles.locationValue}>
                            {formatNumber(
                                thermal.latitude,
                                6
                            )}
                        </strong>
                    </div>

                    <div>
                        <span style={styles.locationLabel}>
                            Longitude
                        </span>

                        <strong style={styles.locationValue}>
                            {formatNumber(
                                thermal.longitude,
                                6
                            )}
                        </strong>
                    </div>
                </div>

                <a
                    href={`https://www.google.com/maps/search/?api=1&query=${thermal.latitude},${thermal.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                    style={styles.mapButton}
                >
                    Open Location in Maps ↗
                </a>
            </section>

            {/* THERMAL IMAGING */}
            <section style={styles.card}>
                <div style={styles.cardHeader}>
                    <div>
                        <div style={styles.cardEyebrow}>
                            SATELLITE THERMAL IMAGING
                        </div>
                        <h2 style={styles.cardTitle}>
                            Thermal Event View
                        </h2>
                    </div>
                    <span style={styles.badge}>NASA VIIRS / FIRMS</span>
                </div>
                <div style={{ height: 430, borderRadius: 16, overflow: "hidden" }}>
                    <ThermalMap events={[thermal]} />
                </div>
                <p style={{ marginTop: 12, opacity: 0.72, lineHeight: 1.55 }}>
                    NASA satellite thermal-anomaly imagery is shown as contextual
                    visualization; event measurements and timestamps remain sourced
                    from NASA FIRMS detections.
                </p>
            </section>

            {/* INDUSTRIAL CONTEXT */}
            <section style={styles.card}>
                <div style={styles.cardHeader}>
                    <div>
                        <div style={styles.cardEyebrow}>
                            INDUSTRIAL INTELLIGENCE
                        </div>

                        <h2 style={styles.cardTitle}>
                            Nearest Industrial Facility
                        </h2>
                    </div>

                    <span style={styles.facilityBadge}>
                        FACILITY
                    </span>
                </div>

                {facility ? (
                    <>
                        <div style={styles.facilityName}>
                            {facility.name ||
                                "Unnamed industrial facility"}
                        </div>

                        <div style={styles.detailGrid}>
                            <Detail
                                label="Facility ID"
                                value={facility.id}
                            />

                            <Detail
                                label="OSM Type"
                                value={facility.osm_type}
                            />

                            <Detail
                                label="OSM ID"
                                value={facility.osm_id}
                            />

                            <Detail
                                label="Facility Type"
                                value={
                                    facility.facility_type
                                }
                            />

                            <Detail
                                label="Industrial Type"
                                value={
                                    facility.industrial_type
                                }
                            />

                            <Detail
                                label="Distance"
                                value={
                                    facility.distance_meters !==
                                    null
                                        ? `${formatNumber(
                                              facility.distance_meters,
                                              2
                                          )} m`
                                        : "N/A"
                                }
                            />
                        </div>

                        {facility.distance_meters !== null && (
                            <div style={styles.proximity}>
                                <div
                                    style={
                                        styles.proximityHeader
                                    }
                                >
                                    <span>
                                        Facility proximity
                                    </span>

                                    <strong>
                                        {formatNumber(
                                            facility.distance_meters /
                                                1000,
                                            2
                                        )}{" "}
                                        km
                                    </strong>
                                </div>

                                <div
                                    style={
                                        styles.progressBackground
                                    }
                                >
                                    <div
                                        style={{
                                            ...styles.progress,
                                            width: `${Math.max(
                                                5,
                                                Math.min(
                                                    100,
                                                    100 -
                                                        (facility.distance_meters /
                                                            5000) *
                                                            100
                                                )
                                            )}%`,
                                        }}
                                    />
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div style={styles.noFacility}>
                        No industrial facility was found within the 10 km event context.
                    </div>
                )}

                <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
                    <div style={styles.contextStat}>
                        <span>Within 1 km</span><strong>{facilitySummary.within_1km || 0}</strong>
                    </div>
                    <div style={styles.contextStat}>
                        <span>Within 5 km</span><strong>{facilitySummary.within_5km || 0}</strong>
                    </div>
                    <div style={styles.contextStat}>
                        <span>Within 10 km</span><strong>{facilitySummary.within_10km || 0}</strong>
                    </div>
                </div>

                {nearbyFacilities.length > 0 && (
                    <div style={{ marginTop: 22 }}>
                        <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.08em", opacity: 0.62, marginBottom: 10 }}>
                            NEARBY FACILITIES
                        </div>
                        <div style={{ display: "grid", gap: 8 }}>
                            {nearbyFacilities.slice(0, 10).map((item) => (
                                <div key={item.id} style={styles.facilityRow}>
                                    <div>
                                        <strong>{item.name || "Unnamed facility"}</strong>
                                        <div style={{ fontSize: 12, opacity: 0.62 }}>
                                            {item.facility_type || item.industrial_type || "Industrial facility"}
                                        </div>
                                    </div>
                                    <span>{item.distance_meters != null ? `${(Number(item.distance_meters) / 1000).toFixed(2)} km` : "—"}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </section>

            {/* SYSTEM INTERPRETATION */}
            <section style={styles.card}>
                <div style={styles.cardEyebrow}>
                    SYSTEM INTERPRETATION
                </div>

                <h2 style={styles.cardTitle}>
                    Event Intelligence
                </h2>

                <p style={styles.explanation}>
                    ThermoIntel combines thermal detection
                    characteristics with geospatial industrial
                    context to support event-level intelligence
                    and risk assessment.
                </p>
            </section>
        </div>
    );
}

/* ============================================================
   COMPONENTS
============================================================ */

function MetricCard({ title, value, subtitle }) {
    return (
        <div style={styles.metricCard}>
            <div style={styles.metricTitle}>{title}</div>

            <div style={styles.metricValue}>{value}</div>

            <div style={styles.metricSubtitle}>
                {subtitle}
            </div>
        </div>
    );
}

function Detail({ label, value }) {
    return (
        <div style={styles.detail}>
            <span style={styles.detailLabel}>{label}</span>

            <strong style={styles.detailValue}>
                {value !== null &&
                value !== undefined &&
                value !== ""
                    ? value
                    : "N/A"}
            </strong>
        </div>
    );
}

/* ============================================================
   HELPERS
============================================================ */

function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
        return "N/A";
    }

    return number.toFixed(decimals);
}

function formatDate(value) {
    if (!value) {
        return "N/A";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

/* ============================================================
   STYLES
============================================================ */

const styles = {
    page: {
        minHeight: "100vh",
        background:
            "linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%)",
        color: "#0f172a",
        padding: "32px",
        boxSizing: "border-box",
        fontFamily:
            "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    },

    header: {
        maxWidth: "1400px",
        margin: "0 auto 32px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "20px",
    },

    eyebrow: {
        color: "#2563eb",
        fontSize: "12px",
        fontWeight: 700,
        letterSpacing: "0.16em",
        marginBottom: "10px",
    },

    title: {
        margin: 0,
        fontSize: "36px",
        lineHeight: 1.15,
        fontWeight: 750,
    },

    subtitle: {
        marginTop: "10px",
        marginBottom: 0,
        color: "#64748b",
        fontSize: "15px",
    },

    backButton: {
        textDecoration: "none",
        color: "#0f172a",
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        padding: "11px 16px",
        borderRadius: "10px",
        fontWeight: 600,
        whiteSpace: "nowrap",
    },

    grid: {
        maxWidth: "1400px",
        margin: "0 auto 22px",
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "16px",
    },

    metricCard: {
        background:
            "linear-gradient(145deg, #ffffff, #f8fafc)",
        border: "1px solid #cbd5e1",
        borderRadius: "16px",
        padding: "22px",
        boxShadow: "0 14px 35px rgba(0,0,0,.18)",
    },

    metricTitle: {
        color: "#64748b",
        fontSize: "13px",
        fontWeight: 650,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
    },

    metricValue: {
        marginTop: "10px",
        fontSize: "28px",
        fontWeight: 750,
    },

    metricSubtitle: {
        marginTop: "6px",
        color: "#64748b",
        fontSize: "13px",
    },

    card: {
        maxWidth: "1400px",
        margin: "0 auto 22px",
        background:
            "linear-gradient(145deg, #ffffff, #f8fafc)",
        border: "1px solid #cbd5e1",
        borderRadius: "18px",
        padding: "26px",
        boxShadow: "0 16px 45px rgba(0,0,0,.2)",
    },

    cardHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "20px",
        marginBottom: "24px",
    },

    cardEyebrow: {
        color: "#0369a1",
        fontSize: "11px",
        fontWeight: 750,
        letterSpacing: "0.15em",
        marginBottom: "7px",
    },

    cardTitle: {
        margin: 0,
        fontSize: "22px",
        fontWeight: 700,
    },

    badge: {
        background: "#eff6ff",
        border: "1px solid #31567f",
        color: "#2563eb",
        borderRadius: "999px",
        padding: "7px 11px",
        fontSize: "11px",
        fontWeight: 700,
    },

    facilityBadge: {
        background: "#f0fdf4",
        border: "1px solid #35634e",
        color: "#15803d",
        borderRadius: "999px",
        padding: "7px 11px",
        fontSize: "11px",
        fontWeight: 700,
    },

    detailGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(210px, 1fr))",
        gap: "1px",
        background: "#f1f5f9",
        border: "1px solid #f1f5f9",
        borderRadius: "12px",
        overflow: "hidden",
    },

    detail: {
        background: "#eff6ff",
        padding: "17px",
        minHeight: "60px",
        boxSizing: "border-box",
    },

    detailLabel: {
        display: "block",
        color: "#64748b",
        fontSize: "12px",
        marginBottom: "7px",
    },

    detailValue: {
        color: "#0f172a",
        fontSize: "14px",
        wordBreak: "break-word",
    },

    locationBox: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "16px",
        marginBottom: "18px",
    },

    locationLabel: {
        display: "block",
        color: "#64748b",
        fontSize: "12px",
        marginBottom: "6px",
    },

    locationValue: {
        fontSize: "22px",
    },

    mapButton: {
        display: "inline-block",
        textDecoration: "none",
        background: "#2563eb",
        color: "#fff",
        padding: "11px 15px",
        borderRadius: "9px",
        fontSize: "13px",
        fontWeight: 650,
    },

    facilityName: {
        fontSize: "24px",
        fontWeight: 700,
        marginBottom: "22px",
        color: "#0f172a",
    },

    proximity: {
        marginTop: "22px",
        padding: "16px",
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "12px",
    },

    proximityHeader: {
        display: "flex",
        justifyContent: "space-between",
        color: "#475569",
        fontSize: "13px",
        marginBottom: "10px",
    },

    progressBackground: {
        height: "8px",
        background: "#eff6ff",
        borderRadius: "999px",
        overflow: "hidden",
    },

    progress: {
        height: "100%",
        background:
            "linear-gradient(90deg, #2563eb, #60a5fa)",
        borderRadius: "999px",
    },

    explanation: {
        color: "#64748b",
        lineHeight: 1.7,
        maxWidth: "900px",
        marginBottom: 0,
    },

    noFacility: {
        padding: "20px",
        borderRadius: "10px",
        background: "#fef3c7",
        border: "1px solid #fde68a",
        color: "#92400e",
    },

    loading: {
        minHeight: "80vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        color: "#64748b",
        fontSize: "16px",
    },

    errorCard: {
        maxWidth: "700px",
        margin: "80px auto",
        background: "#fee2e2",
        border: "1px solid #fecaca",
        borderRadius: "16px",
        padding: "30px",
        color: "#0f172a",
    },
};

export default EventDetailsPage;