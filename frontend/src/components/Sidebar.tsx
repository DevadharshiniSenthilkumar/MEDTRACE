import { NavLink } from "react-router-dom";
import {
  VialIcon,
  DashboardIcon,
  QueueIcon,
  FacilityIcon,
  MapIcon,
  RootCauseIcon,
  HistoryIcon,
} from "./icons";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: DashboardIcon },
  { to: "/rescue-queue", label: "Rescue queue", icon: QueueIcon },
  { to: "/surplus", label: "Surplus & expiry", icon: MapIcon },
  { to: "/root-causes", label: "Root causes", icon: RootCauseIcon },
  { to: "/history", label: "Feedback history", icon: HistoryIcon },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark">
          <VialIcon size={26} />
        </span>
        <span>MedTrace</span>
      </div>

      <nav className="sidebar-nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              "sidebar-link" + (isActive ? " active" : "")
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
        <NavLink
          to="/"
          className={({ isActive }) =>
            "sidebar-link" + (isActive ? " active" : "")
          }
        >
          <FacilityIcon />
          Load data
        </NavLink>
      </nav>

      <p className="sidebar-foot">
        Decision support only. Every transfer needs officer approval —
        MedTrace never moves stock on its own.
      </p>
    </aside>
  );
}
