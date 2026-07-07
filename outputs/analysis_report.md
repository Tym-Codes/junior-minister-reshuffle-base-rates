# UK reshuffle junior-minister base-rate analysis

Plain English answer: when a secretary of state changes, junior ministers are much less likely to stay in the exact same role. In the main 14-day window, 35.9% of junior ministers stayed when their SoS changed, compared with 69.2% when their SoS stayed. The non-stayers split as follows: when the SoS changed, 32.9% left government or moved to no better/lower-ranked role, 17.8% moved sideways, and 13.3% were promoted. When the SoS stayed, those shares were 11.2%, 10.8%, and 8.8%.

## Stayed In Original Role

| Sample | SoS changed stayed/denom | SoS changed stayed % | SoS stayed stayed/denom | SoS stayed stayed % | Difference | RR of staying |
|---|---:|---:|---:|---:|---:|---:|
| All events | 570/1586 | 35.9 | 1612/2328 | 69.2 | -33.3 pp | 0.52 |
| New PM reshuffles | 105/349 | 30.1 | 63/112 | 56.2 | -26.2 pp | 0.53 |
| Excluding elections | 507/1096 | 46.3 | 1435/1974 | 72.7 | -26.4 pp | 0.64 |
| Technical/economic | 103/317 | 32.5 | 254/387 | 65.6 | -33.1 pp | 0.50 |

## Four-Way Outcome Split

| Sample | SoS changed? | Stayed exact role | Left/no-better | Sideways | Promoted |
|---|---:|---:|---:|---:|---:|
| All events | No | 1612/2328 (69.2%) | 261/2328 (11.2%) | 251/2328 (10.8%) | 204/2328 (8.8%) |
| All events | Yes | 570/1586 (35.9%) | 522/1586 (32.9%) | 283/1586 (17.8%) | 211/1586 (13.3%) |
| New PM reshuffles | No | 63/112 (56.2%) | 25/112 (22.3%) | 14/112 (12.5%) | 10/112 (8.9%) |
| New PM reshuffles | Yes | 105/349 (30.1%) | 102/349 (29.2%) | 81/349 (23.2%) | 61/349 (17.5%) |
| Technical/economic | No | 254/387 (65.6%) | 54/387 (14.0%) | 52/387 (13.4%) | 27/387 (7.0%) |
| Technical/economic | Yes | 103/317 (32.5%) | 116/317 (36.6%) | 60/317 (18.9%) | 38/317 (12.0%) |

## Strict And Loose Movement

The strict moved-out measure is simply the inverse of staying in the exact original role. If the appointment ID changes, it counts as movement. That means same-department portfolio changes, cross-department moves, promotions, exits and machinery-of-government ambiguous changes all count as strict movement.

The loose moved-out measure asks a narrower question: did the minister substantively leave the original junior departmental position? It counts moved department, promoted, or left government. Same-department portfolio/title tweaks are not counted. Machinery-of-government ambiguous cases are excluded from the standard loose numerator and reported separately in `loose_moved_out_including_ambiguous`.

## Burnham/Kendall/Narayan Interpretation

For a hypothetical Burnham reshuffle where Liz Kendall leaves DSIT, the base rate is that Narayan's chance of staying in the exact AI/online-safety role would fall materially relative to a no-SoS-change scenario. The most relevant empirical slices point to roughly 30.1% staying in new-PM reshuffles when the SoS changes, and 32.5% staying in technical/economic departments when the SoS changes.

The closest observed DSIT analogue in the dataset is the 5 September 2025 reshuffle: DSIT's secretary of state changed, and of four junior ministers in post before the reshuffle, Feryal Clark and Baroness Jones left government, Chris Bryant moved to another department, and Patrick Vallance stayed in DSIT with a title/portfolio tweak. Narayan himself was appointed after that event, so that case is not directly about his survival probability.

Continuity may matter more for a specialised AI/online-safety brief than the average junior role, especially if the incoming secretary wants domain knowledge, bill continuity, regulator relationships, or investor/industry signalling. But the historical base rate still says a SoS change is a risk factor for staying in post.

## Caveats

Ordinary reshuffles are derived from clustered SoS-level appointment churn because IfG does not provide a canonical ordinary-reshuffle event list. Machinery-of-government changes are coded separately as ambiguous in the original A-F coding, but business/science/digital departments have frequent name and function changes. The technical/economic subset is keyword-based and should be treated as directional rather than hand-validated.
