# Memoria API Documentation

## Overview

The API allows you to start workflows, receive real-time updates via WebSocket, and provide clarifications during workflow execution.

**Base URL:** `http://localhost:8000`  
**API Version:** 0.1.0

---

## Table of Contents

- [Execute Workflow Endpoint](#execute-workflow)
- [WebSocket Stream Endpoint](#websocket-stream)
- [AI Answer Endpoint](#ai-answer)
- [Workflow Flow](#workflow-flow)
- [Status Codes](#status-codes)
- [Notes](#notes)

---

## Workflow Endpoints

### Execute Workflow

**Endpoint:** `POST /workflow/execute`

**Description:**  
Executes a workflow step. When no `workflow_id` is provided, a new conversation is started. When `workflow_id` is present, the call continues an existing conversation. The same endpoint accepts clarification answers as regular user input.

**Parameters:**  

**Parameters:**  
- `workflow_id` (string, required): The UUID returned from the execute workflow endpoint

**Server → Client Messages (JSON):**
- Workflow progress updates
- Intermediate results
- Final answer when workflow completes

**Client → Server Messages (JSON):**
- Request the final answer (skip remaining events)
- Send control signals

**Sample Response:**
```json
{
  "type": "event",
  "data": {}
}
```

---

### AI Answer

**Endpoint:** `POST /workflow/ai-answer`

**Description:**  
Stores the AI agent's final response and reasoning for bookkeeping so downstream systems can reconstruct conversation history.

**Parameters:**  
- `workflow_id` (string, required): The workflow identifier
- `message_id` (string, required): The message that produced the final answer
- `response` (string, required): The final AI response content
- `reasoning` (string, optional): Reasoning tokens or trace
- `tool_calls` (string, optional): History of tool calls and actions taken

**Request Body:**
```json
{
  "workflow_id": "uuid4-string",
  "message_id": "uuid4-string",
  "response": "string",
  "reasoning": "string (optional)",
  "tool_calls": "string (optional)"
}
```

**Response Fields:**  
- `status` (string): Always `"ok"`

**Sample Response:**
```json
{
  "status": "ok"
}
```

**Example in JavaScript:**
```javascript
fetch('http://localhost:8000/workflow/ai-answer', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    workflow_id: 'uuid4-string',
    message_id: 'uuid4-string',
    response: 'Here is the final answer',
    reasoning: 'Model reasoning trace',
    tool_calls: 'Executed search, summarized results'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Workflow Flow

### Basic Workflow (No Clarifications)

1. Client calls `POST /workflow/execute` with `ask_clarifications=false` (omit `workflow_id` for new conversation)
2. Server returns `workflow_id`, `message_id`, and current workflow status immediately
3. Client connects to `WS /workflow/ws/{workflow_id}`
4. Server streams updates as workflow progresses
5. Server sends final answer when complete

### Continuing an Existing Conversation

1. Client calls `POST /workflow/execute` with the existing `workflow_id` and new `user_input`
2. Server retrieves past conversation history and state from database
3. Server returns same `workflow_id` with a new `message_id`
4. Client connects to `WS /workflow/ws/{workflow_id}`
5. Server processes new message with full conversation context
6. Server streams updates and final answer

### Interactive Workflow (With Clarifications)

1. Client calls `POST /workflow/execute` with `ask_clarifications=true`
2. Server returns `workflow_id`, `message_id`, and a `clarification_question`
3. Client submits the clarification answer via `POST /workflow/execute` with the same `workflow_id`
4. Server may return another clarification question or proceed
5. Once clarifications are complete, client connects to WebSocket
6. Server streams updates and final answer

---

## Status Codes

- `200 OK` - Successful request
- `201 Created` - Workflow successfully created
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Workflow not found
- `500 Internal Server Error` - Server error

---

## Notes

- Workflow state and events are stored in PostgreSQL
- WebSocket connections should handle reconnection logic
- Workflow IDs are UUID4 format
- JSON contracts for WebSocket messages and request/response bodies will be refined as development progresses

---

**Last Updated:** January 14, 2026 5:12 pm est by Hussain