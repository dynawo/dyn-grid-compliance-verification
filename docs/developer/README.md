# DyCoV developer documentation

This directory contains documentation intended for **developers and contributors**
who want to **build, modify, or extend DyCoV**.

It is **not required** for end‑users who only want to install and use DyCoV.
If your goal is to run studies or perform validations, refer instead to:

- `docs/installation/` — how to install DyCoV
- `docs/tutorials/` — how to use DyCoV workflows

---

## Scope of this directory

The documents in this directory cover topics such as:

- building DyCoV from source,
- developer installation workflows,
- internal architecture and design decisions,
- extending DyCoV with new features or tests,
- contributing to the codebase.

This documentation assumes familiarity with:
- Linux environments,
- Python development,
- command‑line tooling,
- version control systems (Git).

---

## Typical use cases

You will need the documentation in this directory if you want to:

- develop or debug DyCoV itself → start with `setup.md`, `project_structure.md`, and `extending_dycov.md`
- add or modify Performance Checking Sheets (PCS) → see `add_new_pcs.md`
- extend supported models or workflows → see `extending_dycov.md`
- contribute code changes upstream → follow standard Git workflows and ensure tests pass
- understand internal data flows and architecture → see `project_structure.md` and design documents

If you do **not** intend to modify DyCoV, you can safely ignore this directory.

---

## Relationship with other documentation

The DyCoV documentation is structured as follows:

- **Installation (`docs/installation/`)**  
  How to make DyCoV available on a system.

- **Tutorials (`docs/tutorials/`)**  
  Step‑by‑step guides on using DyCoV once installed.

- **Developer documentation (`docs/developer/`)**  
  How DyCoV works internally and how to extend it.

Each directory targets a **different audience** and should be read independently.

---

## Getting started as a developer

To start developing DyCoV, refer to the developer‑specific build and setup
instructions provided in this directory.

End‑user installation methods (distribution image, WSL, Docker) are **not**
suitable for development workflows.

---

## Key developer guides

The following documents are recommended starting points depending on your task:

- [Setup](setup.md) — set up a local development environment
- [Project structure](project_structure.md) — understand the repository organization
- [Extending DyCoV](extending_dycov.md) — understand extension principles and architecture
- [Add new PCS](add_new_pcs.md) — step-by-step guide to implement a new PCS
