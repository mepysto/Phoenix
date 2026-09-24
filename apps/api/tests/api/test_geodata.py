from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.v1.geodata import get_clustering_service, get_event_service
from src.main import app
from src.schemas.event import (
    ClusterBBox,
    ClusterResponse,
    DataSourceRef,
    DisplayPoint,
    EventCluster,
    EventResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    Location,
)
from src.services.clustering_service import ClusteringService
from src.services.event_service import EventService


class TestVectorTiles:
    def test_get_vector_tile_success(self, client: TestClient) -> None:
        response = client.get("/api/v1/geodata/tiles/10/512/512")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-protobuf"

    def test_get_vector_tile_different_zoom_levels(self, client: TestClient) -> None:
        for z in [0, 5, 10, 15]:
            response = client.get(f"/api/v1/geodata/tiles/{z}/0/0")
            assert response.status_code == 200

    def test_get_vector_tile_invalid_coordinates(self, client: TestClient) -> None:
        response = client.get("/api/v1/geodata/tiles/a/b/c")
        assert response.status_code == 422

    def test_get_vector_tile_returns_empty_content(self, client: TestClient) -> None:
        response = client.get("/api/v1/geodata/tiles/1/1/1")
        assert response.status_code == 200
        assert response.content == b""


def create_mock_geojson_service(
    features: list[GeoJSONFeature] | None = None,
    total: int | None = None,
) -> MagicMock:
    if features is None:
        features = [
            GeoJSONFeature(
                geometry={"type": "Point", "coordinates": [135.0, 35.0]},
                properties={
                    "id": str(uuid4()),
                    "title": "Test Earthquake",
                    "type": "earthquake",
                    "severity": "high",
                    "is_active": True,
                },
            ),
            GeoJSONFeature(
                geometry={"type": "Point", "coordinates": [90.4, 23.8]},
                properties={
                    "id": str(uuid4()),
                    "title": "Test Flood",
                    "type": "flood",
                    "severity": "critical",
                    "is_active": True,
                },
            ),
        ]

    if total is None:
        total = len(features)

    service = MagicMock(spec=EventService)

    async def mock_get_events_as_geojson(
        filters: Any, include_properties: bool = True, limit: int = 1000
    ) -> GeoJSONFeatureCollection:
        result_features = features
        if not include_properties:
            result_features = [
                GeoJSONFeature(geometry=f.geometry, properties={})
                for f in features
            ]
        return GeoJSONFeatureCollection(
            features=result_features[:limit],
            metadata={
                "total": total,
                "returned": min(len(result_features), limit),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    service.get_events_as_geojson = mock_get_events_as_geojson
    return service


class TestGeoJSONExport:
    @pytest.fixture
    def geojson_client(self) -> Generator[TestClient, None, None]:
        mock_service = create_mock_geojson_service()
        app.dependency_overrides[get_event_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def empty_geojson_client(self) -> Generator[TestClient, None, None]:
        mock_service = create_mock_geojson_service(features=[], total=0)
        app.dependency_overrides[get_event_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def null_geometry_client(self) -> Generator[TestClient, None, None]:
        features = [
            GeoJSONFeature(
                geometry=None,
                properties={
                    "id": str(uuid4()),
                    "title": "Event without coordinates",
                    "type": "war",
                    "severity": "high",
                    "is_active": True,
                },
            ),
        ]
        mock_service = create_mock_geojson_service(features=features)
        app.dependency_overrides[get_event_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_get_events_geojson_success(self, geojson_client: TestClient) -> None:
        response = geojson_client.get("/api/v1/geodata/events/geojson")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2
        assert data["metadata"]["total"] == 2
        assert data["metadata"]["returned"] == 2

    def test_get_events_geojson_empty_result(
        self, empty_geojson_client: TestClient
    ) -> None:
        response = empty_geojson_client.get("/api/v1/geodata/events/geojson")

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 0
        assert data["metadata"]["total"] == 0

    def test_get_events_geojson_null_geometry(
        self, null_geometry_client: TestClient
    ) -> None:
        response = null_geometry_client.get("/api/v1/geodata/events/geojson")

        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 1
        assert data["features"][0]["geometry"] is None
        assert data["features"][0]["properties"]["title"] == "Event without coordinates"

    def test_get_events_geojson_with_filters(self, geojson_client: TestClient) -> None:
        response = geojson_client.get(
            "/api/v1/geodata/events/geojson",
            params={
                "types": ["earthquake"],
                "severities": ["high", "critical"],
                "is_active": True,
                "min_lat": 20.0,
                "max_lat": 40.0,
                "min_lng": 100.0,
                "max_lng": 150.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"

    def test_get_events_geojson_with_limit(self, geojson_client: TestClient) -> None:
        response = geojson_client.get(
            "/api/v1/geodata/events/geojson",
            params={"limit": 500},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"

    def test_get_events_geojson_include_properties_false(
        self, geojson_client: TestClient
    ) -> None:
        response = geojson_client.get(
            "/api/v1/geodata/events/geojson",
            params={"include_properties": False},
        )

        assert response.status_code == 200
        data = response.json()
        for feature in data["features"]:
            assert feature["properties"] == {}

    def test_get_events_geojson_feature_structure(
        self, geojson_client: TestClient
    ) -> None:
        response = geojson_client.get("/api/v1/geodata/events/geojson")

        assert response.status_code == 200
        data = response.json()

        for feature in data["features"]:
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature
            if feature["geometry"] is not None:
                assert feature["geometry"]["type"] == "Point"
                assert "coordinates" in feature["geometry"]
                assert len(feature["geometry"]["coordinates"]) == 2

    def test_get_events_geojson_limit_exceeds_max(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/geodata/events/geojson",
            params={"limit": 10000},
        )
        assert response.status_code == 422

    def test_get_events_geojson_metadata_fields(
        self, geojson_client: TestClient
    ) -> None:
        response = geojson_client.get("/api/v1/geodata/events/geojson")

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert "total" in data["metadata"]
        assert "returned" in data["metadata"]
        assert "generated_at" in data["metadata"]


def create_mock_event_response(
    lat: float = 35.0,
    lng: float = 135.0,
    event_type: str = "earthquake",
    severity: str = "high",
    is_active: bool = True,
) -> EventResponse:
    now = datetime.now(timezone.utc)
    return EventResponse(
        id=uuid4(),
        type=event_type,
        title=f"Test {event_type.capitalize()}",
        description=f"Test {event_type} event",
        location=Location(lat=lat, lng=lng, country="Test Country", country_code="TC"),
        geo_precision="exact",
        display_point=DisplayPoint(lat=lat, lng=lng, source="event"),
        severity=severity,
        affected_population=1000,
        start_date=now,
        is_active=is_active,
        sources=[DataSourceRef(id=uuid4(), name="Test Source", type="test")],
        created_at=now,
        updated_at=now,
    )


def create_mock_clustering_service(
    clusters: list[EventCluster] | None = None,
    unclustered: list[EventResponse] | None = None,
    zoom: int = 5,
) -> MagicMock:
    if clusters is None:
        clusters = [
            EventCluster(
                cluster_id="cluster_abc123",
                center_lat=35.0,
                center_lng=135.0,
                count=5,
                bbox=ClusterBBox(min_lat=34.0, max_lat=36.0, min_lng=134.0, max_lng=136.0),
                event_types={"earthquake": 3, "flood": 2},
                max_severity="critical",
            ),
            EventCluster(
                cluster_id="cluster_def456",
                center_lat=23.8,
                center_lng=90.4,
                count=3,
                bbox=ClusterBBox(min_lat=22.0, max_lat=25.0, min_lng=89.0, max_lng=92.0),
                event_types={"flood": 3},
                max_severity="high",
            ),
        ]

    if unclustered is None:
        unclustered = [create_mock_event_response(lat=40.0, lng=-74.0)]

    total_events = sum(c.count for c in clusters) + len(unclustered)

    service = MagicMock(spec=ClusteringService)

    async def mock_get_clusters(
        zoom: int, filters: Any
    ) -> ClusterResponse:
        if zoom >= 15:
            all_events = unclustered + [
                create_mock_event_response(lat=35.0 + i * 0.01, lng=135.0 + i * 0.01)
                for i in range(total_events - len(unclustered))
            ]
            return ClusterResponse(
                zoom=zoom,
                clusters=[],
                unclustered=all_events,
                total_events=len(all_events),
                total_clusters=0,
            )
        return ClusterResponse(
            zoom=zoom,
            clusters=clusters,
            unclustered=unclustered,
            total_events=total_events,
            total_clusters=len(clusters),
        )

    service.get_clusters = mock_get_clusters
    return service


class TestEventClusters:
    @pytest.fixture
    def cluster_client(self) -> Generator[TestClient, None, None]:
        mock_service = create_mock_clustering_service()
        app.dependency_overrides[get_clustering_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def empty_cluster_client(self) -> Generator[TestClient, None, None]:
        mock_service = create_mock_clustering_service(clusters=[], unclustered=[])
        app.dependency_overrides[get_clustering_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def high_zoom_client(self) -> Generator[TestClient, None, None]:
        mock_service = create_mock_clustering_service()
        app.dependency_overrides[get_clustering_service] = lambda: mock_service
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_get_clusters_success(self, cluster_client: TestClient) -> None:
        response = cluster_client.get("/api/v1/geodata/events/clusters?zoom=5")

        assert response.status_code == 200
        data = response.json()
        assert data["zoom"] == 5
        assert len(data["clusters"]) == 2
        assert len(data["unclustered"]) == 1
        assert data["total_events"] == 9
        assert data["total_clusters"] == 2

    def test_get_clusters_empty_result(self, empty_cluster_client: TestClient) -> None:
        response = empty_cluster_client.get("/api/v1/geodata/events/clusters?zoom=5")

        assert response.status_code == 200
        data = response.json()
        assert data["zoom"] == 5
        assert len(data["clusters"]) == 0
        assert len(data["unclustered"]) == 0
        assert data["total_events"] == 0
        assert data["total_clusters"] == 0

    def test_get_clusters_high_zoom_no_clustering(
        self, high_zoom_client: TestClient
    ) -> None:
        response = high_zoom_client.get("/api/v1/geodata/events/clusters?zoom=16")

        assert response.status_code == 200
        data = response.json()
        assert data["zoom"] == 16
        assert len(data["clusters"]) == 0
        assert len(data["unclustered"]) > 0
        assert data["total_clusters"] == 0

    def test_get_clusters_zoom_required(self, cluster_client: TestClient) -> None:
        response = cluster_client.get("/api/v1/geodata/events/clusters")

        assert response.status_code == 422

    def test_get_clusters_zoom_validation(self, cluster_client: TestClient) -> None:
        response = cluster_client.get("/api/v1/geodata/events/clusters?zoom=-1")
        assert response.status_code == 422

        response = cluster_client.get("/api/v1/geodata/events/clusters?zoom=21")
        assert response.status_code == 422

    def test_get_clusters_with_filters(self, cluster_client: TestClient) -> None:
        response = cluster_client.get(
            "/api/v1/geodata/events/clusters",
            params={
                "zoom": 5,
                "types": ["earthquake"],
                "severities": ["high", "critical"],
                "is_active": True,
                "min_lat": 20.0,
                "max_lat": 40.0,
                "min_lng": 100.0,
                "max_lng": 150.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert "unclustered" in data

    def test_get_clusters_structure(self, cluster_client: TestClient) -> None:
        response = cluster_client.get("/api/v1/geodata/events/clusters?zoom=5")

        assert response.status_code == 200
        data = response.json()

        for cluster in data["clusters"]:
            assert "cluster_id" in cluster
            assert "center_lat" in cluster
            assert "center_lng" in cluster
            assert "count" in cluster
            assert "event_types" in cluster
            assert isinstance(cluster["event_types"], dict)
            if cluster["bbox"] is not None:
                assert "min_lat" in cluster["bbox"]
                assert "max_lat" in cluster["bbox"]
                assert "min_lng" in cluster["bbox"]
                assert "max_lng" in cluster["bbox"]

    def test_get_clusters_unclustered_structure(
        self, cluster_client: TestClient
    ) -> None:
        response = cluster_client.get("/api/v1/geodata/events/clusters?zoom=5")

        assert response.status_code == 200
        data = response.json()

        for event in data["unclustered"]:
            assert "id" in event
            assert "type" in event
            assert "title" in event
            assert "severity" in event
            assert "location" in event

    def test_get_clusters_different_zoom_levels(
        self, cluster_client: TestClient
    ) -> None:
        for zoom in [0, 5, 10, 14]:
            response = cluster_client.get(f"/api/v1/geodata/events/clusters?zoom={zoom}")
            assert response.status_code == 200
            data = response.json()
            assert data["zoom"] == zoom

    def test_get_clusters_zoom_boundary(self, high_zoom_client: TestClient) -> None:
        response = high_zoom_client.get("/api/v1/geodata/events/clusters?zoom=15")
        assert response.status_code == 200
        data = response.json()
        assert data["clusters"] == []

        response = high_zoom_client.get("/api/v1/geodata/events/clusters?zoom=14")
        assert response.status_code == 200
