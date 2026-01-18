---
agent: agent
---
Whenever you're interacting with PostgreSQL databases using SQLAlchemy, ensure the following: 
1. Use SQLAlchemy 2.0 Syntax like mapped_column and Mapped[] type hints and other query constructs await session.execute(select(...)) and scalar() etc. our app is async and should expect to run at scale with many concurrent requests.
2. Use Global AsyncEngine per application life-cycle.
3. Use a session factory to generate AsyncSession instances. This decouples database configuration from your business logic.
4. Short-lived "Unit of Work": A session should only live for the duration of a DB operation.
5. Never put await llm_call() or any external API request inside a db_session block. This leads to pool exhaustion and we are building for scale. 
6. Use async with session.begin(): to automatically handle BEGIN, COMMIT, and ROLLBACK on errors
7. with_for_update(): Apply this to SELECT statements when an agent is about to modify a row. (Pessimistic Locking)
8. For UI/Dashboard fetches, updates sent to client from fastapi, use standard select() without locks.
9. Carefully consider when a re-fetch from the DB is necessary to ensure data consistency, don't over rely on python objects in memory. Know that given your limit context, you can not determine the full state of the DB or order of operations. 
10. MutableDict.as_mutable(JSONB): When defining the model, wrap the JSONB column. Without this, SQLAlchemy cannot detect changes made to internal keys.
11. Use .bool_op("||") for shallow merges. Ideal for adding top-level metadata or appending to history arrays without fetching the whole object. not ideal for deep merges. jsonb_set(): Use this for deep, nested updates within JSONB columns.
12. If you see we can utilize a GIN index, expression index or other indices based on query patterns in existing code or the code you are adding, suggest them to me proactively (without writing the code, only write that once I approve). 
13. selectinload(): Use this for One-to-Many relationships. session.flush(): Use to send changes to the DB and receive auto-generated IDs (like a new Log.id) without committing the transaction or releasing row locks.
14. session.refresh(): Use to manually re-load attributes on an object if they were modified by the DB (like timestamps or default values) or if you need to load a relationship after the initial query.
15. Wrap your SQLAlchemy logic in dedicated Service classes when it makes sense to make code more modular and testable.