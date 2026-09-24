# Responsible Use

Phoenix turns public signals into a shared picture of disasters and conflicts
so that people can respond and rebuild. The same capabilities could be
misused. This document states the limits that Phoenix, its contributors and
its deployments work within.

## 1. Not for safety-critical decisions on its own

Phoenix aggregates third-party data that may be **delayed, incomplete,
modelled or wrong**. Do not use it as the sole basis for evacuation,
navigation, emergency dispatch, medical, financial or other safety-critical
decisions. Verify important information with the authoritative source. GDACS,
for example, states that its information "is purely indicative and should not
be used for any decision making without alternate sources of information".

The **Data sources** panel shows how fresh each feed is. A quiet map can also
mean that a feed has stopped updating.

## 2. People are not a query type

Phoenix models **events, places, infrastructure and systems**. It does not
model individuals. The project will not build, and will not merge
contributions that add:

- search or lookup of named people;
- face recognition or other biometric identification;
- tracking, profiling or re-identification of individuals;
- exposure of the location of refugees, displaced people, aid workers, or
  anyone else identifiable as an individual.

Needs and offers (Phase 2) describe organisations and requirements, not the
whereabouts of individual people.

## 3. Conflict and surveillance data

Monitoring features (for example aircraft, vessels and public cameras) exist
to support recovery. They are not for targeting.

- **Public data only.** Every layer uses documented public sources
  ([DATA_SOURCES.md](./DATA_SOURCES.md)). Phoenix does no private scraping and
  holds no leaked or access-restricted data.
- **Conflict zones.** Deployments can delay or aggregate (grid) the positions
  of military assets and armed-conflict events in active conflict areas. Use
  this for any deployment where near-real-time positions could endanger
  people.
- **Camera feeds** show only the location and public stream of cameras that
  their operators publish. Phoenix does not identify the people they show.
  Snapshots pass through the API proxy (so viewers' addresses are not sent to
  camera operators) and are held in memory for about a minute. They are
  never recorded or archived, and no face or licence-plate recognition is
  run on them.
- **Aircraft** from aircraft whose operators joined the FAA privacy
  programmes (PIA, LADD) are never shown.

## 4. Licences and attribution

Each source keeps its own licence. Attribution is shown on the map and listed
in [DATA_SOURCES.md](./DATA_SOURCES.md). Phoenix is operated
non-commercially. A commercial deployment must set
`NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT=1`, which switches off sources licensed for
non-commercial use only, and must check the remaining terms itself.

## 5. Keys and privacy

- API keys live **only on the server** and are never sent to browsers. Layers
  that need a key show as locked until an operator configures one.
- Phoenix has no user accounts in its public map and sets no tracking cookies.
  Settings are stored in the viewer's own browser.

## 6. Reporting concerns

If you find a feature, dataset or deployment that crosses these lines, open an
issue in the repository or contact the maintainers privately for sensitive
reports.
