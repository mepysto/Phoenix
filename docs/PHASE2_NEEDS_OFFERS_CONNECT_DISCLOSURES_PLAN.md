Phoenix Phase 2 Dev Plan (Needs/Offers/Connect/Disclosures)

0) Scope / Non-goals
- 목표: 니즈(Need) 등록(승인 기관만) + 오퍼(Offer) 등록(로그인 사용자만) + 추천/연결(Connect) 기반 매칭 + 이벤트 단위 공시(Disclosure) + 조직(Org) 신청/관리자 승인 + 전체 이메일 매직링크 로그인
- 비목표(보류): 3D 복구 설계 툴, 결제/물류/채팅, 블록체인 추적, 자동 집행(“매칭=지원 확정”)
1) 핵심 정책(요구사항 반영)
인증
- 모든 사용자(일반/기관멤버) 로그인: 이메일 매직링크 단일 방식
Org(기관) 승인/접근
- Org 유형: UN, INTERNATIONAL_NGO, LOCAL_PARTNER, OTHER
- Org 등록: 유저가 신청 가능
- 시스템 접근: 로그인은 가능, 다만 Org 승인 전에는 권한 제한(Need 작성/Disclosure 작성 등 불가)
- 관리자(플랫폼 운영자=나)만 Org 승인/거절 가능
Need
- Need 등록 주체: 승인(approved)된 Org의 멤버만
- Need visibility 기본값: public
- Need의 contact_email: Org 대표메일(primary_email)로 고정
  - 구현 원칙: Need 테이블에 contact_email을 저장하지 않고, 응답에서 org.primary_email을 join하여 내려 대표메일 변경 시 자동 갱신되게 함
Offer
- Offer 작성: 무조건 로그인 사용자만
- Offer visibility 기본값: public (공개 Offer 허용)
Matching / Connect
- 매칭 범위: “연결/추천”까지만(플랫폼이 지원을 확정/집행하지 않음)
- Connect 승인: 양측 승인(two-sided approval)이 기본
  - Need측 승인 권한: Need 소속 Org 멤버 누구나
  - Offer측 승인 권한: Offer 작성자
- 이메일 교환: Connect가 최종 승인된 이후에만 양측 이메일을 서로 노출/공유
- 공유 채널: 우선 이메일만
Disclosure(프로젝트 공시)
- 시작 단위: 이벤트(Event) 단위
- 작성 권한: (a) 관리자 또는 (b) 해당 이벤트에 연결된 승인 Org 멤버
- Disclosure에 연결되는 Org: 복수 Org 가능
- 추가 요구: 작성자가 소속되지 않은 Org도 “태그”로 추가 가능(단, 권한은 별개)
2) 데이터 모델(초안) — DB 우선 설계
> 기존 apps/api/src/models/event.py의 Event를 기준으로 확장
2.1 Auth
users
- id (uuid pk)
- email (citext/unique) (없으면 varchar unique라도 OK)
- created_at, last_login_at
- (옵션) is_platform_admin bool는 DB 대신 PHOENIX_ADMIN_EMAILS env로도 가능(MVP)
magic_link_tokens
- id
- email
- token_hash
- purpose = login
- expires_at, used_at, created_at
- redirect_path (옵션)
sessions (또는 JWT만 사용)
- id, user_id, expires_at, revoked_at, created_at
2.2 Orgs & Membership
orgs
- id
- name
- org_type (enum)
- status = pending|approved|rejected
- primary_email
- requested_by_user_id
- approved_by_user_id, approved_at
- rejected_by_user_id, rejected_at, rejection_reason
- created_at, updated_at
org_memberships
- id
- org_id
- user_id
- role = member|org_admin
- status = active|removed (invite는 추후 확장)
- unique (org_id, user_id)
- created_at
2.3 Event ↔ Org 연결(권한 판단용)
event_orgs
- id
- event_id
- org_id
- created_at
- unique (event_id, org_id)
- 생성 규칙(MVP): 승인 Org가 특정 Event에 대해 Need를 생성하면 자동으로 link 생성(또는 별도 endpoint로 명시적 link)
2.4 Needs / Offers / Connect
needs
- id
- event_id
- org_id
- title, description
- priority = low|medium|high|critical
- quantity, unit (옵션)
- location (옵션: POINT, 혹은 lat/lng)
- visibility = public|org_only|private (default public)
- status = open|paused|closed (default open)
- tags (JSONB: ["shelter","water","medical"]) — 자유 입력
- created_by_user_id
- created_at, updated_at
offers
- id
- event_id (nullable; 이벤트 특정이 아니어도 되면 null)
- created_by_user_id (로그인 유저)
- title, description
- offer_type = funding|goods|service|volunteer|transport|other
- quantity, unit (옵션)
- location (옵션)
- visibility = public|private (default public)
- status = open|withdrawn|closed (default open)
- tags (JSONB string list)
- created_at, updated_at
connect_requests
- id
- need_id
- offer_id
- status = pending|need_approved|offer_approved|approved|rejected|canceled
- need_approved_by_user_id, need_approved_at
- offer_approved_by_user_id, offer_approved_at
- approved_at (양측 승인 완료 시)
- rejected_by_user_id, rejected_at, rejection_reason (옵션)
- created_by_user_id, created_at, updated_at
- 제약: unique (need_id, offer_id)로 중복 connect 방지
2.5 Tags (표준 추천용)
standard_tags
- id
- slug (unique) / label
- category (옵션)
- is_active
- seed 데이터로 초기 추천 태그 제공
2.6 Disclosures
disclosures
- id
- event_id
- title
- body (markdown)
- visibility = public|org_only (default public)
- created_by_user_id
- created_at, updated_at
disclosure_orgs
- disclosure_id
- org_id
- role = publisher|tagged
- unique (disclosure_id, org_id, role)
- 해석:
  - publisher: “이 공시는 이 org가 공시 주체로 포함됨”(복수 가능)
  - tagged: “참조/태그된 org”(작성자 소속 아니어도 허용)
