
import re


class InternshipResearchAgent:

    def __init__(self, jobs):

        self.jobs = jobs

    # Standardize skill names

    # Normalize skills consistently

    # Normalize skill names

    # Normalize skills consistently
    def normalize_skill(self, skill):

        skill = str(skill).strip().lower()
        skill = re.sub(r"\\s+", " ", skill)

        aliases = {
            "sklearn": "scikit-learn",
            "scikit learn": "scikit-learn",
            "eda": "exploratory data analysis"
        }

        return aliases.get(skill, skill)

    # Collect and deduplicate all job requirements
    def _collect_job_requirements(self, job):

        fields = [
            "required_skills",
            "data_workflow_competencies",
            "foundational_ml_topics"
        ]

        requirements = []
        seen = set()

        for field in fields:

            items = job.get(field) or []

            if isinstance(items, str):
                items = [items]

            for skill in items:

                if not skill or not str(skill).strip():
                    continue

                key = self.normalize_skill(skill)

                if key not in seen:
                    requirements.append(str(skill).strip())
                    seen.add(key)

        return requirements

    # Separate equipment and practical requirements from technical skills
    def _is_non_skill_requirement(self, skill):

        key = self.normalize_skill(skill)

        return (
            "laptop" in key
            or "notebook computer" in key
            or "personal computer" in key
            or "own computer" in key
        )

    # Return non-skill requirements separately
    def get_non_skill_requirements(self, job):

        return [
            skill
            for skill in self._collect_job_requirements(job)
            if self._is_non_skill_requirement(skill)
        ]

    # Collect technical requirements and remove duplicate umbrella topics

    # Separate technical skills from equipment requirements
    def _is_non_skill_requirement(self, skill):

        key = self.normalize_skill(skill)

        return (
            "laptop" in key
            or "personal computer" in key
            or "own computer" in key
        )

    def _collect_job_requirements(self, job):

        fields = [
            "required_skills",
            "data_workflow_competencies",
            "foundational_ml_topics"
        ]

        requirements = []
        seen = set()

        for field in fields:

            items = job.get(field) or []

            if isinstance(items, str):
                items = [items]

            for skill in items:

                skill = str(skill).strip()
                key = self.normalize_skill(skill)

                if skill and key not in seen:
                    requirements.append(skill)
                    seen.add(key)

        return requirements

    def get_other_requirements(self, job):

        return [
            skill
            for skill in self._collect_job_requirements(job)
            if self._is_non_skill_requirement(skill)
        ]

    # Collect unique technical requirements
    def get_requirements(self, job):

        requirements = [
            skill for skill in self._collect_job_requirements(job)
            if not self._is_non_skill_requirement(skill)
        ]

        seen = {
            self.normalize_skill(skill)
            for skill in requirements
        }

        filtered = []

        for skill in requirements:

            key = self.normalize_skill(skill)

            if "(" in key and ")" in key:

                content = key.split("(", 1)[1].rsplit(")", 1)[0]

                topics = [
                    self.normalize_skill(topic.strip())
                    for topic in re.split(r",|;|\\band\\b", content)
                    if topic.strip()
                ]

                if (
                    len(topics) >= 2
                    and all(topic in seen for topic in topics)
                ):
                    continue

            filtered.append(skill)

        return filtered

    # Compare one job
    def compare_job(self, job, candidate_set):

        requirements = self.get_requirements(job)
        other_requirements = self.get_other_requirements(job)

        if not requirements:

            return {
                "status": "insufficient_data",
                "role": job.get("role"),
                "reason": "No technical requirements extracted.",
                "other_requirements": other_requirements
            }

        matched = [
            skill for skill in requirements
            if self.normalize_skill(skill) in candidate_set
        ]

        missing = [
            skill for skill in requirements
            if self.normalize_skill(skill) not in candidate_set
        ]

        score = round(
            len(matched) / len(requirements) * 100,
            2
        )

        optional = job.get("optional_skills") or []

        optional_matched = [
            skill for skill in optional
            if self.normalize_skill(skill) in candidate_set
        ]

        return {
            "status": "analyzed",
            "company": job.get("company"),
            "role": job.get("role"),
            "source_url": job.get("source_url"),
            "match_percentage": score,
            "matched_skills": matched,
            "missing_skills": missing,
            "total_requirements": len(requirements),
            "optional_skills_matched": optional_matched,
            "other_requirements": other_requirements
        }

    def analyze(self, candidate_skills):

        if not candidate_skills:
            raise ValueError("Candidate skills cannot be empty.")

        candidate_set = {
            self.normalize_skill(skill)
            for skill in candidate_skills
            if skill and str(skill).strip()
        }

        if not candidate_set:
            raise ValueError("No valid candidate skills provided.")

        comparisons = []
        skipped_jobs = []

        for job in self.jobs:

            if job.get("extraction_status") != "success":

                skipped_jobs.append({
                    "role": job.get("role"),
                    "reason": "Job extraction unsuccessful."
                })

                continue

            result = self.compare_job(job, candidate_set)

            if result["status"] == "analyzed":
                comparisons.append(result)

            else:
                skipped_jobs.append(result)

        ranked_jobs = sorted(
            comparisons,
            key=lambda item: item["match_percentage"],
            reverse=True
        )

        for index, job in enumerate(ranked_jobs, start=1):
            job["rank"] = index

        best_job = ranked_jobs[0] if ranked_jobs else None

        return {

            "candidate_profile": {
                "skills": candidate_skills
            },

            "analysis_summary": {

                "jobs_analyzed": len(ranked_jobs),

                "jobs_skipped": len(skipped_jobs),

                "best_matching_role": (
                    best_job["role"] if best_job else None
                ),

                "best_match_percentage": (
                    best_job["match_percentage"] if best_job else None
                )
            },

            "ranked_jobs": ranked_jobs,

            "skipped_jobs": skipped_jobs,

            "methodology": (
                "Exact normalized skill matching. "
                "Match percentage is not selection probability."
            )
        }
