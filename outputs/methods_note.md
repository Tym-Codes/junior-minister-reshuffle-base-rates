# Methods note and limitations

This is a base-rate exercise, not punditry. It asks how junior ministers in a department fare when the department's SoS-rank head changes during a reshuffle window.

## Source data

The analysis uses the Institute for Government Ministers Database public CSVs as the primary source. The key tables are `appointment.csv` for person-post date spans, `post.csv` for role name, department and rank equivalence, `organisation.csv` for departments, `organisation_link.csv` for machinery-of-government links, `person.csv` for names, and `appointment_characteristics.csv` for cabinet status. GOV.UK ministerial pages were used only as a check on the current Kendall/Narayan roles; they are not the source for the historical estimates.

## Unit of analysis

The unit is one junior minister in post immediately before a reshuffle event. A minister is treated as active on date `d` when `start_date <= d` and `end_date > d`, matching IfG's note that ministers who left on a date are not included on that date. Junior ministers are IfG rank equivalence `MoS` or `PUSS`. Secretaries of state, the prime minister, deputy prime minister, parliamentary leadership roles and ordinary whips are excluded from the starting population.

## Event construction

IfG named general elections are coded as `election_formation`. Non-election changes of prime minister are coded as `new_pm_reshuffle`; for these, the event date is reset from IfG's "government formation complete" date to the first accession/reshuffle date because the cabinet and junior-minister churn begins before the completion marker. The dates used are Major 1990-11-28, Brown 2007-06-27, May 2016-07-13, Johnson 2019-07-24, Truss 2022-09-06 and Sunak 2022-10-25. PM-formation-complete events within 60 days of a general election are treated as duplicate election-formation markers and excluded as separate events.

Ordinary reshuffles are derived because IfG does not provide a canonical ordinary-reshuffle event list. A derived ordinary event is selected when at least three SoS-rank organisations have appointment starts or exits in the following 14 days, excluding dates within 21 days of a named election or PM-change event. This is transparent and reproducible, but can include resignation-driven clusters and miss smaller reshuffles.

## Departmental-head change

The main explanatory variable is `sos_changed_in_original_department`. It compares the SoS-rank person in the junior minister's original organisation on the day before the event with the SoS-rank person active at the end of the event window. The default window is event date plus 14 days, with 7- and 21-day sensitivity checks. IfG organisation links are used so name changes, mergers, demergers and transfers of functions do not automatically look like a clean change of department.

## Original A-F outcome coding

Outcome A means the same appointment ID remains active at the end of the window: the minister stayed in exactly the same role and department. Outcome B means the minister is still a junior minister in the same linked department but with a different appointment/title. Outcome C means the minister remains a junior minister but in another department. Outcome D means promotion to secretary-of-state or cabinet-level status, including junior ministers who attend cabinet. Outcome E means no active ministerial appointment at the end of the window. Outcome F means the case is ambiguous because a machinery-of-government link overlaps the event window and the movement is not a clean exact stay, promotion, departure or ordinary title change.

## Strict versus loose movement

The strict moved-out definition treats anything other than exact same appointment in the same department as movement. Strict moved out is therefore B, C, D, E and F. This answers: "did the minister keep the exact original role?"

The loose moved-out definition treats only a department move, promotion or departure as movement: C, D and E. Same-department title or portfolio tweaks, B, are not counted as movement. Ambiguous machinery-of-government cases, F, are excluded from the standard loose numerator but are reported in a separate `loose_moved_out_including_ambiguous` sensitivity. This answers: "did the minister leave the original departmental junior-minister position in a substantively larger way?"

## Revised stay/split outcome coding

For the revised framing, `stayed_in_original_role` is the dependent variable. It is true only for outcome A. All observations are also assigned to a four-way `split_outcome_code`:

- `stayed_original_role`: exact same appointment ID at the end of the window.
- `left_or_no_better_role`: left government, had no active final role, or moved to a lower IfG rank equivalence. For example, MoS to PUSS is treated as demotion/no-better.
- `sideways_move`: remained in government at the same junior rank but changed title, portfolio or department. Ambiguous machinery-of-government cases are included here when the person remains at a junior level; the original `outcome_code == F` is retained for sensitivity checks.
- `promoted`: promoted to SoS/Cabinet-level or moved upward in junior rank, such as PUSS to MoS.

This four-way split is descriptive. It does not infer whether a minister wanted the move, whether a same-rank role was politically better, or whether an exit was voluntary.

Departmental restructures remain noisy. IfG organisation links are used, and ambiguous machinery-of-government cases are coded separately as F. Even so, title renames and transferred briefs can blur the line between continuity and movement, especially in business/science/digital departments whose names have changed often.

The technical/economic subset is keyword-based. It should be treated as a directional slice around DSIT, BEIS, BIS, DTI, DIUS, BERR, DCMS digital/science/business/innovation/trade/technology style briefs, not as a hand-validated taxonomy.

The analysis does not infer motives. A junior minister may leave because of performance, factional balancing, personal request, parliamentary arithmetic, departmental abolition, promotion prospects, or the incoming secretary of state's preference. The estimates are therefore base rates conditional on observed reshuffle structure, not causal effects.
