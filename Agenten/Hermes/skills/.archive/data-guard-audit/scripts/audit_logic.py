import argparse
import os
import pathlib
import sys

def get_repo_root():
    curr = pathlib.Path(os.getcwd()).resolve()
    if "MaxHirn" in curr.parts:
        return curr.parent
    return curr

ROOT = get_repo_root()

# TIER 0: Irreplaceable. No bulk deletes/overwrites.
TIER_0_PARTS = [
    "MaxHirn/Wissen",
    "MaxHirn/Archiv",
    "Agenten/Hermes/skills",
    "Agenten/MCP-Server",
    "Agenten/Handel",
    "Zugaenge.md"
]

# TIER 1: Operational. Requires backup before destructive changes.
TIER_1_PARTS = [
    "Agenten/Hermes",
    "Agenten/Routinen",
    "Agenten/MCP-Server",
    "Agenten/Handel"
]

QUARANTINE_DIR = "_zu_loeschen"

def get_tier(path_input):
    try:
        target_path = pathlib.Path(path_input).resolve()
        repo_root = ROOT.resolve()
        try:
            rel_path = target_path.relative_to(repo_root)
            rel_path_str = str(rel_path).replace("\\", "/")
        except ValueError:
            rel_path_str = str(target_path).replace("\\", "/")
    except Exception as e:
        print(f"Error resolving path: {e}", file=sys.stderr)
        return 2

    # Check Tier 0
    for part in TIER_0_PARTS:
        if part.replace("\\", "/") in rel_path_str:
            return 0
            
    # Check Tier 1
    for part in TIER_1_PARTS:
        if part.replace("\\", "/") in rel_path_str:
            return 1
            
    return 2

def audit(path_str, action):
    tier = get_tier(path_str)
    
    if tier == 0:
        if action in ["delete", "bulk_delete", "overwrite"]:
            return "DENY", "Tier 0: Irreplaceable data. Do not overwrite or delete."
        if action in ["move", "rename"]:
            return "QUARANTINE", f"Tier 0: Move to {QUARANTINE_DIR} instead."
        return "ALLOW", "Tier 0: Read-only access ok."
        
    if tier == 1:
        if action in ["delete", "bulk_delete", "overwrite", "move", "rename"]:
            return "ENFORCE_BACKUP", "Tier 1: Create a .bak-YYYYMMDD copy before acting."
        return "ALLOW", "Tier 1: Read-only access ok."
        
    return "ALLOW", "Tier 2: Reproducible data. Free hand."

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Target file or directory")
    parser.add_argument("--action", required=True, choices=["delete", "bulk_delete", "overwrite", "move", "rename", "bulk_move"], help="Planned action")
    args = parser.parse_args()

    decision, reason = audit(args.path, args.action)
    print(f"DECISION: {decision}")
    print(f"REASON: {reason}")
    
    if decision == "DENY":
        sys.exit(1)
    elif decision == "ENFORCE_BACKUP":
        sys.exit(2)
    elif decision == "QUARANTINE":
        sys.exit(3)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
