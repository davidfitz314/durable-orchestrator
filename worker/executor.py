from typing import Any, Dict

def transform_step(step_name: str, input_json: Dict[str, Any]) -> Dict[str, Any]:
    if step_name == "add_one":
        x = int(input_json.get("x", 0))
        return {"x": x + 1}

    # default behavior for unknown transforms
    return {"step": step_name, "echo": input_json}