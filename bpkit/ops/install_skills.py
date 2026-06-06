"""Copy this repo's .claude/skills into the user's personal ~/.claude/skills so the
bpkit slash-commands (/setup, /bp-channel, /bp-read, /bp-test) work from ANY project
directory, not just this repo.

Each installed skill is stamped with this repo's absolute path so its commands still
resolve when invoked from elsewhere. Idempotent -- re-run after pulling repo updates.

Host-side; run with the bundled python directly (NOT via ue_run):
    & $py bpkit/ops/install_skills.py
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, ".claude", "skills")
DST = os.path.join(os.path.expanduser("~"), ".claude", "skills")

HEADER = (
    "> _Installed by bpkit._ The bpkit repo is at `%s` -- run the commands in this\n"
    "> skill from there (cd into it first, or prefix the script paths with that root).\n\n"
    % REPO)


def _stamp(body):
    """Insert HEADER after the YAML frontmatter so the file stays valid."""
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            cut = body.find("\n", end + 1)
            if cut != -1:
                return body[:cut + 1] + "\n" + HEADER + body[cut + 1:]
    return HEADER + body


def main():
    if not os.path.isdir(SRC):
        print("no skills found at", SRC)
        return
    os.makedirs(DST, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(SRC)):
        src_md = os.path.join(SRC, name, "SKILL.md")
        if not os.path.isfile(src_md):
            continue
        with open(src_md, "r", encoding="utf-8") as f:
            body = f.read()
        out_dir = os.path.join(DST, name)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(_stamp(body))
        print("installed /%s -> %s" % (name, os.path.join(out_dir, "SKILL.md")))
        n += 1
    print("\n%d skill(s) installed to %s" % (n, DST))
    print("They now work in any project. Restart Claude Code if ~/.claude/skills "
          "did not exist before (a new top-level skills dir must be picked up on start).")


if __name__ == "__main__":
    main()
