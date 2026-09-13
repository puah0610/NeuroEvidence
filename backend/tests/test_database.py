from app.models import FeedbackRequest


def test_feedback_and_empty_summary(database) -> None:
    feedback_id = database.save_feedback(
        FeedbackRequest(trace_id="missing-trace", helpful=False, issue_type="citation_issue")
    )
    assert feedback_id
    summary = database.summary()
    assert summary.feedback_count == 1
    assert summary.helpful_rate == 0.0

