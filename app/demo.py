import sys
import json
from datetime import datetime, timezone

from app.utils.parser import load_jobs, load_candidates
from app.utils.scorer import rank_candidates
from app.settings import config

def main():
    print("="*50)
    print(" INITIATING BATCH MATCHING PROCESS")
    print("="*50)

    jobs = load_jobs()
    candidates = load_candidates()

    if not jobs or not candidates:
        print("Error: Could not load data.")
        sys.exit(1)

    print(f"Loaded {len(jobs)} jobs and {len(candidates)} candidates.\n")

    
    rank_dir = config.output_dir / "rank"
    insights_dir = config.output_dir / "insights"
    
    rank_dir.mkdir(parents=True, exist_ok=True)
    insights_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for job in jobs:
        print(f"Processing: {job.title} ({job.id})")
        
        ranked_results = rank_candidates(candidates, job)
        
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
            "topK": len(ranked_results),
            "results": rank_output_list,
            "meta": { "approach": "baseline-v1", "generatedAt": timestamp }
        }

        insights_payload = {
            "jobId": job.id,
            "topK": len(ranked_results),
            "results": insights_output_list,
            "meta": { "approach": "baseline-v1-insights", "generatedAt": timestamp }
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
    print(f" Check the '{rank_dir.parent.resolve()}' directory.")
    print("="*50)

if __name__ == "__main__":
    main()