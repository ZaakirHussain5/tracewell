import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Explorer } from "./components/Explorer";
import { Layout } from "./components/Layout";
import { TraceDetail } from "./components/TraceDetail";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Explorer />} />
          <Route path="traces/:traceId" element={<TraceDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
