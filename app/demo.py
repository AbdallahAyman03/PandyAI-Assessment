import argparse
import sys
import json
from datetime import datetime, timezone

from app.utils.parser import load_jobs, load_candidates
from app.utils.approaches import run_approach, VALID_APPROACHES
from app.settings import config
from app.utils.embedding import index_candidates

def main():
    parser = argparse.ArgumentParser(description="Run batch matching process.")
    parser.add_argument("--approach", choices=VALID_APPROACHES, default="deterministic", help="Analytical approach to use")
    parser.add_argument("--top-k", type=int, default=5, help="Number of top candidates to rank per job")
    args = parser.parse_args()

    print("="*50)
    print(f" INITIATING BATCH MATCHING PROCESS ({args.approach.upper()})")
    print("="*50)

    jobs = load_jobs()
    candidates = load_candidates()

    if not jobs or not candidates:
        print("Error: Could not load data.")
        sys.exit(1)

    print(f"Loaded {len(jobs)} jobs and {len(candidates)} candidates.\n")

    if args.approach in ["hybrid", "agentic"]:
        print("Pre-indexing all candidates for semantic search...")
        index_candidates(candidates)
    
    approach_dir = config.output_dir / args.approach
    rank_dir = approach_dir / "rank"
    insights_dir = approach_dir / "insights"
    
    rank_dir.mkdir(parents=True, exist_ok=True)
    insights_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for job in jobs:
        print(f"Processing: {job.title} ({job.id})")
        
        ranked_results = run_approach(args.approach, candidates, job, top_k=args.top_k)
        
        # --- SPLIT THE DATA ---
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

        rank_payload = {
            "jobId": job.id,
            "approach": args.approach,
            "topK": len(ranked_results),
            "results": rank_output_list,
            "meta": { "approach": args.approach, "generatedAt": timestamp }
        }

        insights_payload = {
            "jobId": job.id,
            "approach": args.approach,
            "topK": len(ranked_results),
            "results": insights_output_list,
            "meta": { "approach": f"{args.approach}-insights", "generatedAt": timestamp }
        }

        rank_file = rank_dir / f"{job.id}.json"
        insights_file = insights_dir / f"{job.id}.json"
        
        try:
            with open(rank_file, 'w', encoding='utf-8') as f:
                json.dump(rank_payload, f, indent=2, ensure_ascii=False)
            with open(insights_file, 'w', encoding='utf-8') as f:
                json.dump(insights_payload, f, indent=2, ensure_ascii=False)
            success_count += 1
        except IOError as e:
            print(f"  -> Failed to write outputs for {job.id}: {e}")

    print("\n" + "="*50)
    print(f" BATCH COMPLETE: Successfully generated {success_count * 2} files.")
    print(f" Check the '{approach_dir.resolve()}' directory.")
    print("="*50)

if __name__ == "__main__":
    main()