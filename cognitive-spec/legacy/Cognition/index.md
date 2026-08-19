# AI/Cognition — Index

The Living Brain v0.1 cognitive layer. Core: [[cognitive-architecture]].

## Modules

| File | Scope |
|---|---|
| [[cognitive-architecture]] | 3 layers, awake loop, constitution |
| [[perception-policy]] | Observation encoding, epistemic status |
| [[attention-and-salience]] | Salience score, attention gate |
| [[global-workspace]] | Cognitive event bus, working memory |
| [[goal-system]] | Goal levels, priority, lifecycle |
| [[decision-policy]] | Decision score, risk modes, reward |
| [[future-simulation]] | Option generation, branches, probability guard |
| [[world-model]] | Entity/edge schema, contradiction rule |
| [[self-model]] | Stable/operational/narrative self |
| [[metacognition]] | Internal state, neuromodulators, token metrics |
| [[offline-consolidation]] | Sleep loop, consolidation, hot-path |

## Runtime & Memory links

- Runtime store contract → [[runtime-contract]] · schemas → [[event-schema]], [[state-schema]], [[decision-episode-schema]]
- Synaptic learning → [[synaptic-policy]] · node types → [[memory-types]] · distillation → [[consolidation-policy]]
