"""Deterministic finite automaton for simplified shopping sessions."""
from dataclasses import dataclass
from typing import Iterable

BROWSE = "Browse"
VIEW = "View Product"
ADD = "Add to Cart"
REMOVE = "Remove from Cart"
CHECKOUT = "Checkout"
PURCHASE = "Purchase"
ABANDON = "Abandon"
ALPHABET = (BROWSE, VIEW, ADD, REMOVE, CHECKOUT, PURCHASE, ABANDON)
STATES = ("S0", "S1", "S2", "S3", "S4", "S5", "SD")
STATE_NAMES = {"S0":"Session started", "S1":"Product viewed", "S2":"Cart contains item", "S3":"Checkout started", "S4":"Purchase completed", "S5":"Session abandoned", "SD":"Invalid sequence"}
START_STATE = "S0"
ACCEPTING_STATES = frozenset({"S4"})

# Missing edges lead to SD. Terminal states stay terminal only for their matching event;
# any later event is an invalid continuation.
TRANSITIONS = {
    ("S0", BROWSE): "S0", ("S0", VIEW): "S1", ("S0", ABANDON): "S5",
    ("S1", BROWSE): "S1", ("S1", VIEW): "S1", ("S1", ADD): "S2", ("S1", ABANDON): "S5",
    ("S2", BROWSE): "S2", ("S2", VIEW): "S2", ("S2", ADD): "S2", ("S2", REMOVE): "S1", ("S2", CHECKOUT): "S3", ("S2", ABANDON): "S5",
    ("S3", PURCHASE): "S4", ("S3", ABANDON): "S5",
}

@dataclass
class DFAResult:
    actions: list[str]
    state_history: list[str]
    transitions: list[dict]
    final_state: str
    status: str
    accepted: bool

def transition(state: str, action: str) -> str:
    """Return the deterministic next state, using SD for unknown edges/actions."""
    return TRANSITIONS.get((state, action), "SD") if action in ALPHABET else "SD"

def process_actions(actions: Iterable[str]) -> DFAResult:
    sequence = list(actions)
    state, history, steps = START_STATE, [START_STATE], []
    for action in sequence:
        next_state = transition(state, action)
        steps.append({"previous_state": state, "action": action, "next_state": next_state,
                      "explanation": explain_transition(state, action, next_state)})
        state = next_state
        history.append(state)
    status = "invalid" if state == "SD" else "completed" if state == "S4" else "abandoned" if state == "S5" else "incomplete"
    return DFAResult(sequence, history, steps, state, status, state in ACCEPTING_STATES)

def explain_transition(previous: str, action: str, next_state: str) -> str:
    if next_state == "SD":
        return f"'{action}' is not allowed from {STATE_NAMES.get(previous, previous)}; the DFA enters its dead state."
    explanations = {
        ("S0", BROWSE): "The session is browsing the store.", ("S0", VIEW): "A product is viewed for the first time.",
        ("S0", ABANDON): "The visitor leaves without viewing a product.", ("S1", VIEW): "Another product is viewed; the viewed state remains.",
        ("S1", BROWSE): "Browsing continues before a cart is created.", ("S1", ADD): "An item is added to the cart.",
        ("S1", ABANDON): "The visitor leaves after viewing products.", ("S2", VIEW): "A product is viewed while the cart is retained.",
        ("S2", BROWSE): "Browsing continues with an item in the cart.", ("S2", ADD): "Another item is added; the cart remains non-empty.",
        ("S2", REMOVE): "The cart becomes empty; viewed-product history remains.", ("S2", CHECKOUT): "Checkout begins with a non-empty cart.",
        ("S2", ABANDON): "The visitor abandons a non-empty cart.", ("S3", PURCHASE): "The checkout completes; this is an accepting state.",
        ("S3", ABANDON): "The visitor leaves during checkout.",
    }
    return explanations.get((previous, action), f"The DFA moves to {STATE_NAMES[next_state]}.")

def classify_session(actions: Iterable[str]) -> str:
    return process_actions(actions).status
