import React from "react";
import { Link } from "react-router-dom";
import { getEvents } from "../services/api";
import LocationFilter from "../components/LocationFilter";

function Events() {
    const [events, setEvents] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    const [search, setSearch] = React.useState("");
    const [pageSize, setPageSize] = React.useState(100);
    const [currentPage, setCurrentPage] = React.useState(1);
    const [location, setLocation] = React.useState(null);

    React.useEffect(() => {
        loadEvents();

        const interval = setInterval(
            loadEvents,
            60 * 1000
        );

        return () => clearInterval(interval);
    }, [location]);

    async function loadEvents() {
        try {
            setLoading(true);
            setError(null);

            const data = await getEvents(null, null, location);
            setEvents(Array.isArray(data?.events) ? data.events : []);
            setCurrentPage(1);
        } catch (err) {
            console.error(err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    const filteredEvents = events.filter((event) => {
        const value = search.toLowerCase();

        return (
            String(event.id)
                .toLowerCase()
                .includes(value) ||
            String(event.satellite || "")
                .toLowerCase()
                .includes(value) ||
            String(event.instrument || "")
                .toLowerCase()
                .includes(value) ||
            String(event.daynight || "")
                .toLowerCase()
                .includes(value) ||
            String(event.thermal_classification || "")
                .toLowerCase()
                .includes(value) ||
            String(event.latitude || "")
                .includes(value) ||
            String(event.longitude || "")
                .includes(value)
        );
    });

    const totalPages = Math.max(1, Math.ceil(filteredEvents.length / pageSize));
    const safePage = Math.min(currentPage, totalPages);
    const pageStart = (safePage - 1) * pageSize;
    const visibleEvents = filteredEvents.slice(pageStart, pageStart + pageSize);

    return (
        <div style={styles.page}>
            {/* HEADER */}
            <header style={styles.header}>
                <div>
                    <div style={styles.eyebrow}>
                        THERMOINTEL / THERMAL EVENTS
                    </div>

                    <h1 style={styles.title}>
                        Thermal Events
                    </h1>

                    <p style={styles.subtitle}>
                        Browse and inspect canonical thermal events clustered from the FIRMS detection dataset.
                    </p>
                </div>

                <Link to="/" style={styles.backButton}>
                    ← Dashboard
                </Link>
            </header>

            <section style={{ ...styles.controlCard, marginBottom: 12 }}>
                <LocationFilter value={location} onApply={setLocation} compact />
            </section>

            {/* CONTROLS */}
            <section style={styles.controlCard}>
                <div style={styles.searchContainer}>
                    <span style={styles.searchIcon}>⌕</span>

                    <input
                        type="text"
                        placeholder="Search events, satellite, coordinates..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value);
                            setCurrentPage(1);
                        }}
                        style={styles.search}
                    />
                </div>

                <div style={styles.controlsRight}>
                    <label style={styles.limitLabel}>
                        Rows / page
                        <select
                            value={pageSize}
                            onChange={(e) => {
                                setPageSize(Number(e.target.value));
                                setCurrentPage(1);
                            }}
                            style={styles.select}
                        >
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                            <option value={100}>100</option>
                            <option value={250}>250</option>
                            <option value={500}>500</option>
                        </select>
                    </label>

                    <button
                        onClick={loadEvents}
                        style={styles.refreshButton}
                    >
                        ↻ Refresh
                    </button>
                </div>
            </section>

            {/* SUMMARY */}
            <section style={styles.summaryGrid}>
                <SummaryCard
                    label="Events Loaded"
                    value={events.length}
                />

                <SummaryCard
                    label="Search Results"
                    value={filteredEvents.length}
                />

                <SummaryCard
                    label="Day Events"
                    value={
                        events.filter(
                            (e) => e.daynight === "D"
                        ).length
                    }
                />

                <SummaryCard
                    label="Night Events"
                    value={
                        events.filter(
                            (e) => e.daynight === "N"
                        ).length
                    }
                />
            </section>

            {/* ERROR */}
            {error && (
                <div style={styles.errorCard}>
                    <strong>
                        Unable to load thermal events
                    </strong>

                    <p>{error}</p>

                    <p style={styles.errorHint}>
                        Make sure the ThermoIntel FastAPI
                        backend is running on port 8000.
                    </p>
                </div>
            )}

            {/* LOADING */}
            {loading && (
                <div style={styles.loadingCard}>
                    Loading thermal events...
                </div>
            )}

            {/* TABLE */}
            {!loading && !error && (
                <section style={styles.tableCard}>
                    <div style={styles.tableHeader}>
                        <div>
                            <div style={styles.cardEyebrow}>
                                EVENT DATABASE
                            </div>

                            <h2 style={styles.cardTitle}>
                                ThermoIntel Thermal Events
                            </h2>
                        </div>

                        <div style={styles.resultCount}>
                            {filteredEvents.length} results · current view
                        </div>
                    </div>

                    {filteredEvents.length === 0 ? (
                        <div style={styles.empty}>
                            No thermal events match your
                            search.
                        </div>
                    ) : (
                        <div style={styles.tableWrapper}>
                            <table style={styles.table}>
                                <thead>
                                    <tr>
                                        <th style={styles.th}>
                                            ID
                                        </th>

                                        <th style={styles.th}>
                                            Acquisition
                                        </th>

                                        <th style={styles.th}>
                                            Location
                                        </th>

                                        <th style={styles.th}>
                                            Satellite
                                        </th>

                                        <th style={styles.th}>
                                            Instrument
                                        </th>

                                        <th style={styles.th}>
                                            FRP
                                        </th>

                                        <th style={styles.th}>
                                            Classification
                                        </th>

                                        <th style={styles.th}>
                                            Class Confidence
                                        </th>

                                        <th style={styles.th}>
                                            Period
                                        </th>

                                        <th style={styles.th}>
                                            Action
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {visibleEvents.map(
                                        (event) => (
                                            <tr
                                                key={
                                                    event.id
                                                }
                                                style={
                                                    styles.tr
                                                }
                                            >
                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <strong>
                                                        #
                                                        {
                                                            event.id
                                                        }
                                                    </strong>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    {formatDate(
                                                        event.acquisition_datetime
                                                    )}
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <div>
                                                        {
                                                            formatNumber(
                                                                event.latitude,
                                                                4
                                                            )
                                                        }
                                                    </div>

                                                    <div
                                                        style={
                                                            styles.coordinate
                                                        }
                                                    >
                                                        {
                                                            formatNumber(
                                                                event.longitude,
                                                                4
                                                            )
                                                        }
                                                    </div>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <span
                                                        style={
                                                            styles.badge
                                                        }
                                                    >
                                                        {
                                                            event.satellite ||
                                                            "N/A"
                                                        }
                                                    </span>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    {
                                                        event.instrument ||
                                                        "N/A"
                                                    }
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <strong>
                                                        {event.frp !==
                                                            null
                                                            ? `${formatNumber(
                                                                event.frp,
                                                                2
                                                            )} MW`
                                                            : "N/A"}
                                                    </strong>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <span style={styles.badge}>
                                                        {event.thermal_classification || "OTHER THERMAL SOURCE"}
                                                    </span>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    {event.classification_confidence != null
                                                        ? `${(Number(event.classification_confidence) * 100).toFixed(1)}%`
                                                        : "N/A"}
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <span
                                                        style={
                                                            event.daynight ===
                                                                "D"
                                                                ? styles.dayBadge
                                                                : styles.nightBadge
                                                        }
                                                    >
                                                        {event.daynight ===
                                                            "D"
                                                            ? "DAY"
                                                            : event.daynight ===
                                                                "N"
                                                                ? "NIGHT"
                                                                : "N/A"}
                                                    </span>
                                                </td>

                                                <td
                                                    style={
                                                        styles.td
                                                    }
                                                >
                                                    <Link
                                                        to={`/events/${event.id}`}
                                                        style={
                                                            styles.viewButton
                                                        }
                                                    >
                                                        View →
                                                    </Link>
                                                </td>
                                            </tr>
                                        )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {filteredEvents.length > 0 && (
                        <div style={styles.pagination}>
                            <button
                                type="button"
                                style={styles.pageButton}
                                disabled={safePage <= 1}
                                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                            >
                                ← Previous
                            </button>
                            <span style={styles.pageInfo}>
                                Page {safePage} of {totalPages} · Showing {pageStart + 1}-{Math.min(pageStart + pageSize, filteredEvents.length)} of {filteredEvents.length}
                            </span>
                            <button
                                type="button"
                                style={styles.pageButton}
                                disabled={safePage >= totalPages}
                                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </section>
            )}
        </div>
    );
}


/* ============================================================
   SUMMARY CARD
============================================================ */

function SummaryCard({ label, value }) {
    return (
        <div style={styles.summaryCard}>
            <span style={styles.summaryLabel}>
                {label}
            </span>

            <strong style={styles.summaryValue}>
                {value}
            </strong>
        </div>
    );
}


/* ============================================================
   HELPERS
============================================================ */

function formatNumber(value, decimals = 2) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
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
        margin: "0 auto 30px",
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
        color: "#64748b",
        fontSize: "15px",
        maxWidth: "750px",
    },

    backButton: {
        textDecoration: "none",
        color: "#0f172a",
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        padding: "11px 16px",
        borderRadius: "10px",
        fontWeight: 600,
    },

    controlCard: {
        maxWidth: "1400px",
        margin: "0 auto 20px",
        padding: "16px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "16px",
        flexWrap: "wrap",
        background: "#ffffff",
        border: "1px solid #cbd5e1",
        borderRadius: "15px",
    },

    searchContainer: {
        flex: "1 1 400px",
        position: "relative",
    },

    searchIcon: {
        position: "absolute",
        left: "14px",
        top: "10px",
        fontSize: "20px",
        color: "#64748b",
    },

    search: {
        width: "100%",
        boxSizing: "border-box",
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        borderRadius: "9px",
        padding: "12px 14px 12px 42px",
        color: "#0f172a",
        outline: "none",
        fontSize: "14px",
    },

    controlsRight: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
    },

    limitLabel: {
        color: "#64748b",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        fontSize: "13px",
    },

    select: {
        background: "#eff6ff",
        color: "#334155",
        border: "1px solid #bfdbfe",
        borderRadius: "8px",
        padding: "9px 10px",
    },

    refreshButton: {
        background: "#2563eb",
        border: "1px solid #32699e",
        color: "#fff",
        padding: "10px 14px",
        borderRadius: "8px",
        cursor: "pointer",
        fontWeight: 650,
    },

    summaryGrid: {
        maxWidth: "1400px",
        margin: "0 auto 20px",
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "14px",
    },

    summaryCard: {
        background:
            "linear-gradient(145deg, #ffffff, #f8fafc)",
        border: "1px solid #cbd5e1",
        borderRadius: "14px",
        padding: "19px",
    },

    summaryLabel: {
        display: "block",
        color: "#64748b",
        fontSize: "12px",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
    },

    summaryValue: {
        display: "block",
        marginTop: "8px",
        fontSize: "27px",
    },

    tableCard: {
        maxWidth: "1400px",
        margin: "0 auto",
        background: "#ffffff",
        border: "1px solid #cbd5e1",
        borderRadius: "17px",
        overflow: "hidden",
    },

    tableHeader: {
        padding: "24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "15px",
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
        fontSize: "21px",
    },

    resultCount: {
        color: "#64748b",
        fontSize: "13px",
    },

    tableWrapper: {
        overflowX: "auto",
    },

    table: {
        width: "100%",
        borderCollapse: "collapse",
        minWidth: "1050px",
    },

    th: {
        textAlign: "left",
        padding: "13px 15px",
        background: "#f1f5f9",
        borderTop: "1px solid #e2e8f0",
        borderBottom: "1px solid #e2e8f0",
        color: "#64748b",
        fontSize: "11px",
        textTransform: "uppercase",
        letterSpacing: "0.07em",
        whiteSpace: "nowrap",
    },

    tr: {
        borderBottom: "1px solid #e2e8f0",
    },

    td: {
        padding: "15px",
        fontSize: "13px",
        color: "#475569",
        verticalAlign: "middle",
    },

    coordinate: {
        color: "#64748b",
        marginTop: "3px",
        fontSize: "12px",
    },

    badge: {
        display: "inline-block",
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        color: "#0369a1",
        padding: "5px 8px",
        borderRadius: "6px",
        fontSize: "11px",
        fontWeight: 700,
    },

    dayBadge: {
        background: "#fef3c7",
        border: "1px solid #fde68a",
        color: "#a16207",
        padding: "5px 8px",
        borderRadius: "6px",
        fontSize: "10px",
        fontWeight: 700,
    },

    nightBadge: {
        background: "#eef2ff",
        border: "1px solid #c7d2fe",
        color: "#4f46e5",
        padding: "5px 8px",
        borderRadius: "6px",
        fontSize: "10px",
        fontWeight: 700,
    },

    viewButton: {
        textDecoration: "none",
        color: "#2563eb",
        fontWeight: 650,
        whiteSpace: "nowrap",
    },

    errorCard: {
        maxWidth: "1400px",
        margin: "20px auto",
        padding: "22px",
        background: "#fee2e2",
        border: "1px solid #fecaca",
        borderRadius: "14px",
        color: "#7f1d1d",
    },

    errorHint: {
        color: "#991b1b",
    },

    loadingCard: {
        maxWidth: "1400px",
        margin: "20px auto",
        padding: "50px",
        textAlign: "center",
        color: "#64748b",
        background: "#f1f5f9",
        border: "1px solid #cbd5e1",
        borderRadius: "15px",
    },

    empty: {
        padding: "60px",
        textAlign: "center",
        color: "#64748b",
    },
    pagination: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
        padding: "18px 0 4px",
    },

    pageButton: {
        border: "1px solid #bfdbfe",
        background: "#eff6ff",
        color: "#0f172a",
        borderRadius: "8px",
        padding: "9px 14px",
        cursor: "pointer",
    },

    pageInfo: {
        color: "#64748b",
        fontSize: "13px",
    },

};

export default Events;