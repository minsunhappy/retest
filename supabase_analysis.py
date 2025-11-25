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
        scores = rec.get("question_scores") or {}

        for interface_code, payload in scores.items():
            if not payload:
                continue
            score_dict = payload.get("scores") or {}
            rows.append(
                {
                    "participant_id": participant_key,
                    "name": participant.get("name"),
                    "age": participant.get("age"),
                    "gender": participant.get("gender"),
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


def plot_interface_scores(df: pd.DataFrame, output_dir: Path, label: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    melted = df.melt(id_vars=["interface"], value_vars=QUESTION_ORDER, var_name="question", value_name="score").dropna()
    plt.figure(figsize=(10, 6))
    sns.barplot(data=melted, x="interface", y="score", hue="question", order=INTERFACE_ORDER, palette="Set2", ci="sd")
    plt.ylim(0, 7)
    plt.title(f"Average Scores by Interface ({label})")
    plt.ylabel("Likert Score (1-7)")
    plt.xlabel("Interface")
    plt.legend(title="")
    plt.tight_layout()
    plt.savefig(output_dir / f"{label}_barplot.png", dpi=200)
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

    plot_interface_scores(df, dest, label)
    df.to_csv(dest / f"{label}_raw_long.csv", index=False)
    print(f"[INFO] {label} 분석 결과를 {dest}에 저장했습니다.")


def main():
    parser = argparse.ArgumentParser(description="Supabase 설문 응답 분석")
    parser.add_argument("--supabase-url", default=os.environ.get("SUPABASE_URL"), help="Supabase 프로젝트 URL")
    parser.add_argument("--service-key", default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFyb2Nob3d5a3lubWRoeWlrY2pkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODM4ODAsImV4cCI6MjA3OTY1OTg4MH0.pdnjDMltF0kmSFOKiJL5wJIYTwtFLZWdaRUTUxhvaf4", help="Supabase service key")
    parser.add_argument("--table", default="survey_responses", help="조회할 테이블 이름")
    parser.add_argument("--limit", type=int, default=None, help="조회할 레코드 수 제한")
    parser.add_argument("--output-dir", default="supabase_analysis", help="결과 저장 폴더")
    args = parser.parse_args()

    if not args.supabase_url or not args.service_key:
        raise SystemExit("SUPABASE_URL 또는 SUPABASE_SERVICE_KEY 환경 변수가 설정되어 있지 않습니다.")

    print("[INFO] Supabase에서 데이터를 가져오는 중...")
    rows = fetch_supabase_rows(args.supabase_url, args.service_key, table=args.table, limit=args.limit)
    df = flatten_question_scores(rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analyze_group(df, "overall", output_dir)

    for folder, sub_df in df.groupby("data_folder"):
        label = f"data_{folder or 'unknown'}"
        analyze_group(sub_df, label, output_dir)

    print("[DONE] 모든 분석을 완료했습니다.")


if __name__ == "__main__":
    main()

