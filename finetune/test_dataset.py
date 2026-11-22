import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import skills
from finetune.build_dataset import TOOLS_SCHEMA, build_examples

BANNED_FLUFF = (
    "let me know if you need further assistance",
    "i'd be happy to help",
    "feel free to ask",
)


def test_schema_matches_skills():
    schema_names = {t["function"]["name"] for t in TOOLS_SCHEMA}
    assert schema_names == set(skills.SKILLS.keys()), (
        f"Schema mismatch: {schema_names} vs {set(skills.SKILLS.keys())}"
    )
    for item in TOOLS_SCHEMA:
        fn_spec = item["function"]
        fn = skills.SKILLS[fn_spec["name"]]
        sig_params = set(inspect.signature(fn).parameters.keys())
        schema_params = set(fn_spec["parameters"]["properties"].keys())
        assert schema_params == sig_params, (
            f"Param mismatch for {fn_spec['name']}: {schema_params} vs {sig_params}"
        )


def test_dataset_quality():
    rows = build_examples()
    assert len(rows) >= 300, f"Expected >= 300 examples, got {len(rows)}"

    tools_seen = set()
    non_tool_count = 0
    multi_turn_count = 0
    param_map = {
        t["function"]["name"]: (
            set(t["function"]["parameters"]["properties"].keys()),
            set(t["function"]["parameters"]["required"]),
        )
        for t in TOOLS_SCHEMA
    }

    for i, row in enumerate(rows):
        encoded = json.dumps(row, ensure_ascii=False)
        parsed = json.loads(encoded)
        msgs = parsed["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "assistant" and msgs[-1]["content"].strip()

        final_lower = msgs[-1]["content"].lower()
        for phrase in BANNED_FLUFF:
            assert phrase not in final_lower, f"Row {i} has fluff: {phrase}"

        tool_calls_in_row = 0
        for m in msgs:
            for tc in m.get("tool_calls", []):
                tool_calls_in_row += 1
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                assert name in param_map, f"Unknown tool: {name}"
                allowed, required = param_map[name]
                assert set(args.keys()).issubset(allowed), f"Bad args for {name}: {args}"
                assert required.issubset(set(args.keys())), f"Missing args for {name}: {args}"
                if name == "add_task":
                    assert not args["task"].lower().startswith("add task"), (
                        f"Row {i} leaked command prefix: {args}"
                    )
                tools_seen.add(name)

        if tool_calls_in_row == 0:
            non_tool_count += 1
        elif tool_calls_in_row >= 2:
            multi_turn_count += 1

    assert tools_seen == set(skills.SKILLS.keys()), f"Missing tools: {set(skills.SKILLS.keys()) - tools_seen}"
    assert non_tool_count >= 50, "Need enough non-tool examples to avoid over-calling tools"
    assert multi_turn_count >= 50, f"Expected >= 50 multi-turn examples, got {multi_turn_count}"


if __name__ == "__main__":
    test_schema_matches_skills()
    test_dataset_quality()
    print("PASS: 300-row dataset (including multi-turn) matches skills.py.")