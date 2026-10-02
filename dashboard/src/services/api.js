import axios from "axios";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    Accept: "application/json",
  },
});


// ============================================================
// THERMAL EVENTS
// ============================================================

export async function getEvents(limit = null, windowHours = null, location = null) {
  const params = {};

  if (limit !== null && limit !== undefined) {
    params.limit = limit;
  }

  if (windowHours !== null && windowHours !== undefined) params.window_hours = windowHours;
  if (location?.latitude != null && location?.longitude != null) {
    params.latitude = location.latitude;
    params.longitude = location.longitude;
    params.radius_km = location.radius_km;
  }

  const { data } = await api.get("/events", {
    params,
  });

  return data;
}


export async function getEvent(eventId) {
  const { data } = await api.get(`/events/${eventId}`);
  return data;
}


export async function getNearbyEvents(
  latitude,
  longitude,
  radius_km = 10
) {
  const { data } = await api.get("/events/nearby", {
    params: {
      latitude,
      longitude,
      radius_km,
    },
  });

  return data;
}


export async function getEventContext(eventId) {
  const { data } = await api.get(`/events/${eventId}/context`);
  return data;
}


export async function getEventSummary() {
  const { data } = await api.get("/events/summary");
  return data;
}


// ============================================================
// DASHBOARD
// ============================================================

export async function getDashboardSummary(windowHours = null, location = null) {
  const params = {};

  if (windowHours !== null && windowHours !== undefined) params.window_hours = windowHours;
  if (location?.latitude != null && location?.longitude != null) {
    params.latitude = location.latitude; params.longitude = location.longitude; params.radius_km = location.radius_km;
  }

  const { data } = await api.get("/dashboard/summary", {
    params,
  });

  return data;
}


// ============================================================
// FACILITIES
// ============================================================

export async function getFacilities(limit = null, offset = 0, location = null, search = null) {
  const params = { offset };
  if (limit !== null && limit !== undefined) params.limit = limit;
  if (search) params.search = search;
  if (location?.latitude != null && location?.longitude != null) { params.latitude = location.latitude; params.longitude = location.longitude; params.radius_km = location.radius_km; }
  const { data } = await api.get("/facilities", { params });

  return data;
}


// ============================================================
// RISK
// ============================================================

export async function getRiskSummary() {
  const { data } = await api.get("/risk/summary");
  return data;
}


export async function getRiskScores(limit = 100000, location = null) {
  const params = { limit };
  if (location?.latitude != null && location?.longitude != null) { params.latitude = location.latitude; params.longitude = location.longitude; params.radius_km = location.radius_km; }
  const { data } = await api.get("/risk", { params });

  return data;
}


export async function getRiskEvent(eventId) {
  const { data } = await api.get(`/risk/${eventId}`);
  return data;
}


// ============================================================
// INTELLIGENCE
// ============================================================

export async function getIntelligenceSummary() {
  const { data } = await api.get("/intelligence/summary");
  return data;
}


export async function getIntelligenceEvents(limit = 100000) {
  const { data } = await api.get("/intelligence/events", {
    params: {
      limit,
    },
  });

  return data;
}


export async function getHighRiskEvents(limit = 20) {
  const { data } = await api.get("/intelligence/high-risk", {
    params: {
      limit,
    },
  });

  return data;
}


export async function getIntelligenceEvent(eventId) {
  const { data } = await api.get(`/intelligence/events/${eventId}`);
  return data;
}

export async function searchLocation(query) {
  const { data } = await api.get("/locations/search", { params: { q: query } });
  return data;
}

export default api;