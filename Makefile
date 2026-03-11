SHELL := /bin/bash

.PHONY: evals-build evals-test evals-agent evals-backend evals-backend-score

evals-build:
	agents/.venv/bin/python agents/evals/runners/build_adk_evalset.py \
		--catalog agents/evals/cases/core_v1.json \
		--catalog agents/evals/cases/session_v1.json

evals-test:
	server/.venv/bin/python -m pytest agents/evals/tests -q

evals-agent:
	agents/.venv/bin/python agents/evals/runners/run_agent_eval.py \
		--catalog agents/evals/cases/core_v1.json \
		--catalog agents/evals/cases/session_v1.json \
		--print-detailed-results

evals-backend:
	server/.venv/bin/python agents/evals/runners/run_backend_eval.py \
		--catalog agents/evals/cases/core_v1.json \
		--output agents/evals/results/core_backend_results.json

evals-backend-score:
	server/.venv/bin/python agents/evals/runners/score_backend_eval.py \
		--catalog agents/evals/cases/core_v1.json \
		--results agents/evals/results/core_backend_results.json \
		--output agents/evals/results/core_backend_scored.json
