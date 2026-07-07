from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

FAR_FUTURE = pd.Timestamp("2100-01-01")
WINDOWS = [7, 14, 21]
MAIN_WINDOW = 14


def read_csv(name: str, date_cols: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(WORK / name, dtype=str)
    for col in date_cols or []:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


appointment = read_csv("appointment.csv", ["start_date", "end_date"])
appointment_characteristics = read_csv(
    "appointment_characteristics.csv", ["start_date", "end_date"]
)
event = read_csv("event.csv", ["date"])
organisation = read_csv("organisation.csv", ["start_date", "end_date"])
organisation_link = read_csv("organisation_link.csv", ["link_start_date", "link_end_date"])
person = read_csv("person.csv", ["start_date", "end_date"])
post = read_csv("post.csv")
post_relationship = read_csv("post_relationship.csv")
POST_GROUP = {
    row["post_id"]: (row.get("group_name"), row.get("group_seniority"))
    for _, row in post_relationship.drop_duplicates("post_id").iterrows()
}


appointments = (
    appointment.merge(
        post.rename(
            columns={
                "id": "post_id",
                "name": "post_name",
                "display_name": "post_display_name",
            }
        ),
        on="post_id",
        how="left",
    )
    .merge(
        organisation.rename(
            columns={
                "id": "organisation_id",
                "name": "organisation_name",
                "short_name": "organisation_short_name",
                "start_date": "organisation_start_date",
                "end_date": "organisation_end_date",
            }
        ),
        on="organisation_id",
        how="left",
    )
)

appointments = appointments.rename(columns={"id": "appointment_id"})
appointments["end_filled"] = appointments["end_date"].fillna(FAR_FUTURE)
appointments["rank_equivalence_value"] = pd.to_numeric(
    appointments["rank_equivalence_value"], errors="coerce"
)

appointment_characteristics = appointment_characteristics.rename(
    columns={"id": "appointment_characteristic_id"}
)
appointment_characteristics["end_filled"] = appointment_characteristics["end_date"].fillna(
    FAR_FUTURE
)


def active_on(df: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    return df[(df["start_date"] <= date) & (df["end_filled"] > date)].copy()


def characteristics_on(date: pd.Timestamp) -> pd.DataFrame:
    return appointment_characteristics[
        (appointment_characteristics["start_date"] <= date)
        & (appointment_characteristics["end_filled"] > date)
    ].copy()


def cabinet_status_for(date: pd.Timestamp) -> pd.DataFrame:
    chars = characteristics_on(date)
    return chars[["appointment_id", "cabinet_status", "is_acting", "is_on_leave"]]


@lru_cache(maxsize=None)
def person_name_at(person_id: str, date: pd.Timestamp) -> str:
    rows = person[person["id"].eq(person_id)].copy()
    rows["start_filled"] = rows["start_date"].fillna(pd.Timestamp("1900-01-01"))
    rows["end_filled"] = rows["end_date"].fillna(FAR_FUTURE)
    active = rows[(rows["start_filled"] <= date) & (rows["end_filled"] > date)]
    if active.empty:
        active = rows.sort_values("start_filled", ascending=False).head(1)
    return str(active.iloc[0]["display_name"])


_ACTIVE_MINISTER_CACHE: dict[pd.Timestamp, pd.DataFrame] = {}
_HEADS_CACHE: dict[pd.Timestamp, pd.DataFrame] = {}


def active_ministers(date: pd.Timestamp) -> pd.DataFrame:
    if date in _ACTIVE_MINISTER_CACHE:
        return _ACTIVE_MINISTER_CACHE[date].copy()
    active = active_on(appointments, date)
    active = active.merge(cabinet_status_for(date), on="appointment_id", how="left")
    _ACTIVE_MINISTER_CACHE[date] = active.copy()
    return active


def junior_ministers(date: pd.Timestamp) -> pd.DataFrame:
    active = active_ministers(date)
    return active[active["rank_equivalence"].isin(["MoS", "PUSS"])].copy()


def heads_by_org(date: pd.Timestamp) -> pd.DataFrame:
    if date in _HEADS_CACHE:
        return _HEADS_CACHE[date].copy()
    active = active_ministers(date)
    heads = active[active["rank_equivalence"].eq("SoS")].copy()
    _HEADS_CACHE[date] = heads.copy()
    return heads


def org_linked_during(org_id: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    links = organisation_link[
        (
            organisation_link["predecessor_organisation_id"].eq(org_id)
            | organisation_link["successor_organisation_id"].eq(org_id)
        )
        & (organisation_link["link_start_date"] <= end)
        & (organisation_link["link_end_date"] >= start)
    ].copy()
    return links


def related_orgs(org_id: str, start: pd.Timestamp, end: pd.Timestamp) -> set[str]:
    links = org_linked_during(org_id, start, end)
    ids = {org_id}
    ids.update(links["predecessor_organisation_id"].dropna().tolist())
    ids.update(links["successor_organisation_id"].dropna().tolist())
    return ids


def post_group(post_id: str) -> tuple[str | None, str | None]:
    return POST_GROUP.get(post_id, (None, None))


def is_technical_economic(row: pd.Series) -> bool:
    text = " ".join(
        [
            str(row.get("organisation_name", "")),
            str(row.get("organisation_short_name", "")),
            str(row.get("post_display_name", "")),
        ]
    ).lower()
    keywords = [
        "science",
        "innovation",
        "technology",
        "digital",
        "artificial intelligence",
        " ai ",
        "online safety",
        "business",
        "enterprise",
        "trade",
        "industry",
        "industrial strategy",
        "energy",
        "commerce",
        "data",
        "creative industries",
        "culture, media and sport",
        "culture, media",
        "dti",
        "bis",
        "beis",
        "dsit",
        "dcms",
        "dius",
        "berr",
    ]
    padded = f" {text} "
    return any(k in padded for k in keywords)


def selected_named_events() -> pd.DataFrame:
    events = event.copy()
    elections = events[events["type"].eq("General election")]["date"].tolist()
    pm_start_overrides = {
        "Major government formation complete": pd.Timestamp("1990-11-28"),
        "Brown government formation complete": pd.Timestamp("2007-06-27"),
        "May government formation complete": pd.Timestamp("2016-07-13"),
        "Johnson government formation complete": pd.Timestamp("2019-07-24"),
        "Truss government formation complete": pd.Timestamp("2022-09-06"),
        "Sunak government formation complete": pd.Timestamp("2022-10-25"),
    }
    rows = []
    for _, row in events.iterrows():
        date = pm_start_overrides.get(row["name"], row["date"])
        if row["type"] == "General election":
            kind = "election_formation"
        elif row["type"] == "Change of prime minister":
            near_election = any(e <= date <= e + pd.Timedelta(days=60) for e in elections)
            if near_election:
                continue
            kind = "new_pm_reshuffle"
        else:
            kind = "named_event"
        rows.append(
            {
                "event_id": row["id"],
                "event_name": row["name"],
                "event_date": date,
                "event_type": kind,
                "event_source": "IfG event table",
                "event_selection_note": (
                    "Named IfG event; election-adjacent PM-complete duplicates removed. "
                    "For non-election PM changes, event_date is manually reset from IfG's "
                    "formation-complete date to the first PM reshuffle/accession date."
                ),
            }
        )
    return pd.DataFrame(rows)


def sos_change_count_for_window(start: pd.Timestamp, days: int) -> int:
    end = start + pd.Timedelta(days=days)
    sos = appointments[appointments["rank_equivalence"].eq("SoS")]
    changed_orgs = set(
        sos[(sos["start_date"] >= start) & (sos["start_date"] <= end)][
            "organisation_id"
        ].tolist()
    )
    changed_orgs.update(
        sos[(sos["end_date"] >= start) & (sos["end_date"] <= end)][
            "organisation_id"
        ].tolist()
    )
    return len(changed_orgs)


def derive_ordinary_events(named: pd.DataFrame) -> pd.DataFrame:
    sos = appointments[appointments["rank_equivalence"].eq("SoS")]
    dates = pd.concat([sos["start_date"], sos["end_date"]]).dropna().drop_duplicates()
    dates = sorted(pd.to_datetime(dates).tolist())
    named_dates = named["event_date"].tolist()
    candidates = []
    for date in dates:
        if date < pd.Timestamp("1979-05-04"):
            continue
        if any(abs((date - nd).days) <= 21 for nd in named_dates):
            continue
        count = sos_change_count_for_window(date, MAIN_WINDOW)
        if count >= 3:
            candidates.append((date, count))

    selected = []
    last = None
    for date, count in candidates:
        if last is not None and (date - last).days <= MAIN_WINDOW:
            continue
        selected.append((date, count))
        last = date

    rows = []
    for i, (date, count) in enumerate(selected, 1):
        rows.append(
            {
                "event_id": f"derived-ordinary-{i:03d}",
                "event_name": f"Derived ordinary reshuffle cluster ({date.date()})",
                "event_date": date,
                "event_type": "ordinary_reshuffle_cluster",
                "event_source": "Derived from IfG SoS-level appointment starts/exits",
                "event_selection_note": (
                    f"Selected because at least 3 SoS-level organisations changed within {MAIN_WINDOW} days; "
                    f"observed {count}."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_event_frame() -> pd.DataFrame:
    named = selected_named_events()
    ordinary = derive_ordinary_events(named)
    events = pd.concat([named, ordinary], ignore_index=True).sort_values("event_date")
    events["event_year"] = events["event_date"].dt.year
    return events.reset_index(drop=True)


def head_changed_for_org(org_id: str, event_date: pd.Timestamp, window_days: int) -> tuple[bool, str]:
    before = event_date - pd.Timedelta(days=1)
    after = event_date + pd.Timedelta(days=window_days)
    before_heads = heads_by_org(before)
    after_heads = heads_by_org(after)
    org_ids = related_orgs(org_id, event_date, after)
    before_people = set(before_heads[before_heads["organisation_id"].eq(org_id)]["person_id"])
    after_people = set(after_heads[after_heads["organisation_id"].isin(org_ids)]["person_id"])
    changed = before_people != after_people
    detail = f"head_before={';'.join(sorted(before_people)) or 'none'}; head_after={';'.join(sorted(after_people)) or 'none'}; compared_org_count={len(org_ids)}"
    return changed, detail


def classify_outcome(
    junior: pd.Series, event_date: pd.Timestamp, window_days: int
) -> dict[str, object]:
    before = event_date - pd.Timedelta(days=1)
    after = event_date + pd.Timedelta(days=window_days)
    person_id = junior["person_id"]
    original_appt = junior["appointment_id"]
    original_org = junior["organisation_id"]
    original_post = junior["post_id"]
    after_person = active_ministers(after)
    after_person = after_person[after_person["person_id"].eq(person_id)].copy()
    links = org_linked_during(original_org, event_date, after)
    original_related_orgs = related_orgs(original_org, event_date, after)

    exact = after_person[after_person["appointment_id"].eq(original_appt)]
    if not exact.empty:
        outcome = "A"
        label = "Stayed in exactly the same role and department"
        final = exact.iloc[0]
    elif after_person.empty:
        outcome = "E"
        label = "Left government"
        final = None
    else:
        promoted = after_person[
            after_person["rank_equivalence"].isin(["PM", "DPM", "SoS"])
            | after_person["cabinet_status"].isin(["Full cabinet", "Attends cabinet"])
        ]
        if not promoted.empty:
            outcome = "D"
            label = "Promoted to secretary of state or Cabinet-level role"
            final = promoted.iloc[0]
        else:
            junior_after = after_person[
                after_person["rank_equivalence"].isin(["MoS", "PUSS"])
            ].copy()
            if junior_after.empty:
                final = after_person.iloc[0]
                outcome = "D" if final["rank_equivalence"] in ["Parl. lead"] else "C"
                label = (
                    "Promoted to secretary of state or Cabinet-level role"
                    if outcome == "D"
                    else "Moved to another department"
                )
            else:
                same_dept = junior_after[
                    junior_after["organisation_id"].isin(original_related_orgs)
                ]
                if not same_dept.empty:
                    final = same_dept.iloc[0]
                    if links.empty:
                        outcome = "B"
                        label = "Stayed in same department but changed portfolio/title"
                    else:
                        outcome = "F"
                        label = "Ambiguous due to department restructure/title rename"
                else:
                    final = junior_after.iloc[0]
                    if not links.empty:
                        outcome = "F"
                        label = "Ambiguous due to department merger/abolition or machinery-of-government change"
                    else:
                        outcome = "C"
                        label = "Moved to another department"

    pre_group, _ = post_group(original_post)
    if final is None:
        final_fields = {
            "final_appointment_id": "",
            "final_post_id": "",
            "final_post_name": "",
            "final_rank_equivalence": "",
            "final_organisation_id": "",
            "final_organisation_name": "",
            "final_cabinet_status": "",
        }
    else:
        final_fields = {
            "final_appointment_id": final["appointment_id"],
            "final_post_id": final["post_id"],
            "final_post_name": final["post_display_name"],
            "final_rank_equivalence": final["rank_equivalence"],
            "final_organisation_id": final["organisation_id"],
            "final_organisation_name": final["organisation_name"],
            "final_cabinet_status": final.get("cabinet_status", ""),
        }
    final_group = post_group(final_fields["final_post_id"])[0] if final is not None else None
    return {
        "outcome_code": outcome,
        "outcome_label": label,
        "same_post_group_after": bool(pre_group and final_group and pre_group == final_group),
        "mog_link_types": ";".join(sorted(links["type"].dropna().unique().tolist())),
        **final_fields,
    }


def rows_for_window(events: pd.DataFrame, window_days: int) -> pd.DataFrame:
    rows = []
    for _, ev in events.iterrows():
        event_date = ev["event_date"]
        before = event_date - pd.Timedelta(days=1)
        after = event_date + pd.Timedelta(days=window_days)
        pre_active = active_ministers(before)
        after_active = active_ministers(after)
        juniors = pre_active[pre_active["rank_equivalence"].isin(["MoS", "PUSS"])].copy()
        heads_before = pre_active[pre_active["rank_equivalence"].eq("SoS")]
        heads_after = after_active[after_active["rank_equivalence"].eq("SoS")]
        before_heads_by_org = (
            heads_before.groupby("organisation_id")["person_id"].apply(set).to_dict()
        )
        after_heads_by_org = (
            heads_after.groupby("organisation_id")["person_id"].apply(set).to_dict()
        )
        after_by_person = {
            pid: group.copy() for pid, group in after_active.groupby("person_id", dropna=False)
        }
        related_cache: dict[str, set[str]] = {}
        links_cache: dict[str, pd.DataFrame] = {}
        for _, junior in juniors.iterrows():
            original_org = junior["organisation_id"]
            if original_org not in related_cache:
                links_cache[original_org] = org_linked_during(original_org, event_date, after)
                ids = {original_org}
                links = links_cache[original_org]
                ids.update(links["predecessor_organisation_id"].dropna().tolist())
                ids.update(links["successor_organisation_id"].dropna().tolist())
                related_cache[original_org] = ids

            related = related_cache[original_org]
            links = links_cache[original_org]
            before_people = set(before_heads_by_org.get(original_org, set()))
            after_people = set()
            for org_id in related:
                after_people.update(after_heads_by_org.get(org_id, set()))
            head_changed = before_people != after_people
            detail = (
                f"head_before={';'.join(sorted(before_people)) or 'none'}; "
                f"head_after={';'.join(sorted(after_people)) or 'none'}; "
                f"compared_org_count={len(related)}"
            )

            person_id = junior["person_id"]
            original_appt = junior["appointment_id"]
            original_post = junior["post_id"]
            after_person = after_by_person.get(person_id, pd.DataFrame()).copy()

            exact = (
                after_person[after_person["appointment_id"].eq(original_appt)]
                if not after_person.empty
                else pd.DataFrame()
            )
            if not exact.empty:
                outcome_code = "A"
                outcome_label = "Stayed in exactly the same role and department"
                final = exact.iloc[0]
            elif after_person.empty:
                outcome_code = "E"
                outcome_label = "Left government"
                final = None
            else:
                promoted = after_person[
                    after_person["rank_equivalence"].isin(["PM", "DPM", "SoS"])
                    | after_person["cabinet_status"].isin(["Full cabinet", "Attends cabinet"])
                ]
                if not promoted.empty:
                    outcome_code = "D"
                    outcome_label = "Promoted to secretary of state or Cabinet-level role"
                    final = promoted.iloc[0]
                else:
                    junior_after = after_person[
                        after_person["rank_equivalence"].isin(["MoS", "PUSS"])
                    ].copy()
                    if junior_after.empty:
                        final = after_person.iloc[0]
                        if final["rank_equivalence"] in ["Parl. lead"]:
                            outcome_code = "D"
                            outcome_label = "Promoted to secretary of state or Cabinet-level role"
                        else:
                            outcome_code = "C"
                            outcome_label = "Moved to another department"
                    else:
                        same_dept = junior_after[junior_after["organisation_id"].isin(related)]
                        if not same_dept.empty:
                            final = same_dept.iloc[0]
                            if links.empty:
                                outcome_code = "B"
                                outcome_label = (
                                    "Stayed in same department but changed portfolio/title"
                                )
                            else:
                                outcome_code = "F"
                                outcome_label = (
                                    "Ambiguous due to department restructure/title rename"
                                )
                        else:
                            final = junior_after.iloc[0]
                            if not links.empty:
                                outcome_code = "F"
                                outcome_label = (
                                    "Ambiguous due to department merger/abolition or machinery-of-government change"
                                )
                            else:
                                outcome_code = "C"
                                outcome_label = "Moved to another department"

            pre_group, _ = post_group(original_post)
            final_group = post_group(final["post_id"])[0] if final is not None else None
            if final is None:
                final_fields = {
                    "final_appointment_id": "",
                    "final_post_id": "",
                    "final_post_name": "",
                    "final_rank_equivalence": "",
                    "final_organisation_id": "",
                    "final_organisation_name": "",
                    "final_cabinet_status": "",
                }
            else:
                final_fields = {
                    "final_appointment_id": final["appointment_id"],
                    "final_post_id": final["post_id"],
                    "final_post_name": final["post_display_name"],
                    "final_rank_equivalence": final["rank_equivalence"],
                    "final_organisation_id": final["organisation_id"],
                    "final_organisation_name": final["organisation_name"],
                    "final_cabinet_status": final.get("cabinet_status", ""),
                }
            outcome = {
                "outcome_code": outcome_code,
                "outcome_label": outcome_label,
                "same_post_group_after": bool(pre_group and final_group and pre_group == final_group),
                "mog_link_types": ";".join(sorted(links["type"].dropna().unique().tolist())),
                **final_fields,
            }
            rows.append(
                {
                    "event_id": ev["event_id"],
                    "event_name": ev["event_name"],
                    "event_date": event_date.date().isoformat(),
                    "event_year": int(ev["event_year"]),
                    "event_type": ev["event_type"],
                    "event_source": ev["event_source"],
                    "event_selection_note": ev["event_selection_note"],
                    "window_days": window_days,
                    "pre_event_date": before.date().isoformat(),
                    "window_end_date": after.date().isoformat(),
                    "person_id": junior["person_id"],
                    "person_name": person_name_at(junior["person_id"], before),
                    "original_appointment_id": junior["appointment_id"],
                    "original_post_id": junior["post_id"],
                    "original_post_name": junior["post_display_name"],
                    "original_rank_equivalence": junior["rank_equivalence"],
                    "original_cabinet_status": junior.get("cabinet_status", ""),
                    "original_organisation_id": junior["organisation_id"],
                    "original_organisation_name": junior["organisation_name"],
                    "original_organisation_short_name": junior["organisation_short_name"],
                    "sos_changed_in_original_department": bool(head_changed),
                    "sos_change_detail": detail,
                    "technical_economic_department_or_brief": is_technical_economic(junior),
                    "strict_moved_out": outcome["outcome_code"] != "A",
                    "loose_moved_out": outcome["outcome_code"] in ["C", "D", "E"],
                    "loose_moved_out_including_ambiguous": outcome["outcome_code"]
                    in ["C", "D", "E", "F"],
                    **outcome,
                }
            )
    return pd.DataFrame(rows)


def rate_table(df: pd.DataFrame, outcome_col: str, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols + ["sos_changed_in_original_department"], dropna=False)[outcome_col]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "moved_n", "count": "denominator"})
    )
    grouped["moved_pct"] = grouped["moved_n"] / grouped["denominator"] * 100

    rows = []
    for keys, sub in grouped.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = dict(zip(group_cols, keys))
        yes = sub[sub["sos_changed_in_original_department"].eq(True)]
        no = sub[sub["sos_changed_in_original_department"].eq(False)]
        if yes.empty or no.empty:
            continue
        a = float(yes.iloc[0]["moved_n"])
        b = float(yes.iloc[0]["denominator"] - yes.iloc[0]["moved_n"])
        c = float(no.iloc[0]["moved_n"])
        d = float(no.iloc[0]["denominator"] - no.iloc[0]["moved_n"])
        # Haldane-Anscombe correction for ratio stability when a cell is zero.
        odds_ratio = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
        p_yes = a / (a + b) if a + b else math.nan
        p_no = c / (c + d) if c + d else math.nan
        rr = p_yes / p_no if p_no else math.nan
        rows.append(
            {
                **base,
                "outcome_definition": outcome_col,
                "sos_changed_moved_n": int(a),
                "sos_changed_denominator": int(a + b),
                "sos_changed_pct": p_yes * 100,
                "sos_stayed_moved_n": int(c),
                "sos_stayed_denominator": int(c + d),
                "sos_stayed_pct": p_no * 100,
                "difference_pp": (p_yes - p_no) * 100,
                "relative_risk": rr,
                "odds_ratio": odds_ratio,
            }
        )
    return pd.DataFrame(rows)


def outcome_distribution(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (
        df.groupby(group_cols + ["sos_changed_in_original_department", "outcome_code", "outcome_label"])
        .size()
        .reset_index(name="n")
        .sort_values(group_cols + ["sos_changed_in_original_department", "outcome_code"])
    )


RANK_ORDER = {
    "PM": 1,
    "DPM": 2,
    "SoS": 3,
    "Parl. lead": 3,
    "MoS": 4,
    "PUSS": 5,
    "Parl.": 6,
}


def add_split_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """Add a stayed-role dependent variable and four-way post-reshuffle outcome."""
    df = df.copy()
    df["stayed_in_original_role"] = df["outcome_code"].eq("A")

    def classify(row: pd.Series) -> tuple[str, str]:
        if row["outcome_code"] == "A":
            return "stayed_original_role", "Stayed in exact original role"
        if row["outcome_code"] == "D":
            return "promoted", "Promoted"
        if row["outcome_code"] == "E" or not str(row.get("final_rank_equivalence", "")).strip():
            return "left_or_no_better_role", "Left government or had no better role"

        original_rank = RANK_ORDER.get(str(row.get("original_rank_equivalence", "")))
        final_rank = RANK_ORDER.get(str(row.get("final_rank_equivalence", "")))
        if original_rank is not None and final_rank is not None:
            if final_rank < original_rank:
                return "promoted", "Promoted"
            if final_rank > original_rank:
                return "left_or_no_better_role", "Demoted or moved to a lower-ranked role"

        if row["outcome_code"] == "F":
            return "sideways_move", "Sideways move / ambiguous restructure"
        return "sideways_move", "Moved sideways"

    split = df.apply(classify, axis=1, result_type="expand")
    df["split_outcome_code"] = split[0]
    df["split_outcome_label"] = split[1]
    df["promoted_split"] = df["split_outcome_code"].eq("promoted")
    df["sideways_split"] = df["split_outcome_code"].eq("sideways_move")
    df["left_or_no_better_split"] = df["split_outcome_code"].eq("left_or_no_better_role")
    return df


def stay_rate_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols + ["sos_changed_in_original_department"], dropna=False)[
            "stayed_in_original_role"
        ]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "stayed_n", "count": "denominator"})
    )
    rows = []
    for keys, sub in grouped.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = dict(zip(group_cols, keys))
        yes = sub[sub["sos_changed_in_original_department"].eq(True)]
        no = sub[sub["sos_changed_in_original_department"].eq(False)]
        if yes.empty or no.empty:
            continue
        stay_yes = float(yes.iloc[0]["stayed_n"])
        den_yes = float(yes.iloc[0]["denominator"])
        stay_no = float(no.iloc[0]["stayed_n"])
        den_no = float(no.iloc[0]["denominator"])
        p_yes = stay_yes / den_yes if den_yes else math.nan
        p_no = stay_no / den_no if den_no else math.nan
        rows.append(
            {
                **base,
                "sos_changed_stayed_n": int(stay_yes),
                "sos_changed_denominator": int(den_yes),
                "sos_changed_stayed_pct": p_yes * 100,
                "sos_stayed_stayed_n": int(stay_no),
                "sos_stayed_denominator": int(den_no),
                "sos_stayed_stayed_pct": p_no * 100,
                "difference_pp": (p_yes - p_no) * 100,
                "relative_risk_of_staying": p_yes / p_no if p_no else math.nan,
            }
        )
    return pd.DataFrame(rows)


