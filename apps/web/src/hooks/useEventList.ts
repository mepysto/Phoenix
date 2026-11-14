"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { eventsAPI, type ApiDisasterEvent, type EventFacets } from "@/lib/api/client";
import { toEventFilter, type EventQuery } from "@/lib/eventQuery";

export const LIST_PAGE_SIZE = 50;

interface EventListState {
  events: ApiDisasterEvent[];
  total: number;
  facets: EventFacets | null;
  loading: boolean;
  loadingMore: boolean;
  error: boolean;
}

/**
 * One page of the disaster list in the chosen order, plus the counts for the
 * filter chips. A newer query always wins over a slower, older response.
 */
export function useEventList(query: EventQuery) {
  const [state, setState] = useState<EventListState>({
    events: [],
    total: 0,
    facets: null,
    loading: true,
    loadingMore: false,
    error: false,
  });
  const request = useRef(0);
  const key = JSON.stringify(query);

  const load = useCallback(() => {
    const id = ++request.current;
    const filter = toEventFilter(query);
    setState((s) => ({ ...s, loading: true, error: false }));
    Promise.all([eventsAPI.list(filter, LIST_PAGE_SIZE, 0, query.sort), eventsAPI.facets(filter)])
      .then(([page, facets]) => {
        if (id !== request.current) return;
        setState({
          events: page.data,
          total: page.pagination.total,
          facets,
          loading: false,
          loadingMore: false,
          error: false,
        });
      })
      .catch(() => {
        if (id === request.current) setState((s) => ({ ...s, loading: false, error: true }));
      });
    // query is captured through key
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(load, [load]);

  const loadMore = useCallback(() => {
    const id = request.current;
    setState((s) => ({ ...s, loadingMore: true }));
    eventsAPI
      .list(toEventFilter(query), LIST_PAGE_SIZE, state.events.length, query.sort)
      .then((page) => {
        if (id !== request.current) return;
        setState((s) => ({
          ...s,
          events: [...s.events, ...page.data.filter((e) => !s.events.some((x) => x.id === e.id))],
          total: page.pagination.total,
          loadingMore: false,
        }));
      })
      .catch(() => {
        if (id === request.current) setState((s) => ({ ...s, loadingMore: false, error: true }));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, state.events.length]);

  return { ...state, reload: load, loadMore, hasMore: state.events.length < state.total };
}