권한 규칙(제안):
- 작성자는 publisher에 최소 1개 org를 넣을 수 있는데,
  - (MVP) 작성자가 멤버인 승인 org만 publisher로 허용
  - tagged는 어떤 org든 허용(요구사항 반영)
- 관리자 작성 시 publisher 없이도 가능(또는 선택)
3) API 설계(엔드포인트)
3.1 Auth
- POST /api/v1/auth/magic-link/request { email, redirect_path? }
- POST /api/v1/auth/magic-link/verify { token } → 세션/JWT 발급
- POST /api/v1/auth/logout
- GET /api/v1/me
3.2 Org
- POST /api/v1/orgs/apply { name, org_type, primary_email }
- GET /api/v1/orgs/{org_id} (public 일부)
- GET /api/v1/orgs/mine (내 멤버십)
- POST /api/v1/admin/orgs/{org_id}/approve
- POST /api/v1/admin/orgs/{org_id}/reject
- POST /api/v1/orgs/{org_id}/members (org_admin 또는 platform_admin; MVP에서 멤버 추가 필요 시)
3.3 Needs
- GET /api/v1/needs?event_id=&visibility=&tags=... (public read)
- POST /api/v1/needs (승인 org 멤버만)
- PATCH /api/v1/needs/{need_id} (해당 org 멤버/관리자)
- 응답에 contact_email은 항상 org.primary_email로 내려줌
3.4 Offers
- GET /api/v1/offers?event_id=&visibility=&tags=... (public read; private이면 작성자만)
- POST /api/v1/offers (로그인 유저만)
- PATCH /api/v1/offers/{offer_id} (작성자/관리자)
3.5 Matching (추천)
- GET /api/v1/matching/recommendations?need_id=...
  - 결과: 정렬된 offer 리스트 + score(규칙 기반 MVP)
  - (추후) AI 매칭
3.6 Connect
- POST /api/v1/connects { need_id, offer_id } (로그인 필요; 생성자 제한은 정책으로 결정)
- POST /api/v1/connects/{connect_id}/approve (need측/org멤버 또는 offer측/작성자)
- POST /api/v1/connects/{connect_id}/reject
- GET /api/v1/connects/{connect_id} (당사자만 상세; 승인 전에는 상대 이메일 미노출)
- 최종 승인 시 동작:
  - status=approved로 전환
  - 이메일 발송(양측에 서로 이메일 포함) + DB에 approved_at 기록
  - 승인 전/후 응답에서 이메일 노출 정책 준수
3.7 Disclosures
- GET /api/v1/events/{event_id}/disclosures (public read)
- POST /api/v1/events/{event_id}/disclosures
  - 권한: platform_admin OR (event_orgs에 연결된 승인 org 멤버)
  - body에 publisher_org_ids[], tagged_org_ids[]
- PATCH /api/v1/disclosures/{disclosure_id} (작성자/관리자)
3.8 Standard Tag 추천
- GET /api/v1/tags/standard?query=water&limit=20
4) 권한 체크(가드) — 최소 규칙
- 로그인만: Offer create, Connect create/approve(offer side)
- 승인 org 멤버만: Need create/update, Connect approve(need side), Disclosure create(조건부)
- 이벤트 연결(org↔event): event_orgs 존재 + org status approved
- 이메일 노출:
  - connect.status != approved → 상대 이메일은 항상 null/미제공
  - approved → 양측에게 상대 이메일 제공(서로 노출)
5) 구현 순서(추천)
1. Auth: users + magic link + session/JWT + Depends(get_current_user)
2. Org: apply/approve, membership, “승인 전 로그인은 OK, 권한만 제한” 적용
3. Need CRUD(+ contact_email computed)
4. Offer CRUD(로그인 필수, visibility default public)
5. Matching 추천 endpoint(초기 규칙 기반: tag overlap + event_id + distance 선택)
6. Connect two-sided approval + 승인 후 이메일 발송/노출
7. Disclosures(event 단위) + multi-org(publisher/tagged)
8. Web UI: 로그인/Org 신청/Need 작성/Offer 작성/추천/Connect 승인/Disclosures 작성
9. Tests: API 권한/상태전이/이메일 노출 규칙
6) 테스트 체크리스트(필수)
- Auth
  - 매직링크 요청 → 토큰 발급/만료/1회성 검증
- Org
  - org 신청(pending) 상태에서 로그인 가능, Need 생성 시 403
  - admin 승인 후 Need 생성 가능
  - org.primary_email 변경 → Need 조회 시 contact_email 자동 변경 확인(“저장 안 함” 방식)
- Offer
  - 비로그인 offer 생성 401
  - 로그인 offer 생성 OK, visibility default public
- Connect
  - 생성 후 승인 전: 상대 이메일 API 응답에 절대 나오지 않음
  - need측: 같은 org 멤버 누구나 approve 가능
  - offer측: offer 작성자만 approve 가능
  - 양측 승인 완료 후에만: 이메일 노출 + 이메일 발송 트리거
- Disclosure
  - 이벤트 연결된 승인 org 멤버 작성 가능
  - disclosure에 publisher_org_ids 복수 가능
  - tagged_org_ids에 작성자 미소속 org 포함 가능
