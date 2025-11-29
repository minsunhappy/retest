#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase에 저장된 설문 응답을 불러와서
- 인터페이스별/질문별 요약 통계
- 데이터 폴더(영상)별 요약 통계
- Friedman test 및 Holm-Bonferroni 보정이 적용된 Wilcoxon pairwise 비교
를 수행하고 결과를 CSV/JSON/그래프 형태로 저장합니다.

환경 변수:
    SUPABASE_URL          - 예) https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY  - service_role 또는 정책상 select 권한이 있는 키

사용 예시:
    python supabase_analysis.py --output-dir analysis_results
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.stats import friedmanchisquare, wilcoxon
from statsmodels.stats.multitest import multipletests

plt.rcParams["font.family"] = "DejaVu Sans"

QUESTION_ORDER = ["Q1", "Q2", "Q3", "Q4"]
INTERFACE_ORDER = ["C", "D", "D1", "Y", "Y1"]


def normalize_gender(value: str | None) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    if not text:
        return "unknown"
    male_tokens = {"m", "male", "남", "남자", "man"}
    female_tokens = {"f", "female", "여", "여자", "woman"}
    if text in male_tokens:
        return "male"
    if text in female_tokens:
        return "female"
    return "other"


def fetch_supabase_rows(url: str, service_key: str, table: str = "survey_responses", limit: int | None = None):
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }
    params = {"select": "*"}
    if limit:
        params["limit"] = limit
    resp = requests.get(f"{url}/rest/v1/{table}", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def flatten_question_scores(records: list[dict]) -> pd.DataFrame:
    rows = []
    for rec in records:
        participant = rec.get("participant") or {}
        participant_key = rec.get("id") or f"{participant.get('name','unknown')}_{rec.get('created_at','')}"
        name = participant.get("name") or rec.get("name")
        age = participant.get("age") or rec.get("age")
        gender = participant.get("gender") or rec.get("gender")
        scores = rec.get("question_scores") or {}
        pairing_meta = scores.get("_pairing_info") or {}
        pairing_index = pairing_meta.get("permutation_index")
        pairing_number = pairing_meta.get("permutation_number")

        for interface_code, payload in scores.items():
            if interface_code.startswith("_"):
                continue
            if interface_code not in INTERFACE_ORDER:
                continue
            if not payload:
                continue
            score_dict = payload.get("scores") or {}
            rows.append(
                {
                    "participant_id": participant_key,
                    "name": name,
                    "age": age,
                    "gender": gender,
                    "interface": interface_code,
                    "data_folder": payload.get("dataFolder") or payload.get("data_folder"),
                    "html_file": payload.get("htmlFile"),
                    "Q1": score_dict.get("Q1"),
                    "Q2": score_dict.get("Q2"),
                    "Q3": score_dict.get("Q3"),
                    "Q4": score_dict.get("Q4"),
                    "preferred_interface": rec.get("preferred_interface"),
                    "preferred_reason": rec.get("preferred_reason"),
                    "created_at": rec.get("created_at"),
                    "pairing_index": pairing_index,
                    "pairing_number": pairing_number,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Supabase에서 가져온 question_scores 데이터가 없습니다.")
    # 정렬 기준을 명시적으로 설정
    df["interface"] = pd.Categorical(df["interface"], categories=INTERFACE_ORDER, ordered=True)
    return df


def compute_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = (
        df.groupby("interface")[QUESTION_ORDER]
        .agg(["mean", "std", "count"])
        .rename_axis(index="interface")
    )
    return stats


def run_friedman_tests(df: pd.DataFrame) -> dict:
    results = {}
    for question in QUESTION_ORDER:
        pivot = df.pivot_table(index="participant_id", columns="interface", values=question)
        pivot = pivot.dropna(axis=0, how="any")
        available_interfaces = [col for col in INTERFACE_ORDER if col in pivot.columns]
        if len(available_interfaces) < 3 or pivot.empty:
            continue
        args = [pivot[col] for col in available_interfaces]
        stat, p = friedmanchisquare(*args)
        results[question] = {
            "interfaces": available_interfaces,
            "statistic": stat,
            "p_value": p,
            "n": len(pivot),
        }
    return results


def run_pairwise_wilcoxon(df: pd.DataFrame) -> dict:
    results = {}
    for question in QUESTION_ORDER:
        pivot = df.pivot_table(index="participant_id", columns="interface", values=question)
        available = [col for col in INTERFACE_ORDER if col in pivot.columns]
        pairs = []
        pvals = []
        stats = []

        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                a, b = available[i], available[j]
                paired = pivot[[a, b]].dropna()
                if len(paired) < 5:
                    continue
                stat, p = wilcoxon(paired[a], paired[b])
                pairs.append((a, b))
                stats.append(stat)
                pvals.append(p)

        if not pvals:
            continue

        corrected = multipletests(pvals, method="holm")
        entries = []
        for (a, b), stat, raw_p, corr_p, reject in zip(pairs, stats, pvals, corrected[1], corrected[0]):
            entries.append(
                {
                    "interface_a": a,
                    "interface_b": b,
                    "statistic": stat,
                    "p_value": raw_p,
                    "p_value_holm": corr_p,
                    "reject_null": bool(reject),
                    "n": int(
                        df[(df["interface"] == a) | (df["interface"] == b)]
                        .groupby("participant_id")
                        .filter(lambda x: x["interface"].nunique() == 2)["participant_id"]
                        .nunique()
                    ),
                }
            )
        results[question] = entries
    return results


def p_value_to_stars(p: float) -> str:
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < 0.05:
        return '*'
    return ''


def plot_interface_scores(
    df: pd.DataFrame,
    friedman_results: dict,
    pairwise_results: dict,
    output_dir: Path,
    label: str
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    question_labels = {
        "Q1": "Q1. Mental Demand",
        "Q2": "Q2. Physical Demand",
        "Q3": "Q3. Contextual Alignment",
        "Q4": "Q4. Overall Engagement",
    }
    interface_labels = {
        "C": "ComVi (C)",
        "D": "Danmaku (D)",
        "D1": "Danmaku One (D1)",
        "Y": "YouTube (Y)",
        "Y1": "YouTube One (Y1)",
    }
    colors = ["#266DD3", "#FF914D", "#FDC830", "#4C956C", "#B56576"]

    fig, ax = plt.subplots(figsize=(13, 6))
    total_participants = df["participant_id"].nunique()
    x = np.arange(len(QUESTION_ORDER))
    bar_width = 0.16
    offsets = np.linspace(-(len(INTERFACE_ORDER) - 1) / 2, (len(INTERFACE_ORDER) - 1) / 2, len(INTERFACE_ORDER)) * bar_width

    bar_centers = {question: {} for question in QUESTION_ORDER}

    for idx, (interface, color) in enumerate(zip(INTERFACE_ORDER, colors)):
        subset = df[df["interface"] == interface]
        if subset.empty:
            continue
        means = [subset[q].mean() for q in QUESTION_ORDER]
        sems = [subset[q].sem() for q in QUESTION_ORDER]
        positions = x + offsets[idx]
        bars = ax.bar(
            positions,
            means,
            width=bar_width,
            color=color,
            alpha=0.85,
            yerr=sems,
            capsize=4,
            label=interface_labels.get(interface, interface),
            edgecolor="white",
            linewidth=0.8,
        )
        for px, mean in zip(positions, means):
            if pd.notna(mean):
                ax.text(px, mean + 0.05, f"{mean:.2f}", ha="center", va="bottom", fontsize=9)
        for question, pos, mean, sem in zip(QUESTION_ORDER, positions, means, sems):
            if pd.notna(mean):
                bar_centers[question][interface] = {
                    "x": pos,
                    "height": mean + (sem if pd.notna(sem) else 0)
                }

    ax.set_xticks(x)
    ax.set_xticklabels([question_labels[q] for q in QUESTION_ORDER], fontsize=11)
    ax.set_ylim(1, 7.2)
    ax.set_yticks(range(1, 8))
    ax.set_ylabel("7-point Likert scale", fontsize=12)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(f"Interface comparison by question ({label})", fontsize=14, pad=12)
    ax.legend(ncol=3, fontsize=10)

    # annotate N
    ax.text(
        0.02,
        1.02,
        f"N = {total_participants}",
        transform=ax.transAxes,
        fontsize=11,
        ha="left",
        va="bottom",
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
    )

    # significance markers per question
    for question in QUESTION_ORDER:
        entries = pairwise_results.get(question, [])
        if not entries:
            continue

        max_height = max(
            (bar_centers[question][iface]["height"] for iface in bar_centers[question]),
            default=0
        )
        offset_step = 0.18
        level = 0
        for entry in entries:
            if not entry.get("reject_null"):
                continue
            iface_a = entry["interface_a"]
            iface_b = entry["interface_b"]
            data_a = bar_centers[question].get(iface_a)
            data_b = bar_centers[question].get(iface_b)
            if not data_a or not data_b:
                continue

            x1 = data_a["x"]
            x2 = data_b["x"]
            y = max_height + 0.15 + level * offset_step
            ax.plot([x1, x1, x2, x2], [y - 0.03, y, y, y - 0.03], color="black", linewidth=1)
            stars = p_value_to_stars(entry.get("p_value_holm", entry.get("p_value", 1)))
            if stars:
                ax.text((x1 + x2) / 2, y + 0.02, stars, ha="center", va="bottom", fontsize=11)
            level += 1

    plt.tight_layout()
    plt.savefig(output_dir / f"{label}_barplot.jpg", dpi=200, bbox_inches="tight", format="jpg")
    plt.close()


def analyze_group(df: pd.DataFrame, label: str, output_dir: Path) -> None:
    if df.empty:
        print(f"[WARN] {label} 데이터가 없어 분석을 건너뜁니다.")
        return

    dest = output_dir / label
    dest.mkdir(parents=True, exist_ok=True)

    descriptive = compute_descriptive_stats(df)
    descriptive.to_csv(dest / f"{label}_descriptive.csv")

    friedman_results = run_friedman_tests(df)
    pairwise_results = run_pairwise_wilcoxon(df)

    with open(dest / f"{label}_stats.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "friedman": friedman_results,
                "pairwise_wilcoxon": pairwise_results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    plot_interface_scores(df, friedman_results, pairwise_results, dest, label)
    df.to_csv(dest / f"{label}_raw_long.csv", index=False)
    print(f"[INFO] {label} 분석 결과를 {dest}에 저장했습니다.")


def summarize_demographics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total": 0,
            "gender_counts": {"male": 0, "female": 0, "other": 0, "unknown": 0},
            "mean_age": float("nan"),
            "std_age": float("nan"),
            "age_count": 0,
        }
    subset = (
        df[["participant_id", "age", "gender"]]
        .drop_duplicates(subset=["participant_id"])
        .copy()
    )
    subset["gender_norm"] = subset["gender"].apply(normalize_gender)
    gender_counts = subset["gender_norm"].value_counts().to_dict()
    ages = pd.to_numeric(subset["age"], errors="coerce")
    return {
        "total": subset["participant_id"].nunique(),
        "gender_counts": {
            "male": int(gender_counts.get("male", 0)),
            "female": int(gender_counts.get("female", 0)),
            "other": int(gender_counts.get("other", 0)),
            "unknown": int(gender_counts.get("unknown", 0)),
        },
        "mean_age": float(ages.mean()) if ages.notna().any() else float("nan"),
        "std_age": float(ages.std(ddof=0)) if ages.notna().sum() > 1 else float("nan"),
        "age_count": int(ages.notna().sum()),
    }


def compute_interface_usage(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=INTERFACE_ORDER)
    working = df.copy()
    working["data_folder"] = working["data_folder"].fillna("unknown")
    table = (
        working.groupby(["data_folder", "interface"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=INTERFACE_ORDER, fill_value=0)
        .sort_index()
    )
    return table


def summarize_preference(df: pd.DataFrame) -> tuple[pd.Series, int, int]:
    if df.empty:
        empty = pd.Series(dtype=int)
        return empty, 0, 0
    pref = (
        df[["participant_id", "preferred_interface"]]
        .drop_duplicates(subset=["participant_id"])
        .copy()
    )
    pref["preferred_interface"] = (
        pref["preferred_interface"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    total_participants = pref["participant_id"].nunique()
    valid = pref[pref["preferred_interface"].isin(INTERFACE_ORDER)]
    counts = valid["preferred_interface"].value_counts().reindex(INTERFACE_ORDER, fill_value=0)
    recorded = int(valid.shape[0])
    return counts, total_participants, recorded


def format_table_lines(table: pd.DataFrame) -> list[str]:
    if table.empty:
        return ["데이터별 인터페이스 노출 기록이 없습니다."]
    header = ["데이터폴더"] + INTERFACE_ORDER
    lines = ["\t".join(header)]
    for folder, row in table.iterrows():
        values = [folder] + [str(int(row.get(iface, 0))) for iface in INTERFACE_ORDER]
        lines.append("\t".join(values))
    return lines


def format_preference_lines(counts: pd.Series, total: int, recorded: int) -> list[str]:
    if total == 0:
        return ["선호 인터페이스 응답이 없습니다."]
    lines = [
        f"선호 인터페이스 응답 인원: {recorded} / {total}명"
    ]
    for iface in INTERFACE_ORDER:
        count = int(counts.get(iface, 0))
        pct = (count / recorded * 100) if recorded else 0.0
        lines.append(f"- {iface}: {count}명 ({pct:.1f}%)")
    others = recorded - int(counts.sum())
    if others > 0:
        pct = (others / recorded * 100) if recorded else 0.0
        lines.append(f"- 기타 코드: {others}명 ({pct:.1f}%)")
    missing = total - recorded
    if missing > 0:
        lines.append(f"- 미응답: {missing}명")
    return lines


def generate_overall_report(df: pd.DataFrame, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    report_path = dest / "report.txt"
    demographics = summarize_demographics(df)
    usage_table = compute_interface_usage(df)
    pref_counts, pref_total, pref_recorded = summarize_preference(df)

    mean_age = demographics["mean_age"]
    std_age = demographics["std_age"]
    mean_str = f"{mean_age:.2f}" if not pd.isna(mean_age) else "N/A"
    std_str = f"{std_age:.2f}" if not pd.isna(std_age) else "N/A"

    lines = [
        "# Overall Report",
        "",
        "## 인구통계 요약",
        f"- 총 인원: {demographics['total']}명",
        f"- 남자: {demographics['gender_counts']['male']}명",
        f"- 여자: {demographics['gender_counts']['female']}명",
        f"- 기타/미응답: {demographics['gender_counts']['other'] + demographics['gender_counts']['unknown']}명",
        f"- 나이 평균: {mean_str} (N={demographics['age_count']})",
        f"- 나이 표준편차: {std_str}",
        "",
        "## 데이터별 인터페이스 노출 횟수",
        *format_table_lines(usage_table),
        "",
        "## 선호 인터페이스 비율",
        *format_preference_lines(pref_counts, pref_total, pref_recorded),
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] overall report를 {report_path}에 저장했습니다.")


def main():
    parser = argparse.ArgumentParser(description="Supabase 설문 응답 분석")
    parser.add_argument("--supabase-url", default="https://qrochowykynmdhyikcjd.supabase.co", help="Supabase 프로젝트 URL")
    parser.add_argument("--service-key", default="sb_secret_b5KsbgIGaADZhXwwvL6tcQ_ASY9NrQZ", help="Supabase service key")
    parser.add_argument("--table", default="survey_responses", help="조회할 테이블 이름")
    parser.add_argument("--limit", type=int, default=None, help="조회할 레코드 수 제한")
    parser.add_argument("--output-dir", default="supabase_analysis", help="결과 저장 폴더")
    args = parser.parse_args()

    if not args.supabase_url or not args.service_key:
        raise SystemExit("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY 환경 변수가 설정되어 있지 않습니다.")

    print("[INFO] Supabase에서 데이터를 가져오는 중...")
    rows = fetch_supabase_rows(args.supabase_url, args.service_key, table=args.table, limit=args.limit)
    df = flatten_question_scores(rows)

    # 2025-11-27 14:31:54.837+00 이후로 수집된 데이터만 필터링
    cutoff_time = pd.to_datetime("2025-11-20 14:31:54.837+00")
    # cutoff_time = pd.to_datetime("2025-11-27 14:31:54.837+00")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df[df["created_at"] > cutoff_time]
    print(f"[INFO] 필터링 후 데이터 수: {len(df)} rows (cutoff: {cutoff_time})")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analyze_group(df, "overall", output_dir)
    generate_overall_report(df, output_dir / "overall")

    for folder, sub_df in df.groupby("data_folder"):
        label = f"data_{folder or 'unknown'}"
        analyze_group(sub_df, label, output_dir)

    print("[DONE] 모든 분석을 완료했습니다.")


if __name__ == "__main__":
    main()

