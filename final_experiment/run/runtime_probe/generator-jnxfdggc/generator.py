import sympy
import z3
import json,sys; r=json.load(sys.stdin); print(json.dumps([{'problem':'runtime probe','answer':0} for _ in range(r['count'])]))