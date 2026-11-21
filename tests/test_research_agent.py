from research_agent import InternshipResearchAgent


def sample_job():
    return {
        "company": "Example Labs",
        "role": "AI / ML Intern",
        "source_url": "https://example.com/jobs/ai-intern",
        "extraction_status": "success",
        "required_skills": [
            "Python",
            "Scikit-learn",
            "Machine Learning concepts (regression, classification, clustering, model evaluation)",
            "Personal laptop",
        ],
        "foundational_ml_topics": [
            "Regression",
            "Classification",
            "Clustering",
            "Model evaluation",
        ],
        "eligibility": ["Currently pursuing a relevant degree"],
        "optional_skills": ["PyTorch"],
    }


def test_normalization_handles_aliases_and_whitespace():
    agent = InternshipResearchAgent([])
    assert agent.normalize_skill("  Scikit   Learn ") == "scikit-learn"
    assert agent.normalize_skill("SKLEARN") == "scikit-learn"


def test_parent_requirement_and_equipment_are_not_double_counted():
    job = sample_job()
    agent = InternshipResearchAgent([job])
    assert agent.get_requirements(job) == [
        "Python", "Scikit-learn", "Regression", "Classification",
        "Clustering", "Model evaluation",
    ]
    assert agent.get_other_requirements(job) == ["Personal laptop"]


def test_match_score_uses_distinct_technical_requirements():
    agent = InternshipResearchAgent([sample_job()])
    report = agent.analyze(["Python", "NumPy", "Regression", "Classification"])
    result = report["ranked_jobs"][0]
    assert result["total_requirements"] == 6
    assert result["match_percentage"] == 50.0
    assert result["matched_skills"] == ["Python", "Regression", "Classification"]
    assert result["other_requirements"] == ["Personal laptop"]


def test_eligibility_is_returned_separately():
    agent = InternshipResearchAgent([sample_job()])
    result = agent.compare_job(sample_job(), {"python"})
    assert result["eligibility_requirements"] == ["Currently pursuing a relevant degree"]


def test_optional_skills_are_reported_but_not_in_score():
    agent = InternshipResearchAgent([sample_job()])
    result = agent.compare_job(sample_job(), {"python", "pytorch"})
    assert result["optional_skills_matched"] == ["PyTorch"]
    assert result["total_requirements"] == 6


def test_ineligible_extraction_is_skipped():
    job = sample_job()
    job["extraction_status"] = "failed"
    report = InternshipResearchAgent([job]).analyze(["Python"])
    assert report["analysis_summary"]["jobs_analyzed"] == 0
    assert report["analysis_summary"]["jobs_skipped"] == 1
