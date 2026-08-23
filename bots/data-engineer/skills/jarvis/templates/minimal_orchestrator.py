"""Minimal Jarvis-style orchestrator skeleton -- copy & modify.

Pure stdlib. Demonstrates the durable-state + decompose + dispatch + verify loop
without the full library. Run: python minimal_orchestrator.py
"""
import sqlite3, time, hashlib


class Store:
    def __init__(self, path="orch.db"):
        self.c = sqlite3.connect(path)
        self.c.execute("CREATE TABLE IF NOT EXISTS tasks("
                       "id TEXT PRIMARY KEY, goal TEXT, status TEXT, verify TEXT)")
        self.c.commit()

    def add(self, t):
        self.c.execute("INSERT OR REPLACE INTO tasks VALUES(?,?,?,?)",
                       (t["id"], t["goal"], t["status"], t["verify"]))

    def get_open(self):
        return [dict(zip(("id", "goal", "status", "verify"), r))
                for r in self.c.execute("SELECT * FROM tasks WHERE status='open'")]

    def set(self, i, s):
        self.c.execute("UPDATE tasks SET status=? WHERE id=?", (s, i))
        self.c.commit()


def decompose(goal, open_goals):
    # Replace with LLM call. Returns the next missing sub-goal or None.
    milestones = ["define offer", "build landing page", "drive traffic"]
    for m in milestones:
        if m not in open_goals:
            return m
    return None


def cycle(store, goal):
    open_tasks = store.get_open()
    open_goals = {t["goal"] for t in open_tasks}
    sub = decompose(goal, open_goals)
    if sub:
        tid = "t_" + hashlib.sha1(sub.encode()).hexdigest()[:8]
        store.add({"id": tid, "goal": sub, "status": "open", "verify": "manual"})
        print(f"[create] {sub}")
    ready = open_tasks[0] if open_tasks else None
    if ready:
        # >>> HERE the Hermes agent would call delegate_task(goal=ready['goal']) <<<
        print(f"[dispatch] worker for: {ready['goal']}  (task_id={ready['id']})")
        store.set(ready["id"], "doing")


if __name__ == "__main__":
    s = Store(":memory:")
    GOAL = "earn online"
    for _ in range(5):
        cycle(s, GOAL)
        time.sleep(0.1)
