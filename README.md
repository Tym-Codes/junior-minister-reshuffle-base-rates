# UK reshuffle junior-minister base-rate analysis

This repo contains a reproducible analysis built from the Institute for Government Ministers Database public data.

Source data:
- IfG Ministers Database public GitHub CSVs and SQLite database, downloaded to `work/`.
- IfG documents that the database covers all UK government ministers since 1979 and records role, department, rank and dates in office.
- IfG rank equivalence is used to identify `SoS`, `MoS` and `PUSS` posts.

Event construction:
- IfG named general elections are coded as `election_formation`.
- IfG change-of-prime-minister events are coded as `new_pm_reshuffle`, except PM-complete events within 60 days of a general election, which are treated as duplicate election-formation markers.
- For non-election PM changes, the event date is reset from IfG's "government formation complete" date to the first PM reshuffle/accession date: Major 1990-11-28, Brown 2007-06-27, May 2016-07-13, Johnson 2019-07-24, Truss 2022-09-06 and Sunak 2022-10-25.
- Ordinary reshuffles are derived mechanically: a date is selected when at least three SoS-rank organisations have appointment starts/exits in the following 14 days, excluding dates within 21 days of named election/PM events.

Main coding choices:
- A minister is in post on date `d` where `start_date <= d` and `end_date > d`, following IfG's note that ministers leaving on a date are not included on that date.
- Junior ministers are `MoS` and `PUSS` rank-equivalence posts. Secretaries of state and parliamentary-whip/leadership ranks are excluded from the unit of analysis.
- Departmental-head change compares the SoS-rank person active in the original organisation the day before the event with the SoS-rank person active at event date plus the window. IfG organisation links are used for name changes, mergers, demergers and transfers.
- Outcome A requires the same appointment ID to remain active at the end of the window.
- Outcome B requires a new junior appointment in the same linked organisation.
- Outcome F is used when a machinery-of-government link overlaps the event window and the movement is otherwise not a clean exact stay, promotion, departure or ordinary same-department title change.

Files:
- `junior_minister_reshuffle_dataset.csv`: main 14-day dataset.
- `junior_minister_reshuffle_dataset_all_windows.csv`: 7/14/21-day sensitivity dataset.
- `reshuffle_events.csv`: event list used by the analysis.
- `summary_rates.csv`: headline probabilities, differences, relative risks and odds ratios.
- `stay_rates.csv`: probability of staying in the exact original role, using stay as the dependent variable.
- `split_outcome_distribution.csv`: four-way split of outcomes into stayed, left/no-better, sideways and promoted.
- `split_outcome_summary.csv`: same four-way split aggregated by split code only.
- `window_sensitivity.csv`: 7/14/21-day sensitivity comparisons.
- `outcome_distribution.csv`: A-F outcome counts by event type and SoS-change status.
- `event_level_patterns.csv`: event-level continuity/clear-out diagnostics.
- `SCHEMA.md`: column schema.
- `methods_note.md`: limitations and interpretation notes.
- `build_reshuffle_analysis.py`: reproducible script.
