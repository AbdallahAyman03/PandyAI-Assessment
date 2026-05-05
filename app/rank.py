import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.utils.parser import load_jobs, load_candidates
from app.utils.scorer import rank_candidates
from app.settings import config

def main():
    parser = argparse.ArgumentParser(description="Rank candidates for a specific job.")
    parser.add_argument("--job-id", required=True, help="The ID of the job to match against (e.g., j-001)")
    parser.add_argument("--top-k", type=int, default=None, help="Number of top candidates to return")
    parser.add_argument("--out", required=True, help="Base file path (e.g., outputs/j-001.json)")
    
    args = parser.parse_args()

    print("Loading data...")
    jobs = load_jobs()
    candidates = load_candidates()

    if not jobs or not candidates:
        print("Error: Could not load jobs or candidates.")
        sys.exit(1)

    target_job = next((job for job in jobs if job.id == args.job_id), None)
    if not target_job:
        print(f"\nError: Job ID '{args.job_id}' not found.")
        sys.exit(1)

    print(f"Ranking candidates for job: '{target_job.title}'...")
    ranked_results = rank_candidates(candidates, target_job, top_k=args.top_k)

  
    rank_output_list = []
    insights_output_list = []

    for res in ranked_results:
      
        res_copy = dict(res)
        
        
        insights_data = res_copy.pop("insights", None)
        
        
        rank_output_list.append(res_copy)
        
        
        if insights_data:
            insights_output_list.append({
                "candidateId": res["candidateId"],
                "candidateName": res["candidateName"],
                "insights": insights_data
            })

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    rank_payload = {
        "jobId": target_job.id,
        "topK": args.top_k if args.top_k is not None else len(ranked_results),
        "results": rank_output_list,
        "meta": { "approach": "baseline-v1", "generatedAt": timestamp }
    }

    insights_payload = {
        "jobId": target_job.id,
        "topK": args.top_k if args.top_k is not None else len(ranked_results),
        "results": insights_output_list,
        "meta": { "approach": "baseline-v1-insights", "generatedAt": timestamp }
    }

    output_dir = config.output_dir   

    rank_dir = output_dir / "rank"
    insights_dir = output_dir / "insights"

    rank_dir.mkdir(parents=True, exist_ok=True)
    insights_dir.mkdir(parents=True, exist_ok=True)

    rank_file = rank_dir / f"{target_job.id}.json"
    insights_file = insights_dir / f"{target_job.id}.json"

    try:
        with open(rank_file, 'w', encoding='utf-8') as f:
            json.dump(rank_payload, f, indent=2, ensure_ascii=False)
            
        with open(insights_file, 'w', encoding='utf-8') as f:
            json.dump(insights_payload, f, indent=2, ensure_ascii=False)
            
        print("\nSuccess!")
        print(f" -> Rank data saved to:     {rank_file.resolve()}")
        print(f" -> Insights data saved to: {insights_file.resolve()}")
    except IOError as e:
        print(f"\nError writing to output files: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()