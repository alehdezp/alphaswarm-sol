# Production Readiness Checklist

## Skill Design
- [ ] Trigger description is specific and unambiguous
- [ ] Output contract is structured and testable
- [ ] Tool permissions are minimal and scoped
- [ ] Evidence-first requirement enforced
- [ ] Graph-first requirement enforced (BSKG query before reading code)

## Subagent Design
- [ ] Role is narrow and outcome is clear
- [ ] Context isolation expected (distilled output only)
- [ ] Cost budget is explicit
- [ ] Guardrails defined for tool access

## Cost & Reliability
- [ ] Progressive disclosure used
- [ ] Model tiering configured (cheap validator -> expert)
- [ ] Caching enabled for repeated queries
- [ ] Token budgets enforced per run

## Validation
- [ ] Golden outputs or example runs
- [ ] Regression checks for prompt drift
- [ ] Evidence refs included in sample outputs
