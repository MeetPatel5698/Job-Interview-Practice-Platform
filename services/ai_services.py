import json
import os
import re
from typing import Any

from openai import OpenAI, OpenAIError


DEFAULT_MODEL = "gpt-5.4-mini"

ROLE_QUESTION_BANK = {
    "Software Developer": [
        "Describe a project where you had to debug a difficult issue. What was your process and what did you learn?",
        "How do you decide between writing a quick solution and taking time to design a more maintainable one?",
        "Tell me about a time you worked with version control on a team project. How did you handle conflicts or changes?",
    ],
    "Web Developer": [
        "Walk me through how you would build a responsive web page from a design mockup.",
        "How would you improve the performance of a slow-loading web page?",
        "Describe how you handle form validation and error messages in a web application.",
    ],
    "Data Analyst": [
        "Tell me about a time you found an insight in data and explained it to a non-technical audience.",
        "How would you clean and validate a dataset before creating a report?",
        "Describe a dashboard or report you would build to help a team make better decisions.",
    ],
}

GENERIC_QUESTIONS = [
    "Tell me about a recent project that demonstrates your skills for this role.",
    "Describe a challenge you faced in a team setting and how you handled it.",
    "What strengths would you bring to this position, and where are you still improving?",
]

EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "string",
            "description": "Clear interview coaching feedback in 3 to 5 sentences.",
        },
        "improvements": {
            "type": "string",
            "description": "Specific improvement advice in 2 to 4 sentences.",
        },
        "score": {
            "type": "integer",
            "description": "Whole-number interview answer score from 1 to 10.",
        },
    },
    "required": ["feedback", "improvements", "score"],
    "additionalProperties": False,
}

QUESTION_SET_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "description": "Mock interview questions tailored to the role and job description.",
            "items": {
                "type": "string",
            },
        },
    },
    "required": ["questions"],
    "additionalProperties": False,
}

SESSION_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {
            "type": "string",
            "description": "Main strengths shown across the interview session.",
        },
        "weaknesses": {
            "type": "string",
            "description": "Main weaknesses or gaps shown across the interview session.",
        },
        "improvements": {
            "type": "string",
            "description": "Practical improvement advice for future interviews.",
        },
    },
    "required": ["strengths", "weaknesses", "improvements"],
    "additionalProperties": False,
}


def generate_interview_questions(
    role: str,
    role_description: str = "",
    count: int = 5,
) -> list[str]:
    role = _clean_role(role)
    role_description = _clean_text(role_description)
    count = max(3, min(8, int(count)))
    client = _get_client()

    if client is None:
        return fallback_questions(role, role_description, count)

    try:
        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are PrepBot, a practical mock interview coach. "
                "Generate realistic interview practice questions for students and junior candidates. "
                "Use the role description to make the questions job-related instead of generic."
            ),
            input=(
                f"Role: {role}\n"
                f"Role description: {role_description or 'No extra description provided.'}\n\n"
                f"Generate exactly {count} concise mock interview questions. "
                "Mix technical, behavioral, and scenario-based questions. "
                "Each question should be answerable in 2 to 4 minutes and should connect to the role description."
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "interview_questions",
                    "schema": QUESTION_SET_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=700,
            temperature=0.7,
        )

        result = json.loads(response.output_text)
        questions = _normalize_questions(result.get("questions"), count)
        if questions:
            return questions
    except (OpenAIError, json.JSONDecodeError, TypeError, ValueError):
        pass

    return fallback_questions(role, role_description, count)


