import {
  Activity,
  Flame,
  ShieldAlert,
  Factory,
  TrendingUp,
} from "lucide-react";

import { useEffect, useState } from "react";

import StatCard from "../components/StatCard";
import ThermalMap from "../components/ThermalMap";
import LocationFilter from "../components/LocationFilter";

import {
  getDashboardSummary,
  getEvents,
  getFacilities,
} from "../services/api";


const WINDOW_OPTIONS = [
  {
    label: "LIVE",
    value: null,
  },
  {
    label: "24 HOURS",
    value: 24,
  },
  {
    label: "3 DAYS",
    value: 72,
  },
  {
    label: "7 DAYS",
    value: 168,
  },
];


export default function Dashboard() {

  const [summary, setSummary] = useState(null);

  const [events, setEvents] = useState([]);

  const [facilityCount, setFacilityCount] = useState(0);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  const [windowHours, setWindowHours] = useState(null);
  const [location, setLocation] = useState(null);

  const [currentTime, setCurrentTime] = useState(
    new Date()
  );


  // ============================================================
  // LIVE CLOCK
  // ============================================================

  useEffect(() => {

    const clockInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      clearInterval(clockInterval);
    };

  }, []);


  // ============================================================
  // LOAD DASHBOARD
  // ============================================================

  useEffect(() => {

    let mounted = true;


    async function loadDashboard() {

      try {

        setError(null);


        // ------------------------------------------------------
        // Dashboard summary and event feed use EXACTLY
        // the same selected window.
        // ------------------------------------------------------

        const [summaryData, eventData, facilityData] =
          await Promise.all([

            getDashboardSummary(windowHours, location),

            getEvents(null, windowHours, location),

            getFacilities(1, 0, location),

          ]);


        if (!mounted) {
          return;
        }


        setSummary(summaryData);


        setEvents(
          Array.isArray(eventData?.events)
            ? eventData.events
            : []
        );


        setFacilityCount(
          Number(
            facilityData?.total_count ??
            facilityData?.count
          ) || 0
        );

      }

      catch (err) {

        if (!mounted) {
          return;
        }


        console.error(
          "[Dashboard] Loading error:",
          err
        );


        setError(
          err?.response?.data?.detail ||
          err?.message ||
          "Unable to connect to ThermoIntel backend."
        );

      }

      finally {

        if (mounted) {
          setLoading(false);
        }

      }

    }


    setLoading(true);

    loadDashboard();


    // Refresh dashboard data every 60 seconds.

    const refreshInterval = setInterval(
      loadDashboard,
      60 * 1000
    );


    return () => {

      mounted = false;

      clearInterval(refreshInterval);

    };

  }, [windowHours, location]);


  // ============================================================
  // LOADING
  // ============================================================

  if (loading) {

    return (
      <div className="loading-screen">

        <Activity
          className="spin"
          size={28}
        />

        <span>
          Loading intelligence system...
        </span>

      </div>
    );

  }


  // ============================================================
  // ERROR
  // ============================================================

  if (error) {

    return (
      <div className="error-panel">

        <ShieldAlert size={28} />

        <div>

          <h2>
            Backend connection failed
          </h2>

          <p>
            {error}
          </p>

          <code>API: /api/v1 · Backend: container/local proxy</code>

        </div>

      </div>
    );

  }


  // ============================================================
  // SUMMARY VALUES
  // ============================================================

  const totalEvents =
    Number(
      summary?.thermal?.total_events
    ) || 0;


  const riskEvents =
    Number(summary?.overview?.risk_assessed_events) || 0;

  const dayEvents = Number(summary?.thermal?.day_events) || 0;
  const nightEvents = Number(summary?.thermal?.night_events) || 0;


  const averageFRP =
    Number(
      summary?.thermal?.average_max_frp
    ) || 0;


  const maximumFRP =
    Number(
      summary?.thermal?.maximum_frp
    ) || 0;


  const earliestEvent =
    summary?.thermal?.earliest_event ||
    null;


  const latestEvent =
    summary?.thermal?.latest_event ||
    null;


  const selectedWindow =
    WINDOW_OPTIONS.find(
      (option) =>
        option.value === windowHours
    );


  const selectedWindowLabel =
    selectedWindow?.label || "LIVE";


  const isLive =
    windowHours === null;


  // ============================================================
  // MONITORING WINDOW
  // ============================================================

  const liveWindowEnd =
    currentTime;


  const liveWindowStart =
    !isLive
      ? new Date(
        currentTime.getTime() -
        windowHours *
        60 *
        60 *
        1000
      )
      : null;


  const formatDateTime = (value) => {

    if (!value) {
      return "—";
    }

    return new Date(
      value
    ).toLocaleString();

  };


  return (
    <>

      {/* ======================================================
          HERO
      ====================================================== */}

      <section className="hero">

        <div>

          <div className="eyebrow">
            EVENT INTELLIGENCE PLATFORM
          </div>

          <h1>
            Thermal Intelligence
            <br />
            Operations Center
          </h1>

          <p>
            Unified thermal detection,
            industrial context and risk
            intelligence.
          </p>

        </div>


        <div className="hero-status">

          <div className="status-dot large" />

          <div>

            <strong>
              ENGINE ONLINE
            </strong>

            <span>
              Intelligence pipeline operational
            </span>

          </div>

        </div>

      </section>


      <section className="panel" style={{ marginTop: "22px" }}>
        <LocationFilter value={location} onApply={setLocation} />
      </section>

      <section className="panel" style={{ marginTop: "22px" }}>
        <div className="panel-header">
          <div>
            <div className="panel-kicker">THERMAL IMAGING / SATELLITE VIEW</div>
            <h2>India Thermal Event Map</h2>
          </div>
          <span>{events.length} events in selected window</span>
        </div>
        <ThermalMap events={events} location={location} />
      </section>

      {/* ======================================================
          WINDOW SELECTOR
      ====================================================== */}

      <section className="panel">

        <div className="panel-header">

          <div>

            <div className="panel-kicker">
              DATA WINDOW
            </div>

            <h2>
              Monitoring Range
            </h2>

          </div>


          <div className="panel-badge">
            {selectedWindowLabel}
          </div>

        </div>


        <div
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
          }}
        >

          {WINDOW_OPTIONS.map(
            (option) => {

              const selected =
                option.value ===
                windowHours;


              return (
                <button
                  key={option.label}
                  type="button"
                  onClick={() =>
                    setWindowHours(
                      option.value
                    )
                  }
                  style={{
                    padding:
                      "10px 16px",

                    borderRadius:
                      "8px",

                    border:
                      selected
                        ? "1px solid #93c5fd"
                        : "1px solid #cbd5e1",

                    background:
                      selected
                        ? "#eff6ff"
                        : "#ffffff",

                    cursor:
                      "pointer",

                    fontWeight:
                      selected
                        ? 700
                        : 500,
                    color: selected ? "#1d4ed8" : "#475569",
                  }}
                >

                  {option.label}

                </button>
              );

            }
          )}

        </div>

      </section>


      {/* ======================================================
          STAT CARDS
      ====================================================== */}

      <section className="stats-grid">

        <StatCard
          title="THERMAL EVENTS"
          value={totalEvents}
          subtitle={`${selectedWindowLabel} window`}
          icon={Flame}
        />


        <StatCard
          title="DAY EVENTS"
          value={dayEvents}
          subtitle="Satellite day observations"
          icon={Activity}
        />

        <StatCard
          title="NIGHT EVENTS"
          value={nightEvents}
          subtitle="Satellite night observations"
          icon={Activity}
        />

        <StatCard
          title="AVERAGE FRP"
          value={`${averageFRP.toFixed(2)} MW`}
          subtitle="Average event maximum"
          icon={Activity}
        />


        <StatCard
          title="MAXIMUM FRP"
          value={`${maximumFRP.toFixed(2)} MW`}
          subtitle="Highest observed"
          icon={TrendingUp}
          variant="warning"
        />


        <StatCard
          title="FACILITIES"
          value={facilityCount}
          subtitle="Industrial locations"
          icon={Factory}
        />

      </section>


      {/* ======================================================
          EVENT ACTIVITY + COVERAGE
      ====================================================== */}

      <section className="dashboard-grid">


        {/* EVENT ACTIVITY */}

        <div className="panel large-panel">

          <div className="panel-header">

            <div>

              <div className="panel-kicker">
                LIVE DATA
              </div>

              <h2>
                Thermal Event Activity
              </h2>

            </div>


            <div className="panel-badge">
              {totalEvents} EVENTS
            </div>

          </div>


          <div className="event-feed">

            {events.length === 0 ? (

              <div className="empty-state">
                No thermal events available.
              </div>

            ) : (

              events
                .slice(0, 8)
                .map((event) => (

                  <div
                    className="event-row"
                    key={event.id}
                  >

                    <div className="event-marker">

                      <Flame size={16} />

                    </div>


                    <div className="event-main">

                      <strong>
                        Thermal event #{event.id}
                      </strong>

                      <span>

                        {event.thermal_classification || "OTHER THERMAL SOURCE"}

                      </span>

                      <span>

                        {Number.isFinite(
                          Number(event.latitude)
                        )
                          ? Number(
                            event.latitude
                          ).toFixed(4)
                          : "—"}

                        {", "}

                        {Number.isFinite(
                          Number(event.longitude)
                        )
                          ? Number(
                            event.longitude
                          ).toFixed(4)
                          : "—"}

                      </span>

                    </div>


                    <div className="event-frp">

                      <strong>

                        {Number(
                          event.max_frp || 0
                        ).toFixed(2)}

                      </strong>

                      <span>
                        MW FRP
                      </span>

                    </div>


                    <div className="event-time">

                      {event.last_detected_at
                        ? new Date(
                          event.last_detected_at
                        ).toLocaleString()
                        : "—"}

                    </div>

                  </div>

                ))

            )}

          </div>

        </div>


        {/* INTELLIGENCE COVERAGE */}

        <div className="panel">

          <div className="panel-header">

            <div>

              <div className="panel-kicker">
                SYSTEM
              </div>

              <h2>
                Intelligence Coverage
              </h2>

            </div>

          </div>


          <div className="coverage-list">

            <div>

              <span>
                Thermal events
              </span>

              <strong>
                {totalEvents}
              </strong>

            </div>


            <div>

              <span>
                Risk assessed
              </span>

              <strong>
                {riskEvents}
              </strong>

            </div>


            <div>

              <span>
                Industrial facilities
              </span>

              <strong>
                {facilityCount}
              </strong>

            </div>


            <div>

              <span>
                Pipeline
              </span>

              <strong>
                Active
              </strong>

            </div>

          </div>


          <div className="coverage-status">

            <span className="status-dot" />

            Spatial intelligence available

          </div>

        </div>

      </section>


      {/* ======================================================
          MONITORING WINDOW
      ====================================================== */}

      <section className="panel">

        <div className="panel-header">

          <div>

            <div className="panel-kicker">
              SYSTEM INFORMATION
            </div>

            <h2>
              Monitoring Window
            </h2>

          </div>


          <div className="panel-badge">
            {selectedWindowLabel}
          </div>

        </div>


        <div className="time-range">

          <div>

            <span>
              {isLive
                ? "EARLIEST DETECTION"
                : "WINDOW START"}
            </span>


            <strong>

              {isLive
                ? formatDateTime(
                  earliestEvent
                )
                : formatDateTime(
                  liveWindowStart
                )}

            </strong>

          </div>


          <div className="range-line" />


          <div>

            <span>
              CURRENT TIME
            </span>


            <strong>
              {formatDateTime(
                liveWindowEnd
              )}
            </strong>

          </div>

        </div>


        {!isLive && (

          <div
            style={{
              marginTop: "12px",
              fontSize: "0.85rem",
              opacity: 0.7,
            }}
          >

            Latest detected event:{" "}

            {latestEvent
              ? formatDateTime(
                latestEvent
              )
              : "—"}

          </div>

        )}


        {isLive && latestEvent && (

          <div
            style={{
              marginTop: "12px",
              fontSize: "0.85rem",
              opacity: 0.7,
            }}
          >

            Latest detected event:{" "}

            {formatDateTime(
              latestEvent
            )}

          </div>

        )}

      </section>

    </>
  );
}