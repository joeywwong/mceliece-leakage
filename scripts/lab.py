"""Standard-library-only runner. Raw data and metadata precede derived reports."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
PARSER = argparse.ArgumentParser()
PARSER.add_argument("--opt", choices=["O2", "O3"], default="O2")
PARSER.add_argument("--cc", default="gcc")
PARSER.add_argument("--flags", default="")
PARSER.add_argument("action", choices=["test", "trace", "bench", "inspect", "sanitize", "report"])
ARGS = PARSER.parse_args()
BUILD = ROOT / "build" / ARGS.opt


def write(path, content):
    """Replace one file atomically after its content is complete."""
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    paths = sorted(list(ROOT.glob("src/*")) + list(ROOT.glob("scripts/*.py")) + [ROOT / "Makefile"])
    return {str(p.relative_to(ROOT)): digest(p) for p in paths if p.is_file()}


def query(command):
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"
    except OSError:
        return "UNAVAILABLE"


def metadata(action, commands, binaries=()):
    cpu = "UNAVAILABLE"
    if Path("/proc/cpuinfo").exists():
        cpu = next((line.split(":", 1)[1].strip() for line in
                    Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")), cpu)
    return {
        "action": action, "utc": datetime.now(timezone.utc).isoformat(),
        "opt": ARGS.opt, "compiler": query(shlex.split(ARGS.cc) + ["--version"]),
        "target": query(shlex.split(ARGS.cc) + ["-dumpmachine"]),
        "flags": ARGS.flags, "platform": platform.platform(), "cpu": cpu,
        "python": platform.python_version(), "commands": commands,
        "commit": query(["git", "rev-parse", "HEAD"]),
        "git_status": query(["git", "status", "--porcelain"]),
        "source_sha256": sources(),
        "binary_sha256": {str(p.relative_to(ROOT)): digest(p) for p in binaries},
    }


def save_meta(name, meta):
    write(RESULTS / (name + ".json"), json.dumps(meta, indent=2) + "\n")


def execute(command, name):
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    write(RESULTS / (name + ".stdout"), result.stdout)
    write(RESULTS / (name + ".stderr"), result.stderr)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"{command} failed: {result.returncode}; raw logs: results/{name}.*")
    return result


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def splitmix(state):
    mask = (1 << 64) - 1
    state = (state + 0x9E3779B97F4A7C15) & mask
    value = state
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & mask
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & mask
    return state, value ^ (value >> 31)


def simulate(data):
    truth = [int(row["branchy_xor_executed"]) for row in data]
    assert len(truth) == 2016 and all(bit in (0, 1) for bit in truth)
    assert all(int(row["decision"]) == int(row["original_coefficient"]) == bit
               for row, bit in zip(data, truth))
    seed = 0x5EED20261030
    state = seed
    raw = io.StringIO()
    out = csv.writer(raw, lineterminator="\n")
    out.writerow(["flip_probability", "index", "truth", "flipped", "observation", "estimate"])
    summary = []
    # One observation per bit, no redundancy. Estimator simply trusts observation.
    for numerator in range(5):
        threshold = ((1 << 64) * numerator) // 10
        correct = flips = 0
        for i, bit in enumerate(truth):
            state, uniform = splitmix(state)
            flipped = int(uniform < threshold)
            observation = bit ^ flipped
            estimate = observation  # Never accesses truth to choose an estimate.
            correct += estimate == bit
            flips += flipped
            out.writerow([f"{numerator / 10:.1f}", i, bit, flipped, observation, estimate])
        summary.append({"p": numerator / 10, "n": len(truth), "flips": flips,
                        "correct": correct, "accuracy": correct / len(truth),
                        "always_zero_accuracy": truth.count(0) / len(truth)})
    write(RESULTS / f"noise-{ARGS.opt}.csv", raw.getvalue())
    hw = {str(bit): [int(row["masked_operand_hw"]) for row in data
                    if int(row["decision"]) == bit] for bit in (0, 1)}
    return {"noise_seed_hex": hex(seed), "generator": "SplitMix64; continuous stream across rates",
            "noise": summary, "trace_seed_hex": "0x20261030", "trace_bits": len(truth),
            "trace_ones": sum(truth), "masked_xor_count": sum(int(r["masked_xor_executed"]) for r in data),
            "abstract_operand_hw": {bit: {"n": len(values), "mean": statistics.mean(values),
                                          "min": min(values), "max": max(values)}
                                    for bit, values in hw.items()}}


def run_binary(action):
    name = f"{action}-{ARGS.opt}"
    # Invalidate a previous completed result before a potentially failing rerun.
    save_meta(name, {"status": "INCOMPLETE"})
    binary = BUILD / action
    command = [str(binary)]
    result = execute(command, name)
    meta = metadata(action, [command], [binary])
    if action == "test":
        if "PASS=526 FAIL=0" not in result.stdout:
            raise RuntimeError("Unexpected test output")
        meta["result"] = result.stdout.strip()
        print(meta["result"])
    else:
        write(RESULTS / (name + ".csv"), result.stdout)
        data = rows(result.stdout)
        if action == "trace":
            meta.update(simulate(data))
            print(f"SOFTWARE MODEL: {meta['trace_bits']} decisions; {meta['trace_ones']} conditional XORs")
        else:
            assert len(data) == 404
            meta["groups"] = []
            for variant in ("branchy", "masked"):
                for kind in ("identity", "random"):
                    group = [r for r in data if r["variant"] == variant and r["input_class"] == kind]
                    assert len(group) == 101 and all(int(r["batch"]) == 512 for r in group)
                    values = [int(r["elapsed_ns"]) / int(r["batch"]) for r in group]
                    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
                    meta["groups"].append({"variant": variant, "class": kind, "samples": len(values),
                                           "median_ns": statistics.median(values), "q1_ns": q1, "q3_ns": q3,
                                           "min_ns": min(values), "max_ns": max(values)})
            meta["timer_and_checksum"] = result.stderr.strip()
            print("HOST MEASURED:", meta["timer_and_checksum"])
            for group in meta["groups"]:
                print(f"{group['variant']:7} {group['class']:8}: median {group['median_ns']:.2f} ns/matrix; "
                      f"Q1..Q3 {group['q1_ns']:.2f}..{group['q3_ns']:.2f}")
    meta["status"] = "PASS"
    save_meta(name, meta)


def inspect():
    save_meta("inspect", {"status": "INCOMPLETE"})
    if not shutil.which("objdump"):
        save_meta("inspect", {"status": "SKIP", "reason": "objdump unavailable"})
        print("SKIP: objdump unavailable")
        return
    commands, binaries = [], []
    for opt in ("O2", "O3"):
        binary = ROOT / "build" / opt / "bench"
        binaries.append(binary)
        for symbol in ("gf2_branchy", "gf2_masked"):
            cmd = ["objdump", "-d", "-M", "intel", f"--disassemble={symbol}", str(binary)]
            result = execute(cmd, f"inspect-{opt}-{symbol}")
            write(RESULTS / f"{opt}-{symbol}.asm", result.stdout)
            commands.append(cmd)
    meta = metadata("inspect", commands, binaries)
    meta["optimization_levels"] = ["O2", "O3"]
    meta["objdump"] = query(["objdump", "--version"])
    meta["status"] = "PASS"
    meta["interpretation"] = "Disassembly saved; manual interpretation is in docs/ASSEMBLY_REVIEW.md."
    save_meta("inspect", meta)
    print("Saved linked benchmark kernel disassembly at O2 and O3; requires manual review.")


def sanitize():
    save_meta("sanitize", {"status": "INCOMPLETE"})
    folder = ROOT / "build" / "sanitize"
    folder.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fno-lto", "-O1", "-g",
             "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
    compiler = shlex.split(ARGS.cc)
    commands = []
    probe = folder / "probe.c"
    write(probe, "int main(void) { return 0; }\n")
    probe_cmd = compiler + flags + [str(probe), "-o", str(folder / "probe")]
    try:
        execute(probe_cmd, "sanitize-probe-build")
        execute([str(folder / "probe")], "sanitize-probe-run")
    except (OSError, RuntimeError) as error:
        save_meta("sanitize", {"status": "SKIP", "reason": str(error), "flags": flags})
        print("SKIP: sanitizer toolchain/runtime probe unavailable; see results/sanitize-probe-* logs")
        return
    commands.extend([probe_cmd, [str(folder / "probe")]])
    objects = []
    for name, traced in [("branchy", False), ("masked", False), ("support", False), ("test", False),
                         ("branchy", True), ("masked", True)]:
        obj = folder / (name + ("_trace" if traced else "") + ".o")
        cmd = compiler + flags + (["-DGF2_TRACE"] if traced else []) + ["-c", f"src/{name}.c", "-o", str(obj)]
        execute(cmd, "sanitize-build-" + obj.stem)
        commands.append(cmd)
        objects.append(str(obj))
    binary = folder / "test"
    cmd = compiler + flags + objects + ["-o", str(binary)]
    execute(cmd, "sanitize-link")
    result = execute([str(binary)], "sanitize-test")
    if "PASS=526 FAIL=0" not in result.stdout:
        raise RuntimeError("Unexpected sanitizer test output")
    meta = metadata("sanitize", commands + [cmd, [str(binary)]], [binary])
    meta.update(status="PASS", flags=flags, opt="O1", result=result.stdout.strip())
    save_meta("sanitize", meta)
    print("ASan/UBSan:", result.stdout.strip())


def completed(name):
    path = RESULTS / (name + ".json")
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("status") != "PASS":
        return None
    if data.get("source_sha256") != sources():
        raise RuntimeError(f"Stale {name} source hashes; rerun before generating a report")
    for path, expected in data.get("binary_sha256", {}).items():
        if not (ROOT / path).exists() or digest(ROOT / path) != expected:
            raise RuntimeError(f"Stale {name} binary hash for {path}; rerun before reporting")
    return data


def report():
    lines = ["# Completed host results", "", "Generated from completed local runs only. Timing is host measured; "
             "operation traces, noisy observations and Hamming weights are software models/simulations.", ""]
    for opt in ("O2", "O3"):
        test = completed(f"test-{opt}")
        lines += [f"- {opt} correctness: {test['result'] if test else 'NOT RUN'}"]
    san = completed("sanitize")
    lines += [f"- ASan/UBSan: {san['result'] if san else 'NOT RUN / SKIP; see results/sanitize.json'}",
              "- Hardware: NOT RUN; no board access, firmware, or physical capture.", "",
              "| Build | Variant | L class | Samples | Median ns/matrix | Q1–Q3 ns/matrix |",
              "|---|---|---|---:|---:|---:|"]
    for opt in ("O2", "O3"):
        data = completed(f"bench-{opt}")
        if not data:
            lines += [f"| {opt} | NOT RUN | — | — | — | — |"]
            continue
        for g in data["groups"]:
            lines += [f"| {opt} | {g['variant']} | {g['class']} | {g['samples']} | {g['median_ns']:.2f} | "
                      f"{g['q1_ns']:.2f}–{g['q3_ns']:.2f} |"]
    lines += ["", "Each sample batches 512 eliminations; 8 warm-up batches per group; 64 inputs per class. "
              "Copying and an output checksum are included. Groups are deterministically shuffled each round. "
              "Spread is the inclusive interquartile range. No Welch t-test or dudect run was performed. "
              "Scheduling, caches, branch prediction, frequency changes and WSL can affect results. "
              "These class comparisons do not establish key leakage or prove its absence.", ""]
    data = completed(f"trace-{ARGS.opt}")
    if data:
        lines += [f"Software operation trace: {data['trace_bits']} decisions, {data['trace_ones']} branchy XORs, "
                  f"{data['masked_xor_count']} masked XORs. Matrix seed `{data['trace_seed_hex']}`.", "",
                  "Synthetic binary flips; one observation per decision; estimator returns observation. "
                  f"Noise seed `{data['noise_seed_hex']}`; {data['generator']}. "
                  "Baseline always predicts zero, chosen without looking at the truth distribution.", "",
                  "| Flip probability | Actual flips / bits | Estimator accuracy | Always-zero baseline |",
                  "|---:|---:|---:|---:|"]
        for r in data["noise"]:
            lines += [f"| {r['p']:.1f} | {r['flips']} / {r['n']} | {100*r['accuracy']:.2f}% | "
                      f"{100*r['always_zero_accuracy']:.2f}% |"]
        lines += ["", "Abstract masked operand Hamming weights (two words combined; not power measurements):"]
        for bit, stats in data["abstract_operand_hw"].items():
            lines += [f"- decision {bit}: n={stats['n']}, mean={stats['mean']:.3f}, "
                      f"range={stats['min']}–{stats['max']}"]
    else:
        lines += ["Traces and simulation: NOT RUN."]
    inspection = completed("inspect")
    lines += ["", "Disassembly: " + ("O2/O3 linked kernels saved; see [manual review](docs/ASSEMBLY_REVIEW.md)."
                                      if inspection else "NOT RUN."), "",
              "Raw CSV, stdout/stderr, compiler/CPU/OS metadata, binary and source SHA-256 hashes: `results/`. "
              "These files are local and gitignored. Regenerate with the README commands."]
    write(ROOT / "RESULTS.md", "\n".join(lines) + "\n")
    print("Generated RESULTS.md from completed runs, with source hashes checked.")


if __name__ == "__main__":
    try:
        if ARGS.action in ("test", "trace", "bench"):
            run_binary(ARGS.action)
        else:
            globals()[ARGS.action]()
    except (RuntimeError, OSError, AssertionError) as error:
        sys.exit(f"FAIL: {error}")