def generate_interview_question(
    role: str,
    role_description: str = "",
    question_number: int = 0,
    resume_text: str = "",
) -> str:
    role = _clean_role(role)
    role_description = _clean_text(role_description)
    resume_text = _clean_text(resume_text)
    question_number = max(0, int(question_number))
    client = _get_client()

    if client is None:
        return fallback_question(role, role_description, question_number, resume_text)

    try:
        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are PrepBot, a practical mock interview coach. "
                "Generate one realistic interview question at a time for a student or junior candidate. "
                "Use the role description to make the question job-related instead of generic."
            ),
            input=(
                f"Role: {role}\n"
                f"Role description: {role_description or 'No extra description provided.'}\n"
                f"Candidate resume/context: {_shorten_context(resume_text)}\n"
                f"Question number in this mock interview: {question_number + 1}\n\n"
                "Generate exactly one concise mock interview question. "
                "If resume context is available, ask a question that helps the candidate connect their real experience to the role. "
                "Do not include numbering, explanations, or answer hints. "
                "Make the question answerable in 2 to 4 minutes."
            ),
            max_output_tokens=140,
            temperature=0.7,
        )

        question = _clean_text(response.output_text)
        if question:
            return question
    except (OpenAIError, ValueError):
        pass

    return fallback_question(role, role_description, question_number, resume_text)


def evaluate_interview_answer(
    role: str,
    question: str,
    answer: str,
    role_description: str = "",
    resume_text: str = "",
) -> tuple[str, int, str]:
    role = _clean_role(role)
    question = _clean_text(question) or fallback_question(role)
    answer = _clean_text(answer)
    role_description = _clean_text(role_description)
    resume_text = _clean_text(resume_text)

    if not answer:
        return (
            "Please provide an answer before requesting feedback. A strong response should include a clear example, your actions, and the result.",
            1,
            "Write at least a short answer that includes what happened, what you did, and what changed because of your work.",
        )

    client = _get_client()
    if client is None:
        return fallback_evaluation(role, question, answer, role_description, resume_text)

    try:
        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are PrepBot, an interview coach. Evaluate answers fairly for junior candidates. "
                "Be specific, constructive, and concise. Do not invent experience the candidate did not mention."
            ),
            input=(
                f"Role: {role}\n"
                f"Role description: {role_description or 'No extra description provided.'}\n"
                f"Candidate resume/context: {_shorten_context(resume_text)}\n"
                f"Interview question: {question}\n"
                f"Candidate answer: {answer}\n\n"
                "Return feedback, improvements, and a score from 1 to 10. Reward clear examples, role-specific detail, "
                "structured communication, concrete results, and direct connection to the role description. "
                "If resume context is available, suggest how the candidate can use their real experience more effectively. "
                "Penalize vague, incomplete, or off-topic answers."
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "interview_evaluation",
                    "schema": EVALUATION_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=500,
            temperature=0.2,
        )

        result = json.loads(response.output_text)
        return _normalize_evaluation(result)
    except (OpenAIError, json.JSONDecodeError, TypeError, ValueError):
        return fallback_evaluation(role, question, answer, role_description, resume_text)


def generate_answer_suggestion(
    role: str,
    role_description: str,
    question: str,
    resume_text: str = "",
) -> str:
    role = _clean_role(role)
    role_description = _clean_text(role_description)
    question = _clean_text(question)
    resume_text = _clean_text(resume_text)
    client = _get_client()

    if client is None:
        return fallback_answer_suggestion(role, role_description, question, resume_text)

    try:
        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are PrepBot, an interview coach. Create a realistic sample answer that helps the candidate learn. "
                "Base it only on the resume/context provided. Do not invent specific companies, dates, or achievements."
            ),
            input=(
                f"Role: {role}\n"
                f"Role description: {role_description or 'No extra description provided.'}\n"
                f"Candidate resume/context: {_shorten_context(resume_text)}\n"
                f"Interview question: {question}\n\n"
                "Write a concise sample answer in first person using the candidate's actual experience where possible. "
                "If resume context is thin, give a safe structure and say what detail the candidate should add."
            ),
            max_output_tokens=350,
            temperature=0.4,
        )

        suggestion = _clean_text(response.output_text)
        if suggestion:
            return suggestion
    except (OpenAIError, ValueError):
        pass

    return fallback_answer_suggestion(role, role_description, question, resume_text)


