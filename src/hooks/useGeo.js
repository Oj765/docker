// frontend/src/hooks/useGeo.js
// React Query hooks for all geo endpoints

import { useQuery, useMutation } from '@tanstack/react-query';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const get = async (path) => {
  const r = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('jwt') || ''}` }
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
};

const post = async (path, body) => {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('jwt') || ''}`
    },
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
};

export const useHeatmap = (hours = 24) =>
  useQuery({
    queryKey:   ['geo', 'heatmap', hours],
    queryFn:    () => get(`/geo/heatmap?hours=${hours}`),
    refetchInterval: 30_000,   // refresh every 30s
    staleTime:  20_000,
  });

export const useGeoSummary = () =>
  useQuery({
    queryKey:   ['geo', 'summary'],
    queryFn:    () => get('/geo/summary'),
    refetchInterval: 30_000,
    staleTime:  20_000,
  });

export const useCountryDetail = (countryCode, days = 7) =>
  useQuery({
    queryKey:   ['geo', 'country', countryCode, days],
    queryFn:    () => get(`/geo/country/${countryCode}?days=${days}`),
    enabled:    !!countryCode,
    staleTime:  60_000,
  });

export const useGeoFilter = () =>
  useMutation({
    mutationFn: (params) => post('/geo/filter', params),
  });
