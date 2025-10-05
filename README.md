# Lensix (Circle to Search for Linux)

A powerful Circle to Search tool built in Python for any Linux desktop. This script allows you to draw a circle around anything on your screen to perform a text or visual search with Google.

## Installation

You can install Lensix with a single command. This will download the project, check for dependencies, and install the tool on your system.

**Prerequisites:** You must have `git` and `curl` installed.
On Debian/Ubuntu, you can install them with: `sudo apt install git curl`

### One-Step Install Command

Open your terminal and run the following command:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/shashwathv/lensix/main/scripts/bootstrap.sh)"
```

After the installation is complete, you can run the program from any terminal by simply typing:

```bash
lensix
```

---

**A Note on Security:** This method involves piping a script from the internet directly into your shell. This requires that you trust the source of the script. I recommend inspecting the `bootstrap.sh` script on GitHub before running the command if you have any concerns.
