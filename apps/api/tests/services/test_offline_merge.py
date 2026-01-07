"""Tests for OfflineMergeService."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.event import (
    Dataset,
    Event,
    EventMetric,
    EventSource,
    EventType,
    GeoPrecision,
    GeoLayer,
    SeverityLevel,
)
from src.services.dedup.offline_merge_service import (
    OfflineMergeConfig,
    OfflineMergeService,
    OfflineMergeStats,
    ADVISORY_LOCK_ID,
)
from src.services.dedup import offline_merge_service as oms_module


class TestOfflineMergeConfig:
    def test_default_values(self):
        config = OfflineMergeConfig()

        assert config.chunk_size == 1000
        assert config.fuzzy_radius_meters == 50_000
        assert config.fuzzy_window_hours == 48
        assert config.max_group_size == 200
        assert config.progress_log_every == 100
        assert config.dry_run is False

    def test_custom_values(self):
        config = OfflineMergeConfig(
            chunk_size=500,
            fuzzy_radius_meters=100_000,
            fuzzy_window_hours=72,
            max_group_size=100,
            progress_log_every=50,
            dry_run=True,
        )

        assert config.chunk_size == 500
        assert config.fuzzy_radius_meters == 100_000
        assert config.fuzzy_window_hours == 72
        assert config.max_group_size == 100
        assert config.progress_log_every == 50
        assert config.dry_run is True


class TestOfflineMergeStats:
    def test_default_values(self):
        stats = OfflineMergeStats()

        assert stats.scanned == 0
        assert stats.groups_found == 0
        assert stats.merges_applied == 0
        assert stats.sources_relinked == 0
        assert stats.duplicates_marked == 0
        assert stats.skipped == 0
        assert stats.errors == []

    def test_can_add_errors(self):
        stats = OfflineMergeStats()
        stats.errors.append("Test error")

        assert len(stats.errors) == 1
        assert stats.errors[0] == "Test error"

    def test_new_relink_fields_default_to_zero(self):
        stats = OfflineMergeStats()

        assert stats.geo_layers_relinked == 0
        assert stats.datasets_relinked == 0
        assert stats.metrics_relinked == 0


class TestOfflineMergeServiceInit:
    def test_init_with_default_config(self):
        session = AsyncMock()
        service = OfflineMergeService(session)

        assert service.session == session
        assert service.config.dry_run is False
        assert service._lock_connection is None

    def test_init_with_custom_config(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=True)
        service = OfflineMergeService(session, config)

        assert service.config.dry_run is True


class TestOfflineMergeServiceLocking:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        return OfflineMergeService(session)

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, service):
        mock_connection = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = True
        mock_connection.execute.return_value = mock_result

        async def mock_connect():
            return mock_connection

        with patch.object(oms_module, "engine") as mock_engine:
            mock_engine.connect = mock_connect

            result = await service.acquire_lock()

            assert result is True
            assert service._lock_connection is mock_connection

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, service):
        mock_connection = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_connection.execute.return_value = mock_result

        async def mock_connect():
            return mock_connection

        with patch.object(oms_module, "engine") as mock_engine:
            mock_engine.connect = mock_connect

            result = await service.acquire_lock()

            assert result is False
            assert service._lock_connection is None
            mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_when_acquired(self, service):
        mock_connection = AsyncMock()
        service._lock_connection = mock_connection

        await service.release_lock()

        assert service._lock_connection is None
        mock_connection.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_when_not_acquired(self, service):
        service._lock_connection = None

        await service.release_lock()


class TestOfflineMergeServiceSelectCanonical:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        return OfflineMergeService(session)

    def _create_mock_event(
        self,
        geo_precision: GeoPrecision = GeoPrecision.approximate,
        has_sources: bool = True,
        source_name: str = "GDACS",
    ) -> MagicMock:
        event = MagicMock(spec=Event)
        event.id = uuid4()
        event.type = EventType.earthquake
        event.title = "Test Event"
        event.description = "Description"
        event.latitude = 35.0
        event.longitude = 139.0
        event.geo_precision = geo_precision
        event.region = "Japan"
        event.country_code = "JP"
        event.severity = SeverityLevel.high
        event.glide_number = "EQ-2024-000001-JPN"
        event.affected_population = 10000
        event.updated_at = datetime.now(timezone.utc)
        event.created_at = datetime.now(timezone.utc)

        if has_sources:
            mock_source = MagicMock()
            mock_source.source = MagicMock()
            mock_source.source.name = source_name
            event.sources = [mock_source]
        else:
            event.sources = []

        return event

    def test_select_higher_geo_precision(self, service):
        event_approximate = self._create_mock_event(geo_precision=GeoPrecision.approximate)
        event_exact = self._create_mock_event(geo_precision=GeoPrecision.exact)

        canonical = service._select_canonical([event_approximate, event_exact])

        assert canonical.id == event_exact.id

    def test_select_higher_source_reliability(self, service):
        event_gdacs = self._create_mock_event(source_name="GDACS")
        event_eonet = self._create_mock_event(source_name="EONET")

        canonical = service._select_canonical([event_eonet, event_gdacs])

        assert canonical.id == event_gdacs.id

    def test_select_with_no_sources(self, service):
        event1 = self._create_mock_event(has_sources=False)
        event2 = self._create_mock_event(has_sources=True, source_name="GDACS")

        canonical = service._select_canonical([event1, event2])

        assert canonical.id == event2.id


class TestOfflineMergeServiceResolveGroup:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=True)
        return OfflineMergeService(session, config)

    def _create_mock_event(self, event_id=None) -> MagicMock:
        event = MagicMock(spec=Event)
        event.id = event_id or uuid4()
        event.type = EventType.earthquake
        event.title = "Test Event"
        event.description = "Description"
        event.geo_precision = GeoPrecision.approximate
        event.updated_at = datetime.now(timezone.utc)
        event.created_at = datetime.now(timezone.utc)

        mock_source = MagicMock()
        mock_source.source = MagicMock()
        mock_source.source.name = "GDACS"
        event.sources = [mock_source]

        return event

    @pytest.mark.asyncio
    async def test_resolve_group_with_single_event(self, service):
        result = await service.resolve_group([uuid4()])

        assert result["merges"] == 0
        assert result["duplicates_marked"] == 0

    @pytest.mark.asyncio
    async def test_resolve_group_dry_run(self, service):
        event1 = self._create_mock_event()
        event2 = self._create_mock_event()
        event_ids = [event1.id, event2.id]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event1, event2]
        service.session.execute.return_value = mock_result

        result = await service.resolve_group(event_ids)

        assert result["duplicates_marked"] == 1
        assert result["merges"] == 1


class TestOfflineMergeServiceRun:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=True, max_group_size=10)
        return OfflineMergeService(session, config)

    @pytest.mark.asyncio
    async def test_run_fails_without_lock(self, service):
        service.acquire_lock = AsyncMock(return_value=False)

        stats = await service.run()

        assert len(stats.errors) == 1
        assert "advisory lock" in stats.errors[0].lower()
        assert stats.groups_found == 0

    @pytest.mark.asyncio
    async def test_run_skips_large_groups(self, service):
        service.acquire_lock = AsyncMock(return_value=True)
        service.release_lock = AsyncMock()

        large_group = [uuid4() for _ in range(20)]
        service.find_duplicate_groups = AsyncMock(return_value=[large_group])

        stats = await service.run()

        assert stats.skipped == 1
        assert stats.groups_found == 1


class TestOfflineMergeServiceIntegration:
    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_full_dry_run_flow(self, session):
        config = OfflineMergeConfig(dry_run=True)
        service = OfflineMergeService(session, config)

        service.acquire_lock = AsyncMock(return_value=True)
        service.release_lock = AsyncMock()
        service.find_duplicate_groups = AsyncMock(return_value=[])

        stats = await service.run()

        assert stats.groups_found == 0
        assert stats.merges_applied == 0
        assert len(stats.errors) == 0
        service.release_lock.assert_called_once()


class TestOfflineMergeServiceConnectedComponent:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=True, max_group_size=10)
        return OfflineMergeService(session, config)

    def _create_mock_event(self, event_id=None, lat=35.0, lng=139.0) -> MagicMock:
        event = MagicMock(spec=Event)
        event.id = event_id or uuid4()
        event.type = EventType.earthquake
        event.latitude = lat
        event.longitude = lng
        event.start_date = datetime.now(timezone.utc)
        return event

    @pytest.mark.asyncio
    async def test_expand_connected_component_finds_bridge_duplicates(self, service):
        event_a = self._create_mock_event()
        event_b = self._create_mock_event()
        event_c = self._create_mock_event()

        call_count = 0
        async def mock_find_candidates(ref, exclude_ids):
            nonlocal call_count
            call_count += 1
            if ref.id == event_a.id:
                return [event_b]
            elif ref.id == event_b.id:
                return [event_c]
            return []

        service._find_spatiotemporal_candidates = mock_find_candidates

        group = await service._expand_connected_component(
            seed_event=event_a,
            exclude_ids=set(),
        )

        assert len(group) == 3
        assert event_a.id in group
        assert event_b.id in group
        assert event_c.id in group

    @pytest.mark.asyncio
    async def test_expand_connected_component_respects_max_group_size(self, service):
        events = [self._create_mock_event() for _ in range(15)]

        async def mock_find_candidates(ref, exclude_ids):
            remaining = [e for e in events if e.id not in exclude_ids and e.id != ref.id]
            return remaining[:5]

        service._find_spatiotemporal_candidates = mock_find_candidates

        group = await service._expand_connected_component(
            seed_event=events[0],
            exclude_ids=set(),
        )

        assert len(group) <= service.config.max_group_size + 1


class TestOfflineMergeServiceRollback:
    @pytest.mark.asyncio
    async def test_rollback_on_group_error(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=False, max_group_size=10)
        service = OfflineMergeService(session, config)

        service.acquire_lock = AsyncMock(return_value=True)
        service.release_lock = AsyncMock()

        group1 = [uuid4(), uuid4()]
        group2 = [uuid4(), uuid4()]
        service.find_duplicate_groups = AsyncMock(return_value=[group1, group2])

        call_count = 0
        async def failing_resolve(event_ids):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated failure")
            return {
                "merges": 1,
                "sources_relinked": 0,
                "geo_layers_relinked": 0,
                "datasets_relinked": 0,
                "metrics_relinked": 0,
                "duplicates_marked": 1,
            }

        service.resolve_group = failing_resolve

        stats = await service.run()

        assert len(stats.errors) == 1
        assert stats.merges_applied == 1
        session.rollback.assert_called_once()
        session.commit.assert_called_once()


class TestOfflineMergeServiceRelinkChildren:
    @pytest.fixture
    def service(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=False)
        return OfflineMergeService(session, config)

    @pytest.fixture
    def dry_run_service(self):
        session = AsyncMock()
        config = OfflineMergeConfig(dry_run=True)
        return OfflineMergeService(session, config)

    @pytest.mark.asyncio
    async def test_relink_geo_layers_moves_all_layers(self, service):
        from_event_id = uuid4()
        to_event_id = uuid4()
        layer_ids = [uuid4(), uuid4(), uuid4()]

        mock_result = MagicMock()
        mock_result.all.return_value = [(lid,) for lid in layer_ids]
        service.session.execute.return_value = mock_result

        count = await service._relink_geo_layers(from_event_id, to_event_id)

        assert count == 3
        service.session.execute.assert_called_once()

        call_args = service.session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "geo_layers" in compiled.lower()
        assert "UPDATE" in compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_datasets_moves_all_datasets(self, service):
        from_event_id = uuid4()
        to_event_id = uuid4()
        dataset_ids = [uuid4(), uuid4()]

        mock_result = MagicMock()
        mock_result.all.return_value = [(did,) for did in dataset_ids]
        service.session.execute.return_value = mock_result

        count = await service._relink_datasets(from_event_id, to_event_id)

        assert count == 2
        service.session.execute.assert_called_once()

        call_args = service.session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "datasets" in compiled.lower()
        assert "UPDATE" in compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_event_metrics_moves_metrics(self, service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(from_event_id,), (from_event_id,)]
        service.session.execute.return_value = mock_result

        count = await service._relink_event_metrics(from_event_id, to_event_id)

        assert count == 2
        assert service.session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_relink_event_metrics_handles_conflicts(self, service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        mock_delete_result = MagicMock()
        mock_update_result = MagicMock()
        mock_update_result.all.return_value = [(from_event_id,)]

        service.session.execute = AsyncMock(
            side_effect=[mock_delete_result, mock_update_result]
        )

        count = await service._relink_event_metrics(from_event_id, to_event_id)

        assert count == 1
        assert service.session.execute.call_count == 2

        delete_call = service.session.execute.call_args_list[0][0][0]
        delete_compiled = str(delete_call.compile(compile_kwargs={"literal_binds": True}))
        assert "DELETE" in delete_compiled.upper()
        assert "event_metrics" in delete_compiled.lower()

        update_call = service.session.execute.call_args_list[1][0][0]
        update_compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "UPDATE" in update_compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_children_returns_counts(self, service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        geo_result = MagicMock()
        geo_result.all.return_value = [(uuid4(),), (uuid4(),)]

        dataset_result = MagicMock()
        dataset_result.all.return_value = [(uuid4(),)]

        delete_result = MagicMock()
        metric_result = MagicMock()
        metric_result.all.return_value = [(uuid4(),), (uuid4(),), (uuid4(),)]

        service.session.execute = AsyncMock(
            side_effect=[geo_result, dataset_result, delete_result, metric_result]
        )

        result = await service.relink_children(from_event_id, to_event_id)

        assert result == {
            "geo_layers": 2,
            "datasets": 1,
            "event_metrics": 3,
        }

    @pytest.mark.asyncio
    async def test_relink_geo_layers_dry_run_only_counts(self, dry_run_service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        dry_run_service.session.execute.return_value = mock_result

        count = await dry_run_service._relink_geo_layers(from_event_id, to_event_id)

        assert count == 5
        dry_run_service.session.execute.assert_called_once()

        call_args = dry_run_service.session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "SELECT" in compiled.upper()
        assert "UPDATE" not in compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_datasets_dry_run_only_counts(self, dry_run_service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        dry_run_service.session.execute.return_value = mock_result

        count = await dry_run_service._relink_datasets(from_event_id, to_event_id)

        assert count == 3
        dry_run_service.session.execute.assert_called_once()

        call_args = dry_run_service.session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "SELECT" in compiled.upper()
        assert "UPDATE" not in compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_event_metrics_dry_run_only_counts(self, dry_run_service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 7
        dry_run_service.session.execute.return_value = mock_result

        count = await dry_run_service._relink_event_metrics(from_event_id, to_event_id)

        assert count == 7
        dry_run_service.session.execute.assert_called_once()

        call_args = dry_run_service.session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "SELECT" in compiled.upper()
        assert "UPDATE" not in compiled.upper()
        assert "DELETE" not in compiled.upper()

    @pytest.mark.asyncio
    async def test_relink_children_dry_run_only_counts(self, dry_run_service):
        from_event_id = uuid4()
        to_event_id = uuid4()

        geo_result = MagicMock()
        geo_result.scalar.return_value = 2

        dataset_result = MagicMock()
        dataset_result.scalar.return_value = 1

        metric_result = MagicMock()
        metric_result.scalar.return_value = 4

        dry_run_service.session.execute = AsyncMock(
            side_effect=[geo_result, dataset_result, metric_result]
        )

        result = await dry_run_service.relink_children(from_event_id, to_event_id)

        assert result == {
            "geo_layers": 2,
            "datasets": 1,
            "event_metrics": 4,
        }
        assert dry_run_service.session.execute.call_count == 3
