# Phoenix API Reference

Phoenix 프로젝트의 백엔드 API 명세서입니다. 이 API는 실시간 재난 데이터 제공 및 동기화를 담당합니다.

## 1. 개요

### 기본 정보

- **Base URL**: `http://localhost:8000`
- **응답 형식**: `application/json`
- **시간 형식**: ISO 8601 (UTC)

### 인증 (Authentication)

일부 관리용 엔드포인트(동기화 등)는 API Key 인증이 필요합니다.

- **Header**: `X-API-Key`
- **Value**: 설정된 API Sync Key (기본값: `dev-sync-key`)

---

## 2. 엔드포인트 문서

### 2.1 이벤트 목록 조회

`GET /api/v1/events`

재난 이벤트 목록을 필터링하여 조회합니다.

#### Query Parameters

| 파라미터     | 타입            | 기본값 | 설명                                                  |
| :----------- | :-------------- | :----- | :---------------------------------------------------- |
| `types`      | `array[string]` | -      | 이벤트 유형 (예: earthquake, flood, tropical_cyclone) |
| `severities` | `array[string]` | -      | 심각도 (예: red, orange, green)                       |
| `is_active`  | `boolean`       | -      | 활성 이벤트 여부                                      |
| `start_date` | `string`        | -      | 시작 날짜 (ISO 8601)                                  |
| `end_date`   | `string`        | -      | 종료 날짜 (ISO 8601)                                  |
| `min_lng`    | `float`         | -      | Bounding Box 최소 경도                                |
| `min_lat`    | `float`         | -      | Bounding Box 최소 위도                                |
| `max_lng`    | `float`         | -      | Bounding Box 최대 경도                                |
| `max_lat`    | `float`         | -      | Bounding Box 최대 위도                                |
| `limit`      | `integer`       | 50     | 조회 제한 (최대 200)                                  |
| `offset`     | `integer`       | 0      | 오프셋                                                |

#### Response Example (200 OK)

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "earthquake",
      "title": "Magnitude 7.2 earthquake in Turkey",
      "description": "A major earthquake occurred near Gaziantep...",
      "location": {
        "lat": 37.17,
        "lng": 37.03,
        "country": "Turkey",
        "country_code": "TR",
        "region": "Middle East"
      },
      "severity": "red",
      "affected_population": 1500000,
      "affected_area_km2": 2500.5,
      "start_date": "2025-12-20T10:30:00Z",
      "end_date": null,
      "is_active": true,
      "sources": [
        {
          "id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
          "name": "GDACS",
          "type": "rss"
        }
      ],
      "geometry": {
        "type": "Point",
        "coordinates": [37.03, 37.17]
      },
      "created_at": "2025-12-20T10:35:00Z",
      "updated_at": "2025-12-20T11:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

---

### 2.2 이벤트 상세 조회

`GET /api/v1/events/{id}`

특정 이벤트의 상세 정보와 관련 레이어, 데이터셋, 메트릭을 조회합니다.

#### Path Parameters

| 파라미터 | 타입   | 설명               |
| :------- | :----- | :----------------- |
| `id`     | `UUID` | 이벤트 고유 식별자 |

#### Response Example (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "earthquake",
  "title": "Magnitude 7.2 earthquake in Turkey",
  "location": { ... },
  "layers": [
    {
      "id": "f83a6b10-...",
      "event_id": "550e8400-...",
      "layer_type": "shakemap",
      "geometry": { ... },
      "properties": { "intensity": 8.5 }
    }
  ],
  "datasets": [],
  "metrics": []
}
```

---

### 2.3 이벤트 레이어 조회

`GET /api/v1/events/{id}/layers`

특정 이벤트와 관련된 모든 지리 공간 레이어 목록을 조회합니다.

#### Path Parameters

| 파라미터 | 타입   | 설명               |
| :------- | :----- | :----------------- |
| `id`     | `UUID` | 이벤트 고유 식별자 |

---

### 2.4 벡터 타일 조회

`GET /api/v1/geodata/tiles/{z}/{x}/{y}`

지리 공간 데이터를 위한 Mapbox Vector Tile(MVT)을 반환합니다.

#### Path Parameters

| 파라미터 | 타입      | 설명        |
| :------- | :-------- | :---------- |
| `z`      | `integer` | 줌 레벨     |
| `x`      | `integer` | 타일 X 좌표 |
| `y`      | `integer` | 타일 Y 좌표 |

---

### 2.5 GDACS 동기화 트리거

`POST /api/v1/sync/gdacs`

GDACS(Global Disaster Alert and Coordination System)의 최신 데이터를 즉시 동기화합니다.

- **Authentication**: `X-API-Key` 헤더 필요

#### Response Example (200 OK)

```json
{
  "status": "completed",
  "synced": 5
}
```

---

### 2.6 헬스체크

`GET /health`

API 서버의 상태를 확인합니다.

#### Response Example (200 OK)

```json
{
  "status": "healthy"
}
```

---

## 3. 스키마 정의

### EventResponse

| 필드                  | 타입              | 설명                                  |
| :-------------------- | :---------------- | :------------------------------------ |
| `id`                  | `UUID`            | 이벤트 고유 ID                        |
| `type`                | `string`          | 이벤트 유형 (earthquake, flood, etc.) |
| `title`               | `string`          | 이벤트 제목                           |
| `description`         | `string?`         | 상세 설명                             |
| `location`            | `Location`        | 위치 정보                             |
| `severity`            | `string`          | 심각도 (red, orange, green)           |
| `affected_population` | `integer?`        | 예상 피해 인구                        |
| `affected_area_km2`   | `float?`          | 예상 피해 면적 (km²)                  |
| `start_date`          | `datetime`        | 시작 일시                             |
| `end_date`            | `datetime?`       | 종료 일시                             |
| `is_active`           | `boolean`         | 활성 상태 여부                        |
| `sources`             | `DataSourceRef[]` | 데이터 소스 정보                      |
| `geometry`            | `GeoJSON?`        | 지리 정보 (Point, Polygon 등)         |

### Location

| 필드           | 타입      | 설명                           |
| :------------- | :-------- | :----------------------------- |
| `lat`          | `float`   | 위도                           |
| `lng`          | `float`   | 경도                           |
| `country`      | `string?` | 국가명                         |
| `country_code` | `string?` | 국가 코드 (ISO 3166-1 alpha-2) |
| `region`       | `string?` | 지역/대륙                      |

### Pagination

| 필드       | 타입      | 설명                  |
| :--------- | :-------- | :-------------------- |
| `total`    | `integer` | 전체 아이템 수        |
| `limit`    | `integer` | 페이지당 아이템 수    |
| `offset`   | `integer` | 오프셋                |
| `has_more` | `boolean` | 다음 페이지 존재 여부 |

---

## 4. 에러 응답

공통 에러 응답 형식은 다음과 같습니다:

```json
{
  "detail": "에러 메시지"
}
```

### 주요 에러 코드

- **401 Unauthorized**: API Key가 누락되었거나 잘못되었습니다.
- **404 Not Found**: 요청한 리소스를 찾을 수 없습니다.
- **422 Validation Error**: 요청 파라미터가 유효하지 않습니다.
- **500 Internal Server Error**: 서버 내부 오류가 발생했습니다.