def summarize_interview_session(
    role: str,
    role_description: str,
    resume_text: str,
    answers: list[dict[str, Any]],
) -> tuple[str, str, str]:
    role = _clean_role(role)
    role_description = _clean_text(role_description)
    resume_text = _clean_text(resume_text)
    client = _get_client()

    if client is None:
        return fallback_session_summary(role, answers)

    try:
        answer_lines = []
        for index, answer in enumerate(answers, start=1):
            answer_lines.append(
                f"Q{index}: {answer.get('question')}\n"
                f"Answer: {answer.get('answer')}\n"
                f"Score: {answer.get('score')}/10\n"
                f"Feedback: {answer.get('feedback')}\n"
                f"Improvements: {answer.get('improvements')}"
            )

        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are PrepBot, an interview coach. Summarize a completed mock interview for a student or junior candidate. "
                "Be constructive, specific, and practical."
            ),
            input=(
                f"Role: {role}\n"
                f"Role description: {role_description or 'No extra description provided.'}\n"
                f"Candidate resume/context: {_shorten_context(resume_text)}\n\n"
                "Completed answers:\n"
                + "\n\n".join(answer_lines)
                + "\n\nReturn strengths, weaknesses, and improvements for the final results page."
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "interview_session_summary",
                    "schema": SESSION_SUMMARY_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=600,
            temperature=0.3,
        )

        result = json.loads(response.output_text)
        return _normalize_session_summary(result)
    except (OpenAIError, json.JSONDecodeError, TypeError, ValueError):
        return fallback_session_summary(role, answers)


def fallback_question(
    role: str,
    role_description: str = "",
    question_number: int = 0,
    resume_text: str = "",
) -> str:
    combined_context = " ".join(
        value
        for value in [role_description, resume_text]
        if value
    )
    questions = fallback_questions(role, combined_context, count=8)
    index = max(0, int(question_number)) % len(questions)
    return questions[index]


def fallback_questions(
    role: str,
    role_description: str = "",
    count: int = 5,
) -> list[str]:
    role = _clean_role(role)
    role_description = _clean_text(role_description)
    questions = list(ROLE_QUESTION_BANK.get(role, GENERIC_QUESTIONS))

    for term in _extract_focus_terms(role_description):
        questions.append(
            f"How have you used {term} in a project or work situation, and what result did you achieve?"
        )
        questions.append(
            f"If this {role} position required {term}, how would you approach that responsibility in your first month?"
        )

    questions.append(
        f"Based on this role description, which requirement best matches your experience as a {role}, and why?"
    )
    questions.append(
        f"What skill from the role description would you need to strengthen, and how are you working on it?"
    )

    unique_questions = []
    for question in questions:
        if question not in unique_questions:
            unique_questions.append(question)

    return unique_questions[:count]


def fallback_evaluation(
    role: str,
    question: str,
    answer: str,
    role_description: str = "",
    resume_text: str = "",
) -> tuple[str, int, str]:
    del question

    words = answer.split()
    word_count = len(words)
    lower_answer = answer.lower()
    focus_terms = _extract_focus_terms(
        " ".join([role_description, resume_text])
    )
    score = 4

    if word_count >= 80:
        score += 3
    elif word_count >= 40:
        score += 2
    elif word_count >= 20:
        score += 1

    if any(term in lower_answer for term in ["example", "project", "result", "impact", "learned"]):
        score += 1

    if any(term in lower_answer for term in ["team", "user", "client", "customer", "stakeholder"]):
        score += 1

    if role.lower().split()[0] in lower_answer:
        score += 1

    if any(term.lower() in lower_answer for term in focus_terms):
        score += 1

    score = _clamp_score(score)

    feedback = (
        "Your answer gives PrepBot enough information to evaluate the basic direction of your response. "
        f"For a {role} interview, connect your example more directly to the skills the role uses every day."
    )

    improvements = (
        "Use a clearer structure: situation, task, action, and result. "
        "Add one concrete technical or workplace detail from the role description or resume, then finish with what improved because of your work."
    )

    return feedback, score, improvements


