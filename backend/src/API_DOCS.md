# Memoria API Documentation

## Overview

The API allows you to start workflows, receive real-time updates via WebSocket, and provide clarifications during workflow execution.

**Base URL:** `http://localhost:8000`  
**API Version:** 0.1.0

---

## Table of Contents

- [Start Workflow Endpoint](#start-workflow)
- [WebSocket Stream Endpoint](#websocket-stream)
- [Submit Clarification Endpoint](#submit-clarification)
- [Workflow Flow](#workflow-flow)
- [Status Codes](#status-codes)
- [Notes](#notes)

---

## Workflow Endpoints

### Start Workflow

**Endpoint:** `POST /workflow/start`

**Description:**  
Initiates a new workflow instance and returns a unique workflow ID along with clarification questions if applicable.

**Parameters:**  
- `user_input` (string, required): The user's query or input for the workflow
- `ask_clarifications` (boolean, optional): Whether the workflow should ask clarification questions before proceeding

**Request Body:**
```json
{
  "user_input": "string",
  "ask_clarifications": true/false
  // Additional parameters to be defined
}
```

**Response Fields:**  
- `workflow_id` (string): UUID4 identifier for tracking this workflow
- `status` (string): Current status of the workflow (`"started"`)
- `clarification_question` (string|null): A clarification question if `ask_clarifications=true` and workflow needs clarification, otherwise `null`

**Sample Response:**
```json
{
  "workflow_id": "uuid4-string",
  "status": "started",
  "clarification_question": "string or null"
}
```

**Example in JavaScript:**
```javascript
fetch('http://localhost:8000/workflow/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    user_input: 'Analyze sales trends for Q3',
    ask_clarifications: true
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

### WebSocket Stream

**Endpoint:** `WS /workflow/ws/{workflow_id}`

**Description:**  
Establishes a WebSocket connection for bidirectional communication with the workflow.

**Parameters:**  
- `workflow_id` (string, required): The UUID returned from the start workflow endpoint

**Request Body:**  
N/A (WebSocket connection)

**Duplex Communication options (will be updated):**  

Server → Client Messages (JSON):
- Workflow progress updates
- Intermediate results
- Final answer when workflow completes

Client → Server Messages (JSON):
- Request the final answer (skip remaining events)
- Send control signals

**Sample Response:**
```json
{
  "type": "event",
  "data": {}
  // Structure to be defined
}
```

**Example in JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/workflow/ws/your-workflow-id');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Request final answer
ws.send(JSON.stringify({ action: 'get_final_answer' }));
```

---

### Submit Clarification

**Endpoint:** `POST /workflow/input/{workflow_id}`

**Description:**  
Submit an answer to a clarification question from the workflow, if applicable.

**Parameters:**  
- `workflow_id` (string, required): The UUID of the workflow
- `clarification_answer` (string, required): User's response to the clarification question

**Request Body:**
```json
{
  "clarification_answer": "string"
  // Additional parameters to be defined
}
```

**Response Fields:**  
- `workflow_id` (string): The workflow identifier
- `status` (string): `"ok"` if workflow can proceed, `"needs_clarification"` if more input is needed
- `clarification_question` (string|null): Next clarification question if `status="needs_clarification"`
- `workflow_status` (string): Current workflow state (`"running"`, `"completed"`, etc.)

**Sample Response:**
```json
{
  "workflow_id": "uuid4-string",
  "status": "ok",
  "clarification_question": "string or null",
  "workflow_status": "running"
}
```

**Example in JavaScript:**
```javascript
fetch(`http://localhost:8000/workflow/input/your-workflow-id`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    clarification_answer: 'Focus on the Southeast region'
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Workflow Flow

### Basic Workflow (No Clarifications)

1. Client calls `POST /workflow/start` with `ask_clarifications=false`
2. Server returns `workflow_id` immediately
3. Client connects to `WS /workflow/ws/{workflow_id}`
4. Server streams updates as workflow progresses
5. Server sends final answer when complete

### Interactive Workflow (With Clarifications)

1. Client calls `POST /workflow/start` with `ask_clarifications=true`
2. Server returns `workflow_id` and a `clarification_question`
3. Client submits answer via `POST /workflow/input/{workflow_id}`
4. Server may return another clarification question or status `"ok"`
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