# tirage simple de 100 essais parmi les non identiques
# attention : l'échantillon annoté a en fait été tiré en 2 phases (cf design.json), ce script
# ne sert que pour refaire un tirage, d'où le --force
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "classify"))
from batches import fmt_item, items

OUT = ROOT / "validation"
N = 100


def main():
    if (OUT / "sample.json").exists() and "--force" not in sys.argv:
        sys.exit("sample.json existe déjà, --force pour l'écraser")
    its = items()
    pool = sorted(n for n, it in its.items() if "label" not in it)
    ids = random.Random(120).sample(pool, N)
    sample = [{k: its[n][k] for k in ("nct", "registered", "deposited", "deposited_secondary_titles")}
              for n in ids]
    (OUT / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1))
    (OUT / "sample_items.txt").write_text("\n".join(fmt_item(it) for it in sample))
    print(f"{len(sample)} essais tirés parmi {len(pool)} -> validation/sample.json, validation/sample_items.txt")


if __name__ == "__main__":
    main()
