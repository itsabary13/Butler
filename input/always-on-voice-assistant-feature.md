# Feature: Always-On Voice Assistant

## Goal

Extend the existing Personal Butler so it becomes an always-available
voice assistant that can be reached from anywhere, remembers
conversations, and can perform actions such as creating calendar events.

This feature should integrate with the existing Skills architecture
without breaking current functionality.

------------------------------------------------------------------------

# High Level Requirements

The Personal Butler must become:

-   Always available (24/7)
-   Cloud hosted
-   Reachable from any device
-   Voice-first
-   Context aware
-   Long-term memory enabled
-   Action capable

The user should never need to connect to their personal computer.

The Butler must continue running even when the developer machine is
turned off.

------------------------------------------------------------------------

# Architecture

Current architecture already contains:

-   Butler Orchestrator
-   Skills
-   Memory
-   Task Management
-   Calendar Skill

Extend it with:

``` text
Phone
    │
Voice Interface
    │
API Gateway
    │
Conversation Service
    │
Butler Orchestrator
    │
+----------------------+
| Existing Skills      |
+----------------------+
        │
Memory Layer
        │
Database
```

------------------------------------------------------------------------

# Voice Interface

Support voice conversations.

Required capabilities:

-   Speech to Text
-   Text to Speech
-   Streaming conversation
-   Interruptions
-   Multi-turn conversations

The user should be able to speak naturally.

------------------------------------------------------------------------

# Remote Availability

The Butler must be deployable on a cloud server.

Requirements:

-   Docker deployment
-   Docker Compose
-   Optional Kubernetes deployment
-   HTTPS
-   Reverse Proxy
-   Authentication

The service must survive server restarts.

------------------------------------------------------------------------

# Multi Device Support

Design the communication layer so multiple clients can connect.

Examples:

-   Mobile App
-   Telegram
-   WhatsApp
-   Web UI
-   Future Smart Speaker

The Conversation Service should hide transport-specific details from the
Butler.

------------------------------------------------------------------------

# Conversation Service

Responsible for:

-   Maintaining conversation sessions
-   Tracking active conversations
-   Streaming responses
-   Voice session management
-   User identification

------------------------------------------------------------------------

# Memory Integration

Implement:

## Short-Term Memory

-   Current conversation
-   Recent messages
-   Temporary context

Lifetime: several hours.

## Long-Term Memory

Store only meaningful information:

-   User preferences
-   Relationships
-   Projects
-   Recurring tasks
-   Habits
-   Important dates
-   Facts learned over time

Each memory should include:

-   Timestamp
-   Confidence
-   Source
-   Category
-   Importance score

------------------------------------------------------------------------

# Calendar Integration

Support natural language:

-   Create
-   Update
-   Delete
-   Query availability

Examples:

-   Schedule dinner tomorrow
-   Move my meeting
-   Cancel my dentist appointment
-   Find a free hour next Tuesday

------------------------------------------------------------------------

# Confirmation Rules

Require confirmation for destructive actions such as deleting or moving
meetings.

Allow automatic confirmation for reminders and simple personal events.

------------------------------------------------------------------------

# Voice Personality

The Butler should be:

-   Calm
-   Concise
-   Proactive
-   Context aware
-   Helpful

------------------------------------------------------------------------

# Background Tasks

Support proactive behaviors:

-   Morning summary
-   Upcoming meetings
-   Travel reminders
-   Follow-up reminders
-   Daily digest

------------------------------------------------------------------------

# Notifications

Support:

-   Push notifications
-   Telegram
-   Email

------------------------------------------------------------------------

# API

Expose APIs for:

-   Start conversation
-   Continue conversation
-   Upload audio
-   Stream responses
-   Calendar operations
-   Memory queries
-   Health endpoint

------------------------------------------------------------------------

# Security

-   JWT
-   OAuth support
-   Encrypted secrets
-   Encrypted memory storage
-   Audit logging

------------------------------------------------------------------------

# Configuration

Providers should be configurable:

-   Voice
-   LLM
-   Calendar
-   Notifications
-   Memory
-   Authentication

------------------------------------------------------------------------

# Future Extensibility

Support provider abstraction for:

-   OpenAI
-   Claude
-   Gemini
-   Local models

------------------------------------------------------------------------

# Acceptance Criteria

A user can be outside their home, open Telegram (or a future mobile
app), speak:

> Schedule lunch with David next Wednesday at one.

The Butler:

-   Understands the request
-   Creates the calendar event
-   Remembers David as a frequent contact if appropriate
-   Confirms the action
-   Stores only meaningful long-term memory

No personal computer is required.

------------------------------------------------------------------------

# Non-Functional Requirements

-   Highly modular
-   Skill-based architecture
-   Testable
-   Provider-independent
-   Cloud-native
-   Event-driven
-   Fully documented
-   Unit tests
-   Integration tests
-   Logging
-   Metrics
-   Health monitoring
