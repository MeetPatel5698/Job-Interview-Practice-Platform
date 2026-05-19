# PrepBot – AI-Powered Mock Interview Practice Platform

## Project Overview

PrepBot is a web-based AI-powered interview practice platform designed to help students, graduates, and job seekers improve their interview skills through realistic mock interview simulations.

The platform allows users to practice technical and HR interviews, receive AI-generated feedback, track performance history, and build confidence before real interviews.

---

# Problem Statement

Many students and job seekers struggle during interviews because they lack:
- Real interview experience
- Personalized feedback
- Communication confidence
- Technical interview preparation

Most existing interview preparation platforms are either expensive or provide only static interview questions without intelligent analysis or feedback.

PrepBot aims to solve this problem by providing an interactive and affordable AI-powered interview practice experience.

---

# Features

## Current / Planned Features

- User Signup & Login System
- Role-Based Interview Selection
- AI-Generated Interview Questions
- Technical and HR Interview Modes
- Text-Based Answer Submission
- AI Feedback and Scoring
- Interview Performance Dashboard
- Interview History Tracking
- Responsive Frontend UI
- Database Integration
- GitHub Team Collaboration

---

# Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web framework |
| SQLite | Database management |
| HTML/CSS | Frontend structure and styling |
| JavaScript | Frontend interactivity |
| OpenAI API | AI-generated questions and feedback |
| Git & GitHub | Version control and collaboration |

---

# Project Structure

```text
prepbot/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   └── interview.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
├── models/
│   └── models.py
│
├── routes/
│   └── routes.py
│
├── services/
│   └── ai_service.py
│
└── venv/
```

---


# Database Design

The platform includes the following main database tables:

- Users
- Interviews
- Questions
- Responses

These tables help manage:
- User accounts
- Interview sessions
- AI-generated questions
- User answers and scores

---

# AI Integration

PrepBot uses AI services to:
- Generate interview questions dynamically
- Analyze user responses
- Provide interview feedback
- Suggest improvements
- Generate interview scores

---

# Team Members

| Name | Responsibility |
|---|---|
| Smit Parmar | Backend Development & Database Integration |
| Meetkumar Patel | Frontend UI Design & User Interface |
| Karmkumar Patel | AI Integration, Testing & GitHub Management |

---

# Future Enhancements

Future versions of PrepBot may include:
- Voice-based interview practice
- Speech-to-text support
- Advanced AI evaluation
- Resume analysis
- Video interview simulation
- Performance analytics dashboard
- Mobile application support

---

# Out of Scope

The following features are currently out of scope:
- Emotion detection
- Multiplayer interview system
- Real recruiter integration
- Advanced speech recognition
- Mobile application

---

# License

This project is developed for educational purposes as part of a software development course project.

---

# Conclusion

PrepBot aims to provide an accessible and intelligent interview preparation platform that helps users practice interviews in a realistic environment while receiving personalized AI-driven feedback and improvement suggestions.
