from flask import session

def get_simulation():
    if "simulation" not in session:
        session["simulation"] = []
    return session["simulation"]

def add_trade(trade):
    sim = get_simulation()
    sim.append(trade)
    session["simulation"] = sim

def clear_simulation():
    session["simulation"] = []
