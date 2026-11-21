import re


class InternshipResearchAgent:
    """Compare candidate skills with extracted internship requirements."""

    REQUIREMENT_FIELDS = (
        "required_skills",
        "data_workflow_competencies",
        "foundational_ml_topics",
    )

    ALIASES = {
        "sklearn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "python 3": "python",
        "js": "javascript",
        "eda": "exploratory data analysis",
        "powerbi": "power bi",
    }

    def __init__(self, jobs):
        self.jobs = jobs

    def normalize_skill(self, skill):
        """Normalize casing, whitespace and a small set of common aliases."""
        value = re.sub(r"\s+", " ", str(skill or "").strip().lower())
        return self.ALIASES.get(value, value)

    def _collect_job_requirements(self, job):
        requirements = []
        seen = set()
        for field in self.REQUIREMENT_FIELDS:
            items = job.get(field) or []
            if isinstance(items, str):
                items = [items]
            for item in items:
                label = str(item or "").strip()
                if not label:
                    continue
                key = self.normalize_skill(label)
                if key not in seen:
                    requirements.append(label)
                    seen.add(key)
        return requirements

    def _is_non_skill_requirement(self, skill):
        key = self.normalize_skill(skill)
        return any(
            phrase in key
            for phrase in (
                "laptop", "notebook computer", "personal computer", "own computer"
            )
        )

    def get_other_requirements(self, job):
        """Return equipment requirements separately from technical skills."""
        return [
            item for item in self._collect_job_requirements(job)
            if self._is_non_skill_requirement(item)
        ]

    def get_requirements(self, job):
        """Return distinct technical requirements, dropping duplicate umbrellas."""
        all_items = [
            item for item in self._collect_job_requirements(job)
            if not self._is_non_skill_requirement(item)
        ]
        normalized = {self.normalize_skill(item) for item in all_items}
        filtered = []
        for item in all_items:
            key = self.normalize_skill(item)
            if "(" in key and ")" in key:
                content = key.split("(", 1)[1].rsplit(")", 1)[0]
                topics = [
                    self.normalize_skill(part.strip())
                    for part in re.split(r",|;|\band\b", content)
                    if part.strip()
                ]
                if len(topics) >= 2 and all(topic in normalized for topic in topics):
                    continue
            filtered.append(item)
        return filtered

    def compare_job(self, job, candidate_set):
        requirements = self.get_requirements(job)
        other_requirements = self.get_other_requirements(job)
        if not requirements:
            return {
                "status": "insufficient_data",
                "role": job.get("role"),
                "reason": "No technical requirements extracted.",
                "other_requirements": other_requirements,
            }

        matched = [
            item for item in requirements
            if self.normalize_skill(item) in candidate_set
        ]
        missing = [
            item for item in requirements
            if self.normalize_skill(item) not in candidate_set
        ]
        score = round(len(matched) / len(requirements) * 100, 2)

        optional = job.get("optional_skills") or []
        if isinstance(optional, str):
            optional = [optional]
        optional_matched = [
            item for item in optional
            if self.normalize_skill(item) in candidate_set
        ]

        eligibility = job.get("eligibility") or []
        if isinstance(eligibility, str):
            eligibility = [eligibility]

        return {
            "status": "analyzed",
            "company": job.get("company"),
            "role": job.get("role"),
            "source_url": job.get("source_url"),
            "location": job.get("location"),
            "work_mode": job.get("work_mode"),
            "experience": job.get("experience"),
            "stipend": job.get("stipend"),
            "deadline": job.get("deadline"),
            "openings": job.get("openings"),
            "match_percentage": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "total_requirements": len(requirements),
            "optional_skills_matched": optional_matched,
            "other_requirements": other_requirements,
            "eligibility_requirements": eligibility,
        }

    def analyze(self, candidate_skills):
        if not candidate_skills:
            raise ValueError("Candidate skills cannot be empty.")

        cleaned_skills = [
            str(skill).strip()
            for skill in candidate_skills
            if str(skill or "").strip()
        ]
        candidate_set = {self.normalize_skill(skill) for skill in cleaned_skills}
        if not candidate_set:
            raise ValueError("No valid candidate skills provided.")

        comparisons = []
        skipped_jobs = []
        for job in self.jobs:
            if job.get("extraction_status") != "success":
                skipped_jobs.append({
                    "role": job.get("role"),
                    "reason": "Job extraction unsuccessful.",
                })
                continue
            result = self.compare_job(job, candidate_set)
            if result["status"] == "analyzed":
                comparisons.append(result)
            else:
                skipped_jobs.append(result)

        ranked_jobs = sorted(
            comparisons,
            key=lambda item: (-item["match_percentage"], item.get("role") or ""),
        )
        for rank, job in enumerate(ranked_jobs, start=1):
            job["rank"] = rank

        best_job = ranked_jobs[0] if ranked_jobs else None
        return {
            "candidate_profile": {"skills": cleaned_skills},
            "analysis_summary": {
                "jobs_analyzed": len(ranked_jobs),
                "jobs_skipped": len(skipped_jobs),
                "best_matching_role": best_job["role"] if best_job else None,
                "best_match_percentage": best_job["match_percentage"] if best_job else None,
            },
            "ranked_jobs": ranked_jobs,
            "skipped_jobs": skipped_jobs,
            "methodology": (
                "Exact normalized technical-skill matching against extracted "
                "requirements. Equipment and eligibility are reported separately. "
                "Match percentage is not selection probability."
            ),
        }
