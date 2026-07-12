# Jarvis – Claude Code Master Project

## Goal

Build **Jarvis**, a personal operating system, while learning **Claude Code** and **spec-driven development**.

The emphasis is on:
- Writing specifications first
- Building incrementally
- Using Claude Code Skills as specialized experts
- Producing production-quality architecture

---

# Vision

Jarvis is not just a chatbot.

It is a modular application with an AI interface that can:
- Remember information
- Manage tasks and projects
- Organize documents and notes
- Assist with software development
- Plan trips
- Build automations

---

# Development Philosophy

Every feature follows the same lifecycle:

Idea
→ Epic
→ User Stories
→ Functional Requirements
→ Domain Model
→ API Design
→ Database Design
→ UI
→ Implementation
→ Tests
→ Review
→ Documentation

Never skip directly to implementation.

---

# Repository Structure

```text
jarvis/
  specs/
    epics/
    stories/
  skills/
    requirements-analyst/
    architect/
    backend-developer/
    frontend-developer/
    database-designer/
    test-engineer/
    reviewer/
  backend/
  frontend/
  docs/
```

---

# Claude Code Skills

## Requirements Analyst
Produces epics, user stories, acceptance criteria and edge cases.

## Architect
Defines architecture, modules and boundaries.

## Domain Designer
Defines entities and relationships.

## API Designer
Designs REST/OpenAPI.

## Database Designer
Designs schema and migrations.

## Backend Developer
Implements backend.

## Frontend Developer
Implements UI.

## Test Engineer
Creates automated tests.

## Reviewer
Reviews code quality, security and architecture.

---

# MVP Roadmap

## Phase 1
- Authentication
- Memory
- Notes
- Tasks
- Search

## Phase 2
- Projects
- Knowledge Base
- Documents

## Phase 3
- Calendar
- Travel
- Recipes
- Shopping

## Phase 4
- AI orchestration
- Integrations
- Automation engine

---

# Definition of Done

Every feature must include:
- Specification
- Acceptance criteria
- Architecture updates
- Tests
- Documentation
- Review

---

# First Epic

Implement the Memory module.

Capabilities:
- Create memory
- Update memory
- Delete memory
- Search memories
- Tag memories
- Link related memories
- AI retrieval

This module will become the foundation for all future AI interactions.
