import {
  LayoutDashboard,
  Radio,
  ShieldAlert,
  Factory,
} from "lucide-react";

import { NavLink } from "react-router-dom";

const navigation = [
  {
    label: "Overview",
    path: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Thermal Events",
    path: "/events",
    icon: Radio,
  },
  {
    label: "Risk Intelligence",
    path: "/risk",
    icon: ShieldAlert,
  },
  {
    label: "Industrial Facilities",
    path: "/facilities",
    icon: Factory,
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">TI</div>

        <div>
          <div className="brand-name">
            ThermoIntel
          </div>

          <div className="brand-subtitle">
            EVENT INTELLIGENCE
          </div>
        </div>
      </div>

      <div className="nav-section">
        <div className="nav-title">
          OPERATIONS
        </div>

        {navigation.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${
                  isActive ? "active" : ""
                }`
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot" />
          <span>INTELLIGENCE ENGINE ONLINE</span>
        </div>
      </div>
    </aside>
  );
}