def fallback_answer_suggestion(
    role: str,
    role_description: str,
    question: str,
    resume_text: str = "",
) -> str:
    focus_terms = _extract_focus_terms(
        " ".join([role_description, resume_text])
    )
    detail = focus_terms[0] if focus_terms else "a relevant project or class experience"

    return (
        f"For this {role} question, start with a real example involving {detail}. "
        "Use this structure: briefly describe the situation, explain the action you personally took, "
        "then finish with the result or lesson learned. Add a specific detail from your resume so the answer sounds like your own experience."
    )


def fallback_session_summary(
    role: str,
    answers: list[dict[str, Any]],
) -> tuple[str, str, str]:
    scores = [
        int(answer.get("score") or 0)
        for answer in answers
    ]
    average = sum(scores) / len(scores) if scores else 0

    if average >= 8:
        strengths = f"You showed strong readiness for a {role} interview, especially in answer completeness and role alignment."
        weaknesses = "The main remaining gap is polishing answers so each one has a clear result or measurable impact."
    elif average >= 6:
        strengths = f"You showed a workable foundation for a {role} interview and answered enough to evaluate your thinking."
        weaknesses = "Several answers need more specific examples, stronger structure, and clearer connection to the job description."
    else:
        strengths = "You completed the session and identified what needs practice, which is a useful first step."
        weaknesses = f"Your answers need more detail, stronger examples, and clearer {role} skills before a real interview."

    improvements = (
        "Use the STAR structure for every answer: situation, task, action, result. "
        "Before the next session, prepare two or three resume-based examples that show technical skills, teamwork, and problem solving."
    )

    return strengths, weaknesses, improvements


def _get_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    return OpenAI(api_key=api_key)


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def _clean_role(role: str) -> str:
    return _clean_text(role) or "Software Developer"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return text


def _shorten_context(value: str, limit: int = 2500) -> str:
    text = _clean_text(value)
    if not text:
        return "No resume/context provided."

    return text[:limit]


def _normalize_evaluation(result: dict[str, Any]) -> tuple[str, int, str]:
    feedback = _clean_text(result.get("feedback"))
    improvements = _clean_text(result.get("improvements"))
    score = _clamp_score(result.get("score", 1))

    if not feedback:
        feedback = "Your answer was evaluated, but the feedback response was empty. Try adding a clearer example and role-specific details."

    if not improvements:
        improvements = "Add a specific example, explain your personal actions, and connect the result back to the role description."

    return feedback, score, improvements


def _normalize_session_summary(result: dict[str, Any]) -> tuple[str, str, str]:
    strengths = _clean_text(result.get("strengths"))
    weaknesses = _clean_text(result.get("weaknesses"))
    improvements = _clean_text(result.get("improvements"))

    if not strengths:
        strengths = "You completed the mock interview and provided enough answers to review your performance."

    if not weaknesses:
        weaknesses = "Some answers could use clearer examples, stronger structure, or closer connection to the role."

    if not improvements:
        improvements = "Practice using the STAR method and include more concrete details from your projects or resume."

    return strengths, weaknesses, improvements


def _normalize_questions(value: Any, count: int) -> list[str]:
    if not isinstance(value, list):
        return []

    questions = []
    for item in value:
        question = _clean_text(item)
        if question and question not in questions:
            questions.append(question)

    return questions[:count]


def _extract_focus_terms(role_description: str) -> list[str]:
    stop_words = {
        "about",
        "ability",
        "applications",
        "build",
        "candidate",
        "description",
        "develop",
        "experience",
        "familiar",
        "knowledge",
        "preferred",
        "required",
        "responsibilities",
        "responsibility",
        "skills",
        "strong",
        "team",
        "using",
        "with",
        "work",
        "working",
    }

    terms = []
    for term in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", role_description):
        normalized = term.strip(".,;:()[]{}")
        if normalized.lower() in stop_words:
            continue

        if normalized not in terms:
            terms.append(normalized)

    return terms[:4]


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 1

    return max(1, min(10, score))
