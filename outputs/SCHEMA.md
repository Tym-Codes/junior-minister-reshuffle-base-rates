# Derived dataset schema

Unit: one junior minister (IfG rank equivalence `MoS` or `PUSS`) in post on the day before a reshuffle event.

Key fields:
- `event_id`, `event_name`, `event_date`, `event_type`: reshuffle identifier and category.
- `window_days`: event date plus 7, 14, or 21 days; the main dataset uses 14.
- `person_id`, `person_name`: IfG person identifier and date-appropriate display name.
- `original_*`: appointment, post, rank, cabinet status, and organisation immediately before the event.
- `sos_changed_in_original_department`: whether the SoS-rank departmental head for the original department changed by the end of the window, allowing IfG organisation links.
- `outcome_code`: A exact same role/department; B same department/title change; C moved department; D promoted to SoS/Cabinet-level; E left government; F ambiguous machinery-of-government/title-rename case.
- `strict_moved_out`: outcome is anything except A.
- `loose_moved_out`: outcome is C, D, or E.
- `loose_moved_out_including_ambiguous`: outcome is C, D, E, or F.
- `stayed_in_original_role`: main dependent variable for the revised framing; true only for outcome A.
- `split_outcome_code`: four-way outcome: `stayed_original_role`, `left_or_no_better_role`, `sideways_move`, or `promoted`.
- `split_outcome_label`: human-readable version of `split_outcome_code`; demotions are labelled separately from exits when rank information permits.
- `technical_economic_department_or_brief`: keyword flag for DSIT/BEIS/BIS/DTI/DCMS digital/science/business/innovation/trade/technology style departments or briefs.
