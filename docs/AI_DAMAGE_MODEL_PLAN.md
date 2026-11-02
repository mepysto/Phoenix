# Phoenix AI damage assessment — plan (PRD FR-5.1, FR-5.3)

> Status: proposal. Not built. Phoenix today shows **Copernicus EMS expert
> grading** per event (`/events/{id}/damage`); this plan covers Phoenix's own
> model for disasters where no expert product exists yet.

## Why not build it right away

A model that labels buildings "destroyed" is read as fact by responders. Shipping one needs four things this
repository does not have yet, and each is a hard prerequisite rather than a nice-to-have:

1. **Training data with a compatible licence.** The standard dataset, xBD (xView2 challenge: before/after
   imagery with per-building damage labels on a four-level scale), is licensed CC BY-NC-SA 4.0. That fits
   Phoenix's non-commercial operation but must be switched off for commercial deployments, as other
   non-commercial sources already are (`NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT`).
2. **High-resolution post-event imagery.** Damage to individual buildings needs sub-metre imagery. The
   free daily imagery Phoenix uses (VIIRS, ~375 m) cannot show it. Sources: vendor open-data programmes
   released for specific disasters, and Copernicus EMS products when licensed for reuse — each with its own
   terms, recorded in `DATA_SOURCES.md` before use.
3. **GPU compute** for training, and inference capacity sized for a disaster's area (tens to thousands of
   km²) within hours.
4. **Validation on held-out disasters** — accuracy on the training set says little about the next
   earthquake in a different building stock.

## Proposed approach

| Step | What | Done when |
|---|---|---|
| 1. Baseline | Two-stage model as in published xView2 solutions: building localisation on pre-event imagery, then damage classification on pre/post pairs (Siamese encoder). | Reproduces published xBD scores within a few points. |
| 2. Held-out evaluation | Evaluate per disaster type and region on disasters not seen in training; report per-class F1, not one average. | Results published in the repo, including where it fails. |
| 3. Uncertainty | Calibrated probabilities per building; show "uncertain" instead of a grade below a threshold. | Calibration error reported; UI never shows a grade without its confidence. |
| 4. Explanations (FR-5.3) | Per-building pre/post crops and a saliency overlay, linked from each prediction. | A reviewer can see *why* a building was graded. |
| 5. Human in the loop | Predictions are drafts until a verified-partner organisation confirms an area; confirmed areas feed back as labels. | No prediction is shown as confirmed without review. |
| 6. Integration | A separate inference worker writes `damage` geo layers with `source: "phoenix-model"`, model version and confidence, beside the Copernicus layers. The UI labels the two sources differently. | Same `/events/{id}/damage` endpoint, source shown per area. |

## Responsible use

- Model output is labelled as a model estimate everywhere, with its version and date, and never mixed with
  expert grading without saying which is which.
- Bias monitoring: report accuracy separately for regions and building types under-represented in training
  (PRD §11 "AI bias"); hold a release if any group falls well below the overall score.
- Conflict areas follow `CONFLICT_ZONE_POLICY`: building-level damage maps can expose targets; deployments
  can restrict them to aggregated grids or to verified partners.
- No people, vehicles or faces are detected or stored (`RESPONSIBLE_USE.md` §2).

## Decisions needed from the project owner

1. Funding or a partner for GPU compute and imagery.
2. Whether to start with one disaster type (the PRD's Phase 1 suggestion: earthquake or flood).
3. Which organisations review predictions before they are shown publicly.
