from __future__ import annotations

from app.schemas.job import (
    JobAnalysis,
    JobLearningContext,
    JobLearningRecommendation,
    RequiredTopic,
)


_KNOWN_TOPICS = {
    "python": "Python",
    "postgresql": "PostgreSQL",
    "system design": "System Design",
}


def build_job_learning_context(job_id: str, analysis: JobAnalysis) -> JobLearningContext:
    """Build bounded learning context from job requirements without inference."""
    required_topics = []
    for source_text in analysis.extracted_requirements[:50]:
        normalized = source_text.strip().casefold()
        required_topics.append(
            RequiredTopic(
                topic=_KNOWN_TOPICS.get(normalized),
                source_text=source_text,
            )
        )
    return JobLearningContext(
        job_id=job_id,
        required_topics=required_topics,
        proficiency_status="unknown",
    )


def recommend_job_learning(context: JobLearningContext) -> JobLearningRecommendation:
    """Create a deterministic learning recommendation from approved job context."""
    recommendations: list[str] = []
    next_steps: list[str] = []

    for required_topic in context.required_topics:
        if required_topic.topic is None:
            recommendations.append(
                "Review the requirement: "
                f"'{required_topic.source_text}'; current data does not identify "
                "a specific technical topic."
            )
            next_steps.append("Review the requirement for a more specific learning topic.")
            continue

        recommendations.append(
            f"Study {required_topic.topic} fundamentals and practical usage "
            "relevant to this requirement."
        )
        next_steps.append(f"Review {required_topic.topic} and practice with a small project.")

    if not context.required_topics:
        recommendations.append("No learning-specific topics were identified in the job context.")
        next_steps.append("Review the job requirements for more specific learning topics.")

    return JobLearningRecommendation(
        job_id=context.job_id,
        required_topics=[topic.model_copy(deep=True) for topic in context.required_topics],
        proficiency_status=context.proficiency_status,
        recommendations=recommendations[:20],
        next_steps=next_steps[:20],
    )
