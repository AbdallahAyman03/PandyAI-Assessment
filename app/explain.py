import argparse
import sys
import textwrap

from app.utils.parser import load_jobs, load_candidates
from app.utils.scorer import score_candidate

def main():
    parser = argparse.ArgumentParser(description="Explain the matching score for a single candidate.")
    parser.add_argument("--job-id", required=True, help="The ID of the job to match against (e.g., j-001)")
    parser.add_argument("--candidate-id", required=True, help="The ID of the candidate to evaluate (e.g., c-018)")
    
    args = parser.parse_args()

    jobs = load_jobs()
    candidates = load_candidates()

    if not jobs or not candidates:
        print("Error: Could not load jobs or candidates. Please check your data directory.")
        sys.exit(1)

    target_job = next((job for job in jobs if job.id == args.job_id), None)
    if not target_job:
        print(f"Error: Job ID '{args.job_id}' not found.")
        sys.exit(1)

    target_candidate = next((cand for cand in candidates if cand.id == args.candidate_id), None)
    if not target_candidate:
        print(f"Error: Candidate ID '{args.candidate_id}' not found.")
        sys.exit(1)

    result = score_candidate(target_candidate, target_job)

    print("\n" + "="*60)
    print(" MATCH EXPLANATION REPORT")
    print("="*60)
    print(f"Candidate  : {target_candidate.fullName} ({target_candidate.id})")
    print(f"Job        : {target_job.title} ({target_job.id})")
    print(f"Final Score: {result['score']} / 100")
    print("-" * 60)
    
    print("SUMMARY:")
    print(f"  {result['summary']}")
    print("-" * 60)
    
    print("SCORING BREAKDOWN:")
    for reason in result['reasons']:
        weight = reason['weight']
        weight_str = f"+{weight}" if weight > 0 else f"{weight}"
        if weight == 0:
            weight_str = " 0.0"
            
        print(f"  [{weight_str.rjust(6)}] {reason['type'].upper()}")
        
        wrapped_evidence = textwrap.fill(reason['evidence'], width=54)
        for line in wrapped_evidence.split('\n'):
            print(f"           {line}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()