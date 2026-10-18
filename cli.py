"""Command-line demo.

  python cli.py seed        reset the graph and load knowledge + demo orders
  python cli.py run         run every pending order through the agents
  python cli.py show ID     print one order's result
"""
import sys

from compounder import db
from compounder import queries as Q
from compounder.agents.orchestrator import process_pending
from compounder.report import order_report

ICON = {"block": "BLOCK", "warn": "WARN ", "info": "info "}


def show(order_id: str):
    rep = order_report(order_id)
    p, d, f = rep["patient"], rep["drug"], rep["formulation"]
    print(f"\n=== {order_id} | {p.get('name')} | {d.get('name')} | {rep['order']['status']}")
    for s in rep["steps"]:
        print(f"  [{s['agent']:<11}] {s['summary']}")
    if f:
        print(f"  -> {f['drug']} {f['concentration']} {f['form'].lower()} in {f['base']}")
        print(f"     {f['dose_text']}; make {f['quantity']} {f['quantity_unit']}; BUD {f['bud_days']} days")
        print(f"     Label: {f['directions']}")
        for i, step in enumerate(f.get("procedure") or [], 1):
            print(f"       {i}. {step}")
    cov = rep.get("coverage")
    if cov:
        print(f"  $ {cov['plan']}: {cov['recommended']} ({cov['route']}), copay {cov.get('copay_usd')}, PA {cov['prior_auth']}")
    for fd in rep["findings"]:
        print(f"  {ICON.get(fd['severity'], fd['severity'])} [{fd['category']}] {fd['message']}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "seed":
        from compounder.seed.loader import load_all
        print(f"Seeded graph ({load_all()} commercial products).")
    elif cmd == "run":
        results = process_pending()
        for oid in results:
            show(oid)
        if not results:
            for o in db.run(Q.LIST_ORDERS):
                show(o["order_id"])
    elif cmd == "show":
        show(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
