import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Bell,
  Search,
  X,
  Thermometer,
  ShieldAlert,
  Factory,
} from "lucide-react";

export default function Topbar() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const [searchText, setSearchText] = useState("");

  const searchRef = useRef(null);
  const alertRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target)
      ) {
        setSearchOpen(false);
      }

      if (
        alertRef.current &&
        !alertRef.current.contains(event.target)
      ) {
        setAlertOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);

    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  // Open search
  const handleSearchClick = () => {
    setAlertOpen(false);
    setSearchOpen((previous) => !previous);

    setTimeout(() => {
      if (!searchOpen) {
        document.getElementById("thermointel-search-input")?.focus();
      }
    }, 50);
  };

  // Open alerts
  const handleAlertClick = () => {
    setSearchOpen(false);
    setAlertOpen((previous) => !previous);
  };

  // Navigate to a dashboard section
  const navigateTo = (path) => {
    window.location.href = path;
  };

  const searchItems = [
    {
      name: "Overview",
      description: "Thermal intelligence dashboard",
      path: "/",
      icon: Activity,
    },
    {
      name: "Thermal Events",
      description: "View detected thermal events",
      path: "/events",
      icon: Thermometer,
    },
    {
      name: "Risk Intelligence",
      description: "View event risk analysis",
      path: "/risk",
      icon: ShieldAlert,
    },
    {
      name: "Industrial Facilities",
      description: "View monitored facilities",
      path: "/facilities",
      icon: Factory,
    },
  ];

  const filteredItems = searchItems.filter((item) => {
    const value = searchText.toLowerCase();

    return (
      item.name.toLowerCase().includes(value) ||
      item.description.toLowerCase().includes(value)
    );
  });

  return (
    <header
      className="topbar"
      style={{
        position: "relative",
        zIndex: 100,
      }}
    >
      <div className="topbar-left">
        <div className="page-context">
          <Activity size={18} />
          <span>THERMAL MONITORING</span>
        </div>
      </div>

      <div className="topbar-right">
        <div className="system-pill">
          <span className="status-dot" />
          LIVE SYSTEM
        </div>

        {/* SEARCH */}
        <div
          ref={searchRef}
          style={{
            position: "relative",
          }}
        >
          <button
            type="button"
            className={`icon-button ${searchOpen ? "active" : ""
              }`}
            onClick={handleSearchClick}
            aria-label="Search"
            title="Search"
          >
            <Search size={18} />
          </button>

          {searchOpen && (
            <div
              style={{
                position: "absolute",
                top: "48px",
                right: "0",
                width: "340px",
                background: "#ffffff",
                border: "1px solid rgba(89, 177, 255, 0.20)",
                borderRadius: "12px",
                padding: "12px",
                boxShadow: "0 18px 45px rgba(0, 0, 0, 0.45)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 12px",
                  background: "#f8fafc",
                  border: "1px solid rgba(89, 177, 255, 0.15)",
                  borderRadius: "8px",
                }}
              >
                <Search size={16} color="#69c5ff" />

                <input
                  id="thermointel-search-input"
                  type="text"
                  value={searchText}
                  onChange={(event) =>
                    setSearchText(event.target.value)
                  }
                  placeholder="Search ThermoIntel..."
                  style={{
                    width: "100%",
                    border: "none",
                    outline: "none",
                    background: "transparent",
                    color: "#e8f1fb",
                    fontSize: "14px",
                  }}
                />

                {searchText && (
                  <button
                    type="button"
                    onClick={() => setSearchText("")}
                    style={{
                      border: "none",
                      background: "transparent",
                      color: "#6f8aa3",
                      cursor: "pointer",
                      padding: "2px",
                      display: "flex",
                    }}
                  >
                    <X size={15} />
                  </button>
                )}
              </div>

              <div
                style={{
                  marginTop: "8px",
                }}
              >
                {filteredItems.length > 0 ? (
                  filteredItems.map((item) => {
                    const Icon = item.icon;

                    return (
                      <button
                        key={item.name}
                        type="button"
                        onClick={() => navigateTo(item.path)}
                        style={{
                          width: "100%",
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          padding: "11px 10px",
                          border: "none",
                          borderRadius: "8px",
                          background: "transparent",
                          color: "#e8f1fb",
                          cursor: "pointer",
                          textAlign: "left",
                        }}
                        onMouseEnter={(event) => {
                          event.currentTarget.style.background =
                            "rgba(56, 161, 255, 0.10)";
                        }}
                        onMouseLeave={(event) => {
                          event.currentTarget.style.background =
                            "transparent";
                        }}
                      >
                        <div
                          style={{
                            width: "34px",
                            height: "34px",
                            borderRadius: "8px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background:
                              "rgba(56, 161, 255, 0.10)",
                            color: "#62c3ff",
                            flexShrink: 0,
                          }}
                        >
                          <Icon size={17} />
                        </div>

                        <div>
                          <div
                            style={{
                              fontSize: "13px",
                              fontWeight: 600,
                            }}
                          >
                            {item.name}
                          </div>

                          <div
                            style={{
                              marginTop: "2px",
                              fontSize: "11px",
                              color: "#66829c",
                            }}
                          >
                            {item.description}
                          </div>
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <div
                    style={{
                      padding: "18px 10px",
                      textAlign: "center",
                      color: "#66829c",
                      fontSize: "13px",
                    }}
                  >
                    No matching section found.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ALERTS */}
        <div
          ref={alertRef}
          style={{
            position: "relative",
          }}
        >
          <button
            type="button"
            className={`icon-button ${alertOpen ? "active" : ""
              }`}
            onClick={handleAlertClick}
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell size={18} />

            <span
              style={{
                position: "absolute",
                top: "5px",
                right: "5px",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#35d69a",
                boxShadow: "0 0 8px rgba(53, 214, 154, 0.8)",
              }}
            />
          </button>

          {alertOpen && (
            <div
              style={{
                position: "absolute",
                top: "48px",
                right: "0",
                width: "320px",
                background: "#ffffff",
                border: "1px solid rgba(89, 177, 255, 0.20)",
                borderRadius: "12px",
                overflow: "hidden",
                boxShadow: "0 18px 45px rgba(0, 0, 0, 0.45)",
              }}
            >
              <div
                style={{
                  padding: "14px 16px",
                  borderBottom:
                    "1px solid rgba(89, 177, 255, 0.10)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div
                    style={{
                      color: "#e8f1fb",
                      fontSize: "14px",
                      fontWeight: 700,
                    }}
                  >
                    System Alerts
                  </div>

                  <div
                    style={{
                      color: "#66829c",
                      fontSize: "11px",
                      marginTop: "3px",
                    }}
                  >
                    ThermoIntel system status
                  </div>
                </div>

                <span
                  style={{
                    fontSize: "10px",
                    color: "#35d69a",
                    background: "rgba(53, 214, 154, 0.10)",
                    padding: "5px 8px",
                    borderRadius: "6px",
                  }}
                >
                  ACTIVE
                </span>
              </div>

              <div
                style={{
                  padding: "8px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    gap: "11px",
                    padding: "12px 10px",
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "8px",
                      background: "rgba(53, 214, 154, 0.10)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#35d69a",
                      flexShrink: 0,
                    }}
                  >
                    <Activity size={16} />
                  </div>

                  <div>
                    <div
                      style={{
                        color: "#e8f1fb",
                        fontSize: "13px",
                        fontWeight: 600,
                      }}
                    >
                      Intelligence engine online
                    </div>

                    <div
                      style={{
                        color: "#66829c",
                        fontSize: "11px",
                        marginTop: "3px",
                        lineHeight: 1.4,
                      }}
                    >
                      Thermal monitoring and risk intelligence
                      systems are operational.
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: "11px",
                    padding: "12px 10px",
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "8px",
                      background: "rgba(98, 195, 255, 0.10)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#62c3ff",
                      flexShrink: 0,
                    }}
                  >
                    <Thermometer size={16} />
                  </div>

                  <div>
                    <div
                      style={{
                        color: "#e8f1fb",
                        fontSize: "13px",
                        fontWeight: 600,
                      }}
                    >
                      Thermal monitoring active
                    </div>

                    <div
                      style={{
                        color: "#66829c",
                        fontSize: "11px",
                        marginTop: "3px",
                      }}
                    >
                      Detection database available.
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    gap: "11px",
                    padding: "12px 10px",
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "8px",
                      background: "rgba(255, 173, 66, 0.10)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#ffad42",
                      flexShrink: 0,
                    }}
                  >
                    <ShieldAlert size={16} />
                  </div>

                  <div>
                    <div
                      style={{
                        color: "#e8f1fb",
                        fontSize: "13px",
                        fontWeight: 600,
                      }}
                    >
                      Risk intelligence ready
                    </div>

                    <div
                      style={{
                        color: "#66829c",
                        fontSize: "11px",
                        marginTop: "3px",
                      }}
                    >
                      Risk classification pipeline available.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}