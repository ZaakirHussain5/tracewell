import { NavLink, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Tracewell
        </NavLink>
        <p className="brand-sub">Agent trace explorer</p>
        <span className="project-chip">Strata Ops</span>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