def split_distribution(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    counts = (
        df.groupby(
            group_cols
            + [
                "sos_changed_in_original_department",
                "split_outcome_code",
                "split_outcome_label",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="n")
    )
    denominators = (
        df.groupby(group_cols + ["sos_changed_in_original_department"], dropna=False)
        .size()
        .reset_index(name="denominator")
    )
    counts = counts.merge(
        denominators, on=group_cols + ["sos_changed_in_original_department"], how="left"
    )
    counts["pct"] = counts["n"] / counts["denominator"] * 100
    return counts.sort_values(
        group_cols + ["sos_changed_in_original_department", "split_outcome_code"]
    )


def split_summary(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    counts = (
        df.groupby(
            group_cols + ["sos_changed_in_original_department", "split_outcome_code"],
            dropna=False,
        )
        .size()
        .reset_index(name="n")
    )
    denominators = (
        df.groupby(group_cols + ["sos_changed_in_original_department"], dropna=False)
        .size()
        .reset_index(name="denominator")
    )
    counts = counts.merge(
        denominators, on=group_cols + ["sos_changed_in_original_department"], how="left"
    )
    counts["pct"] = counts["n"] / counts["denominator"] * 100
    return counts.sort_values(
        group_cols + ["sos_changed_in_original_department", "split_outcome_code"]
    )


def main() -> None:
    events = build_event_frame()
    all_rows = pd.concat([rows_for_window(events, w) for w in WINDOWS], ignore_index=True)
    all_rows = add_split_outcomes(all_rows)
    main = all_rows[all_rows["window_days"].eq(MAIN_WINDOW)].copy()

    event_counts = (
        main.groupby(["event_id", "event_name", "event_date", "event_type", "event_selection_note"])
        .agg(
            junior_ministers_pre_event=("person_id", "count"),
            sos_changed_rows=("sos_changed_in_original_department", "sum"),
            strict_moved_rows=("strict_moved_out", "sum"),
            loose_moved_rows=("loose_moved_out", "sum"),
        )
        .reset_index()
        .sort_values("event_date")
    )

    tables = []
    for outcome in ["strict_moved_out", "loose_moved_out", "loose_moved_out_including_ambiguous"]:
        tables.append(rate_table(main, outcome, ["window_days"]).assign(sample="all_events"))
        tables.append(
            rate_table(
                main[main["event_type"].eq("new_pm_reshuffle")], outcome, ["window_days"]
            ).assign(sample="new_pm_reshuffles")
        )
        tables.append(
            rate_table(
                main[~main["event_type"].eq("election_formation")], outcome, ["window_days"]
            ).assign(sample="excluding_elections")
        )
        tables.append(
            rate_table(
                main[main["technical_economic_department_or_brief"].eq(True)],
                outcome,
                ["window_days"],
            ).assign(sample="technical_economic")
        )
    summary_rates = pd.concat(tables, ignore_index=True)

    sensitivity = []
    for outcome in ["strict_moved_out", "loose_moved_out"]:
        sensitivity.append(rate_table(all_rows, outcome, ["window_days"]).assign(sample="all_events"))
        sensitivity.append(
            rate_table(
                all_rows[~all_rows["event_type"].eq("election_formation")],
                outcome,
                ["window_days"],
            ).assign(sample="excluding_elections")
        )
    sensitivity = pd.concat(sensitivity, ignore_index=True)

    distribution = outcome_distribution(main, ["event_type"])
    stay_tables = []
    split_tables = []
    split_summary_tables = []
    for subset_name, subset in [
        ("all_events", main),
        ("new_pm_reshuffles", main[main["event_type"].eq("new_pm_reshuffle")]),
        ("excluding_elections", main[~main["event_type"].eq("election_formation")]),
        (
            "technical_economic",
            main[main["technical_economic_department_or_brief"].eq(True)],
        ),
    ]:
        stay_tables.append(stay_rate_table(subset, ["window_days"]).assign(sample=subset_name))
        split_tables.append(
            split_distribution(subset, ["window_days"]).assign(sample=subset_name)
        )
        split_summary_tables.append(
            split_summary(subset, ["window_days"]).assign(sample=subset_name)
        )
    stay_rates = pd.concat(stay_tables, ignore_index=True)
    split_outcomes = pd.concat(split_tables, ignore_index=True)
    split_outcome_summary = pd.concat(split_summary_tables, ignore_index=True)
    records = []
    for _, ev in event_counts.iterrows():
        event_rows = main[main["event_id"].eq(ev["event_id"])]
        if event_rows.empty:
            continue
        by_changed = (
            event_rows.groupby("sos_changed_in_original_department")
            .agg(n=("person_id", "count"), strict_moved=("strict_moved_out", "sum"))
            .reset_index()
        )
        changed_n = int(by_changed[by_changed["sos_changed_in_original_department"].eq(True)]["n"].sum())
        changed_moved = int(
            by_changed[by_changed["sos_changed_in_original_department"].eq(True)][
                "strict_moved"
            ].sum()
        )
        stayed_n = int(by_changed[by_changed["sos_changed_in_original_department"].eq(False)]["n"].sum())
        stayed_moved = int(
            by_changed[by_changed["sos_changed_in_original_department"].eq(False)][
                "strict_moved"
            ].sum()
        )
        records.append(
            {
                "event_date": ev["event_date"],
                "event_name": ev["event_name"],
                "event_type": ev["event_type"],
                "sos_changed_juniors": changed_n,
                "sos_changed_strict_moved": changed_moved,
                "sos_changed_strict_moved_pct": changed_moved / changed_n * 100
                if changed_n
                else math.nan,
                "sos_stayed_juniors": stayed_n,
                "sos_stayed_strict_moved": stayed_moved,
                "sos_stayed_strict_moved_pct": stayed_moved / stayed_n * 100
                if stayed_n
                else math.nan,
            }
        )
    event_level_patterns = pd.DataFrame(records)
    event_level_patterns["changed_departments_kept_most_juniors"] = (
        event_level_patterns["sos_changed_juniors"].ge(3)
        & event_level_patterns["sos_changed_strict_moved_pct"].lt(50)
    )
    event_level_patterns["changed_departments_cleared_most_juniors"] = (
        event_level_patterns["sos_changed_juniors"].ge(3)
        & event_level_patterns["sos_changed_strict_moved_pct"].ge(75)
    )

    all_rows.to_csv(OUT / "junior_minister_reshuffle_dataset_all_windows.csv", index=False)
    main.to_csv(OUT / "junior_minister_reshuffle_dataset.csv", index=False)
    events.to_csv(OUT / "reshuffle_events.csv", index=False)
    event_counts.to_csv(OUT / "event_counts.csv", index=False)
    summary_rates.to_csv(OUT / "summary_rates.csv", index=False)
    sensitivity.to_csv(OUT / "window_sensitivity.csv", index=False)
    distribution.to_csv(OUT / "outcome_distribution.csv", index=False)
    stay_rates.to_csv(OUT / "stay_rates.csv", index=False)
    split_outcomes.to_csv(OUT / "split_outcome_distribution.csv", index=False)
    split_outcome_summary.to_csv(OUT / "split_outcome_summary.csv", index=False)
    event_level_patterns.to_csv(OUT / "event_level_patterns.csv", index=False)

    schema = """# Derived dataset schema

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
"""
    (OUT / "SCHEMA.md").write_text(schema, encoding="utf-8")

    readme = f"""# UK reshuffle junior-minister base-rate analysis

This folder contains a reproducible analysis built from the Institute for Government Ministers Database public data.

Source data:
- IfG Ministers Database public GitHub CSVs and SQLite database, downloaded to `work/`.
- IfG documents that the database covers all UK government ministers since 1979 and records role, department, rank and dates in office.
- IfG rank equivalence is used to identify `SoS`, `MoS` and `PUSS` posts.

Event construction:
- IfG named general elections are coded as `election_formation`.
- IfG change-of-prime-minister events are coded as `new_pm_reshuffle`, except PM-complete events within 60 days of a general election, which are treated as duplicate election-formation markers.
- For non-election PM changes, the event date is reset from IfG's "government formation complete" date to the first PM reshuffle/accession date: Major 1990-11-28, Brown 2007-06-27, May 2016-07-13, Johnson 2019-07-24, Truss 2022-09-06 and Sunak 2022-10-25.
- Ordinary reshuffles are derived mechanically: a date is selected when at least three SoS-rank organisations have appointment starts/exits in the following {MAIN_WINDOW} days, excluding dates within 21 days of named election/PM events.

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
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    methods = """# Methods note and limitations

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
"""
    (OUT / "methods_note.md").write_text(methods, encoding="utf-8")

    script_text = Path(__file__).read_text(encoding="utf-8")
    (OUT / "build_reshuffle_analysis.py").write_text(script_text, encoding="utf-8")

    print(f"events={len(events)}")
    print(f"main_rows={len(main)}")
    print(f"all_window_rows={len(all_rows)}")
    print(summary_rates.to_string(index=False))


if __name__ == "__main__":
    main()
