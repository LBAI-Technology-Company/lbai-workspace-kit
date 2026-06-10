# role_world_model_update_agent_v1

## Purpose

Convert approved evidence into role world model deltas and version artifacts.

## Inputs

- Current `role_workspace/world_model/` files
- Evidence artifacts under the relevant task folder
- Company guardrails

## Outputs

- Role world model delta
- New version artifact under `role_workspace/world_model/versions/`
- Lineage note linking evidence to the version
- Task ledger update

## Hard Blocks

- Missing evidence
- Evidence not admissible
- Review-required claim without review
- Change outside role boundary
