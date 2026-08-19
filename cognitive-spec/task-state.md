# Task and Session State Contract

Task/session operational state is a caller- or session-scoped runtime projection.
Durable session records are compressed knowledge, not raw conversation logs.

Session chunks use typed boundaries such as summary, goal, observation,
hypothesis, decision, action, outcome, insight, and handoff. Explicit relations
(`goal -> caused -> decision`, `decision -> predicted -> outcome`, and promotion
links) are indexed separately from chunk content.

Task creation or completion that changes durable knowledge must preserve caller
provenance and pass the existing single-writer, validation, secret, and git
history gates.
