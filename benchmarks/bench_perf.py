"""Performance benchmarks: index build, search latency, prompt size comparison."""

import json
import time
import random
import string
import statistics
from pathlib import Path
from src.vault_ops import VaultOps
from src.indexer import SkillIndexer
from src.search import SkillSearch
from src.hooks import build_session_context

CATEGORIES = [
    "software-development", "research", "writing", "ops",
    "data-science", "design", "security", "testing",
    "devops", "communication", "planning", "analysis",
]

WORDS_EN = [
    "api", "build", "cache", "deploy", "error", "format", "generate",
    "handler", "index", "json", "kubernetes", "log", "monitor", "network",
    "optimize", "parse", "query", "refactor", "search", "test", "update",
    "validate", "workflow", "yaml", "zen",
]

WORDS_ZH = [
    "接口", "构建", "缓存", "部署", "错误", "格式", "生成",
    "处理", "索引", "监控", "优化", "解析", "查询", "重构",
    "搜索", "测试", "更新", "验证", "工作流", "调试",
]


def random_name():
    return "-".join(random.choices(WORDS_EN, k=random.randint(2, 3)))


def random_summary():
    en = " ".join(random.choices(WORDS_EN, k=random.randint(5, 10)))
    zh = "".join(random.choices(WORDS_ZH, k=random.randint(3, 6)))
    return f"{en} {zh}"


def random_triggers():
    count = random.randint(2, 5)
    return random.choices(WORDS_EN + WORDS_ZH, k=count)


def generate_skills(n: int) -> list[dict]:
    """Generate n synthetic skill definitions."""
    skills = []
    for i in range(n):
        cats = random.sample(CATEGORIES, k=random.randint(1, 3))
        skills.append({
            "name": f"skill-{i:05d}-{random_name()}",
            "categories": cats,
            "tags": random.choices(WORDS_EN, k=random.randint(2, 4)),
            "triggers": random_triggers(),
            "summary": random_summary(),
            "content": f"# Skill {i}\n\n" + "\n".join(
                f"- Step {j}: {' '.join(random.choices(WORDS_EN, k=8))}"
                for j in range(random.randint(3, 8))
            ),
        })
    return skills


def populate_vault(vault_path: str, skills: list[dict]) -> float:
    """Write skills to vault, return elapsed seconds."""
    ops = VaultOps(vault_path)
    start = time.perf_counter()
    for i, s in enumerate(skills):
        cat_dir = s["categories"][0]
        path = f"skills/{cat_dir}/{s['name']}.md"
        meta = {
            "name": s["name"],
            "categories": s["categories"],
            "tags": s["tags"],
            "triggers": s["triggers"],
            "summary": s["summary"],
        }
        ops.write_note(path, meta, s["content"])
    return time.perf_counter() - start


def bench_index_build(vault_path: str, db_path: str) -> float:
    """Build full index, return elapsed seconds."""
    ops = VaultOps(vault_path)
    skills = ops.scan_skills()
    indexer = SkillIndexer(db_path)
    start = time.perf_counter()
    count = indexer.build_index(skills)
    elapsed = time.perf_counter() - start
    indexer.close()
    assert count == len(skills)
    return elapsed


