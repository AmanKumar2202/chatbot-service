import re
from typing import Any

from sympy import Eq, diff, integrate, simplify, solve, symbols
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
X = symbols("x")


def _expression(value: str):
    return parse_expr(
        value.strip(),
        local_dict={"x": X},
        transformations=TRANSFORMATIONS,
        evaluate=True,
    )


def solve_math(prompt: str) -> dict[str, Any]:
    normalized = prompt.strip()
    derivative = re.search(
        r"(?:differentiate|derivative\s+of)\s+(.+?)(?:\s+with\s+respect\s+to\s+(\w+))?$",
        normalized,
        re.IGNORECASE,
    )
    if derivative:
        expression = _expression(derivative.group(1))
        variable = symbols(derivative.group(2) or "x")
        answer = diff(expression, variable)
        return {
            "steps": [
                f"Identify the expression: {expression}.",
                f"Differentiate with respect to {variable}.",
                f"Apply symbolic differentiation rules: {answer}.",
            ],
            "final_answer": str(answer),
            "is_generic_template": False,
        }

    integral = re.search(
        r"(?:integrate|integral\s+of)\s+(.+?)(?:\s+with\s+respect\s+to\s+(\w+))?$",
        normalized,
        re.IGNORECASE,
    )
    if integral:
        expression = _expression(integral.group(1))
        variable = symbols(integral.group(2) or "x")
        answer = integrate(expression, variable)
        return {
            "steps": [
                f"Identify the integrand: {expression}.",
                f"Integrate with respect to {variable}.",
                f"Apply symbolic integration rules: {answer}.",
            ],
            "final_answer": f"{answer} + C",
            "is_generic_template": False,
        }

    equation_text = re.sub(
        r"^\s*(?:solve|solve\s+the\s+equation)\s*[:\-]?\s*",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    if "=" in equation_text:
        left_text, right_text = equation_text.split("=", 1)
        left, right = _expression(left_text), _expression(right_text)
        variables = sorted(left.free_symbols | right.free_symbols, key=str)
        if not variables:
            answer = bool(simplify(left - right) == 0)
            return {
                "steps": [
                    f"Evaluate both sides: {left} and {right}.",
                    "Compare the simplified values.",
                ],
                "final_answer": str(answer),
                "is_generic_template": False,
            }
        variable = variables[0]
        rearranged = simplify(left - right)
        solutions = solve(Eq(left, right), variable)
        return {
            "steps": [
                f"Parse the equation: {left} = {right}.",
                f"Move all terms to one side: {rearranged} = 0.",
                f"Solve symbolically for {variable}: {solutions}.",
            ],
            "final_answer": ", ".join(
                f"{variable} = {solution}" for solution in solutions
            )
            or "No solution found",
            "is_generic_template": False,
        }

    arithmetic = re.sub(
        r"^\s*(?:calculate|compute|simplify|evaluate)\s*[:\-]?\s*",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    expression = _expression(arithmetic)
    answer = simplify(expression)
    return {
        "steps": [
            f"Parse the expression: {expression}.",
            f"Simplify using symbolic arithmetic: {answer}.",
        ],
        "final_answer": str(answer),
        "is_generic_template": False,
    }


ESSAY_SCAFFOLDS = {
    "persuasive": [
        "What precise claim will your thesis defend?",
        "What evidence supports each reason?",
        "What is the strongest counterargument, and how will you address it?",
        "How will the conclusion reinforce the significance of your claim?",
    ],
    "compare_contrast": [
        "Which two subjects will you compare?",
        "Which consistent criteria will organize the comparison?",
        "What is the most important similarity and difference?",
        "What conclusion follows from the comparison?",
    ],
    "narrative": [
        "What central event or experience will the narrative explore?",
        "What conflict or turning point creates movement?",
        "Which concrete details establish setting and perspective?",
        "What reflection or change should the ending reveal?",
    ],
    "analytical": [
        "What text, event, or idea will you analyze?",
        "What interpretive thesis connects your observations?",
        "Which evidence supports each analytical point?",
        "How does each paragraph connect evidence back to the thesis?",
    ],
}


def _essay_type(prompt: str) -> str:
    normalized = prompt.casefold()
    if any(cue in normalized for cue in ("persuade", "argue", "position", "opinion")):
        return "persuasive"
    if any(cue in normalized for cue in ("compare", "contrast", "similarities", "differences")):
        return "compare_contrast"
    if any(cue in normalized for cue in ("narrative", "story", "experience")):
        return "narrative"
    return "analytical"


def help_with_essay(prompt: str) -> dict[str, Any]:
    essay_type = _essay_type(prompt)
    questions = ESSAY_SCAFFOLDS[essay_type]
    return {
        "steps": [
            f"Use this generic {essay_type.replace('_', '-')} essay structure:",
            "Introduction: establish context and state a focused thesis.",
            "Body paragraphs: develop one point per paragraph with evidence.",
            "Conclusion: synthesize the points without merely repeating them.",
            *questions,
        ],
        "final_answer": None,
        "is_generic_template": True,
    }
