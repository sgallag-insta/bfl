# bfl-cli (Binary Flame Launcher) 🔥

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
**`bfl` is a therapeutic command-line tool designed to help you "let go" of digital files by simulating the act of burning them before deletion.**

Inspired by the therapeutic practice of writing down worries or negative feelings on a piece of paper and then burning it, `bfl` offers a digital equivalent for your files. It provides a visual "burning" animation in your terminal, after which the selected file is permanently deleted.

## The Concept

In many therapeutic practices, the symbolic act of destruction (like burning a piece of paper with written thoughts) can be a powerful way to process and release difficult emotions or unwanted attachments. `bfl` aims to bring a similar symbolic experience to the digital realm, allowing you to "burn away" files that might represent something you wish to move on from.

## Features

* **Visual Animation:** A `curses`-based animation simulates the file (represented by its name) catching fire, burning to embers, and then turning to ash.
* **Confirmation Step:** Prompts for confirmation before "burning" and deleting the file to prevent accidental data loss.
* **File Deletion:** After the animation, the actual file is deleted from your system.
* **Therapeutic Focus:** Designed with the intention of providing a moment of catharsis.

## Requirements

* Python 3.7+
* A terminal that supports `curses` and ANSI escape codes (most modern terminals on Linux and macOS do).

Disclaimer: bfl is an open-source utility. It is not affiliated with or endorsed by any existing brands or products.