def bench_search(indexer: SkillIndexer, queries: list[str], top_k: int = 3) -> list[float]:
    """Run searches, return list of per-query latencies in ms."""
    engine = SkillSearch(indexer)
    latencies = []
    for q in queries:
        start = time.perf_counter()
        engine.search(q, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
    return latencies


def bench_prompt_size(indexer: SkillIndexer, vault_path: str) -> dict:
    """Compare lazy prompt size vs theoretical full prompt size."""
    # Lazy: category index + discovery
    lazy_ctx = build_session_context(vault_path, indexer)

    # Full: simulate all skill descriptions
    ops = VaultOps(vault_path)
    skills = ops.scan_skills()
    full_lines = []
    for s in skills:
        full_lines.append(f"- {s.name}: {s.summary}")
    full_prompt = "\n".join(full_lines)

    return {
        "lazy_prompt_bytes": len(lazy_ctx.encode("utf-8")),
        "lazy_prompt_kb": round(len(lazy_ctx.encode("utf-8")) / 1024, 2),
        "full_prompt_bytes": len(full_prompt.encode("utf-8")),
        "full_prompt_kb": round(len(full_prompt.encode("utf-8")) / 1024, 2),
        "reduction_pct": round(
            (1 - len(lazy_ctx.encode("utf-8")) / len(full_prompt.encode("utf-8"))) * 100, 1
        ) if full_prompt else 0,
    }


def run_benchmarks(sizes: list[int], base_dir: str):
    results = {}
    base = Path(base_dir)

    for n in sizes:
        print(f"\n{'='*60}")
        print(f"  Benchmark: {n:,} skills")
        print(f"{'='*60}")

        work_dir = base / f"bench_{n}"
        vault_path = work_dir / "vault"
        db_path = work_dir / "index.db"

        # Generate
        skills = generate_skills(n)

        # Write to vault
        vault_path.mkdir(parents=True, exist_ok=True)
        (vault_path / ".obsidian").mkdir(exist_ok=True)
        (vault_path / "skills").mkdir(exist_ok=True)
        write_time = populate_vault(str(vault_path), skills)
        print(f"  Vault write:    {write_time:.2f}s ({n/write_time:.0f} skills/s)")

        # Index build
        idx_time = bench_index_build(str(vault_path), str(db_path))
        print(f"  Index build:    {idx_time:.2f}s ({n/idx_time:.0f} skills/s)")

        # Search latency
        indexer = SkillIndexer(str(db_path))
        queries = [random_name() for _ in range(100)] + random.choices(WORDS_ZH, k=50)
        latencies = bench_search(indexer, queries)
        lat_ms = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        print(f"  Search ({len(queries)} queries):")
        print(f"    mean: {lat_ms:.2f}ms  p50: {p50:.2f}ms  p95: {p95:.2f}ms  p99: {p99:.2f}ms")

        # Prompt size
        prompt_stats = bench_prompt_size(indexer, str(vault_path))
        print(f"  Prompt size:")
        print(f"    Lazy: {prompt_stats['lazy_prompt_kb']}KB  Full: {prompt_stats['full_prompt_kb']}KB  Reduction: {prompt_stats['reduction_pct']}%")

        indexer.close()

        results[n] = {
            "skill_count": n,
            "vault_write_s": round(write_time, 3),
            "index_build_s": round(idx_time, 3),
            "search_queries": len(queries),
            "search_mean_ms": round(lat_ms, 2),
            "search_p50_ms": round(p50, 2),
            "search_p95_ms": round(p95, 2),
            "search_p99_ms": round(p99, 2),
            "prompt_lazy_kb": prompt_stats["lazy_prompt_kb"],
            "prompt_full_kb": prompt_stats["full_prompt_kb"],
            "prompt_reduction_pct": prompt_stats["reduction_pct"],
        }

    return results


def print_summary(results: dict):
    print(f"\n{'='*80}")
    print("  SUMMARY")
    print(f"{'='*80}")
    print(f"{'Skills':>10} | {'Vault':>8} | {'Index':>8} | {'Search':>8} | {'p95':>6} | {'Lazy':>8} | {'Full':>8} | {'Reduce':>7}")
    print(f"{'':>10} | {'write/s':>8} | {'build/s':>8} | {'mean/ms':>8} | {'/ms':>6} | {'/KB':>8} | {'/KB':>8} | {'/%':>7}")
    print("-" * 80)
    for n, r in results.items():
        print(
            f"{n:>10,} | "
            f"{n/r['vault_write_s']:>8.0f} | "
            f"{n/r['index_build_s']:>8.0f} | "
            f"{r['search_mean_ms']:>8.2f} | "
            f"{r['search_p95_ms']:>6.2f} | "
            f"{r['prompt_lazy_kb']:>8.2f} | "
            f"{r['prompt_full_kb']:>8.1f} | "
            f"{r['prompt_reduction_pct']:>7.1f}"
        )


if __name__ == "__main__":
    import sys
    import tempfile

    sizes = [100, 1000, 5000, 10000]
    if len(sys.argv) > 1:
        sizes = [int(x) for x in sys.argv[1:]]

    bench_dir = tempfile.mkdtemp(prefix="skill_vault_bench_")
    print(f"Benchmark dir: {bench_dir}")
    print(f"Sizes: {sizes}")

    results = run_benchmarks(sizes, bench_dir)
    print_summary(results)

    # Save results as JSON
    results_path = Path(bench_dir) / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_path}")
