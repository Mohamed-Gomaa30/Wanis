# Phase 4 – Demo & Lightning.ai Deployment Tasks

## Phase 1 – Setup (common infrastructure)
- [X] T001 Create project structure for deployment scripts (e.g., `scripts/` directory) if not already present

## Phase 2 – Foundational (deployment artifacts)
- [X] T002 [P] Create Lightning.ai component definition file `component.yaml` at the repository root
- [X] T003 [P] Add CI/CD workflow file `.github/workflows/ci.yml` to build and publish the Lightning.ai component
- [X] T004 Write deployment script `deploy_lightning.sh` that pushes the component to Lightning.ai using the CLI

## Phase 3 – Documentation & Verification
- [X] T005 Update `docs/QUICKSTART.md` with a "Deploy on Lightning.ai" section, including usage of `component.yaml` and `deploy_lightning.sh`
- [X] T006 Add CI status badge to `README.md` showing the latest workflow run
- [X] T007 Execute `./deploy_lightning.sh` in a clean environment and verify the component appears in the Lightning.ai console

## Final Phase – Polish
- [X] T008 Review all deployment artifacts for linting and security (e.g., no secrets in `component.yaml`)
- [X] T009 Add monitoring dashboard configuration files (`monitoring/grafana-dashboard.json`) for production metrics
