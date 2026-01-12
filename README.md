# Analysis Helper Tools

A lightweight toolkit designed to streamline collaborative development and version control for physics analysis code.

## :rocket: Overview

This repository performs two main functions:
1.  **Smart Status Check**: Enhances `git status` with interactive diff viewing.
2.  **Directory Compare**: Visualizes differences between "Production" (`pro`) and "Development" (`dev`) environments to facilitate manual merging.

## :hammer_and_wrench: Tools

### `git_tool.py`

A standalone Python script requiring **zero dependencies** (standard library only). It is ready to deploy on any server environment.

#### Usage

**1. Interactive Status Check**

Review your changes with an intuitive interface before committing.

```bash
python3 git_tool.py check
```

**2. Compare & Merge Assistant**

Recursively compare two directories to identify modified, new, or missing files. Perfect for syncing `dev` work to `pro`.

```bash
python3 git_tool.py compare --pro /path/to/e72 --dev /path/to/e72_undev
```

*   **PRO ONLY**: Files missing in dev.
*   **DEV ONLY**: New files in dev.
*   **MODIFIED**: Files with content differences (view diffs instantly).

## :floppy_disk: Installation

Simply drop `git_tool.py` into your path or clone this repository to your server.

```bash
chmod +x git_tool.py
```
