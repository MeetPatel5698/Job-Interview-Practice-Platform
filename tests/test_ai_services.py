import os
import unittest

from services.ai_services import (
    ROLE_QUESTION_BANK,
    evaluate_interview_answer,
    generate_interview_question,
    generate_interview_questions,
    summarize_interview_session,
)


class AIServiceFallbackTests(unittest.TestCase):
    def setUp(self):
        self.original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.original_model = os.environ.pop("OPENAI_MODEL", None)

    def tearDown(self):
        if self.original_api_key is not None:
            os.environ["OPENAI_API_KEY"] = self.original_api_key

        if self.original_model is not None:
            os.environ["OPENAI_MODEL"] = self.original_model

    def test_generate_questions_use_role_specific_fallback_without_api_key(self):
        questions = generate_interview_questions("Web Developer")

        self.assertGreaterEqual(len(questions), 3)
        self.assertIn(questions[0], ROLE_QUESTION_BANK["Web Developer"])

    def test_generate_questions_include_description_focus_without_api_key(self):
        questions = generate_interview_questions(
            "Web Developer",
            "Build Flask applications with REST APIs, SQL databases, and dashboards.",
            count=5,
        )

        self.assertEqual(len(questions), 5)
        self.assertTrue(any("Flask" in question for question in questions))

    def test_generate_question_rotates_by_question_number_without_api_key(self):
        first_question = generate_interview_question(
            "Web Developer",
            "Build Flask applications with SQL dashboards.",
            question_number=0,
        )
        second_question = generate_interview_question(
            "Web Developer",
            "Build Flask applications with SQL dashboards.",
            question_number=1,
        )

        self.assertNotEqual(first_question, second_question)

    def test_evaluate_answer_returns_feedback_and_score_without_api_key(self):
        feedback, score, improvements = evaluate_interview_answer(
            "Software Developer",
            "Describe a project where you had to debug a difficult issue.",
            (
                "In a class project, I found a login bug by checking the Flask route, "
                "the database query, and the browser request. I fixed the query, tested "
                "the result with my team, and learned to verify each layer before changing code."
            ),
            "Use Flask, SQL, and team-based debugging.",
        )

        self.assertIsInstance(feedback, str)
        self.assertGreater(len(feedback), 20)
        self.assertGreater(len(improvements), 20)
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 10)

    def test_empty_answer_gets_low_score(self):
        feedback, score, improvements = evaluate_interview_answer(
            "Data Analyst",
            "How would you clean a dataset?",
            "",
        )

        self.assertIn("provide an answer", feedback)
        self.assertIn("Write", improvements)
        self.assertEqual(score, 1)

    def test_session_summary_returns_strengths_weaknesses_and_improvements(self):
        strengths, weaknesses, improvements = summarize_interview_session(
            "Software Developer",
            "Build Flask APIs with SQL databases.",
            "Built a Flask project with SQLite.",
            [
                {
                    "question": "How did you debug a difficult issue?",
                    "answer": "I checked logs and fixed a SQL query.",
                    "score": 7,
                    "feedback": "Good practical example.",
                    "improvements": "Add measurable impact.",
                }
            ],
        )

        self.assertGreater(len(strengths), 20)
        self.assertGreater(len(weaknesses), 20)
        self.assertGreater(len(improvements), 20)


if __name__ == "__main__":
    unittest.main()
