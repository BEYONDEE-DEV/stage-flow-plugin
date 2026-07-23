# Stageflow Plugin

Stageflow is a Codex plugin for request definition, implementation planning, implementation review, and atomic project documentation workflows.

It also bundles Simple Workflow as a lightweight `plan.md`-centered workflow alongside the full Stageflow flow.

## Installation

The plugin name is `stageflow`, and the marketplace name is `stage-flow`.

### Method 1: Use a Local Clone

Use this when you want to inspect or edit the plugin source locally.

```bash
git clone git@github.com:BEYONDEE-DEV/stage-flow-plugin.git
cd stage-flow-plugin

codex plugin marketplace add "$(pwd)"
codex plugin add stageflow@stage-flow
```

If you prefer HTTPS:

```bash
git clone https://github.com/BEYONDEE-DEV/stage-flow-plugin.git
cd stage-flow-plugin

codex plugin marketplace add "$(pwd)"
codex plugin add stageflow@stage-flow
```

### Method 2: Use the Git Marketplace Directly

Use this when you want to install the plugin without keeping a local clone.

```bash
codex plugin marketplace add git@github.com:BEYONDEE-DEV/stage-flow-plugin.git --ref main
codex plugin add stageflow@stage-flow
```

If you prefer HTTPS:

```bash
codex plugin marketplace add https://github.com/BEYONDEE-DEV/stage-flow-plugin.git --ref main
codex plugin add stageflow@stage-flow
```

## Verify Installation

```bash
codex plugin list
```

You should see:

```text
stageflow@stage-flow  installed, enabled
```

## Included Workflows

- Stageflow: use `Stageflow`, `stageflow`, `stage-flow`, or `.stageflow`.
- Simple Workflow: use `Simple Workflow`, `simple-workflow`, or `.simple`.
- Atomic Docs: use `atomic-docs`.

## Update

For a local clone:

```bash
git pull
codex plugin add stageflow@stage-flow
```

For a Git marketplace install:

```bash
codex plugin marketplace upgrade
codex plugin add stageflow@stage-flow
```

After installing or updating, start a new Codex thread so newly loaded skills and tools are available.

## Notes

- Private repository installs require GitHub SSH or HTTPS authentication on the user's machine.
- Git marketplace installs only use content that has been pushed to GitHub.
